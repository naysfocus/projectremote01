from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ActivityReport, AppAuthorization, Device
from app.schemas import ReportItem
from app.services.operations import upsert_work_job
from app.utils import as_utc, utcnow


class ReportValidationError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _nonnegative_int(summary: dict, key: str, default: int = 0) -> int:
    value = summary.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReportValidationError(f"invalid_{key}")
    return value


def validate_report(app_type: str, item: ReportItem) -> None:
    summary = item.summary
    if app_type == "matrix_generator":
        if item.event_type == "generate_completed":
            required = {"mode", "video_count", "duration_seconds", "run_tag"}
            if not required.issubset(summary):
                raise ReportValidationError("invalid_generate_summary")
            _nonnegative_int(summary, "video_count")
            if not isinstance(summary["duration_seconds"], (int, float)) or summary["duration_seconds"] < 0:
                raise ReportValidationError("invalid_duration")
            return
        if item.event_type in {"generate_started", "generate_progress", "generate_cancelled", "generate_failed"}:
            if not str(summary.get("job_id") or summary.get("run_tag") or "").strip():
                raise ReportValidationError("missing_job_id")
            for key in ("planned_count", "completed_count", "failed_count"):
                if key in summary:
                    _nonnegative_int(summary, key)
            return
    if app_type == "remote_hp":
        if item.event_type in {"upload_session_started", "upload_session_completed", "upload_session_cancelled"}:
            required = {"local_session_id", "account_username", "video_count", "batch_date", "status"}
            if not required.issubset(summary):
                raise ReportValidationError("invalid_upload_summary")
            if summary.get("status") not in {"active", "finished", "cancelled"}:
                raise ReportValidationError("invalid_upload_status")
            _nonnegative_int(summary, "video_count")
            return
        if item.event_type in {"upload_progress", "upload_failed"}:
            if not str(summary.get("local_session_id") or summary.get("job_id") or "").strip():
                raise ReportValidationError("missing_upload_session_id")
            for key in ("planned_count", "completed_count", "failed_count", "video_count"):
                if key in summary:
                    _nonnegative_int(summary, key)
            return
        if item.event_type == "account_added":
            if not isinstance(summary.get("account_username"), str) or not summary["account_username"]:
                raise ReportValidationError("invalid_account_summary")
            return
    if item.event_type in {"app_started", "app_stopped"}:
        return
    raise ReportValidationError("unsupported_event_type")


def save_reports(db: Session, authorization: AppAuthorization, reports: list[ReportItem]) -> tuple[int, int]:
    if authorization.status != "active":
        raise PermissionError("revoked")
    accepted = duplicates = 0
    now = utcnow()
    for item in reports:
        validate_report(authorization.app_type, item)
        exists = db.scalar(select(ActivityReport.id).where(
            ActivityReport.device_id == authorization.device_id,
            ActivityReport.client_report_id == item.client_report_id,
        ))
        if exists is not None:
            duplicates += 1
            continue
        try:
            with db.begin_nested():
                db.add(ActivityReport(
                    device_id=authorization.device_id,
                    app_type=authorization.app_type,
                    event_type=item.event_type,
                    occurred_at=as_utc(item.occurred_at) or item.occurred_at,
                    summary_json=json.dumps(item.summary, separators=(",", ":"), ensure_ascii=False),
                    client_report_id=item.client_report_id,
                ))
                upsert_work_job(db, authorization.device_id, authorization.app_type, item.event_type, item.summary, as_utc(item.occurred_at) or item.occurred_at)
                db.flush()
            accepted += 1
        except IntegrityError:
            duplicates += 1
    device = db.get(Device, authorization.device_id)
    if device is not None:
        device.last_seen_at = now
    db.commit()
    return accepted, duplicates
