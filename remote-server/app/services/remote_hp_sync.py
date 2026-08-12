from __future__ import annotations

from collections import defaultdict
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Any

from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Device,
    RemoteHpAccount,
    RemoteHpHandset,
    RemoteHpMobileClient,
    RemoteHpPlacement,
    RemoteHpUploadSession,
    WorkJob,
)
from app.schemas import RemoteHpInventorySyncRequest, RemoteHpSessionSyncRequest
from app.utils import as_utc, local_display, utcnow


def _clean(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(str(value).strip().split())
    return cleaned[:limit] or None


def sync_inventory(db: Session, server_device_id: int, payload: RemoteHpInventorySyncRequest) -> dict[str, int]:
    now = utcnow()
    db.execute(update(RemoteHpHandset).where(RemoteHpHandset.server_device_id == server_device_id).values(is_present=False, is_online=False))
    db.execute(update(RemoteHpAccount).where(RemoteHpAccount.server_device_id == server_device_id).values(is_present=False))
    db.execute(update(RemoteHpPlacement).where(RemoteHpPlacement.server_device_id == server_device_id).values(is_present=False))
    db.execute(update(RemoteHpMobileClient).where(RemoteHpMobileClient.server_device_id == server_device_id).values(is_present=False))

    handset_rows = db.scalars(select(RemoteHpHandset).where(RemoteHpHandset.server_device_id == server_device_id)).all()
    handset_map = {row.client_device_id: row for row in handset_rows}
    for item in payload.handsets:
        row = handset_map.get(item.client_device_id)
        if row is None:
            row = RemoteHpHandset(server_device_id=server_device_id, client_device_id=item.client_device_id, name=item.name)
            db.add(row)
            handset_map[item.client_device_id] = row
        row.name = _clean(item.name, 160) or f"HP #{item.client_device_id}"
        row.serial = _clean(item.serial, 255)
        row.stable_uid = _clean(item.stable_uid, 80)
        row.usb_serial = _clean(item.usb_serial, 255)
        row.wifi_endpoint = _clean(item.wifi_endpoint, 255)
        row.preferred_transport = _clean(item.preferred_transport, 16)
        row.active_transport = _clean(item.active_transport, 16)
        row.active_serial = _clean(item.active_serial, 255)
        row.label = _clean(item.label, 160)
        row.notes = (item.notes or "").strip()[:2000] or None
        row.is_present = True
        row.is_online = bool(item.online)
        row.local_created_at = as_utc(item.created_at)
        row.last_synced_at = now
    db.flush()

    account_rows = db.scalars(select(RemoteHpAccount).where(RemoteHpAccount.server_device_id == server_device_id)).all()
    account_map = {row.client_account_id: row for row in account_rows}
    for item in payload.accounts:
        row = account_map.get(item.client_account_id)
        if row is None:
            row = RemoteHpAccount(server_device_id=server_device_id, client_account_id=item.client_account_id, username=item.username)
            db.add(row)
            account_map[item.client_account_id] = row
        row.username = _clean(item.username, 255) or f"akun-{item.client_account_id}"
        row.notes = (item.notes or "").strip()[:2000] or None
        row.is_present = True
        row.local_created_at = as_utc(item.created_at)
        row.last_synced_at = now
    db.flush()

    placement_rows = db.scalars(select(RemoteHpPlacement).where(RemoteHpPlacement.server_device_id == server_device_id)).all()
    placement_map = {row.client_placement_id: row for row in placement_rows}
    accepted_placements = 0
    for item in payload.placements:
        account = account_map.get(item.client_account_id)
        handset = handset_map.get(item.client_device_id)
        if account is None or handset is None:
            continue
        row = placement_map.get(item.client_placement_id)
        if row is None:
            row = db.scalar(select(RemoteHpPlacement).where(RemoteHpPlacement.account_id == account.id, RemoteHpPlacement.handset_id == handset.id))
        if row is None:
            row = RemoteHpPlacement(
                server_device_id=server_device_id,
                client_placement_id=item.client_placement_id,
                account_id=account.id,
                handset_id=handset.id,
                app_slot=item.app_slot,
            )
            db.add(row)
            placement_map[item.client_placement_id] = row
        row.client_placement_id = item.client_placement_id
        row.account_id = account.id
        row.handset_id = handset.id
        row.app_slot = item.app_slot
        row.is_present = True
        row.local_created_at = as_utc(item.created_at)
        row.last_synced_at = now
        accepted_placements += 1

    mobile_rows = db.scalars(select(RemoteHpMobileClient).where(RemoteHpMobileClient.server_device_id == server_device_id)).all()
    mobile_map = {row.client_mobile_id: row for row in mobile_rows}
    accepted_mobile = 0
    for item in payload.mobile_clients:
        handset = handset_map.get(item.client_device_id)
        if handset is None:
            continue
        row = mobile_map.get(item.client_mobile_id)
        if row is None:
            row = RemoteHpMobileClient(
                server_device_id=server_device_id,
                client_mobile_id=item.client_mobile_id,
                handset_id=handset.id,
                display_name=item.display_name,
            )
            db.add(row)
            mobile_map[item.client_mobile_id] = row
        row.handset_id = handset.id
        row.display_name = _clean(item.display_name, 160) or f"Android #{item.client_mobile_id}"
        row.status = item.status
        row.app_version = _clean(item.app_version, 64)
        row.overlay_contract_version = _clean(item.overlay_contract_version, 32)
        row.paired_at = as_utc(item.paired_at)
        row.last_seen_at = as_utc(item.last_seen_at)
        row.is_present = True
        row.last_synced_at = now
        accepted_mobile += 1

    device = db.get(Device, server_device_id)
    if device is not None:
        device.last_seen_at = now
    db.commit()
    return {
        "handsets": len(payload.handsets),
        "accounts": len(payload.accounts),
        "placements": accepted_placements,
        "mobile_clients": accepted_mobile,
    }


def _placeholder_account(db: Session, server_device_id: int, client_account_id: int, username: str, now):
    row = db.scalar(select(RemoteHpAccount).where(
        RemoteHpAccount.server_device_id == server_device_id,
        RemoteHpAccount.client_account_id == client_account_id,
    ))
    if row is None:
        row = RemoteHpAccount(
            server_device_id=server_device_id,
            client_account_id=client_account_id,
            username=_clean(username, 255) or f"akun-{client_account_id}",
            is_present=True,
            last_synced_at=now,
        )
        db.add(row)
        db.flush()
    else:
        row.username = _clean(username, 255) or row.username
        row.is_present = True
        row.last_synced_at = now
    return row


def _placeholder_handset(db: Session, server_device_id: int, client_device_id: int, name: str, now):
    row = db.scalar(select(RemoteHpHandset).where(
        RemoteHpHandset.server_device_id == server_device_id,
        RemoteHpHandset.client_device_id == client_device_id,
    ))
    if row is None:
        row = RemoteHpHandset(
            server_device_id=server_device_id,
            client_device_id=client_device_id,
            name=_clean(name, 160) or f"HP #{client_device_id}",
            is_present=True,
            last_synced_at=now,
        )
        db.add(row)
        db.flush()
    else:
        row.name = _clean(name, 160) or row.name
        row.is_present = True
        row.last_synced_at = now
    return row


def _sync_work_job(db: Session, server_device_id: int, session: RemoteHpUploadSession) -> None:
    client_job_id = str(session.client_session_id)
    job = db.scalar(select(WorkJob).where(
        WorkJob.device_id == server_device_id,
        WorkJob.app_type == "remote_hp",
        WorkJob.client_job_id == client_job_id,
    ))
    if job is None:
        job = WorkJob(
            device_id=server_device_id,
            app_type="remote_hp",
            client_job_id=client_job_id,
            started_at=session.started_at or utcnow(),
            updated_at=session.last_synced_at,
        )
        db.add(job)
    status_map = {"active": "running", "finished": "completed", "cancelled": "cancelled", "failed": "failed", "pending": "running"}
    job.status = status_map.get(session.status, "running")
    job.planned_count = max(0, session.planned_count)
    job.completed_count = max(0, session.completed_count)
    job.failed_count = max(0, session.failed_count)
    job.progress_percent = min(100, int((job.completed_count / job.planned_count) * 100)) if job.planned_count else (100 if job.status == "completed" else 0)
    title_parts = [f"@{session.account.username}", session.handset.name]
    if session.batch_date:
        title_parts.append(session.batch_date.isoformat())
    job.title = " · ".join(title_parts)[:255]
    job.metadata_json = json.dumps({
        "source": "remote_hp_session_sync",
        "client_session_id": session.client_session_id,
        "account_username": session.account.username,
        "handset_name": session.handset.name,
        "app_slot": session.app_slot,
        "batch_date": session.batch_date.isoformat() if session.batch_date else None,
    }, ensure_ascii=False, separators=(",", ":"))
    if session.started_at is not None:
        job.started_at = session.started_at
    job.updated_at = session.last_synced_at
    job.finished_at = session.finished_at if job.status in {"completed", "cancelled", "failed"} else None


def sync_sessions(db: Session, server_device_id: int, payload: RemoteHpSessionSyncRequest) -> dict[str, int]:
    now = utcnow()
    accepted = created = updated_count = 0
    for item in payload.sessions:
        account = _placeholder_account(db, server_device_id, item.client_account_id, item.account_username, now)
        handset = _placeholder_handset(db, server_device_id, item.client_device_id, item.device_name, now)
        row = db.scalar(select(RemoteHpUploadSession).where(
            RemoteHpUploadSession.server_device_id == server_device_id,
            RemoteHpUploadSession.client_session_id == item.client_session_id,
        ))
        if row is None:
            row = RemoteHpUploadSession(
                server_device_id=server_device_id,
                client_session_id=item.client_session_id,
                account_id=account.id,
                handset_id=handset.id,
            )
            db.add(row)
            created += 1
        else:
            updated_count += 1
        row.account_id = account.id
        row.handset_id = handset.id
        row.app_slot = item.app_slot
        row.batch_date = item.batch_date
        row.status = item.status
        row.is_present = True
        row.planned_count = max(0, item.planned_count)
        row.completed_count = max(0, item.completed_count)
        row.failed_count = max(0, item.failed_count)
        row.folder_name = _clean(item.folder_name, 255)
        row.started_at = as_utc(item.started_at)
        row.finished_at = as_utc(item.finished_at)
        row.last_synced_at = now
        db.flush()
        _sync_work_job(db, server_device_id, row)
        accepted += 1
    device = db.get(Device, server_device_id)
    if device is not None:
        device.last_seen_at = now
    db.commit()
    return {"accepted": accepted, "created": created, "updated": updated_count}


def reconcile_sessions(db: Session, server_device_id: int, present_session_ids: list[int]) -> dict[str, int]:
    present = set(present_session_ids)
    rows = db.scalars(select(RemoteHpUploadSession).where(
        RemoteHpUploadSession.server_device_id == server_device_id
    )).all()
    hidden = restored = 0
    for row in rows:
        should_present = row.client_session_id in present
        if row.is_present and not should_present:
            row.is_present = False
            hidden += 1
            job = db.scalar(select(WorkJob).where(
                WorkJob.device_id == server_device_id,
                WorkJob.app_type == "remote_hp",
                WorkJob.client_job_id == str(row.client_session_id),
            ))
            if job is not None and job.status == "running":
                job.status = "cancelled"
                job.finished_at = utcnow()
                job.updated_at = utcnow()
        elif not row.is_present and should_present:
            row.is_present = True
            restored += 1
    db.commit()
    return {"present": len(present), "hidden": hidden, "restored": restored}


def remote_hp_summary(db: Session, server_device_id: int, *, batch_date: date | None = None, timezone_name: str = "Asia/Jakarta") -> dict[str, Any]:
    selected_date = batch_date or datetime.now(ZoneInfo(timezone_name)).date()
    base_h = RemoteHpHandset.server_device_id == server_device_id
    base_a = RemoteHpAccount.server_device_id == server_device_id
    handsets = int(db.scalar(select(func.count(RemoteHpHandset.id)).where(base_h, RemoteHpHandset.is_present.is_(True))) or 0)
    online = int(db.scalar(select(func.count(RemoteHpHandset.id)).where(base_h, RemoteHpHandset.is_present.is_(True), RemoteHpHandset.is_online.is_(True))) or 0)
    accounts = int(db.scalar(select(func.count(RemoteHpAccount.id)).where(base_a, RemoteHpAccount.is_present.is_(True))) or 0)
    placements = int(db.scalar(select(func.count(RemoteHpPlacement.id)).where(RemoteHpPlacement.server_device_id == server_device_id, RemoteHpPlacement.is_present.is_(True))) or 0)
    session_filter = [RemoteHpUploadSession.server_device_id == server_device_id, RemoteHpUploadSession.batch_date == selected_date, RemoteHpUploadSession.is_present.is_(True)]
    videos = int(db.scalar(select(func.coalesce(func.sum(RemoteHpUploadSession.completed_count), 0)).where(*session_filter)) or 0)
    completed_sessions = int(db.scalar(select(func.count(RemoteHpUploadSession.id)).where(*session_filter, RemoteHpUploadSession.status == "finished")) or 0)
    active_sessions = int(db.scalar(select(func.count(RemoteHpUploadSession.id)).where(RemoteHpUploadSession.server_device_id == server_device_id, RemoteHpUploadSession.status == "active", RemoteHpUploadSession.is_present.is_(True))) or 0)
    android_clients = int(db.scalar(select(func.count(RemoteHpMobileClient.id)).where(RemoteHpMobileClient.server_device_id == server_device_id, RemoteHpMobileClient.is_present.is_(True), RemoteHpMobileClient.status == "active")) or 0)
    android_online = int(db.scalar(select(func.count(RemoteHpMobileClient.id)).where(
        RemoteHpMobileClient.server_device_id == server_device_id,
        RemoteHpMobileClient.is_present.is_(True),
        RemoteHpMobileClient.status == "active",
        RemoteHpMobileClient.last_seen_at.is_not(None),
        RemoteHpMobileClient.last_seen_at >= func.datetime("now", "-2 minutes"),
    )) or 0)
    last_sync = db.scalar(select(func.max(RemoteHpHandset.last_synced_at)).where(base_h))
    return {
        "handsets": handsets,
        "online_handsets": online,
        "accounts": accounts,
        "placements": placements,
        "uploaded_videos": videos,
        "completed_sessions": completed_sessions,
        "active_sessions": active_sessions,
        "android_clients": android_clients,
        "android_online": android_online,
        "selected_date": selected_date,
        "last_synced_at": last_sync,
    }


def site_remote_hp_summary(db: Session, site_id: int | None = None) -> dict[str, int]:
    device_ids = select(Device.id)
    if site_id is not None:
        device_ids = device_ids.where(Device.site_id == site_id)
    ids = list(db.scalars(device_ids).all())
    if not ids:
        return {"remote_hp_handsets": 0, "remote_hp_online_handsets": 0, "remote_hp_accounts": 0, "remote_hp_android_clients": 0}
    return {
        "remote_hp_handsets": int(db.scalar(select(func.count(RemoteHpHandset.id)).where(RemoteHpHandset.server_device_id.in_(ids), RemoteHpHandset.is_present.is_(True))) or 0),
        "remote_hp_online_handsets": int(db.scalar(select(func.count(RemoteHpHandset.id)).where(RemoteHpHandset.server_device_id.in_(ids), RemoteHpHandset.is_present.is_(True), RemoteHpHandset.is_online.is_(True))) or 0),
        "remote_hp_accounts": int(db.scalar(select(func.count(RemoteHpAccount.id)).where(RemoteHpAccount.server_device_id.in_(ids), RemoteHpAccount.is_present.is_(True))) or 0),
        "remote_hp_android_clients": int(db.scalar(select(func.count(RemoteHpMobileClient.id)).where(RemoteHpMobileClient.server_device_id.in_(ids), RemoteHpMobileClient.is_present.is_(True), RemoteHpMobileClient.status == "active")) or 0),
    }



def remote_hp_batch_rows(db: Session, server_device_id: int, *, limit: int = 31) -> list[dict[str, Any]]:
    rows = db.execute(
        select(
            RemoteHpUploadSession.batch_date,
            func.count(RemoteHpUploadSession.id).label("session_count"),
            func.count(func.distinct(RemoteHpUploadSession.account_id)).label("account_count"),
            func.coalesce(func.sum(RemoteHpUploadSession.completed_count), 0).label("completed_count"),
            func.coalesce(func.sum(RemoteHpUploadSession.failed_count), 0).label("failed_count"),
            func.sum(case((RemoteHpUploadSession.status == "finished", 1), else_=0)).label("finished_count"),
            func.sum(case((RemoteHpUploadSession.status == "active", 1), else_=0)).label("active_count"),
        )
        .where(
            RemoteHpUploadSession.server_device_id == server_device_id,
            RemoteHpUploadSession.is_present.is_(True),
            RemoteHpUploadSession.batch_date.is_not(None),
        )
        .group_by(RemoteHpUploadSession.batch_date)
        .order_by(RemoteHpUploadSession.batch_date.desc())
        .limit(max(1, min(limit, 366)))
    ).all()
    return [
        {
            "batch_date": row.batch_date,
            "session_count": int(row.session_count or 0),
            "account_count": int(row.account_count or 0),
            "completed_count": int(row.completed_count or 0),
            "failed_count": int(row.failed_count or 0),
            "finished_count": int(row.finished_count or 0),
            "active_count": int(row.active_count or 0),
        }
        for row in rows
    ]

def remote_hp_handset_rows(db: Session, server_device_id: int) -> list[dict[str, Any]]:
    rows = db.scalars(select(RemoteHpHandset).where(
        RemoteHpHandset.server_device_id == server_device_id,
        RemoteHpHandset.is_present.is_(True),
    ).options(
        selectinload(RemoteHpHandset.placements).selectinload(RemoteHpPlacement.account),
        selectinload(RemoteHpHandset.mobile_clients),
    ).order_by(RemoteHpHandset.name)).all()
    now = utcnow()
    result = []
    for row in rows:
        mobile = []
        for client in row.mobile_clients:
            if not client.is_present or client.status != "active":
                continue
            seen = as_utc(client.last_seen_at)
            online = bool(seen and (now - seen).total_seconds() <= 120)
            mobile.append({
                "id": client.id,
                "display_name": client.display_name,
                "status": client.status,
                "app_version": client.app_version,
                "overlay_contract_version": client.overlay_contract_version,
                "last_seen_at": client.last_seen_at,
                "online": online,
            })
        result.append({
            "id": row.id,
            "client_device_id": row.client_device_id,
            "name": row.name,
            "label": row.label,
            "serial": row.serial,
            "stable_uid": row.stable_uid,
            "usb_serial": row.usb_serial,
            "wifi_endpoint": row.wifi_endpoint,
            "preferred_transport": row.preferred_transport or "auto",
            "active_transport": row.active_transport,
            "active_serial": row.active_serial,
            "is_online": row.is_online,
            "mobile_clients": mobile,
            "android_count": len(mobile),
            "android_online": sum(1 for client in mobile if client["online"]),
            "account_count": sum(1 for placement in row.placements if placement.is_present),
            "accounts": [placement.account.username for placement in row.placements if placement.is_present],
            "last_synced_at": row.last_synced_at,
        })
    return result


def remote_hp_account_date_rows(db: Session, server_device_id: int, selected_date: date, query_text: str = "", handset_id: int | None = None) -> list[dict[str, Any]]:
    stmt = select(RemoteHpAccount).where(
        RemoteHpAccount.server_device_id == server_device_id,
        RemoteHpAccount.is_present.is_(True),
    ).options(
        selectinload(RemoteHpAccount.placements).selectinload(RemoteHpPlacement.handset),
        selectinload(RemoteHpAccount.upload_sessions).selectinload(RemoteHpUploadSession.handset),
    ).order_by(RemoteHpAccount.username)
    if query_text.strip():
        stmt = stmt.where(RemoteHpAccount.username.ilike(f"%{query_text.strip()}%"))
    accounts = db.scalars(stmt).all()
    result = []
    for account in accounts:
        placements = [p for p in account.placements if p.is_present and (handset_id is None or p.handset_id == handset_id)]
        if handset_id is not None and not placements:
            continue
        sessions = [s for s in account.upload_sessions if s.is_present and s.batch_date == selected_date and (handset_id is None or s.handset_id == handset_id)]
        completed = sum(s.completed_count for s in sessions)
        planned = sum(s.planned_count for s in sessions)
        failed = sum(s.failed_count for s in sessions)
        statuses = {s.status for s in sessions}
        if not sessions:
            status = "not_started"
        elif "active" in statuses:
            status = "active"
        elif statuses == {"finished"}:
            status = "finished"
        elif "cancelled" in statuses:
            status = "cancelled"
        elif "failed" in statuses:
            status = "failed"
        else:
            status = ", ".join(sorted(statuses))
        result.append({
            "id": account.id,
            "client_account_id": account.client_account_id,
            "username": account.username,
            "placements": [{"handset_id": p.handset_id, "handset": p.handset.name, "slot": p.app_slot} for p in placements],
            "completed_count": completed,
            "planned_count": planned,
            "failed_count": failed,
            "status": status,
            "session_count": len(sessions),
            "last_sync": max((s.last_synced_at for s in sessions), default=account.last_synced_at),
        })
    return result


def remote_hp_session_history(
    db: Session,
    server_device_id: int,
    *,
    limit: int = 300,
    query_text: str = "",
    handset_id: int | None = None,
) -> list[dict[str, Any]]:
    stmt = select(RemoteHpUploadSession).join(RemoteHpUploadSession.account).where(
        RemoteHpUploadSession.server_device_id == server_device_id,
        RemoteHpUploadSession.is_present.is_(True),
    )
    if query_text.strip():
        stmt = stmt.where(RemoteHpAccount.username.ilike(f"%{query_text.strip()}%"))
    if handset_id is not None:
        stmt = stmt.where(RemoteHpUploadSession.handset_id == handset_id)
    rows = db.scalars(stmt.options(
        selectinload(RemoteHpUploadSession.account),
        selectinload(RemoteHpUploadSession.handset),
    ).order_by(
        RemoteHpUploadSession.batch_date.desc(), RemoteHpUploadSession.client_session_id.desc()
    ).limit(max(1, min(limit, 2000)))).all()
    return [{
        "client_session_id": row.client_session_id,
        "username": row.account.username,
        "handset": row.handset.name,
        "app_slot": row.app_slot,
        "batch_date": row.batch_date,
        "status": row.status,
        "planned_count": row.planned_count,
        "completed_count": row.completed_count,
        "failed_count": row.failed_count,
        "started_at": row.started_at,
        "finished_at": row.finished_at,
        "last_synced_at": row.last_synced_at,
    } for row in rows]
