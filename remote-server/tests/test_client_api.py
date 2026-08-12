from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.models import ActivationKey, ActivityReport, AppAuthorization, SuspicionEvent
from app.utils import utcnow


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_activation_consumes_key_and_hashes_token(app, activated):
    token = activated["access_token"]
    assert token.startswith("mx_live_")
    with app.state.database.session_factory() as db:
        authorization = db.scalar(select(AppAuthorization))
        assert authorization is not None
        assert authorization.access_token_hash != token
        assert token not in authorization.access_token_hash


def test_reactivation_with_new_code_reissues_token_for_same_device(app, client, activated):
    """v1.1 regression test.

    Scenario: client loses its locally stored token (e.g. it could not be
    decrypted after a Windows restart) but the device fingerprint is
    unchanged. An admin issues a fresh activation code for the same
    app_type. This must succeed and hand back a *new* working token instead
    of failing with already_activated -- while the old token is invalidated
    and no duplicate AppAuthorization row is created.
    """
    old_token = activated["access_token"]
    same_fingerprint = "a" * 64

    with app.state.database.session_factory() as db:
        key = ActivationKey(
            code="RE7Q-2ZKM",
            app_type="matrix_generator",
            status="pending",
            expires_at=utcnow() + timedelta(hours=1),
        )
        db.add(key)
        db.commit()

    response = client.post(
        "/api/v1/activate",
        json={
            "code": "RE7Q-2ZKM",
            "app_type": "matrix_generator",
            "fingerprint_hash": same_fingerprint,
            "os_type": "linux",
            "os_info": "Ubuntu 24.04",
            "app_version": "1.7.0",
        },
    )
    assert response.status_code == 200, response.text
    new_token = response.json()["access_token"]
    assert new_token != old_token

    with app.state.database.session_factory() as db:
        authorizations = db.scalars(select(AppAuthorization)).all()
        # Reissue must reuse the existing row (unique device_id+app_type),
        # not create a second row for the same device.
        assert len(authorizations) == 1
        assert authorizations[0].status == "active"

    # The old token must no longer work.
    stale = client.post(
        "/api/v1/session/open",
        headers=auth_header(old_token),
        json={"fingerprint_hash": same_fingerprint, "app_version": "1.7.0"},
    )
    assert stale.status_code == 401

    # The new token must work.
    fresh = client.post(
        "/api/v1/session/open",
        headers=auth_header(new_token),
        json={"fingerprint_hash": same_fingerprint, "app_version": "1.7.0"},
    )
    assert fresh.status_code == 200, fresh.text


def test_session_lock_heartbeat_close_and_reopen(client, app, activated):
    token = activated["access_token"]
    headers = auth_header(token)
    payload = {"fingerprint_hash": "a" * 64, "app_version": "1.7.0"}

    first = client.post("/api/v1/session/open", headers=headers, json=payload)
    assert first.status_code == 200, first.text
    session_id = first.json()["session_id"]
    assert first.json()["heartbeat_interval_seconds"] == 300

    conflict = client.post("/api/v1/session/open", headers=headers, json=payload)
    assert conflict.status_code == 409
    assert conflict.json()["status"] == "session_conflict"
    with app.state.database.session_factory() as db:
        assert len(db.scalars(select(SuspicionEvent)).all()) == 1

    heartbeat = client.post(
        "/api/v1/session/heartbeat", headers=headers, json={"session_id": session_id}
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["status"] == "active"

    closed = client.post("/api/v1/session/close", headers=headers, json={"session_id": session_id})
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"

    reopened = client.post("/api/v1/session/open", headers=headers, json=payload)
    assert reopened.status_code == 200
    assert reopened.json()["session_id"] != session_id


def test_report_is_idempotent(client, app, activated):
    token = activated["access_token"]
    headers = auth_header(token)
    report = {
        "client_report_id": "report-0001",
        "event_type": "generate_completed",
        "occurred_at": "2026-08-04T09:12:00+07:00",
        "summary": {
            "mode": "horizontal",
            "video_count": 48,
            "duration_seconds": 812,
            "run_tag": "20260804_091200",
        },
    }
    first = client.post("/api/v1/report", headers=headers, json={"reports": [report]})
    assert first.status_code == 200, first.text
    assert first.json()["accepted"] == 1
    assert first.json()["duplicates"] == 0

    retry = client.post("/api/v1/report", headers=headers, json={"reports": [report]})
    assert retry.status_code == 200
    assert retry.json()["accepted"] == 0
    assert retry.json()["duplicates"] == 1
    with app.state.database.session_factory() as db:
        assert len(db.scalars(select(ActivityReport)).all()) == 1


def test_invalid_report_shape_is_rejected(client, activated):
    response = client.post(
        "/api/v1/report",
        headers=auth_header(activated["access_token"]),
        json={
            "reports": [
                {
                    "client_report_id": "bad-report",
                    "event_type": "generate_completed",
                    "occurred_at": "2026-08-04T09:12:00+07:00",
                    "summary": {"video_count": 1},
                }
            ]
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_generate_summary"


def test_simultaneous_session_open_is_atomic(app, settings, activated):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from app.services.sessions import open_session

    with app.state.database.session_factory() as db:
        authorization_id = db.scalar(select(AppAuthorization.id))
    assert authorization_id is not None
    barrier = Barrier(2)

    def worker(ip: str) -> int:
        with app.state.database.session_factory() as db:
            authorization = db.get(AppAuthorization, authorization_id)
            assert authorization is not None
            barrier.wait(timeout=5)
            return open_session(
                db,
                authorization,
                fingerprint_hash="a" * 64,
                app_version="1.7.0",
                request_ip=ip,
                settings=settings,
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = sorted(executor.map(worker, ["10.0.0.1", "10.0.0.2"]))
    assert statuses == [200, 409]
