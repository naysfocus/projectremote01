from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_admin, require_csrf
from app.models import ActivationKey, ActivityReport, AdminUser, Device, SuspicionEvent
from app.schemas import (
    ActivationKeyCreateRequest,
    DeviceUpdateRequest,
    RevokeRequest,
    SuspicionReviewRequest,
)
from app.services.admin import (
    create_activation_key,
    expire_pending_keys,
    get_device_detail,
    list_devices_page,
    review_suspicion,
    set_authorization_status,
    stats_summary,
)
from app.utils import iso

router = APIRouter(prefix="/api/v1", tags=["admin"])


@router.get("/devices")
def devices(
    request: Request,
    q: str = "",
    app_type: str = "",
    status: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=10, le=100),
    _admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows, total = list_devices_page(
        db,
        request.app.state.settings,
        query=q,
        app_type=app_type,
        status=status,
        page=page,
        page_size=page_size,
    )
    return {
        "ok": True,
        "devices": rows,
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


@router.get("/devices/{device_id}")
def device_detail(
    device_id: int,
    request: Request,
    _admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = get_device_detail(db, device_id, request.app.state.settings)
    if data is None:
        raise HTTPException(status_code=404, detail="device_not_found")
    return {"ok": True, "device": data}


@router.get("/devices/{device_id}/reports")
def device_reports(
    device_id: int,
    app_type: str | None = None,
    event_type: str | None = None,
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    _admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.get(Device, device_id) is None:
        raise HTTPException(status_code=404, detail="device_not_found")
    stmt = select(ActivityReport).where(ActivityReport.device_id == device_id)
    if app_type:
        stmt = stmt.where(ActivityReport.app_type == app_type)
    if event_type:
        stmt = stmt.where(ActivityReport.event_type == event_type)
    if date_from:
        stmt = stmt.where(ActivityReport.occurred_at >= date_from)
    if date_to:
        stmt = stmt.where(ActivityReport.occurred_at <= date_to)
    rows = db.scalars(stmt.order_by(ActivityReport.occurred_at.desc()).limit(500)).all()
    return {
        "ok": True,
        "reports": [
            {
                "id": row.id,
                "app_type": row.app_type,
                "event_type": row.event_type,
                "occurred_at": iso(row.occurred_at),
                "received_at": iso(row.received_at),
                "summary": json.loads(row.summary_json),
                "client_report_id": row.client_report_id,
            }
            for row in rows
        ],
    }


@router.patch("/devices/{device_id}", dependencies=[Depends(require_csrf)])
def update_device(
    device_id: int,
    payload: DeviceUpdateRequest,
    _admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="device_not_found")
    if payload.label is not None:
        device.label = payload.label.strip() or None
    if payload.notes is not None:
        device.notes = payload.notes.strip() or None
    db.commit()
    return {"ok": True}


@router.post("/devices/{device_id}/revoke", dependencies=[Depends(require_csrf)])
def revoke_device(
    device_id: int,
    payload: RevokeRequest,
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    auth = set_authorization_status(
        db,
        device_id=device_id,
        app_type=payload.app_type,
        status="revoked",
        actor_type="admin",
        actor_id=str(admin.id),
    )
    if auth is None:
        raise HTTPException(status_code=404, detail="authorization_not_found")
    return {"ok": True, "status": "revoked"}


@router.post("/devices/{device_id}/reactivate", dependencies=[Depends(require_csrf)])
def reactivate_device(
    device_id: int,
    payload: RevokeRequest,
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    auth = set_authorization_status(
        db,
        device_id=device_id,
        app_type=payload.app_type,
        status="active",
        actor_type="admin",
        actor_id=str(admin.id),
    )
    if auth is None:
        raise HTTPException(status_code=404, detail="authorization_not_found")
    return {"ok": True, "status": "active"}


@router.get("/suspicion-events")
def suspicion_events(
    reviewed: bool | None = None,
    _admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stmt = select(SuspicionEvent)
    if reviewed is not None:
        stmt = stmt.where(SuspicionEvent.admin_reviewed.is_(reviewed))
    rows = db.scalars(stmt.order_by(SuspicionEvent.detected_at.desc()).limit(500)).all()
    return {
        "ok": True,
        "events": [
            {
                "id": row.id,
                "device_id": row.device_id,
                "app_type": row.app_type,
                "detected_at": iso(row.detected_at),
                "existing_session_started_at": iso(row.existing_session_started_at),
                "rejected_request_ip": row.rejected_request_ip,
                "admin_reviewed": row.admin_reviewed,
                "admin_action": row.admin_action,
            }
            for row in rows
        ],
    }


@router.post("/suspicion-events/{event_id}/review", dependencies=[Depends(require_csrf)])
def review_event(
    event_id: int,
    payload: SuspicionReviewRequest,
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    event = review_suspicion(db, event_id=event_id, action=payload.action, admin=admin)
    if event is None:
        raise HTTPException(status_code=404, detail="suspicion_event_not_found")
    return {"ok": True, "action": payload.action}


@router.get("/stats/summary")
def stats(
    request: Request,
    _admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return {"ok": True, **stats_summary(db, request.app.state.settings)}


@router.get("/activation-keys")
def activation_keys(
    status: str | None = None,
    _admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    expire_pending_keys(db)
    stmt = select(ActivationKey)
    if status:
        stmt = stmt.where(ActivationKey.status == status)
    rows = db.scalars(stmt.order_by(ActivationKey.created_at.desc()).limit(500)).all()
    return {
        "ok": True,
        "keys": [
            {
                "id": key.id,
                "code": key.code,
                "app_type": key.app_type,
                "status": key.status,
                "created_at": iso(key.created_at),
                "expires_at": iso(key.expires_at),
                "consumed_at": iso(key.consumed_at),
                "consumed_by_device_id": key.consumed_by_device_id,
            }
            for key in rows
        ],
    }


@router.post("/activation-keys", dependencies=[Depends(require_csrf)])
def new_activation_key(
    payload: ActivationKeyCreateRequest,
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    key = create_activation_key(
        db,
        app_type=payload.app_type,
        expires_in_hours=payload.expires_in_hours,
        admin=admin,
    )
    return {
        "ok": True,
        "key": {
            "code": key.code,
            "app_type": key.app_type,
            "status": key.status,
            "expires_at": iso(key.expires_at),
        },
    }


@router.post("/activation-keys/{code}/cancel", dependencies=[Depends(require_csrf)])
def cancel_activation_key(
    code: str,
    _admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    key = db.scalar(select(ActivationKey).where(ActivationKey.code == code.upper()))
    if key is None:
        raise HTTPException(status_code=404, detail="activation_key_not_found")
    if key.status != "pending":
        raise HTTPException(status_code=409, detail="activation_key_not_pending")
    key.status = "cancelled"
    db.commit()
    return {"ok": True, "status": "cancelled"}
