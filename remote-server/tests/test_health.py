from app.config import Settings


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "service": "remote-server", "version": "1.7"}


def test_readiness(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "service": "remote-server",
        "version": "1.7",
        "database": "ready",
    }


def test_cookie_secure_auto(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "auto")
    settings = Settings.from_env()
    assert settings.session_cookie_secure is True

    monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:8000")
    settings = Settings.from_env()
    assert settings.session_cookie_secure is False


def test_dynamic_cookie_secure_flag(client):
    https_response = client.post(
        "/login",
        data={"username": "admin", "password": "testing-password-123"},
        headers={"X-Forwarded-Proto": "https"},
        follow_redirects=False,
    )
    assert https_response.status_code == 303
    assert "secure" in https_response.headers.get("set-cookie", "").lower()


def test_dynamic_cookie_allows_http_recovery(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "testing-password-123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "secure" not in response.headers.get("set-cookie", "").lower()
