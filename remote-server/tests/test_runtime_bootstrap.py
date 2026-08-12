from __future__ import annotations

from pathlib import Path

from app import runtime_bootstrap
from app.config import Settings


def test_runtime_bootstrap_generates_persistent_credentials(tmp_path, monkeypatch):
    runtime_file = tmp_path / "runtime.env"
    credentials_file = tmp_path / "credentials.txt"
    marker_file = tmp_path / ".first_start_pending"
    monkeypatch.setattr(runtime_bootstrap, "RUNTIME_FILE", runtime_file)
    monkeypatch.setattr(runtime_bootstrap, "CREDENTIALS_FILE", credentials_file)
    monkeypatch.setattr(runtime_bootstrap, "FIRST_START_MARKER", marker_file)
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:8800")

    assert runtime_bootstrap.ensure_runtime_config() is True
    first_runtime = runtime_file.read_text(encoding="utf-8")
    assert "SECRET_KEY=" in first_runtime
    assert "ADMIN_USERNAME=admin" in first_runtime
    assert "ADMIN_PASSWORD=" in first_runtime
    assert "http://localhost:8800/login" in credentials_file.read_text(encoding="utf-8")
    assert marker_file.exists()

    assert runtime_bootstrap.ensure_runtime_config() is False
    assert runtime_file.read_text(encoding="utf-8") == first_runtime


def test_settings_load_runtime_file(tmp_path, monkeypatch):
    runtime_file = tmp_path / "runtime.env"
    runtime_file.write_text(
        "SECRET_KEY=runtime-secret-key-that-is-more-than-32-characters\n"
        "ADMIN_USERNAME=runtime-admin\n"
        "ADMIN_PASSWORD=runtime-password-12345\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("RUNTIME_CONFIG_FILE", str(runtime_file))
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:8800")
    monkeypatch.setenv("ENVIRONMENT", "production")

    settings = Settings.from_env()
    settings.validate()
    assert settings.admin_username == "runtime-admin"
    assert settings.admin_password == "runtime-password-12345"
