from __future__ import annotations

import re

from app.integration_store import decrypt_secret
from app.models import IntegrationConfig


def login(client) -> str:
    response = client.post(
        "/login",
        data={"username": "admin", "password": "testing-password-123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match
    return match.group(1)


def test_integrations_page_is_web_managed(client):
    login(client)
    response = client.get("/integrations")
    assert response.status_code == 200
    assert "Telegram Bot" in response.text
    assert "Cloudflare Tunnel" in response.text
    assert "volume Docker persisten" in response.text
    assert "Tidak perlu mengedit" in response.text


def test_save_telegram_encrypts_token_and_creates_pair_code(client, app, monkeypatch):
    csrf = login(client)
    monkeypatch.setattr(
        "app.web.routes.telegram_get_me",
        lambda token: {"id": 123, "username": "remote_test_bot"},
    )
    token = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi"
    response = client.post(
        "/integrations/telegram/save",
        data={
            "token": token,
            "admin_id": "",
            "enabled": "on",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    with app.state.database.session_factory() as db:
        config = db.get(IntegrationConfig, 1)
        assert config is not None
        assert config.telegram_enabled is True
        assert config.telegram_token_encrypted
        assert token not in config.telegram_token_encrypted
        assert decrypt_secret(app.state.settings, config.telegram_token_encrypted) == token
        assert config.telegram_bot_username == "remote_test_bot"
        assert config.telegram_pair_code and len(config.telegram_pair_code) == 8


def test_save_cloudflare_encrypts_token(client, app):
    csrf = login(client)
    token = "eyJ" + "a" * 120
    response = client.post(
        "/integrations/cloudflare/save",
        data={
            "token": token,
            "public_base_url": "server.example.com",
            "protocol": "auto",
            "enabled": "on",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    with app.state.database.session_factory() as db:
        config = db.get(IntegrationConfig, 1)
        assert config is not None
        assert config.cloudflare_enabled is True
        assert config.public_base_url == "https://server.example.com"
        assert config.cloudflare_protocol == "auto"
        assert token not in config.cloudflare_token_encrypted
        assert decrypt_secret(app.state.settings, config.cloudflare_token_encrypted) == token


def test_cloudflare_accepts_full_docker_command_and_blank_hostname(client, app):
    csrf = login(client)
    token = "eyJ" + "b" * 120
    command = f"docker run cloudflare/cloudflared:latest tunnel run --token {token}"
    response = client.post(
        "/integrations/cloudflare/save",
        data={
            "token": command,
            "public_base_url": "",
            "protocol": "http2",
            "enabled": "on",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    with app.state.database.session_factory() as db:
        config = db.get(IntegrationConfig, 1)
        assert config is not None
        assert config.cloudflare_enabled is True
        assert config.cloudflare_protocol == "http2"
        assert decrypt_secret(app.state.settings, config.cloudflare_token_encrypted) == token


def test_cloudflare_rejects_invalid_hostname(client):
    csrf = login(client)
    response = client.post(
        "/integrations/cloudflare/save",
        data={
            "token": "eyJ" + "a" * 120,
            "public_base_url": "not a valid hostname/path",
            "protocol": "auto",
            "enabled": "on",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/integrations?error=")


def test_activation_page_uses_fixed_one_hour(client):
    csrf = login(client)
    response = client.post(
        "/activation-keys",
        data={"app_type": "matrix_generator", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/activation-keys?created=")


def test_cloudflare_token_redaction():
    from app.integration_store import redact_sensitive

    telegram = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi"
    cloudflare = "eyJ" + "z" * 120
    result = redact_sensitive(f"POST /bot{telegram}/getUpdates token={cloudflare}")
    assert telegram not in result
    assert cloudflare not in result
