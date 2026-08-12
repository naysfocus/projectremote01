import os
import tempfile
import unittest

os.environ.setdefault("REMOTE_CLIENT_DATA_DIR", tempfile.mkdtemp(prefix="vmg-app-tests-"))

import app as application


class AppAccessTests(unittest.TestCase):
    def setUp(self):
        self.client = application.app.test_client()
        self.original_allowed = application.remote_server_client._allowed
        self.original_status = application.remote_server_client._status
        self.original_message = application.remote_server_client._message

    def tearDown(self):
        application.remote_server_client._allowed = self.original_allowed
        application.remote_server_client._status = self.original_status
        application.remote_server_client._message = self.original_message

    def test_health_is_public_before_activation(self):
        application.remote_server_client._allowed = False
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["version"], "1.22.1")

    def test_index_redirects_to_activation(self):
        application.remote_server_client._allowed = False
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/activation"))

    def test_api_is_locked_without_access(self):
        application.remote_server_client._allowed = False
        application.remote_server_client._status = "revoked"
        application.remote_server_client._message = "dicabut"
        response = self.client.get("/api/storage")
        self.assertEqual(response.status_code, 423)
        self.assertEqual(response.get_json()["remote_auth_status"], "revoked")

    def test_index_is_available_when_allowed(self):
        application.remote_server_client._allowed = True
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Video Mixer", response.data)


if __name__ == "__main__":
    unittest.main()
