import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


from database import db
from services import device_connection as connection


class WirelessAdbMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp.name, "remote_hp.db")

    def tearDown(self):
        db.DB_PATH = self.old_path
        self.temp.cleanup()

    def _legacy_database(self, serial):
        conn = sqlite3.connect(db.DB_PATH)
        conn.executescript(
            """
            CREATE TABLE devices (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              serial TEXT,
              label TEXT,
              notes TEXT,
              created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
            """
        )
        conn.execute(
            "INSERT INTO devices (id,name,serial,label,notes) VALUES (1,'HP 1',?,'📱','tetap')",
            (serial,),
        )
        conn.commit()
        conn.close()

    def test_usb_legacy_serial_becomes_transport_without_changing_device_row(self):
        self._legacy_database("USB-SERIAL-ABC")
        db._migrate()
        row = db.query("SELECT * FROM devices WHERE id=1", one=True)
        self.assertEqual(row["id"], 1)
        self.assertEqual(row["name"], "HP 1")
        self.assertEqual(row["serial"], "USB-SERIAL-ABC")
        self.assertEqual(row["usb_serial"], "USB-SERIAL-ABC")
        self.assertIsNone(row["wifi_endpoint"])
        self.assertTrue(row["stable_uid"])
        self.assertEqual(row["preferred_transport"], "auto")

    def test_wifi_legacy_serial_becomes_endpoint_without_new_device_identity(self):
        self._legacy_database("192.168.1.50:37123")
        db._migrate()
        row = db.query("SELECT * FROM devices WHERE id=1", one=True)
        stable_uid = row["stable_uid"]
        self.assertEqual(row["wifi_endpoint"], "192.168.1.50:37123")
        self.assertIsNone(row["usb_serial"])
        # Idempotent restart: UID tidak boleh berubah.
        db._migrate()
        again = db.query("SELECT * FROM devices WHERE id=1", one=True)
        self.assertEqual(again["stable_uid"], stable_uid)
        self.assertEqual(again["id"], 1)

    def test_v148_operational_rows_survive_init_db(self):
        conn = sqlite3.connect(db.DB_PATH)
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE devices (
              id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, serial TEXT,
              label TEXT, notes TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE accounts (
              id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, email TEXT,
              password TEXT, phone TEXT, notes TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE account_placements (
              id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL,
              device_id INTEGER NOT NULL, app_slot TEXT NOT NULL DEFAULT 'original',
              created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE,
              FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
            );
            CREATE TABLE upload_sessions (
              id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL,
              device_id INTEGER NOT NULL, folder_path TEXT NOT NULL, subfolder TEXT NOT NULL,
              policy INTEGER NOT NULL, batch_date TEXT, status TEXT DEFAULT 'pending',
              started_at DATETIME DEFAULT CURRENT_TIMESTAMP, finished_at DATETIME,
              FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE,
              FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
            );
            CREATE TABLE uploaded_videos (
              id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL,
              account_id INTEGER NOT NULL, filename TEXT NOT NULL, filepath TEXT NOT NULL,
              file_hash TEXT, batch_date TEXT, uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(session_id) REFERENCES upload_sessions(id) ON DELETE CASCADE,
              FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );
            CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
            INSERT INTO devices (id,name,serial) VALUES (1,'HP Produksi','USB-PROD-1');
            INSERT INTO accounts (id,username) VALUES (1,'akun.produksi');
            INSERT INTO account_placements (id,account_id,device_id,app_slot) VALUES (1,1,1,'original');
            INSERT INTO upload_sessions (id,account_id,device_id,folder_path,subfolder,policy,batch_date,status)
              VALUES (1,1,1,'video-1','batch-01',24,'2026-08-07','finished');
            INSERT INTO uploaded_videos (id,session_id,account_id,filename,filepath,batch_date)
              VALUES (1,1,1,'video01.mp4','video-1/batch-01/video01.mp4','2026-08-07');
            """
        )
        conn.commit()
        conn.close()

        db.init_db()

        self.assertEqual(db.query("SELECT COUNT(*) AS n FROM devices", one=True)["n"], 1)
        self.assertEqual(db.query("SELECT COUNT(*) AS n FROM accounts", one=True)["n"], 1)
        self.assertEqual(db.query("SELECT COUNT(*) AS n FROM account_placements", one=True)["n"], 1)
        self.assertEqual(db.query("SELECT COUNT(*) AS n FROM upload_sessions", one=True)["n"], 1)
        self.assertEqual(db.query("SELECT COUNT(*) AS n FROM uploaded_videos", one=True)["n"], 1)
        device = db.query("SELECT * FROM devices WHERE id = 1", one=True)
        self.assertEqual(device["usb_serial"], "USB-PROD-1")
        self.assertTrue(device["stable_uid"])



class TransportResolutionTests(unittest.TestCase):
    def _device(self, preference="auto"):
        return {
            "id": 1,
            "serial": "USB-1",
            "usb_serial": "USB-1",
            "wifi_endpoint": "192.168.1.20:37123",
            "preferred_transport": preference,
            "wifi_auto_reconnect": 1,
            "stable_uid": "stable-1",
            "last_transport": None,
            "last_usb_seen_at": None,
            "last_wifi_seen_at": None,
        }

    def test_auto_prefers_wifi_when_both_are_online(self):
        state = connection.connection_snapshot(
            self._device("auto"), {"USB-1", "192.168.1.20:37123"}
        )
        self.assertEqual(state["active_transport"], "wifi")
        self.assertEqual(state["active_serial"], "192.168.1.20:37123")

    def test_wifi_preference_falls_back_to_usb(self):
        state = connection.connection_snapshot(self._device("wifi"), {"USB-1"})
        self.assertEqual(state["active_transport"], "usb")
        self.assertEqual(state["active_serial"], "USB-1")

    def test_usb_preference_wins_when_both_are_online(self):
        state = connection.connection_snapshot(
            self._device("usb"), {"USB-1", "192.168.1.20:37123"}
        )
        self.assertEqual(state["active_transport"], "usb")

    def test_no_online_transport_returns_offline_without_guessing(self):
        state = connection.connection_snapshot(self._device("auto"), set())
        self.assertFalse(state["online"])
        self.assertIsNone(state["active_serial"])
        self.assertIsNone(state["active_transport"])


class WirelessReconnectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp.name, "remote_hp.db")
        conn = sqlite3.connect(db.DB_PATH)
        with open(db.SCHEMA_PATH, encoding="utf-8") as schema_file:
            conn.executescript(schema_file.read())
        conn.execute(
            """INSERT INTO devices
               (id,name,serial,stable_uid,usb_serial,wifi_endpoint,preferred_transport,wifi_auto_reconnect)
               VALUES (1,'HP 1','USB-1','stable-1','USB-1','192.168.1.20:37123','auto',1)"""
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        db.DB_PATH = self.old_path
        self.temp.cleanup()

    def test_reconnect_keeps_usb_serial_and_identity(self):
        device = db.query("SELECT * FROM devices WHERE id=1", one=True)
        with patch.object(connection.adb, "connect_wifi", return_value={"ok": True, "ip_port": "192.168.1.20:37123"}):
            result = connection.reconnect_device(device)
        self.assertTrue(result["ok"])
        row = db.query("SELECT * FROM devices WHERE id=1", one=True)
        self.assertEqual(row["stable_uid"], "stable-1")
        self.assertEqual(row["usb_serial"], "USB-1")
        self.assertEqual(row["wifi_endpoint"], "192.168.1.20:37123")
        self.assertEqual(row["serial"], "USB-1")
        self.assertEqual(row["last_transport"], "wifi")

    def test_manager_does_not_scan_and_only_reconnects_saved_endpoint(self):
        manager = connection.WirelessAdbManager(interval=30, backoff=60)
        calls = []
        with patch.object(connection.adb, "get_online_serials", return_value=set()), \
             patch.object(connection.adb, "connect_wifi", side_effect=lambda endpoint: calls.append(endpoint) or {"ok": False}):
            manager.run_once()
        self.assertEqual(calls, ["192.168.1.20:37123"])


if __name__ == "__main__":
    unittest.main()
