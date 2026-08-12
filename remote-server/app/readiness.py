from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import Settings
from app.integration_store import (
    IntegrationConfigurationError,
    get_or_create_config,
    integration_status,
    test_public_health,
)
from app.maintenance import verify_backup
from app.status_files import read_json, write_json

BACKUP_PREFIXES = ("remote-server-", "scaleup-")


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


def _fresh(value: object, seconds: int) -> bool:
    parsed = _parse_time(value)
    if parsed is None:
        return False
    return (datetime.now(timezone.utc) - parsed).total_seconds() <= seconds


def _check(name: str, passed: bool, detail: str, *, critical: bool = True) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail, "critical": critical}


def run_readiness(db: Session, settings: Settings) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    try:
        db.execute(text("SELECT 1"))
        checks.append(_check("Database", True, "SQLite dapat dibaca dan ditulis."))
    except Exception as exc:  # noqa: BLE001
        checks.append(_check("Database", False, f"Database bermasalah: {exc}"))

    scheduler = read_json(Path(settings.data_dir) / "scheduler-status.json")
    scheduler_ok = scheduler.get("status") == "ok" and _fresh(scheduler.get("updated_at"), 7200)
    checks.append(
        _check(
            "Scheduler",
            scheduler_ok,
            "Backup dan maintenance berjalan." if scheduler_ok else "Status scheduler tidak segar atau sedang error.",
        )
    )

    integration = integration_status(settings)
    manager_ok = _fresh(integration.get("updated_at"), 180)
    checks.append(
        _check(
            "Integration manager",
            manager_ok,
            "Pengelola integrasi aktif." if manager_ok else "Status integration manager tidak diperbarui.",
        )
    )

    config = get_or_create_config(db)
    public_url = config.public_base_url or settings.public_base_url
    public_https = public_url.startswith("https://")
    checks.append(
        _check(
            "Alamat HTTPS",
            public_https,
            public_url if public_https else "Hostname publik HTTPS belum valid.",
        )
    )

    cookie_ok = settings.session_cookie_secure_mode in {"auto", "always"}
    checks.append(
        _check(
            "Cookie login",
            cookie_ok,
            "Secure otomatis pada akses HTTPS." if cookie_ok else "Cookie Secure dinonaktifkan.",
        )
    )

    cloudflare = integration.get("cloudflare") if isinstance(integration.get("cloudflare"), dict) else {}
    cloudflare_ok = bool(config.cloudflare_enabled and cloudflare.get("connected"))
    checks.append(
        _check(
            "Cloudflare Tunnel",
            cloudflare_ok,
            "Connector terhubung." if cloudflare_ok else "Tunnel belum terhubung.",
        )
    )

    telegram = integration.get("telegram") if isinstance(integration.get("telegram"), dict) else {}
    telegram_ok = bool(config.telegram_enabled and telegram.get("running") and config.telegram_admin_id)
    checks.append(
        _check(
            "Telegram Bot",
            telegram_ok,
            "Bot berjalan dan admin terpasang." if telegram_ok else "Bot atau admin Telegram belum siap.",
        )
    )

    backup_dir = Path(settings.data_dir) / "backups"
    backups = sorted(
        [p for p in backup_dir.glob("*.sqlite3") if p.name.startswith(BACKUP_PREFIXES)],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    backup_ok = False
    backup_detail = "Belum ada backup terverifikasi."
    if backups:
        try:
            verify_backup(backups[0])
            backup_ok = True
            backup_detail = f"Backup terbaru valid: {backups[0].name}"
        except Exception as exc:  # noqa: BLE001
            backup_detail = f"Backup terbaru rusak: {exc}"
    checks.append(_check("Backup", backup_ok, backup_detail))

    public_health_ok = False
    public_health_detail = "Uji domain belum dijalankan."
    if public_https:
        try:
            test_public_health(public_url)
            public_health_ok = True
            public_health_detail = "Domain HTTPS mencapai endpoint health server."
        except IntegrationConfigurationError as exc:
            public_health_detail = str(exc)
    checks.append(_check("Uji domain publik", public_health_ok, public_health_detail))

    ready = all(item["passed"] for item in checks if item["critical"])
    payload = {"status": "ready" if ready else "attention", "ready": ready, "checks": checks}
    write_json(Path(settings.data_dir) / "readiness-status.json", payload)
    return read_json(Path(settings.data_dir) / "readiness-status.json")
