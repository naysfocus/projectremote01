from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from sqlalchemy import select

from app.maintenance import backup, prune, restore, rotate_backups, verify_backup
from app.models import Heartbeat
from app.scheduler import run_once
from app.utils import utcnow


def test_backup_verify_and_restore(app, settings, tmp_path):
    original = Path(settings.database_url.removeprefix("sqlite:///"))
    backup_path = backup(settings, tmp_path / "backup.sqlite3")
    verify_backup(backup_path)
    assert backup_path.exists()
    assert backup_path.with_suffix(".sqlite3.sha256").exists()

    original.write_bytes(b"not-a-database")
    safety = restore(settings, backup_path)
    assert safety.exists()
    verify_backup(original)


def test_scheduler_creates_status_and_rotates(app, settings):
    settings.backup_retention_count = 2
    first = run_once(settings)
    assert first["status"] == "ok"
    assert (Path(settings.data_dir) / "scheduler-status.json").exists()
    assert len(list((Path(settings.data_dir) / "backups").glob("remote-server-*.sqlite3"))) == 1


def test_prune_old_heartbeats(app, settings):
    settings.heartbeat_retention_days = 30
    with app.state.database.session_factory() as db:
        db.add(Heartbeat(device_id=999, app_type="matrix_generator", received_at=utcnow() - timedelta(days=31)))
        # Foreign keys are enforced; create a minimal device through raw SQL for this focused test.
        db.rollback()
        db.execute(
            __import__("sqlalchemy").text(
                "INSERT INTO devices (id, fingerprint_hash, first_seen_at) VALUES (999, :fp, :seen)"
            ),
            {"fp": "f" * 64, "seen": utcnow()},
        )
        db.add(Heartbeat(device_id=999, app_type="matrix_generator", received_at=utcnow() - timedelta(days=31)))
        db.commit()
    result = prune(settings)
    assert result.deleted_heartbeats == 1
    with app.state.database.session_factory() as db:
        assert db.scalar(select(Heartbeat).where(Heartbeat.device_id == 999)) is None
