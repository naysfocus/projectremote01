from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import db
from services import pairing


class MobilePairingV150Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        self.old_secret_file = os.environ.get("REMOTE_HP_PAIRING_SECRET_FILE")
        db.DB_PATH = str(Path(self.temp.name) / "remote_hp.db")
        os.environ["REMOTE_HP_PAIRING_SECRET_FILE"] = str(Path(self.temp.name) / "pairing.secret")
        pairing.clear_auth_cache()
        db.init_db()
        db.execute(
            "INSERT INTO devices (name,serial,stable_uid,usb_serial,preferred_transport) VALUES (?,?,?,?,?)",
            ("HP Pair", "USB-PAIR", "stable-pair", "USB-PAIR", "auto"),
        )

    def tearDown(self):
        pairing.clear_auth_cache()
        db.DB_PATH = self.old_db_path
        if self.old_secret_file is None:
            os.environ.pop("REMOTE_HP_PAIRING_SECRET_FILE", None)
        else:
            os.environ["REMOTE_HP_PAIRING_SECRET_FILE"] = self.old_secret_file
        self.temp.cleanup()

    def test_pairing_code_is_one_time_and_bearer_is_hashed(self):
        created = pairing.create_pairing_code(1, 10)
        code = created["pairing"]["code"]
        self.assertEqual(len(code), 9)  # XXXX-XXXX
        result = pairing.pair_mobile_client(code, "android-uuid-0001", "Android Operator", "1.0.0")
        token = result["token"]
        self.assertTrue(token.startswith("rhp1_"))
        row = db.query("SELECT * FROM mobile_clients WHERE id=?", (result["client"]["id"],), one=True)
        self.assertNotEqual(row["token_hash"], token)
        self.assertEqual(row["token_hash"], pairing.token_hash(token))
        self.assertEqual(row["overlay_contract_version"], "1.0")
        auth = pairing.authenticate_bearer(f"Bearer {token}")
        self.assertEqual(auth["device_id"], 1)
        with self.assertRaises(pairing.PairingError) as ctx:
            pairing.pair_mobile_client(code, "android-uuid-0002", "Android Kedua", "1.0.0")
        self.assertEqual(ctx.exception.status_code, 409)

    def test_revoke_invalidates_mobile_token(self):
        code = pairing.create_pairing_code(1)["pairing"]["code"]
        result = pairing.pair_mobile_client(code, "android-uuid-0003", "Android Revoked", "1.0.0")
        token = result["token"]
        pairing.revoke_client(result["client"]["id"])
        with self.assertRaises(pairing.PairingError) as ctx:
            pairing.authenticate_bearer(f"Bearer {token}")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_pairing_status_never_exposes_plain_code_or_token(self):
        created = pairing.create_pairing_code(1)
        plain_code = created["pairing"]["code"]
        status = pairing.pairing_status()
        rendered = str(status)
        self.assertNotIn(plain_code, rendered)
        self.assertEqual(status["contract"]["overlay_ux_contract"], "1.0")
        self.assertTrue(status["contract"]["trusted_lan_only"])


if __name__ == "__main__":
    unittest.main()
