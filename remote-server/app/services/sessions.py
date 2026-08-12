from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AppAuthorization, Device, Heartbeat, SuspicionEvent
from app.services.common import add_outbox
from app.utils import as_utc, utcnow


class SessionResult:
    def __init__(self, status: str, status_code: int, session_id: str | None = None):
        self.status = status
        self.status_code = status_code
        self.session_id = session_id


def open_session(
    db: Session,
    authorization: AppAuthorization,
    *,
    fingerprint_hash: str,
    app_version: str,
    request_ip: str,
    settings: Settings,
) -> SessionResult:
    now = utcnow()
    authorization_id = authorization.id

    # The bearer dependency performs a read first. End that transaction, then
    # acquire SQLite's write lock before checking the session slot again. This
    # makes two simultaneous /session/open requests serialize correctly.
    db.rollback()
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))
    authorization = db.get(AppAuthorization, authorization_id)
    if authorization is None:
        return SessionResult("invalid_access_token", 401)
    if authorization.status == "revoked":
        db.rollback()
        return SessionResult("revoked", 403)

    last_seen = as_utc(authorization.session_last_seen_at)
    session_is_live = bool(
        authorization.session_id
        and last_seen
        and now - last_seen <= timedelta(seconds=settings.session_timeout_seconds)
    )
    if session_is_live:
        event = SuspicionEvent(
            device_id=authorization.device_id,
            app_type=authorization.app_type,
            existing_session_started_at=authorization.session_started_at,
            rejected_request_ip=request_ip,
        )
        db.add(event)
        db.flush()
        device = db.get(Device, authorization.device_id)
        add_outbox(
            db,
            "session_conflict",
            {
                "suspicion_event_id": event.id,
                "device_id": authorization.device_id,
                "label": (device.label if device else None) or f"Device #{authorization.device_id}",
                "app_type": authorization.app_type,
                "detected_at": now.isoformat(),
                "request_ip": request_ip,
            },
        )
        db.commit()
        return SessionResult("session_conflict", 409)

    new_session_id = str(uuid.uuid4())
    authorization.session_id = new_session_id
    authorization.session_started_at = now
    authorization.session_last_seen_at = now
    authorization.session_ip = request_ip
    authorization.app_version = app_version
    device = db.get(Device, authorization.device_id)
    if device is not None:
        device.last_seen_at = now
        if fingerprint_hash and not device.fingerprint_hash:
            device.fingerprint_hash = fingerprint_hash
    db.add(Heartbeat(device_id=authorization.device_id, app_type=authorization.app_type, received_at=now))
    db.commit()
    return SessionResult("active", 200, new_session_id)


def heartbeat(
    db: Session,
    authorization: AppAuthorization,
    session_id: str,
) -> SessionResult:
    now = utcnow()
    if authorization.status == "revoked":
        return SessionResult("revoked", 403)
    if not authorization.session_id or authorization.session_id != session_id:
        return SessionResult("session_superseded", 409)

    authorization.session_last_seen_at = now
    device = db.get(Device, authorization.device_id)
    if device is not None:
        device.last_seen_at = now
    db.add(Heartbeat(device_id=authorization.device_id, app_type=authorization.app_type, received_at=now))
    db.commit()
    return SessionResult("active", 200, session_id)


def close_session(db: Session, authorization: AppAuthorization, session_id: str) -> SessionResult:
    if authorization.status == "revoked":
        return SessionResult("revoked", 403)
    if not authorization.session_id or authorization.session_id != session_id:
        return SessionResult("session_superseded", 409)
    authorization.session_id = None
    authorization.session_started_at = None
    authorization.session_last_seen_at = None
    authorization.session_ip = None
    db.commit()
    return SessionResult("closed", 200)
