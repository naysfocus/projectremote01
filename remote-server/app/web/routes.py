from __future__ import annotations

import csv
import io
import json
import math
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import __version__
from app.maintenance import backup, database_summary, rotate_backups, verify_backup
from app.integration_store import (
    IntegrationConfigurationError,
    clear_cloudflare,
    clear_telegram,
    get_or_create_config,
    get_secrets,
    integration_status,
    mask_secret,
    save_cloudflare,
    save_telegram,
    telegram_get_me,
    telegram_send_test,
    test_public_health,
)
from app.models import ActivationKey, ActivityReport, AdminUser, Device, IntegrationConfig, Site, SuspicionEvent, WorkJob
from app.status_files import read_json
from app.readiness import run_readiness
from app.security import generate_csrf_token, hash_password, verify_password
from app.services.common import add_audit
from app.services.admin import (
    create_activation_key,
    expire_pending_keys,
    get_device_detail,
    list_devices_page,
    review_suspicion,
    set_authorization_status,
    stats_summary,
)
from app.utils import iso, local_display, utcnow
from app.services.operations import TIMEZONE_OPTIONS, active_job_rows, set_device_tags, site_rows
from app.services.remote_hp_sync import (
    remote_hp_account_date_rows,
    remote_hp_batch_rows,
    remote_hp_handset_rows,
    remote_hp_session_history,
    remote_hp_summary,
)

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["app_version"] = __version__


def _db(request: Request) -> Session:
    return request.app.state.database.session_factory()


def _admin(request: Request, db: Session) -> AdminUser | None:
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return None
    admin = db.get(AdminUser, int(admin_id))
    session_version = request.session.get("admin_session_version")
    if (
        admin is None
        or not admin.is_active
        or session_version != admin.session_version
    ):
        request.session.clear()
        return None
    return admin


def _ensure_csrf(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = generate_csrf_token()
        request.session["csrf_token"] = token
    return token


def _check_csrf(request: Request, supplied: str) -> None:
    expected = request.session.get("csrf_token")
    if not expected or supplied != expected:
        raise HTTPException(status_code=403, detail="csrf_failed")



def _backup_valid(path: Path) -> bool:
    try:
        verify_backup(path)
    except Exception:
        return False
    return True


def _redirect_login() -> RedirectResponse:
    return RedirectResponse("/login", status_code=303)


@router.get("/", response_class=HTMLResponse)
def root(request: Request):
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, password_changed: int = 0):
    with _db(request) as db:
        if _admin(request, db):
            return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None, "success": "Password berhasil diubah. Silakan login kembali." if password_changed else None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    with _db(request) as db:
        admin = db.scalar(select(AdminUser).where(AdminUser.username == username.strip()))
        if admin is None or not admin.is_active or not verify_password(admin.password_hash, password):
            return templates.TemplateResponse(
                request,
                "login.html",
                {"error": "Username atau password salah."},
                status_code=401,
            )
        admin.last_login_at = utcnow()
        db.commit()
        request.session.clear()
        request.session["admin_id"] = admin.id
        request.session["admin_session_version"] = admin.session_version
        request.session["csrf_token"] = generate_csrf_token()
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form(...)):
    _check_csrf(request, csrf_token)
    request.session.clear()
    return RedirectResponse("/login", status_code=303)




@router.get("/account", response_class=HTMLResponse)
def account_page(request: Request):
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        return templates.TemplateResponse(
            request,
            "account.html",
            {
                "admin": admin,
                "csrf_token": _ensure_csrf(request),
                "error": None,
                "success": None,
            },
        )


@router.post("/account", response_class=HTMLResponse)
def account_update(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...),
):
    _check_csrf(request, csrf_token)
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        error = None
        if not verify_password(admin.password_hash, current_password):
            error = "Password saat ini salah."
        elif len(new_password) < 12:
            error = "Password baru minimal 12 karakter."
        elif new_password != confirm_password:
            error = "Konfirmasi password tidak sama."
        if error:
            return templates.TemplateResponse(
                request,
                "account.html",
                {
                    "admin": admin,
                    "csrf_token": _ensure_csrf(request),
                    "error": error,
                    "success": None,
                },
                status_code=400,
            )
        admin.password_hash = hash_password(new_password)
        admin.session_version += 1
        db.commit()
        credentials_file = Path(
            os.getenv("INITIAL_CREDENTIALS_FILE", "/data/INITIAL_ADMIN_CREDENTIALS.txt")
        )
        try:
            credentials_file.unlink(missing_ok=True)
        except OSError:
            pass
        request.session.clear()
        return RedirectResponse("/login?password_changed=1", status_code=303)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    q: str = "",
    app_type: str = "",
    status: str = "",
    page: int = 1,
    site_id: int | None = None,
):
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        page = max(1, page)
        page_size = 50
        devices, total = list_devices_page(
            db,
            request.app.state.settings,
            query=q,
            app_type=app_type,
            status=status,
            page=page,
            page_size=page_size,
            site_id=site_id,
        )
        stats = stats_summary(db, request.app.state.settings, site_id=site_id)
        sites = db.scalars(select(Site).where(Site.is_active.is_(True)).order_by(Site.name)).all()
        csrf = _ensure_csrf(request)
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "admin": admin,
                "devices": devices,
                "stats": stats,
                "sites": sites,
                "csrf_token": csrf,
                "filters": {"q": q, "app_type": app_type, "status": status, "site_id": site_id},
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "pages": max(1, math.ceil(total / page_size)),
                },
            },
        )


@router.get("/sites", response_class=HTMLResponse)
def sites_page(request: Request):
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        return templates.TemplateResponse(request, "sites.html", {
            "admin": admin, "sites": site_rows(db, request.app.state.settings),
            "timezone_options": TIMEZONE_OPTIONS, "csrf_token": _ensure_csrf(request),
        })


@router.post("/sites")
def site_create(request: Request, name: str = Form(...), code: str = Form(default=""), timezone_name: str = Form(default="Asia/Jakarta"), notes: str = Form(default=""), csrf_token: str = Form(...)):
    _check_csrf(request, csrf_token)
    if timezone_name not in dict(TIMEZONE_OPTIONS):
        raise HTTPException(status_code=422, detail="invalid_timezone")
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        clean_name = " ".join(name.strip().split())
        if not clean_name:
            raise HTTPException(status_code=422, detail="site_name_required")
        if db.scalar(select(Site.id).where(Site.name == clean_name)) is not None:
            raise HTTPException(status_code=409, detail="site_name_exists")
        site = Site(name=clean_name[:160], code=code.strip()[:40] or None, timezone_name=timezone_name, notes=notes.strip() or None, updated_at=utcnow())
        db.add(site); db.commit()
    return RedirectResponse("/sites", status_code=303)


@router.get("/sites/{site_id}", response_class=HTMLResponse)
def site_detail(request: Request, site_id: int):
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        site = db.get(Site, site_id)
        if site is None:
            raise HTTPException(status_code=404, detail="site_not_found")
        devices, _ = list_devices_page(db, request.app.state.settings, site_id=site_id, page=1, page_size=100)
        return templates.TemplateResponse(request, "site_detail.html", {
            "admin": admin, "site": site, "devices": devices,
            "summary": stats_summary(db, request.app.state.settings, site_id=site_id),
            "active_jobs": active_job_rows(db, site_id=site_id, timezone_name=site.timezone_name),
            "timezone_options": TIMEZONE_OPTIONS, "csrf_token": _ensure_csrf(request),
        })


@router.post("/sites/{site_id}")
def site_update(request: Request, site_id: int, name: str = Form(...), code: str = Form(default=""), timezone_name: str = Form(default="Asia/Jakarta"), notes: str = Form(default=""), is_active: str = Form(default=""), csrf_token: str = Form(...)):
    _check_csrf(request, csrf_token)
    if timezone_name not in dict(TIMEZONE_OPTIONS):
        raise HTTPException(status_code=422, detail="invalid_timezone")
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        site = db.get(Site, site_id)
        if site is None:
            raise HTTPException(status_code=404, detail="site_not_found")
        site.name = " ".join(name.strip().split())[:160]
        site.code = code.strip()[:40] or None
        site.timezone_name = timezone_name
        site.notes = notes.strip() or None
        site.is_active = is_active == "1"
        site.updated_at = utcnow(); db.commit()
    return RedirectResponse(f"/sites/{site_id}", status_code=303)


@router.get("/devices/{device_id}", response_class=HTMLResponse)
def device_page(request: Request, device_id: int):
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        device = get_device_detail(db, device_id, request.app.state.settings)
        if device is None:
            raise HTTPException(status_code=404, detail="device_not_found")
        report_rows = db.scalars(
            select(ActivityReport)
            .where(ActivityReport.device_id == device_id)
            .order_by(ActivityReport.occurred_at.desc())
            .limit(100)
        ).all()
        reports = [
            {
                "id": row.id,
                "app_type": row.app_type,
                "event_type": row.event_type,
                "occurred_at": local_display(row.occurred_at, device["timezone_name"]),
                "summary": json.loads(row.summary_json),
            }
            for row in report_rows
        ]
        return templates.TemplateResponse(
            request,
            "device_detail.html",
            {
                "admin": admin,
                "device": device,
                "reports": reports,
                "csrf_token": _ensure_csrf(request),
                "sites": db.scalars(select(Site).where(Site.is_active.is_(True)).order_by(Site.name)).all(),
                "active_jobs": active_job_rows(db, device_id=device_id, timezone_name=device["timezone_name"]),
            },
        )


@router.get("/devices/{device_id}/remote-hp", response_class=HTMLResponse)
def remote_hp_operations_page(
    request: Request,
    device_id: int,
    batch_date: str = "",
    q: str = "",
    handset_id: int | None = None,
):
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        device = get_device_detail(db, device_id, request.app.state.settings)
        if device is None:
            raise HTTPException(status_code=404, detail="device_not_found")
        if not any(auth["app_type"] == "remote_hp" for auth in device["authorizations"]):
            raise HTTPException(status_code=404, detail="remote_hp_not_authorized")
        try:
            selected_date = date.fromisoformat(batch_date) if batch_date else datetime.now(ZoneInfo(device["timezone_name"])).date()
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid_batch_date")
        handsets = remote_hp_handset_rows(db, device_id)
        account_rows = remote_hp_account_date_rows(db, device_id, selected_date, q, handset_id)
        batch_rows = remote_hp_batch_rows(db, device_id, limit=31)
        history = remote_hp_session_history(db, device_id, limit=300, query_text=q, handset_id=handset_id)
        summary = remote_hp_summary(db, device_id, batch_date=selected_date, timezone_name=device["timezone_name"])
        summary["last_synced_at"] = local_display(summary["last_synced_at"], device["timezone_name"])
        for row in handsets:
            row["last_synced_at"] = local_display(row["last_synced_at"], device["timezone_name"])
        for row in account_rows:
            row["last_sync"] = local_display(row["last_sync"], device["timezone_name"])
        for row in history:
            row["started_at"] = local_display(row["started_at"], device["timezone_name"])
            row["finished_at"] = local_display(row["finished_at"], device["timezone_name"])
            row["last_synced_at"] = local_display(row["last_synced_at"], device["timezone_name"])
        return templates.TemplateResponse(request, "remote_hp_operations.html", {
            "admin": admin,
            "device": device,
            "summary": summary,
            "handsets": handsets,
            "account_rows": account_rows,
            "batch_rows": batch_rows,
            "history": history,
            "filters": {"batch_date": selected_date.isoformat(), "q": q, "handset_id": handset_id},
        })


@router.post("/devices/{device_id}/edit")
def device_edit(
    request: Request,
    device_id: int,
    label: str = Form(default=""),
    notes: str = Form(default=""),
    site_id: str = Form(default=""),
    tags: str = Form(default=""),
    csrf_token: str = Form(...),
):
    _check_csrf(request, csrf_token)
    with _db(request) as db:
        if _admin(request, db) is None:
            return _redirect_login()
        device = db.get(Device, device_id)
        if device is None:
            raise HTTPException(status_code=404, detail="device_not_found")
        device.label = label.strip() or None
        device.notes = notes.strip() or None
        device.site_id = int(site_id) if site_id.strip().isdigit() else None
        set_device_tags(db, device, tags)
        db.commit()
    return RedirectResponse(f"/devices/{device_id}", status_code=303)


@router.post("/devices/{device_id}/authorization")
def authorization_action(
    request: Request,
    device_id: int,
    app_type: str = Form(...),
    action: str = Form(...),
    csrf_token: str = Form(...),
):
    _check_csrf(request, csrf_token)
    if app_type not in {"matrix_generator", "remote_hp"} or action not in {"revoke", "reactivate"}:
        raise HTTPException(status_code=422, detail="invalid_action")
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        auth = set_authorization_status(
            db,
            device_id=device_id,
            app_type=app_type,
            status="revoked" if action == "revoke" else "active",
            actor_type="admin",
            actor_id=str(admin.id),
        )
        if auth is None:
            raise HTTPException(status_code=404, detail="authorization_not_found")
    return RedirectResponse(f"/devices/{device_id}", status_code=303)


@router.get("/system", response_class=HTMLResponse)
def system_page(request: Request):
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        settings = request.app.state.settings
        integration_config = get_or_create_config(db)
        db.commit()
        integration_runtime = integration_status(settings)
        integration_runtime.setdefault("telegram", {})
        integration_runtime.setdefault("cloudflare", {})
        database_ok = True
        try:
            db.execute(select(1))
        except Exception:
            database_ok = False
        data_dir = Path(settings.data_dir)
        scheduler_status = read_json(data_dir / "scheduler-status.json")
        backups = sorted(
            [item for item in (data_dir / "backups").glob("*.sqlite3") if item.name.startswith(("remote-server-", "scaleup-"))],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )[:10]
        readiness = read_json(data_dir / "readiness-status.json")
        db_summary = database_summary(settings) if database_ok else {}
        return templates.TemplateResponse(
            request,
            "system.html",
            {
                "admin": admin,
                "csrf_token": _ensure_csrf(request),
                "scheduler": scheduler_status,
                "backups": [
                    {"name": item.name, "size": item.stat().st_size, "verified": _backup_valid(item)}
                    for item in backups
                ],
                "database_summary": db_summary,
                "readiness": readiness,
                "system": {
                    "version": __version__,
                    "environment": settings.environment,
                    "public_base_url": integration_config.public_base_url,
                    "database_kind": settings.database_kind,
                    "database_ok": database_ok,
                    "cookie_secure": settings.session_cookie_secure,
                    "cookie_secure_mode": settings.session_cookie_secure_mode,
                    "heartbeat_interval_seconds": settings.heartbeat_interval_seconds,
                    "session_timeout_seconds": settings.session_timeout_seconds,
                    "grace_period_hours": settings.grace_period_hours,
                    "display_timezone": settings.display_timezone,
                    "telegram_configured": bool(integration_config.telegram_token_encrypted),
                    "telegram_enabled": integration_config.telegram_enabled,
                    "cloudflare_configured": bool(integration_config.cloudflare_token_encrypted),
                    "cloudflare_enabled": integration_config.cloudflare_enabled,
                    "integration_runtime": integration_runtime,
                },
            },
        )


@router.get("/activation-keys", response_class=HTMLResponse)
def activation_keys_page(request: Request, created: str = ""):
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        expire_pending_keys(db)
        keys = db.scalars(select(ActivationKey).order_by(ActivationKey.created_at.desc()).limit(200)).all()
        return templates.TemplateResponse(
            request,
            "activation_keys.html",
            {"admin": admin, "keys": keys, "csrf_token": _ensure_csrf(request), "format_time": lambda value: local_display(value, request.app.state.settings.display_timezone), "created": created},
        )


@router.post("/activation-keys")
def activation_key_create(
    request: Request,
    app_type: str = Form(...),
    csrf_token: str = Form(...),
):
    _check_csrf(request, csrf_token)
    if app_type not in {"matrix_generator", "remote_hp"}:
        raise HTTPException(status_code=422, detail="invalid_app_type")
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        key = create_activation_key(
            db,
            app_type=app_type,
            expires_in_hours=1,
            admin=admin,
        )
    return RedirectResponse(f"/activation-keys?created={key.code}", status_code=303)


@router.post("/activation-keys/{code}/cancel")
def activation_key_cancel(request: Request, code: str, csrf_token: str = Form(...)):
    _check_csrf(request, csrf_token)
    with _db(request) as db:
        if _admin(request, db) is None:
            return _redirect_login()
        key = db.scalar(select(ActivationKey).where(ActivationKey.code == code.upper()))
        if key is None:
            raise HTTPException(status_code=404, detail="activation_key_not_found")
        if key.status == "pending":
            key.status = "cancelled"
            db.commit()
    return RedirectResponse("/activation-keys", status_code=303)


@router.get("/suspicious", response_class=HTMLResponse)
def suspicious_page(request: Request):
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        events = db.execute(
            select(SuspicionEvent, Device)
            .join(Device, Device.id == SuspicionEvent.device_id)
            .order_by(SuspicionEvent.detected_at.desc())
            .limit(300)
        ).all()
        return templates.TemplateResponse(
            request,
            "suspicious.html",
            {"admin": admin, "events": events, "csrf_token": _ensure_csrf(request), "format_time": lambda value: local_display(value, request.app.state.settings.display_timezone)},
        )


@router.post("/suspicious/{event_id}/review")
def suspicious_review(
    request: Request,
    event_id: int,
    action: str = Form(...),
    csrf_token: str = Form(...),
):
    _check_csrf(request, csrf_token)
    if action not in {"ignored", "revoked"}:
        raise HTTPException(status_code=422, detail="invalid_action")
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        if review_suspicion(db, event_id=event_id, action=action, admin=admin) is None:
            raise HTTPException(status_code=404, detail="suspicion_event_not_found")
    return RedirectResponse("/suspicious", status_code=303)


@router.post("/system/readiness")
def system_readiness(request: Request, csrf_token: str = Form(...)):
    _check_csrf(request, csrf_token)
    with _db(request) as db:
        if _admin(request, db) is None:
            return _redirect_login()
        run_readiness(db, request.app.state.settings)
    return RedirectResponse("/system?readiness_checked=1", status_code=303)


@router.post("/system/backup")
def system_backup(request: Request, csrf_token: str = Form(...)):
    _check_csrf(request, csrf_token)
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
    settings = request.app.state.settings
    backup(settings)
    rotate_backups(settings)
    return RedirectResponse("/system?backup_created=1", status_code=303)


@router.get("/system/backups/{filename}")
def download_backup(request: Request, filename: str):
    with _db(request) as db:
        if _admin(request, db) is None:
            return _redirect_login()
    if not filename.startswith(("remote-server-", "scaleup-")) or not filename.endswith(".sqlite3") or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="invalid_backup_name")
    path = Path(request.app.state.settings.data_dir) / "backups" / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="backup_not_found")
    verify_backup(path)
    return FileResponse(path, filename=filename, media_type="application/vnd.sqlite3")


@router.get("/exports/activity.csv")
def export_activity_csv(
    request: Request,
    app_type: str = "",
    event_type: str = "",
):
    with _db(request) as db:
        if _admin(request, db) is None:
            return _redirect_login()
        statement = (
            select(ActivityReport, Device)
            .join(Device, Device.id == ActivityReport.device_id)
            .order_by(ActivityReport.occurred_at.desc())
            .limit(100000)
        )
        if app_type in {"matrix_generator", "remote_hp"}:
            statement = statement.where(ActivityReport.app_type == app_type)
        if event_type.strip():
            statement = statement.where(ActivityReport.event_type == event_type.strip())
        rows = db.execute(statement).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "device_id", "device_label", "app_type", "event_type", "occurred_at_local", "received_at_local", "summary_json", "client_report_id"])
    for report, device in rows:
        writer.writerow([report.id, report.device_id, device.label or f"Device #{device.id}", report.app_type, report.event_type, local_display(report.occurred_at, request.app.state.settings.display_timezone), local_display(report.received_at, request.app.state.settings.display_timezone), report.summary_json, report.client_report_id])
    payload = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        iter([payload]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=remote-server-activity.csv"},
    )


@router.get("/integrations", response_class=HTMLResponse)
def integrations_page(request: Request, saved: str = "", error: str = ""):
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        config = get_or_create_config(db)
        db.commit()
        secrets = get_secrets(db, request.app.state.settings)
        runtime = integration_status(request.app.state.settings)
        messages = {
            "telegram": "Konfigurasi Telegram berhasil disimpan.",
            "telegram_test": "Token Telegram valid dan bot berhasil dikenali.",
            "telegram_message": "Pesan uji berhasil dikirim ke Telegram admin.",
            "telegram_cleared": "Token Telegram dan status bot sudah dihapus.",
            "cloudflare": "Konfigurasi Cloudflare tersimpan. Connector akan menyesuaikan otomatis.",
            "cloudflare_test": "Domain Cloudflare berhasil menjangkau health check server.",
            "cloudflare_cleared": "Tunnel Token Cloudflare sudah dihapus.",
            "cloudflare_restarted": "Connector Cloudflare sedang dimulai ulang.",
        }
        return templates.TemplateResponse(
            request,
            "integrations.html",
            {
                "admin": admin,
                "csrf_token": _ensure_csrf(request),
                "config": config,
                "runtime": runtime,
                "telegram_masked": mask_secret(secrets.telegram_token),
                "cloudflare_masked": mask_secret(secrets.cloudflare_token),
                "cloudflare_public_url": config.public_base_url if config.public_base_url.startswith("https://") else "",
                "success": messages.get(saved),
                "error": error or None,
            },
        )


def _integration_error_redirect(message: str) -> RedirectResponse:
    from urllib.parse import quote

    return RedirectResponse(f"/integrations?error={quote(message)}", status_code=303)


@router.post("/integrations/telegram/save")
def integration_telegram_save(
    request: Request,
    token: str = Form(default=""),
    admin_id: str = Form(default=""),
    enabled: str | None = Form(default=None),
    csrf_token: str = Form(...),
):
    _check_csrf(request, csrf_token)
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        try:
            bot_username = None
            if token.strip():
                bot_info = telegram_get_me(token.strip())
                bot_username = str(bot_info.get("username") or "")
            save_telegram(
                db,
                request.app.state.settings,
                enabled=enabled == "on",
                token=token,
                admin_id=admin_id,
                admin_user_id=admin.id,
                bot_username=bot_username,
            )
            add_audit(
                db,
                actor_type="admin",
                actor_id=str(admin.id),
                action="integration.telegram.update",
                target_type="integration",
                target_id="telegram",
                metadata={"enabled": enabled == "on", "admin_id": admin_id},
            )
            db.commit()
        except IntegrationConfigurationError as exc:
            db.rollback()
            return _integration_error_redirect(str(exc))
    return RedirectResponse("/integrations?saved=telegram", status_code=303)


@router.post("/integrations/telegram/test")
def integration_telegram_test(request: Request, csrf_token: str = Form(...)):
    _check_csrf(request, csrf_token)
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        try:
            config = get_or_create_config(db)
            secrets = get_secrets(db, request.app.state.settings)
            if not secrets.telegram_token:
                raise IntegrationConfigurationError("Token Telegram belum disimpan.")
            info = telegram_get_me(secrets.telegram_token)
            config.telegram_bot_username = str(info.get("username") or "") or None
            config.updated_at = utcnow()
            db.commit()
        except IntegrationConfigurationError as exc:
            return _integration_error_redirect(str(exc))
    return RedirectResponse("/integrations?saved=telegram_test", status_code=303)


@router.post("/integrations/telegram/send-test")
def integration_telegram_send_test(request: Request, csrf_token: str = Form(...)):
    _check_csrf(request, csrf_token)
    with _db(request) as db:
        if _admin(request, db) is None:
            return _redirect_login()
        try:
            config = get_or_create_config(db)
            secrets = get_secrets(db, request.app.state.settings)
            if not secrets.telegram_token or not config.telegram_admin_id:
                raise IntegrationConfigurationError("Token dan Telegram Admin ID harus disimpan terlebih dahulu.")
            telegram_send_test(secrets.telegram_token, config.telegram_admin_id)
        except IntegrationConfigurationError as exc:
            return _integration_error_redirect(str(exc))
    return RedirectResponse("/integrations?saved=telegram_message", status_code=303)


@router.post("/integrations/telegram/clear")
def integration_telegram_clear(request: Request, csrf_token: str = Form(...)):
    _check_csrf(request, csrf_token)
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        clear_telegram(db, admin_user_id=admin.id)
        add_audit(
            db,
            actor_type="admin",
            actor_id=str(admin.id),
            action="integration.telegram.clear",
            target_type="integration",
            target_id="telegram",
        )
        db.commit()
    return RedirectResponse("/integrations?saved=telegram_cleared", status_code=303)


@router.post("/integrations/cloudflare/save")
def integration_cloudflare_save(
    request: Request,
    token: str = Form(default=""),
    public_base_url: str = Form(default=""),
    protocol: str = Form(default="auto"),
    enabled: str | None = Form(default=None),
    csrf_token: str = Form(...),
):
    _check_csrf(request, csrf_token)
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        try:
            save_cloudflare(
                db,
                request.app.state.settings,
                enabled=enabled == "on",
                token=token,
                public_base_url=public_base_url,
                protocol=protocol,
                admin_user_id=admin.id,
            )
            add_audit(
                db,
                actor_type="admin",
                actor_id=str(admin.id),
                action="integration.cloudflare.update",
                target_type="integration",
                target_id="cloudflare",
                metadata={"enabled": enabled == "on", "public_base_url": public_base_url, "protocol": protocol},
            )
            db.commit()
        except IntegrationConfigurationError as exc:
            db.rollback()
            return _integration_error_redirect(str(exc))
    return RedirectResponse("/integrations?saved=cloudflare", status_code=303)


@router.post("/integrations/cloudflare/test")
def integration_cloudflare_test(request: Request, csrf_token: str = Form(...)):
    _check_csrf(request, csrf_token)
    with _db(request) as db:
        if _admin(request, db) is None:
            return _redirect_login()
        try:
            config = get_or_create_config(db)
            test_public_health(config.public_base_url)
        except IntegrationConfigurationError as exc:
            return _integration_error_redirect(str(exc))
    return RedirectResponse("/integrations?saved=cloudflare_test", status_code=303)


@router.post("/integrations/cloudflare/restart")
def integration_cloudflare_restart(request: Request, csrf_token: str = Form(...)):
    _check_csrf(request, csrf_token)
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        config = get_or_create_config(db)
        if not config.cloudflare_enabled or not config.cloudflare_token_encrypted:
            return _integration_error_redirect("Cloudflare belum diaktifkan.")
        config.revision += 1
        config.updated_at = utcnow()
        config.updated_by_admin_id = admin.id
        add_audit(
            db,
            actor_type="admin",
            actor_id=str(admin.id),
            action="integration.cloudflare.restart",
            target_type="integration",
            target_id="cloudflare",
        )
        db.commit()
    return RedirectResponse("/integrations?saved=cloudflare_restarted", status_code=303)


@router.post("/integrations/cloudflare/clear")
def integration_cloudflare_clear(request: Request, csrf_token: str = Form(...)):
    _check_csrf(request, csrf_token)
    with _db(request) as db:
        admin = _admin(request, db)
        if admin is None:
            return _redirect_login()
        clear_cloudflare(db, admin_user_id=admin.id)
        add_audit(
            db,
            actor_type="admin",
            actor_id=str(admin.id),
            action="integration.cloudflare.clear",
            target_type="integration",
            target_id="cloudflare",
        )
        db.commit()
    return RedirectResponse("/integrations?saved=cloudflare_cleared", status_code=303)
