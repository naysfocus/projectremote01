from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ActivityReport, Device, Site, Tag, WorkJob
from app.utils import as_utc, local_day_bounds, utcnow

APP_LABELS = {"matrix_generator": "Video Mixer", "remote_hp": "Remote HP"}
TIMEZONE_OPTIONS = [
    ("Asia/Jakarta", "WIB — Jakarta"),
    ("Asia/Makassar", "WITA — Makassar"),
    ("Asia/Jayapura", "WIT — Jayapura"),
]


def normalize_tags(raw: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for part in raw.replace(";", ",").split(","):
        name = " ".join(part.strip().split())[:80]
        key = name.casefold()
        if name and key not in seen:
            seen.add(key)
            result.append(name)
    return result[:20]


def set_device_tags(db: Session, device: Device, raw: str) -> None:
    names = normalize_tags(raw)
    selected: list[Tag] = []
    for name in names:
        tag = db.scalar(select(Tag).where(func.lower(Tag.name) == name.lower()))
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        selected.append(tag)
    device.tags = selected


def upsert_work_job(db: Session, device_id: int, app_type: str, event_type: str, summary: dict[str, Any], occurred_at: datetime) -> None:
    raw_job_id = summary.get("job_id") or summary.get("local_session_id") or summary.get("run_tag")
    if raw_job_id in (None, ""):
        return
    client_job_id = str(raw_job_id)[:80]
    job = db.scalar(select(WorkJob).where(
        WorkJob.device_id == device_id,
        WorkJob.app_type == app_type,
        WorkJob.client_job_id == client_job_id,
    ))
    now = as_utc(occurred_at) or utcnow()
    if job is None:
        job = WorkJob(
            device_id=device_id,
            app_type=app_type,
            client_job_id=client_job_id,
            started_at=now,
            updated_at=now,
        )
        db.add(job)
    if event_type in {"generate_started", "upload_session_started"}:
        planned = summary.get("planned_count", summary.get("video_count", job.planned_count or 0))
        completed = summary.get("completed_count", 0)
    elif event_type in {"generate_completed", "upload_session_completed", "upload_session_cancelled"}:
        completed = summary.get("completed_count", summary.get("video_count", job.completed_count or 0))
        planned = summary.get("planned_count", job.planned_count or completed)
    else:
        planned = summary.get("planned_count", job.planned_count or summary.get("video_count", 0))
        completed = summary.get("completed_count", job.completed_count or 0)
    failed = summary.get("failed_count", job.failed_count or 0)
    for attr, value in (("planned_count", planned), ("completed_count", completed), ("failed_count", failed)):
        try:
            setattr(job, attr, max(0, int(value or 0)))
        except (TypeError, ValueError):
            pass
    status_map = {
        "generate_started": "running", "generate_progress": "running",
        "generate_completed": "completed", "generate_cancelled": "cancelled", "generate_failed": "failed",
        "upload_session_started": "running", "upload_progress": "running",
        "upload_session_completed": "completed", "upload_session_cancelled": "cancelled", "upload_failed": "failed",
    }
    job.status = status_map.get(event_type, job.status)
    if job.planned_count > 0:
        job.progress_percent = min(100, int((job.completed_count / job.planned_count) * 100))
    elif job.status == "completed":
        job.progress_percent = 100
    job.title = str(summary.get("account_username") or summary.get("mode") or APP_LABELS.get(app_type, app_type))[:255]
    job.metadata_json = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
    job.updated_at = now
    if job.status in {"completed", "cancelled", "failed"}:
        job.finished_at = now


def _summary_values(report: ActivityReport) -> tuple[int, int, int, int]:
    try:
        summary = json.loads(report.summary_json)
    except (json.JSONDecodeError, TypeError):
        return 0, 0, 0, 0
    generated = upload_videos = upload_sessions = mixer_jobs = 0
    if report.event_type == "generate_completed":
        generated = int(summary.get("video_count", 0) or 0)
        mixer_jobs = 1
    elif report.event_type == "upload_session_completed" and summary.get("status") == "finished":
        upload_videos = int(summary.get("video_count", 0) or 0)
        upload_sessions = 1
    return generated, upload_videos, upload_sessions, mixer_jobs


def operation_summary(db: Session, *, timezone_name: str = "Asia/Jakarta", site_id: int | None = None) -> dict[str, int]:
    start, end = local_day_bounds(timezone_name=timezone_name)
    stmt = select(ActivityReport).join(Device, Device.id == ActivityReport.device_id).where(
        ActivityReport.occurred_at >= start, ActivityReport.occurred_at <= end
    )
    if site_id is not None:
        stmt = stmt.where(Device.site_id == site_id)
    reports = db.scalars(stmt).all()
    generated = upload_videos = upload_sessions = mixer_jobs = 0
    for report in reports:
        a, b, c, d = _summary_values(report)
        generated += a; upload_videos += b; upload_sessions += c; mixer_jobs += d
    job_stmt = select(func.count(WorkJob.id)).join(Device, Device.id == WorkJob.device_id).where(WorkJob.status == "running")
    if site_id is not None:
        job_stmt = job_stmt.where(Device.site_id == site_id)
    active_jobs = int(db.scalar(job_stmt) or 0)
    return {
        "generated_videos_today": generated,
        "uploaded_videos_today": upload_videos,
        "upload_sessions_today": upload_sessions,
        "mixer_jobs_today": mixer_jobs,
        "active_jobs": active_jobs,
    }


def site_rows(db: Session, settings) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sites = db.scalars(select(Site).order_by(Site.is_active.desc(), Site.name.asc())).all()
    for site in sites:
        device_count = int(db.scalar(select(func.count(Device.id)).where(Device.site_id == site.id)) or 0)
        summary = operation_summary(db, timezone_name=site.timezone_name, site_id=site.id)
        from app.services.remote_hp_sync import site_remote_hp_summary
        inventory = site_remote_hp_summary(db, site_id=site.id)
        rows.append({
            "id": site.id, "name": site.name, "code": site.code, "timezone_name": site.timezone_name,
            "notes": site.notes, "is_active": site.is_active, "device_count": device_count, **summary, **inventory,
        })
    return rows


def active_job_rows(db: Session, *, site_id: int | None = None, device_id: int | None = None, timezone_name: str = "Asia/Jakarta", limit: int = 100) -> list[dict[str, Any]]:
    stmt = select(WorkJob, Device).join(Device, Device.id == WorkJob.device_id).where(WorkJob.status == "running").order_by(WorkJob.updated_at.desc()).limit(limit)
    if site_id is not None:
        stmt = stmt.where(Device.site_id == site_id)
    if device_id is not None:
        stmt = stmt.where(Device.id == device_id)
    rows = []
    from app.utils import local_display
    for job, device in db.execute(stmt).all():
        rows.append({
            "id": job.id, "device_id": device.id, "device_label": device.label or f"Device #{device.id}",
            "app_type": job.app_type, "app_label": APP_LABELS.get(job.app_type, job.app_type),
            "client_job_id": job.client_job_id, "status": job.status, "planned_count": job.planned_count,
            "completed_count": job.completed_count, "failed_count": job.failed_count,
            "progress_percent": job.progress_percent, "title": job.title,
            "updated_at": local_display(job.updated_at, timezone_name),
        })
    return rows
