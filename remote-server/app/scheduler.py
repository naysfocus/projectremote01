from __future__ import annotations

import fcntl
import logging
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import Settings
from app.maintenance import backup, database_summary, prune, rotate_backups
from app.status_files import read_json, write_json

LOGGER = logging.getLogger("remote_server.scheduler")


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def run_once(settings: Settings) -> dict[str, object]:
    data_dir = Path(settings.data_dir)
    status_path = data_dir / "scheduler-status.json"
    previous = read_json(status_path)
    now = datetime.now(timezone.utc)
    last_backup = _parse_time(previous.get("last_backup_at"))
    backup_due = last_backup is None or now - last_backup >= timedelta(hours=settings.backup_interval_hours)

    payload: dict[str, object] = {
        "status": "ok",
        "last_run_at": now.isoformat(),
        "backup_interval_hours": settings.backup_interval_hours,
        "backup_retention_count": settings.backup_retention_count,
    }
    maintenance_result = prune(settings)
    payload["last_maintenance"] = asdict(maintenance_result)
    payload["database"] = database_summary(settings)

    if backup_due:
        path = backup(settings)
        removed = rotate_backups(settings)
        payload["last_backup_at"] = now.isoformat()
        payload["last_backup_file"] = path.name
        payload["last_backup_size"] = path.stat().st_size
        payload["removed_backups"] = [item.name for item in removed]
    else:
        for key in ("last_backup_at", "last_backup_file", "last_backup_size"):
            if key in previous:
                payload[key] = previous[key]

    write_json(status_path, payload)
    return payload


def main() -> None:
    settings = Settings.from_env()
    settings.validate()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    lock_path = data_dir / ".scheduler.lock"
    with lock_path.open("w", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another scheduler instance is already running.") from exc
        while True:
            try:
                payload = run_once(settings)
                LOGGER.info("Scheduled maintenance completed: %s", payload)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Scheduled maintenance failed")
                write_json(
                    data_dir / "scheduler-status.json",
                    {"status": "error", "last_error": str(exc)[:1000]},
                )
            time.sleep(settings.maintenance_interval_minutes * 60)


if __name__ == "__main__":
    main()
