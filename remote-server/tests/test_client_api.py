from __future__ import annotations

from sqlalchemy import select

from app.models import ActivityReport, AppAuthorization, SuspicionEvent


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
