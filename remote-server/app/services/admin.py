from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.models import ActivationKey, ActivityReport, AdminUser, AppAuthorization, Device, Site, SuspicionEvent, WorkJob
from app.security import generate_activation_code
from app.services.common import add_audit
from app.utils import as_utc, iso, local_display, local_day_bounds, utcnow
from app.services.operations import operation_summary
from app.services.remote_hp_sync import remote_hp_summary, site_remote_hp_summary


def create_activation_key(
    db: Session,
    *,
    app_type: str,
    expires_in_hours: int,
    admin: AdminUser | None = None,
    telegram_id: str | None = None,
) -> ActivationKey:
    for _ in range(10):
        code = generate_activation_code()
        if db.scalar(select(ActivationKey.id).where(ActivationKey.code == code)) is None:
            break
    else:
        raise RuntimeError("Could not generate a unique activation code.")
    key = ActivationKey(
        code=code,
        app_type=app_type,
        expires_at=utcnow() + timedelta(hours=expires_in_hours),
        created_by_admin_id=admin.id if admin else None,
        created_by_telegram_id=telegram_id,
    )
    db.add(key)
    add_audit(
        db,
        actor_type="admin" if admin else "telegram",
        actor_id=str(admin.id) if admin else telegram_id,
        action="activation_key.created",
        target_type="activation_key",
        target_id=code,
        metadata={"app_type": app_type, "expires_in_hours": expires_in_hours},
    )
    db.commit()
    db.refresh(key)
    return key


def expire_pending_keys(db: Session) -> int:
    now = utcnow()
    rows = db.scalars(select(ActivationKey).where(ActivationKey.status == "pending")).all()
    changed = 0
    for key in rows:
        expires_at = as_utc(key.expires_at)
        if expires_at and expires_at <= now:
            key.status = "expired"
            changed += 1
    if changed:
        db.commit()
    return changed


def _serialize_devices(
    db: Session,
    devices: list[Device],
    settings: Settings,
) -> list[dict[str, Any]]:
    now = utcnow()
    ids = [device.id for device in devices]
    pending_counts: dict[int, int] = {}
    if ids:
        pending_counts = dict(
            db.execute(
                select(SuspicionEvent.device_id, func.count(SuspicionEvent.id))
                .where(
                    SuspicionEvent.admin_reviewed.is_(False),
                    SuspicionEvent.device_id.in_(ids),
                )
                .group_by(SuspicionEvent.device_id)
            ).all()
        )
    result: list[dict[str, Any]] = []
    for device in devices:
        auths: list[dict[str, Any]] = []
        any_online = False
        for auth in device.authorizations:
            last_seen = as_utc(auth.session_last_seen_at)
            is_online = bool(
                auth.status == "active"
                and auth.session_id
                and last_seen
                and (now - last_seen).total_seconds() <= settings.session_timeout_seconds
            )
            any_online = any_online or is_online
            auths.append(
                {
                    "app_type": auth.app_type,
                    "status": auth.status,
                    "app_version": auth.app_version,
                    "is_online": is_online,
                    "session_started_at": iso(auth.session_started_at),
                    "session_last_seen_at": iso(auth.session_last_seen_at),
                }
            )
        result.append(
            {
                "id": device.id,
                "label": device.label or f"Device #{device.id}",
                "fingerprint_masked": f"{device.fingerprint_hash[:8]}…{device.fingerprint_hash[-6:]}",
                "os_type": device.os_type,
                "os_info": device.os_info,
                "first_seen_at": local_display(device.first_seen_at, device.site.timezone_name if device.site else settings.display_timezone),
                "last_seen_at": local_display(device.last_seen_at, device.site.timezone_name if device.site else settings.display_timezone),
                "notes": device.notes,
                "site_id": device.site_id,
                "site_name": device.site.name if device.site else None,
                "timezone_name": device.site.timezone_name if device.site else settings.display_timezone,
                "tags": [tag.name for tag in device.tags],
                "is_online": any_online,
                "authorizations": auths,
                "unreviewed_suspicion_count": int(pending_counts.get(device.id, 0)),
            }
        )
    return result


def list_devices_page(
    db: Session,
    settings: Settings,
    *,
    query: str = "",
    app_type: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 50,
    site_id: int | None = None,
) -> tuple[list[dict[str, Any]], int]:
    page = max(1, page)
    page_size = min(max(page_size, 10), 100)
    conditions = []
    query = query.strip()
    if query:
        pattern = f"%{query}%"
        conditions.append(
            or_(
                Device.label.ilike(pattern),
                Device.os_type.ilike(pattern),
                Device.os_info.ilike(pattern),
                Device.fingerprint_hash.ilike(pattern),
            )
        )
    if app_type in {"matrix_generator", "remote_hp"}:
        conditions.append(
            Device.authorizations.any(AppAuthorization.app_type == app_type)
        )
    if site_id is not None:
        conditions.append(Device.site_id == site_id)
    if status == "revoked":
        conditions.append(Device.authorizations.any(AppAuthorization.status == "revoked"))
    elif status == "active":
        conditions.append(Device.authorizations.any(AppAuthorization.status == "active"))

    count_stmt = select(func.count(Device.id))
    data_stmt = select(Device).options(selectinload(Device.authorizations), selectinload(Device.site), selectinload(Device.tags)).order_by(Device.id.desc())
    if conditions:
        count_stmt = count_stmt.where(*conditions)
        data_stmt = data_stmt.where(*conditions)
    total = int(db.scalar(count_stmt) or 0)
    devices = db.scalars(data_stmt.offset((page - 1) * page_size).limit(page_size)).all()
    rows = _serialize_devices(db, list(devices), settings)
    if status in {"online", "offline"}:
        expected = status == "online"
        rows = [row for row in rows if row["is_online"] is expected]
        # Online state is time-derived; total here reflects the filtered page rather than all rows.
        total = len(rows) if page == 1 and len(rows) < page_size else total
    return rows, total


def list_devices(db: Session, settings: Settings) -> list[dict[str, Any]]:
    rows, _ = list_devices_page(db, settings, page=1, page_size=100)
    return rows


def get_device_detail(db: Session, device_id: int, settings: Settings) -> dict[str, Any] | None:
    device = db.scalar(
        select(Device).where(Device.id == device_id).options(selectinload(Device.authorizations), selectinload(Device.site), selectinload(Device.tags))
    )
    if device is None:
        return None
    entry = _serialize_devices(db, [device], settings)[0]
    entry["remote_hp"] = remote_hp_summary(db, device_id, timezone_name=entry["timezone_name"])
    suspicions = db.scalars(
        select(SuspicionEvent)
        .where(SuspicionEvent.device_id == device_id)
        .order_by(SuspicionEvent.detected_at.desc())
        .limit(20)
    ).all()
    entry["suspicion_events"] = [
        {
            "id": event.id,
            "app_type": event.app_type,
            "detected_at": local_display(event.detected_at, entry["timezone_name"]),
            "request_ip": event.rejected_request_ip,
            "admin_reviewed": event.admin_reviewed,
            "admin_action": event.admin_action,
        }
        for event in suspicions
    ]
    return entry


def set_authorization_status(
    db: Session,
    *,
    device_id: int,
    app_type: str,
    status: str,
    actor_type: str,
    actor_id: str | None,
) -> AppAuthorization | None:
    auth = db.scalar(
        select(AppAuthorization).where(
            AppAuthorization.device_id == device_id,
            AppAuthorization.app_type == app_type,
        )
    )
    if auth is None:
        return None
    auth.status = status
    if status == "revoked":
        auth.revoked_at = utcnow()
        auth.session_id = None
        auth.session_started_at = None
        auth.session_last_seen_at = None
        auth.session_ip = None
    else:
        auth.revoked_at = None
    add_audit(
        db,
        actor_type=actor_type,
        actor_id=actor_id,
        action=f"authorization.{status}",
        target_type="device_app",
        target_id=f"{device_id}:{app_type}",
    )
    db.commit()
    return auth


def review_suspicion(
    db: Session,
    *,
    event_id: int,
    action: str,
    admin: AdminUser | None = None,
    telegram_id: str | None = None,
) -> SuspicionEvent | None:
    event = db.get(SuspicionEvent, event_id)
    if event is None:
        return None
    event.admin_reviewed = True
    event.admin_action = action
    event.reviewed_at = utcnow()
    event.reviewed_by_admin_id = admin.id if admin else None
    actor_type = "admin" if admin else "telegram"
    actor_id = str(admin.id) if admin else telegram_id
    add_audit(
        db,
        actor_type=actor_type,
        actor_id=actor_id,
        action=f"suspicion.{action}",
        target_type="suspicion_event",
        target_id=str(event.id),
    )
    if action == "revoked":
        auth = db.scalar(
            select(AppAuthorization).where(
                AppAuthorization.device_id == event.device_id,
                AppAuthorization.app_type == event.app_type,
            )
        )
        if auth is not None:
            auth.status = "revoked"
            auth.revoked_at = utcnow()
            auth.session_id = None
            auth.session_started_at = None
            auth.session_last_seen_at = None
            auth.session_ip = None
    db.commit()
    return event


def stats_summary(db: Session, settings: Settings, site_id: int | None = None) -> dict[str, Any]:
    now = utcnow()
    total_stmt = select(func.count(Device.id))
    if site_id is not None:
        total_stmt = total_stmt.where(Device.site_id == site_id)
    total_devices = int(db.scalar(total_stmt) or 0)
    auth_stmt = select(AppAuthorization).join(Device, Device.id == AppAuthorization.device_id).where(AppAuthorization.status == "active")
    if site_id is not None:
        auth_stmt = auth_stmt.where(Device.site_id == site_id)
    active_authorizations = db.scalars(auth_stmt).all()
    online_sessions = 0
    for auth in active_authorizations:
        last_seen = as_utc(auth.session_last_seen_at)
        if auth.session_id and last_seen and (now - last_seen).total_seconds() <= settings.session_timeout_seconds:
            online_sessions += 1
    suspicion_stmt = select(func.count(SuspicionEvent.id)).join(Device, Device.id == SuspicionEvent.device_id).where(SuspicionEvent.admin_reviewed.is_(False))
    if site_id is not None:
        suspicion_stmt = suspicion_stmt.where(Device.site_id == site_id)
    timezone_name = settings.display_timezone
    if site_id is not None:
        site = db.get(Site, site_id)
        if site is not None:
            timezone_name = site.timezone_name
    operations = operation_summary(db, timezone_name=timezone_name, site_id=site_id)
    remote_hp_inventory = site_remote_hp_summary(db, site_id=site_id)
    return {
        "total_devices": total_devices,
        "active_authorizations": len(active_authorizations),
        "online_sessions": online_sessions,
        "unreviewed_suspicion_events": int(db.scalar(suspicion_stmt) or 0),
        "date": now.date().isoformat(),
        **operations,
        **remote_hp_inventory,
    }
