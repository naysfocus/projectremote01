from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from database import db
from services import remote_hp_data_sync as sync
from services import remote_server_client as client_module


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {"ok": True}

    def json(self):
        return self._body


class RemoteHpDataSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.temp.name) / "remote_hp.db")
        conn = sqlite3.connect(db.DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(Path(db.SCHEMA_PATH).read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO devices (id,name,serial,label,notes,created_at) VALUES (1,?,?,?,?,?)",
            ("HP Utama", "SERIAL-1", "Jakarta-A", "catatan-rahasia-hp", "2026-08-01 00:00:00"),
        )
        conn.execute(
            "INSERT INTO accounts (id,username,email,password,phone,notes,created_at) VALUES (10,?,?,?,?,?,?)",
            (
                "akun.tes",
                "private@example.test",
                "password-sangat-rahasia",
                "+628111111111",
                "catatan-rahasia-akun",
                "2026-08-01 00:00:00",
            ),
        )
        conn.execute(
            "INSERT INTO account_placements (id,account_id,device_id,app_slot,created_at) VALUES (100,10,1,'original','2026-08-01 00:00:00')"
        )
        conn.execute(
            "INSERT INTO mobile_clients (id,device_id,app_device_uuid,display_name,token_hash,token_prefix,status,paired_at,last_seen_at,app_version,overlay_contract_version) "
            "VALUES (900,1,'android-unit-test','Android Operator','hash-rahasia-token','rhp1_xxxxxx','active','2026-08-07T14:00:00+00:00','2026-08-07T14:01:00+00:00','1.0.0','1.0')"
        )
        conn.execute(
            "INSERT INTO upload_sessions (id,account_id,device_id,folder_path,subfolder,policy,batch_date,status,started_at) "
            "VALUES (501,10,1,'D:/Video/Rahasia Klien','batch-01',24,'2026-08-06','active','2026-08-06 01:00:00')"
        )
        for index in range(8):
            conn.execute(
                "INSERT INTO uploaded_videos (session_id,account_id,filename,filepath,batch_date) VALUES (501,10,?,?,?)",
                (f"rahasia-{index}.mp4", f"D:/Video/Rahasia Klien/rahasia-{index}.mp4", "2026-08-06"),
            )
        conn.commit()
        conn.close()

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        self.temp.cleanup()

    def test_inventory_is_privacy_safe_and_reports_online_hp(self):
        with patch.object(sync.adb, "get_online_serials", return_value={"SERIAL-1"}):
            payload, digest = sync.build_inventory_snapshot()

        self.assertEqual(len(digest), 64)
        self.assertEqual(payload["handsets"][0]["name"], "HP Utama")
        self.assertTrue(payload["handsets"][0]["online"])
        self.assertEqual(payload["accounts"][0]["username"], "akun.tes")
        self.assertEqual(payload["mobile_clients"][0]["display_name"], "Android Operator")
        self.assertEqual(payload["mobile_clients"][0]["client_device_id"], 1)
        self.assertEqual(payload["mobile_clients"][0]["app_version"], "1.0.0")
        serialized = json.dumps(payload, ensure_ascii=False)
        for secret in (
            "private@example.test",
            "password-sangat-rahasia",
            "+628111111111",
            "catatan-rahasia-akun",
            "catatan-rahasia-hp",
            "hash-rahasia-token",
            "rhp1_xxxxxx",
        ):
            self.assertNotIn(secret, serialized)
        self.assertNotIn("password", payload["accounts"][0])
        self.assertNotIn("email", payload["accounts"][0])
        self.assertNotIn("phone", payload["accounts"][0])
        self.assertNotIn("notes", payload["accounts"][0])

    def test_upload_snapshot_contains_account_date_and_counts_not_file_details(self):
        rows, digest = sync.build_session_rows()
        self.assertEqual(len(digest), 64)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["client_session_id"], 501)
        self.assertEqual(row["account_username"], "akun.tes")
        self.assertEqual(row["batch_date"], "2026-08-06")
        self.assertEqual(row["planned_count"], 24)
        self.assertEqual(row["completed_count"], 8)
        self.assertEqual(row["folder_name"], "batch-01")
        serialized = json.dumps(rows, ensure_ascii=False)
        self.assertNotIn("rahasia-0.mp4", serialized)
        self.assertNotIn("D:/Video/Rahasia Klien", serialized)
        self.assertEqual(sync.session_reconcile_payload(rows)["present_session_ids"], [501])

    def test_deleted_local_history_can_reconcile_with_empty_id_list(self):
        conn = sqlite3.connect(db.DB_PATH)
        conn.execute("DELETE FROM upload_sessions")
        conn.commit()
        conn.close()
        rows, _ = sync.build_session_rows()
        self.assertEqual(rows, [])
        self.assertEqual(sync.session_reconcile_payload(rows)["present_session_ids"], [])


class RemoteHpClientTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_xdg = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = self.temp.name

    def tearDown(self):
        if self.old_xdg is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = self.old_xdg
        self.temp.cleanup()

    def test_full_sync_posts_inventory_sessions_and_reconciliation(self):
        client = client_module.RemoteServerClient("https://remote.example.test", register_atexit=False)
        client._config.update({
            "access_token": "rh_live_" + "x" * 40,
            "last_full_reconcile_at": None,
            "inventory_digest": None,
            "session_digest": None,
        })
        client._status = "active"
        client._allowed = True
        client.request_data_sync(force=True)
        calls = []

        def post(url, **kwargs):
            calls.append((url, kwargs.get("json")))
            return FakeResponse(200, {"ok": True})

        client._http.post = post
        inventory = ({
            "snapshot_id": "inventory-12345678",
            "synced_at": "2026-08-06T14:00:00+00:00",
            "handsets": [],
            "accounts": [],
            "placements": [],
        }, "inventory-digest")
        rows = ([{
            "client_session_id": 501,
            "client_account_id": 10,
            "client_device_id": 1,
            "account_username": "akun.tes",
            "device_name": "HP Utama",
            "app_slot": "original",
            "batch_date": "2026-08-06",
            "status": "active",
            "planned_count": 24,
            "completed_count": 8,
            "failed_count": 0,
            "folder_name": "batch-01",
            "started_at": "2026-08-06T01:00:00+00:00",
            "finished_at": None,
        }], "session-digest")

        with patch.object(client_module, "build_inventory_snapshot", return_value=inventory), \
             patch.object(client_module, "build_session_rows", return_value=rows):
            client._sync_remote_hp_data()

        paths = [url.removeprefix("https://remote.example.test") for url, _ in calls]
        self.assertEqual(paths, [
            "/api/v1/remote-hp/inventory-sync",
            "/api/v1/remote-hp/session-sync",
            "/api/v1/remote-hp/session-reconcile",
        ])
        self.assertEqual(calls[-1][1]["present_session_ids"], [501])
        saved = client.store.load()
        self.assertEqual(saved["inventory_digest"], "inventory-digest")
        self.assertEqual(saved["session_digest"], "session-digest")
        self.assertTrue(saved["last_data_sync_at"])
        self.assertEqual(saved["last_data_sync_error"], "")

    def test_incremental_progress_sends_only_changed_session_without_reconcile(self):
        client = client_module.RemoteServerClient("https://remote.example.test", register_atexit=False)
        client._config.update({
            "access_token": "rh_live_" + "x" * 40,
            "last_full_reconcile_at": "2026-08-06T14:00:00+00:00",
            "inventory_digest": "same-inventory",
            "session_digest": "full-session-digest",
        })
        client._status = "active"
        client._allowed = True
        client.request_data_sync(session_id=501)
        calls = []

        def post(url, **kwargs):
            calls.append((url, kwargs.get("json")))
            return FakeResponse(200, {"ok": True})

        client._http.post = post
        row = {
            "client_session_id": 501,
            "client_account_id": 10,
            "client_device_id": 1,
            "account_username": "akun.tes",
            "device_name": "HP Utama",
            "app_slot": "original",
            "batch_date": "2026-08-06",
            "status": "active",
            "planned_count": 24,
            "completed_count": 9,
            "failed_count": 0,
            "folder_name": "batch-01",
            "started_at": "2026-08-06T01:00:00+00:00",
            "finished_at": None,
        }

        def build_rows(ids=None):
            self.assertEqual(ids, {501})
            return [row], "incremental-digest"

        with patch.object(client_module, "utcnow", return_value=client_module.parse_datetime("2026-08-06T15:00:00+00:00")), \
             patch.object(client_module, "build_inventory_snapshot", return_value=({
                 "snapshot_id": "inventory-12345678",
                 "synced_at": "2026-08-06T15:00:00+00:00",
                 "handsets": [], "accounts": [], "placements": [],
             }, "same-inventory")), \
             patch.object(client_module, "build_session_rows", side_effect=build_rows):
            client._sync_remote_hp_data()

        paths = [url.removeprefix("https://remote.example.test") for url, _ in calls]
        self.assertEqual(paths, ["/api/v1/remote-hp/session-sync"])
        self.assertEqual(calls[0][1]["sessions"][0]["completed_count"], 9)

    def test_sync_failure_is_queued_without_blocking_application(self):
        client = client_module.RemoteServerClient("https://remote.example.test", register_atexit=False)
        client._config.update({"access_token": "rh_live_" + "x" * 40})
        client._status = "active"
        client._allowed = True
        client.request_data_sync(force=True)
        client._http.post = lambda *args, **kwargs: FakeResponse(500, {"ok": False, "error": "temporary"})
        inventory = ({
            "snapshot_id": "inventory-12345678",
            "synced_at": "2026-08-06T14:00:00+00:00",
            "handsets": [],
            "accounts": [],
            "placements": [],
        }, "inventory-digest")
        with patch.object(client_module, "build_inventory_snapshot", return_value=inventory):
            client._sync_remote_hp_data()
        self.assertTrue(client.is_allowed())
        self.assertTrue(client._data_sync_requested.is_set())
        self.assertIn("inventory_sync_http_500", client.store.load()["last_data_sync_error"])


if __name__ == "__main__":
    unittest.main()
