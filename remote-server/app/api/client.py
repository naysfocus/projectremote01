from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import client_ip, get_authorization, get_db
from app.models import AppAuthorization
from app.schemas import (
    ActivateRequest,
    ReportBatchRequest,
    RemoteHpInventorySyncRequest,
    RemoteHpSessionSyncRequest,
    RemoteHpSessionReconcileRequest,
    SessionCloseRequest,
    SessionHeartbeatRequest,
    SessionOpenRequest,
)
from app.services.activation import ActivationError, activate
from app.services.reports import ReportValidationError, save_reports
from app.services.sessions import close_session, heartbeat, open_session
from app.services.remote_hp_sync import reconcile_sessions, sync_inventory, sync_sessions

router = APIRouter(prefix="/api/v1", tags=["client"])


@router.post("/activate")
def activate_client(payload: ActivateRequest, db: Session = Depends(get_db)):
    try:
        access_token, device = activate(db, payload)
    except ActivationError as exc:
        return JSONResponse(status_code=exc.status_code, content={"ok": False, "error": exc.code})
    return {"ok": True, "access_token": access_token, "device_id": device.id}


@router.post("/session/open")
def session_open(
    payload: SessionOpenRequest,
    request: Request,
    authorization: AppAuthorization = Depends(get_authorization),
    db: Session = Depends(get_db),
):
    settings = request.app.state.settings
    result = open_session(
        db,
        authorization,
        fingerprint_hash=payload.fingerprint_hash,
        app_version=payload.app_version,
        request_ip=client_ip(request),
        settings=settings,
    )
    body = {"ok": result.status_code == 200, "status": result.status}
    if result.status == "active":
        body.update(
            {
                "session_id": result.session_id,
                "grace_period_hours": settings.grace_period_hours,
                "heartbeat_interval_seconds": settings.heartbeat_interval_seconds,
                "session_timeout_seconds": settings.session_timeout_seconds,
            }
        )
    else:
        body["message"] = "Akses tidak tersedia. Hubungi admin."
    return JSONResponse(status_code=result.status_code, content=body)


@router.post("/session/heartbeat")
def session_heartbeat(
    payload: SessionHeartbeatRequest,
    authorization: AppAuthorization = Depends(get_authorization),
    db: Session = Depends(get_db),
):
    result = heartbeat(db, authorization, payload.session_id)
    body = {"ok": result.status_code == 200, "status": result.status}
    if result.status_code != 200:
        body["message"] = "Sesi tidak berlaku. Hubungi admin atau buka ulang aplikasi."
    return JSONResponse(status_code=result.status_code, content=body)


@router.post("/session/close")
def session_close(
    payload: SessionCloseRequest,
    authorization: AppAuthorization = Depends(get_authorization),
    db: Session = Depends(get_db),
):
    result = close_session(db, authorization, payload.session_id)
    return JSONResponse(
        status_code=result.status_code,
        content={"ok": result.status_code == 200, "status": result.status},
    )


@router.post("/report")
def report_activity(
    payload: ReportBatchRequest,
    authorization: AppAuthorization = Depends(get_authorization),
    db: Session = Depends(get_db),
):
    if authorization.status == "revoked":
        return JSONResponse(
            status_code=403,
            content={"ok": False, "status": "revoked", "message": "Akses dicabut oleh admin."},
        )
    try:
        accepted, duplicates = save_reports(db, authorization, payload.reports)
    except ReportValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.code) from exc
    return {
        "ok": True,
        "accepted": accepted,
        "duplicates": duplicates,
        "status": authorization.status,
    }


@router.post("/remote-hp/inventory-sync")
def remote_hp_inventory_sync(
    payload: RemoteHpInventorySyncRequest,
    authorization: AppAuthorization = Depends(get_authorization),
    db: Session = Depends(get_db),
):
    if authorization.status != "active":
        return JSONResponse(status_code=403, content={"ok": False, "status": "revoked"})
    if authorization.app_type != "remote_hp":
        return JSONResponse(status_code=403, content={"ok": False, "status": "wrong_app_type"})
    counts = sync_inventory(db, authorization.device_id, payload)
    return {"ok": True, "snapshot_id": payload.snapshot_id, **counts}


@router.post("/remote-hp/session-sync")
def remote_hp_session_sync(
    payload: RemoteHpSessionSyncRequest,
    authorization: AppAuthorization = Depends(get_authorization),
    db: Session = Depends(get_db),
):
    if authorization.status != "active":
        return JSONResponse(status_code=403, content={"ok": False, "status": "revoked"})
    if authorization.app_type != "remote_hp":
        return JSONResponse(status_code=403, content={"ok": False, "status": "wrong_app_type"})
    counts = sync_sessions(db, authorization.device_id, payload)
    return {"ok": True, "sync_id": payload.sync_id, **counts}


@router.post("/remote-hp/session-reconcile")
def remote_hp_session_reconcile(
    payload: RemoteHpSessionReconcileRequest,
    authorization: AppAuthorization = Depends(get_authorization),
    db: Session = Depends(get_db),
):
    if authorization.status != "active":
        return JSONResponse(status_code=403, content={"ok": False, "status": "revoked"})
    if authorization.app_type != "remote_hp":
        return JSONResponse(status_code=403, content={"ok": False, "status": "wrong_app_type"})
    counts = reconcile_sessions(db, authorization.device_id, payload.present_session_ids)
    return {"ok": True, "reconcile_id": payload.reconcile_id, **counts}
