from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from app.config import Settings
from app.database import Database
from app.integration_store import get_or_create_config, get_secrets, redact_sensitive
from app.status_files import write_json

LOGGER = logging.getLogger("integration_manager")


@dataclass
class ManagedProcess:
    name: str
    process: subprocess.Popen[str] | None = None
    log_handle: TextIO | None = None
    started_at: float | None = None

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process = None
        self.started_at = None
        if self.log_handle is not None:
            self.log_handle.close()
            self.log_handle = None

    def start(self, command: list[str], log_path: Path) -> None:
        self.stop()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Overwrite old logs so credentials leaked by older versions do not persist.
        self.log_handle = log_path.open("w", encoding="utf-8", buffering=1)
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=self.log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        self.started_at = time.time()

    @property
    def alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    @property
    def exit_code(self) -> int | None:
        return None if self.process is None else self.process.poll()


def _tail(path: Path, limit: int = 40) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [redact_sensitive(line) or "" for line in lines[-limit:]]


def _cloudflare_connected(lines: list[str]) -> bool:
    content = "\n".join(lines).lower()
    return any(
        marker in content
        for marker in (
            "registered tunnel connection",
            "connection registered",
            "registered connection",
        )
    )


def _cloudflare_problem(lines: list[str], *, running: bool, connected: bool) -> tuple[str, str]:
    content = "\n".join(lines).lower()
    if connected:
        return "connected", "Connector terhubung ke jaringan Cloudflare."
    if "both udp and tcp fail" in content or "environment has critical failures" in content:
        return (
            "port_7844_blocked",
            "Koneksi keluar TCP dan UDP port 7844 diblokir. Periksa firewall, WARP, atau aturan jaringan VPS.",
        )
    if "allow outbound tcp on port 7844" in content and "allow outbound quic" in content:
        return (
            "port_7844_blocked",
            "Koneksi keluar TCP dan UDP port 7844 diblokir. Periksa firewall, WARP, atau aturan jaringan VPS.",
        )
    if "switching to fallback protocol http2" in content:
        return (
            "quic_unavailable",
            "QUIC tidak tersedia; connector sedang mencoba HTTP/2. Ini normal bila HTTP/2 kemudian terhubung.",
        )
    if "unauthorized" in content or "invalid tunnel secret" in content or "failed to parse token" in content:
        return "invalid_token", "Tunnel Token ditolak. Buat atau rotasi token baru di Cloudflare."
    if "no ingress rules were defined" in content:
        return "route_missing", "Connector aktif, tetapi Published application belum dibuat di Cloudflare."
    if running:
        return "connecting", "Connector berjalan dan sedang mencoba terhubung."
    return "stopped", "Connector belum berjalan atau berhenti karena konfigurasi/koneksi gagal."


def _cloudflare_command(protocol: str, token_file: Path) -> list[str]:
    return [
        "/usr/local/bin/cloudflared",
        "tunnel",
        "--no-autoupdate",
        "--loglevel",
        "info",
        "--protocol",
        protocol,
        "run",
        "--token-file",
        str(token_file),
    ]


def main() -> None:
    settings = Settings.from_env()
    settings.validate()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    database = Database(settings)
    data_dir = Path(settings.data_dir)
    status_file = data_dir / "integration-status.json"
    logs_dir = data_dir / "integration-logs"
    telegram_log = logs_dir / "telegram.log"
    cloudflare_log = logs_dir / "cloudflared.log"
    cloudflare_token_file = Path("/tmp/remote-server-cloudflare-token")
    telegram = ManagedProcess("telegram")
    cloudflare = ManagedProcess("cloudflare")
    shutting_down = False

    def stop_all(_signum: int | None = None, _frame=None) -> None:  # type: ignore[no-untyped-def]
        nonlocal shutting_down
        shutting_down = True
        telegram.stop()
        cloudflare.stop()
        cloudflare_token_file.unlink(missing_ok=True)

    signal.signal(signal.SIGTERM, stop_all)
    signal.signal(signal.SIGINT, stop_all)

    applied_revision: int | None = None
    telegram_enabled = False
    cloudflare_enabled = False
    cloudflare_protocol = "auto"
    secrets = None

    while not shutting_down:
        error: str | None = None
        try:
            with database.session_factory() as db:
                config = get_or_create_config(db)
                db.commit()
                db.refresh(config)
                secrets = get_secrets(db, settings)
                revision = config.revision
                telegram_enabled = bool(config.telegram_enabled and secrets.telegram_token)
                cloudflare_enabled = bool(config.cloudflare_enabled and secrets.cloudflare_token)
                cloudflare_protocol = config.cloudflare_protocol or "auto"

            if revision != applied_revision:
                LOGGER.info("Applying integration configuration revision %s", revision)
                telegram.stop()
                cloudflare.stop()
                if telegram_enabled:
                    telegram.start([sys.executable, "-m", "app.bot"], telegram_log)
                if cloudflare_enabled:
                    cloudflare_token_file.write_text(secrets.cloudflare_token + "\n", encoding="utf-8")
                    cloudflare_token_file.chmod(0o600)
                    cloudflare.start(
                        _cloudflare_command(cloudflare_protocol, cloudflare_token_file),
                        cloudflare_log,
                    )
                else:
                    cloudflare_token_file.unlink(missing_ok=True)
                applied_revision = revision

            if telegram_enabled and not telegram.alive:
                LOGGER.warning("Telegram worker stopped; restarting")
                telegram.start([sys.executable, "-m", "app.bot"], telegram_log)
            if cloudflare_enabled and not cloudflare.alive and secrets is not None:
                LOGGER.warning("Cloudflare connector stopped; restarting")
                cloudflare_token_file.write_text(secrets.cloudflare_token + "\n", encoding="utf-8")
                cloudflare_token_file.chmod(0o600)
                cloudflare.start(
                    _cloudflare_command(cloudflare_protocol, cloudflare_token_file),
                    cloudflare_log,
                )

            telegram_lines = _tail(telegram_log)
            cloudflare_lines = _tail(cloudflare_log)
            connected = cloudflare.alive and _cloudflare_connected(cloudflare_lines)
            problem_code, guidance = _cloudflare_problem(
                cloudflare_lines,
                running=cloudflare.alive,
                connected=connected,
            )
            write_json(
                status_file,
                {
                    "status": "ok",
                    "revision": applied_revision,
                    "manager_pid": os.getpid(),
                    "telegram": {
                        "configured": bool(secrets and secrets.telegram_token),
                        "enabled": telegram_enabled,
                        "running": telegram.alive,
                        "pid": telegram.process.pid if telegram.alive and telegram.process else None,
                        "exit_code": telegram.exit_code,
                        "last_log": telegram_lines[-1] if telegram_lines else None,
                        "recent_logs": telegram_lines[-8:],
                    },
                    "cloudflare": {
                        "configured": bool(secrets and secrets.cloudflare_token),
                        "enabled": cloudflare_enabled,
                        "running": cloudflare.alive,
                        "connected": connected,
                        "protocol": cloudflare_protocol,
                        "problem_code": problem_code,
                        "guidance": guidance,
                        "pid": cloudflare.process.pid if cloudflare.alive and cloudflare.process else None,
                        "exit_code": cloudflare.exit_code,
                        "last_log": cloudflare_lines[-1] if cloudflare_lines else None,
                        "recent_logs": cloudflare_lines[-8:],
                    },
                    "last_error": error,
                },
            )
        except Exception as exc:  # noqa: BLE001
            error = redact_sensitive(str(exc)[:1000])
            LOGGER.exception("Integration manager iteration failed")
            write_json(
                status_file,
                {
                    "status": "error",
                    "revision": applied_revision,
                    "manager_pid": os.getpid(),
                    "last_error": error,
                },
            )
        for _ in range(10):
            if shutting_down:
                break
            time.sleep(1)

    stop_all()


if __name__ == "__main__":
    main()
