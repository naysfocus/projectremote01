from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, select, text

from app.config import Settings
from app.database import Database
from app.models import ActivationKey, ActivityReport, AuditLog, Heartbeat, NotificationOutbox
from app.services.admin import expire_pending_keys
from app.status_files import write_json
from app.utils import utcnow


@dataclass(slots=True)
class MaintenanceResult:
    expired_activation_keys: int = 0
    deleted_heartbeats: int = 0
    deleted_reports: int = 0
    deleted_audit_logs: int = 0
    deleted_outbox_rows: int = 0


def sqlite_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise RuntimeError("This command currently supports SQLite only.")
    return Path(database_url[len(prefix) :]).expanduser().resolve()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_backup(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError("Backup file is missing or empty.")
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()
    if not result or result[0] != "ok":
        raise RuntimeError(f"Backup integrity check failed: {result!r}")


def backup(settings: Settings, destination: Path | None = None) -> Path:
    source = sqlite_path(settings.database_url)
    if not source.exists():
        raise RuntimeError(f"Database does not exist: {source}")
    backup_dir = Path(settings.data_dir) / "backups"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = destination or backup_dir / f"remote-server-{timestamp}.sqlite3"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    with sqlite3.connect(source) as source_db, sqlite3.connect(temporary) as destination_db:
        source_db.backup(destination_db)
    verify_backup(temporary)
    temporary.replace(destination)
    checksum = _sha256(destination)
    destination.with_suffix(destination.suffix + ".sha256").write_text(
        f"{checksum}  {destination.name}\n", encoding="utf-8"
    )
    return destination


def rotate_backups(settings: Settings) -> list[Path]:
    backup_dir = Path(settings.data_dir) / "backups"
    backups = sorted([item for item in backup_dir.glob("*.sqlite3") if item.name.startswith(("remote-server-", "scaleup-"))], key=lambda item: item.stat().st_mtime, reverse=True)
    removed: list[Path] = []
    for path in backups[settings.backup_retention_count :]:
        path.unlink(missing_ok=True)
        path.with_suffix(path.suffix + ".sha256").unlink(missing_ok=True)
        removed.append(path)
    return removed


def restore(settings: Settings, source: Path) -> Path:
    source = source.expanduser().resolve()
    verify_backup(source)
    destination = sqlite_path(settings.database_url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    safety_copy = destination.with_name(
        f"{destination.stem}.before-restore-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}{destination.suffix}"
    )
    if destination.exists():
        shutil.copy2(destination, safety_copy)
    temporary = destination.with_suffix(destination.suffix + ".restore.tmp")
    shutil.copy2(source, temporary)
    verify_backup(temporary)
    temporary.replace(destination)
    for suffix in ("-wal", "-shm"):
        Path(str(destination) + suffix).unlink(missing_ok=True)
    return safety_copy


def prune(settings: Settings) -> MaintenanceResult:
    database = Database(settings)
    now = utcnow()
    result = MaintenanceResult()
    with database.session_factory() as db:
        result.expired_activation_keys = expire_pending_keys(db)
        operations = [
            (
                "deleted_heartbeats",
                delete(Heartbeat).where(Heartbeat.received_at < now - timedelta(days=settings.heartbeat_retention_days)),
            ),
            (
                "deleted_reports",
                delete(ActivityReport).where(ActivityReport.received_at < now - timedelta(days=settings.report_retention_days)),
            ),
            (
                "deleted_audit_logs",
                delete(AuditLog).where(AuditLog.created_at < now - timedelta(days=settings.audit_retention_days)),
            ),
            (
                "deleted_outbox_rows",
                delete(NotificationOutbox).where(
                    NotificationOutbox.sent_at.is_not(None),
                    NotificationOutbox.sent_at < now - timedelta(days=settings.outbox_retention_days),
                ),
            ),
        ]
        for attribute, statement in operations:
            deleted = db.execute(statement)
            setattr(result, attribute, int(deleted.rowcount or 0))
        db.commit()
        db.execute(text("PRAGMA optimize"))
    return result


def database_summary(settings: Settings) -> dict[str, object]:
    path = sqlite_path(settings.database_url)
    database = Database(settings)
    with database.session_factory() as db:
        counts = {
            "devices": int(db.scalar(select(text("COUNT(*)")).select_from(text("devices"))) or 0),
            "heartbeats": int(db.scalar(select(text("COUNT(*)")).select_from(text("heartbeats"))) or 0),
            "reports": int(db.scalar(select(text("COUNT(*)")).select_from(text("activity_reports"))) or 0),
            "audit_logs": int(db.scalar(select(text("COUNT(*)")).select_from(text("audit_logs"))) or 0),
            "outbox_pending": int(
                db.scalar(
                    select(text("COUNT(*)"))
                    .select_from(text("notification_outbox"))
                    .where(text("sent_at IS NULL"))
                )
                or 0
            ),
        }
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "counts": counts,
    }


def write_maintenance_status(settings: Settings, payload: dict[str, object]) -> None:
    write_json(Path(settings.data_dir) / "maintenance-status.json", payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Remote Server backup and maintenance commands")
    sub = parser.add_subparsers(dest="command", required=True)
    backup_parser = sub.add_parser("backup")
    backup_parser.add_argument("destination", nargs="?")
    restore_parser = sub.add_parser("restore")
    restore_parser.add_argument("source")
    sub.add_parser("prune")
    sub.add_parser("summary")
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("source")
    args = parser.parse_args()
    settings = Settings.from_env()
    settings.validate()

    if args.command == "backup":
        path = backup(settings, Path(args.destination) if args.destination else None)
        removed = rotate_backups(settings)
        payload = {
            "status": "ok",
            "last_backup": str(path),
            "last_backup_size": path.stat().st_size,
            "removed_backups": [str(item) for item in removed],
        }
        write_maintenance_status(settings, payload)
        print(path)
    elif args.command == "restore":
        print(restore(settings, Path(args.source)))
    elif args.command == "prune":
        result = prune(settings)
        payload = {"status": "ok", "last_maintenance": asdict(result)}
        write_maintenance_status(settings, payload)
        print(json.dumps(asdict(result), sort_keys=True))
    elif args.command == "summary":
        print(json.dumps(database_summary(settings), sort_keys=True))
    else:
        verify_backup(Path(args.source))
        print("ok")


if __name__ == "__main__":
    main()
