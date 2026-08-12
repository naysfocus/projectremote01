from __future__ import annotations

import re


def login(client) -> str:
    response = client.post(
        "/login",
        data={"username": "admin", "password": "testing-password-123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match, response.text
    return match.group(1)


def test_dashboard_login_and_create_key(client):
    csrf = login(client)
    created = client.post(
        "/api/v1/activation-keys",
        headers={"X-CSRF-Token": csrf},
        json={"app_type": "remote_hp", "expires_in_hours": 1},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["ok"] is True
    assert body["key"]["app_type"] == "remote_hp"
    assert len(body["key"]["code"]) == 9

    listed = client.get("/api/v1/activation-keys")
    assert listed.status_code == 200
    assert listed.json()["keys"][0]["code"] == body["key"]["code"]


def test_admin_revoke_is_immediate(client, activated):
    csrf = login(client)
    token = activated["access_token"]
    opened = client.post(
        "/api/v1/session/open",
        headers={"Authorization": f"Bearer {token}"},
        json={"fingerprint_hash": "a" * 64, "app_version": "1.7.0"},
    )
    assert opened.status_code == 200
    device_id = activated["device_id"]

    revoked = client.post(
        f"/api/v1/devices/{device_id}/revoke",
        headers={"X-CSRF-Token": csrf},
        json={"app_type": "matrix_generator"},
    )
    assert revoked.status_code == 200

    heartbeat = client.post(
        "/api/v1/session/heartbeat",
        headers={"Authorization": f"Bearer {token}"},
        json={"session_id": opened.json()["session_id"]},
    )
    assert heartbeat.status_code == 403
    assert heartbeat.json()["status"] == "revoked"


def test_admin_write_requires_csrf(client):
    login(client)
    response = client.post(
        "/api/v1/activation-keys",
        json={"app_type": "remote_hp", "expires_in_hours": 1},
    )
    assert response.status_code == 403


def test_system_page(client):
    login(client)
    response = client.get("/system")
    assert response.status_code == 200
    assert "Status Sistem" in response.text
    assert "1.7" in response.text
    assert "SQLite" in response.text


def test_admin_can_change_password(client):
    csrf = login(client)
    response = client.post(
        "/account",
        data={
            "current_password": "testing-password-123",
            "new_password": "new-testing-password-456",
            "confirm_password": "new-testing-password-456",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login?password_changed=1"

    old_login = client.post(
        "/login",
        data={"username": "admin", "password": "testing-password-123"},
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/login",
        data={"username": "admin", "password": "new-testing-password-456"},
        follow_redirects=False,
    )
    assert new_login.status_code == 303


def test_password_change_invalidates_other_admin_session(app):
    from fastapi.testclient import TestClient

    first = TestClient(app)
    second = TestClient(app)
    try:
        csrf = login(first)
        login(second)
        response = first.post(
            "/account",
            data={
                "current_password": "testing-password-123",
                "new_password": "new-testing-password-789",
                "confirm_password": "new-testing-password-789",
                "csrf_token": csrf,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        invalidated = second.get("/dashboard", follow_redirects=False)
        assert invalidated.status_code == 303
        assert invalidated.headers["location"] == "/login"
    finally:
        first.close()
        second.close()


def test_activity_csv_export(client, activated):
    login(client)
    response = client.get("/exports/activity.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.content.startswith(b"\xef\xbb\xbf")


def test_readiness_check_is_available(client):
    csrf = login(client)
    response = client.post(
        "/system/readiness",
        data={"csrf_token": csrf},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Hasil uji kesiapan" in response.text
    assert "PERLU PERHATIAN" in response.text or "SIAP PRODUKSI" in response.text
