from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import Base
from app.main import create_app
from app.models import ActivationKey, AdminUser
from app.security import hash_password
from app.utils import utcnow


@pytest.fixture()
def settings(tmp_path):
    return Settings(
        environment="testing",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        secret_key="test-secret-key-that-is-long-enough-for-signed-cookie",
        session_cookie_secure=False,
        session_timeout_seconds=900,
        heartbeat_interval_seconds=300,
        grace_period_hours=3,
        admin_username="admin",
        admin_password="testing-password-123",
        trusted_proxy_headers=False,
        data_dir=str(tmp_path),
    )


@pytest.fixture()
def app(settings):
    application = create_app(settings)
    Base.metadata.create_all(application.state.database.engine)
    with application.state.database.session_factory() as db:
        db.add(AdminUser(username="admin", password_hash=hash_password("testing-password-123")))
        db.commit()
    return application


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def activation_key(app):
    with app.state.database.session_factory() as db:
        key = ActivationKey(
            code="MX7K-QP2R",
            app_type="matrix_generator",
            status="pending",
            expires_at=utcnow() + timedelta(hours=24),
        )
        db.add(key)
        db.commit()
    return "MX7K-QP2R"


@pytest.fixture()
def activated(client, activation_key):
    response = client.post(
        "/api/v1/activate",
        json={
            "code": activation_key,
            "app_type": "matrix_generator",
            "fingerprint_hash": "a" * 64,
            "os_type": "linux",
            "os_info": "Ubuntu 24.04",
            "app_version": "1.7.0",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()
