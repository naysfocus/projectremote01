import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("REMOTE_CLIENT_DATA_DIR", tempfile.mkdtemp(prefix="vmg-cross-platform-"))

from services import remote_server_client as module


class CrossPlatformComposeTests(unittest.TestCase):
    def test_default_compose_has_no_mandatory_linux_devices(self):
        compose = Path("docker-compose.yml").read_text(encoding="utf-8")
        self.assertNotIn("/dev/dri:/dev/dri", compose)
        self.assertNotIn("/etc/machine-id", compose)
        self.assertIn('127.0.0.1:5000:5000', compose)

    def test_gpu_override_keeps_linux_vaapi_support(self):
        compose = Path("docker-compose.gpu.yml").read_text(encoding="utf-8")
        self.assertIn("/dev/dri:/dev/dri", compose)
        self.assertIn("RENDER_GID", compose)

    def test_persistent_host_id_is_stable(self):
        with tempfile.TemporaryDirectory() as temp:
            old = os.environ.get("REMOTE_CLIENT_DATA_DIR")
            os.environ["REMOTE_CLIENT_DATA_DIR"] = temp
            try:
                first = module._persistent_host_id()
                second = module._persistent_host_id()
                self.assertEqual(first, second)
                self.assertTrue((Path(temp) / "host-id").exists())
            finally:
                if old is None:
                    os.environ.pop("REMOTE_CLIENT_DATA_DIR", None)
                else:
                    os.environ["REMOTE_CLIENT_DATA_DIR"] = old


if __name__ == "__main__":
    unittest.main()
