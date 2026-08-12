from __future__ import annotations

import os
import secrets
import string
from datetime import datetime, timezone
from pathlib import Path

RUNTIME_FILE = Path(os.getenv("RUNTIME_CONFIG_FILE", "/data/runtime.env"))
CREDENTIALS_FILE = Path(os.getenv("INITIAL_CREDENTIALS_FILE", "/data/INITIAL_ADMIN_CREDENTIALS.txt"))
FIRST_START_MARKER = Path(os.getenv("FIRST_START_MARKER_FILE", "/data/.first_start_pending"))


def _random_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _write_private(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)


def ensure_runtime_config() -> bool:
    """Create persistent runtime secrets once. Returns True on first creation."""
    RUNTIME_FILE.parent.mkdir(parents=True, exist_ok=True)
    if RUNTIME_FILE.exists():
        RUNTIME_FILE.chmod(0o600)
        return False

    secret_key = os.getenv("SECRET_KEY") or secrets.token_urlsafe(48)
    admin_username = os.getenv("ADMIN_USERNAME", "admin").strip() or "admin"
    admin_password = os.getenv("ADMIN_PASSWORD") or _random_password()
    public_base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8800").rstrip("/")

    _write_private(
        RUNTIME_FILE,
        "\n".join(
            [
                f"SECRET_KEY={secret_key}",
                f"ADMIN_USERNAME={admin_username}",
                f"ADMIN_PASSWORD={admin_password}",
                "",
            ]
        ),
    )
    created_at = datetime.now(timezone.utc).isoformat()
    _write_private(
        CREDENTIALS_FILE,
        "\n".join(
            [
                "Remote Server - Kredensial Awal",
                "=================================",
                f"Dibuat: {created_at}",
                f"Alamat: {public_base_url}/login",
                f"Username: {admin_username}",
                f"Password: {admin_password}",
                "",
                "Segera ubah password melalui menu Akun setelah login.",
                "",
            ]
        ),
    )
    _write_private(FIRST_START_MARKER, "1\n")
    return True


def main() -> None:
    ensure_runtime_config()


if __name__ == "__main__":
    main()
