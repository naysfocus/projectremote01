import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

import requests

from services import remote_server_client as module


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


class RemoteServerClientTests(unittest.TestCase):
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

    def make_client(self):
        return module.RemoteServerClient("https://remote.example.test", register_atexit=False)

    def test_fingerprint_is_sha256(self):
        value = module.fingerprint_hash()
        self.assertEqual(len(value), 64)
        int(value, 16)

    def test_activation_opens_session_and_persists_token(self):
        client = self.make_client()

        def post(url, **kwargs):
            if url.endswith("/activate"):
                return FakeResponse(200, {"ok": True, "access_token": "rh_live_" + "x" * 40, "device_id": 9})
            if url.endswith("/session/open"):
                return FakeResponse(200, {
                    "ok": True,
                    "status": "active",
                    "session_id": "7f460824-7fd8-47bd-ab1b-b9060f9f2390",
                    "grace_period_hours": 3,
                    "heartbeat_interval_seconds": 300,
                    "session_timeout_seconds": 900,
                })
            raise AssertionError(url)

        client._http.post = post
        result = client.activate("ABCD-EFGH")
        self.assertTrue(result["ok"])
        status = client.public_status()
        self.assertTrue(status["allowed"])
        self.assertEqual(status["status"], "active")
        self.assertEqual(status["device_id"], 9)
        self.assertTrue(client.store.load().get("access_token", "").startswith("rh_live_"))

    def test_saved_session_is_resumed_before_opening_new_one(self):
        client = self.make_client()
        client._config.update({
            "access_token": "rh_live_" + "x" * 40,
            "session_id": "7f460824-7fd8-47bd-ab1b-b9060f9f2390",
        })
        client.store.save(client._config)
        calls = []

        def post(url, **kwargs):
            calls.append(url)
            return FakeResponse(200, {"ok": True, "status": "active"})

        client._http.post = post
        result = client.connect()
        self.assertTrue(result["ok"])
        session_calls = [url for url in calls if "/session/" in url]
        self.assertEqual(len(session_calls), 1)
        self.assertTrue(session_calls[0].endswith("/session/heartbeat"))

    def test_network_failure_uses_grace_after_prior_success(self):
        client = self.make_client()
        client._config.update({
            "access_token": "rh_live_" + "x" * 40,
            "session_id": "7f460824-7fd8-47bd-ab1b-b9060f9f2390",
            "last_success_at": datetime.now(timezone.utc).isoformat(),
            "grace_period_hours": 3,
        })
        client.store.save(client._config)
        client._http.post = Mock(side_effect=requests.ConnectionError("offline"))
        result = client.connect()
        self.assertTrue(result["ok"])
        self.assertEqual(client.public_status()["status"], "grace")
        self.assertTrue(client.public_status()["allowed"])

    def test_explicit_revoke_never_uses_grace(self):
        client = self.make_client()
        client._config.update({
            "access_token": "rh_live_" + "x" * 40,
            "session_id": "7f460824-7fd8-47bd-ab1b-b9060f9f2390",
            "last_success_at": datetime.now(timezone.utc).isoformat(),
            "grace_period_hours": 3,
        })
        client.store.save(client._config)
        client._http.post = Mock(return_value=FakeResponse(403, {"ok": False, "status": "revoked"}))
        result = client.connect()
        self.assertFalse(result["ok"])
        self.assertEqual(client.public_status()["status"], "revoked")
        self.assertFalse(client.public_status()["allowed"])

    def test_report_queue_is_idempotent_and_flushes(self):
        client = self.make_client()
        client._config.update({"access_token": "rh_live_" + "x" * 40})
        client._status = "active"
        client._allowed = True
        client.queue_report("upload_session_completed", {"video_count": 24})
        self.assertEqual(client.reports.count(), 1)
        client._http.post = Mock(return_value=FakeResponse(200, {"ok": True, "accepted": 1, "duplicates": 0}))
        client._flush_reports()
        self.assertEqual(client.reports.count(), 0)


if __name__ == "__main__":
    unittest.main()
