import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

import requests

os.environ.setdefault("REMOTE_CLIENT_DATA_DIR", tempfile.mkdtemp(prefix="vmg-client-tests-"))

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
        self.old_dir = os.environ.get("REMOTE_CLIENT_DATA_DIR")
        os.environ["REMOTE_CLIENT_DATA_DIR"] = self.temp.name

    def tearDown(self):
        if self.old_dir is None:
            os.environ.pop("REMOTE_CLIENT_DATA_DIR", None)
        else:
            os.environ["REMOTE_CLIENT_DATA_DIR"] = self.old_dir
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
                payload = kwargs["json"]
                self.assertEqual(payload["app_type"], "matrix_generator")
                self.assertEqual(payload["app_version"], "1.22.1")
                return FakeResponse(200, {"ok": True, "access_token": "mx_live_" + "x" * 40, "device_id": 9})
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
        self.assertTrue(client.public_status()["allowed"])
        self.assertTrue(client.store.load()["access_token"].startswith("mx_live_"))

    def test_network_failure_uses_grace_after_success(self):
        client = self.make_client()
        client._config.update({
            "access_token": "mx_live_" + "x" * 40,
            "session_id": "7f460824-7fd8-47bd-ab1b-b9060f9f2390",
            "last_success_at": datetime.now(timezone.utc).isoformat(),
            "grace_period_hours": 3,
        })
        client.store.save(client._config)
        client._http.post = Mock(side_effect=requests.ConnectionError("offline"))
        result = client.connect()
        self.assertTrue(result["ok"])
        self.assertEqual(client.public_status()["status"], "grace")

    def test_revoke_never_uses_grace(self):
        client = self.make_client()
        client._config.update({
            "access_token": "mx_live_" + "x" * 40,
            "session_id": "7f460824-7fd8-47bd-ab1b-b9060f9f2390",
            "last_success_at": datetime.now(timezone.utc).isoformat(),
        })
        client.store.save(client._config)
        client._http.post = Mock(return_value=FakeResponse(403, {"status": "revoked"}))
        result = client.connect()
        self.assertFalse(result["ok"])
        self.assertFalse(client.public_status()["allowed"])
        self.assertEqual(client.public_status()["status"], "revoked")

    def test_valid_generate_report_flushes(self):
        client = self.make_client()
        client._config.update({"access_token": "mx_live_" + "x" * 40})
        client._status = "active"
        client._allowed = True
        client.queue_report("generate_completed", {
            "mode": "horizontal",
            "video_count": 12,
            "duration_seconds": 45.2,
            "run_tag": "20260805_100000",
        })
        self.assertEqual(client.reports.count(), 1)
        client._http.post = Mock(return_value=FakeResponse(200, {"ok": True, "accepted": 1, "duplicates": 0}))
        client._flush_reports()
        self.assertEqual(client.reports.count(), 0)


if __name__ == "__main__":
    unittest.main()
