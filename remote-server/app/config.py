from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


def _load_runtime_env() -> None:
    runtime_file = Path(os.getenv("RUNTIME_CONFIG_FILE", "/data/runtime.env"))
    if not runtime_file.exists():
        return
    for raw_line in runtime_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            os.environ.setdefault(key, value.strip())


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise RuntimeError(f"{name} must be true or false.")


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        return int(raw) if raw not in (None, "") else default
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc


def _cookie_mode() -> str:
    raw = os.getenv("SESSION_COOKIE_SECURE", "auto").strip().lower()
    if raw == "auto":
        return "auto"
    if raw in TRUE_VALUES:
        return "always"
    if raw in FALSE_VALUES:
        return "never"
    raise RuntimeError("SESSION_COOKIE_SECURE must be auto, true, or false.")


def _cookie_secure(public_base_url: str, mode: str) -> bool:
    if mode == "always":
        return True
    if mode == "never":
        return False
    return public_base_url.strip().lower().startswith("https://")


@dataclass(slots=True)
class Settings:
    app_name: str = "Remote Server"
    environment: str = "production"
    database_url: str = "sqlite:////data/auth.db"
    secret_key: str = "change-me"
    session_cookie_name: str = "remote_server_admin_session"
    session_cookie_secure: bool = False
    session_cookie_secure_mode: str = "auto"
    session_timeout_seconds: int = 900
    heartbeat_interval_seconds: int = 300
    grace_period_hours: int = 3
    activation_key_ttl_hours: int = 1
    admin_username: str = "admin"
    admin_password: str = ""
    bootstrap_admin_telegram_id: str = ""
    telegram_bot_token: str = ""
    cloudflare_tunnel_token: str = ""
    public_base_url: str = "http://localhost:8800"
    trusted_proxy_headers: bool = True
    log_level: str = "INFO"
    data_dir: str = "/data"
    backup_interval_hours: int = 24
    backup_retention_count: int = 14
    maintenance_interval_minutes: int = 60
    heartbeat_retention_days: int = 30
    report_retention_days: int = 365
    audit_retention_days: int = 365
    outbox_retention_days: int = 30
    display_timezone: str = "Asia/Jakarta"

    @classmethod
    def from_env(cls) -> "Settings":
        _load_runtime_env()
        defaults = cls()
        public_base_url = os.getenv("PUBLIC_BASE_URL", defaults.public_base_url).strip().rstrip("/")
        cookie_mode = _cookie_mode()
        return cls(
            app_name=os.getenv("APP_NAME", defaults.app_name),
            environment=os.getenv("ENVIRONMENT", defaults.environment),
            database_url=os.getenv("DATABASE_URL", defaults.database_url),
            secret_key=os.getenv("SECRET_KEY", defaults.secret_key),
            session_cookie_name=os.getenv("SESSION_COOKIE_NAME", defaults.session_cookie_name),
            session_cookie_secure=_cookie_secure(public_base_url, cookie_mode),
            session_cookie_secure_mode=cookie_mode,
            session_timeout_seconds=_int("SESSION_TIMEOUT_SECONDS", defaults.session_timeout_seconds),
            heartbeat_interval_seconds=_int("HEARTBEAT_INTERVAL_SECONDS", defaults.heartbeat_interval_seconds),
            grace_period_hours=_int("GRACE_PERIOD_HOURS", defaults.grace_period_hours),
            activation_key_ttl_hours=_int("ACTIVATION_KEY_TTL_HOURS", defaults.activation_key_ttl_hours),
            admin_username=os.getenv("ADMIN_USERNAME", defaults.admin_username).strip(),
            admin_password=os.getenv("ADMIN_PASSWORD", defaults.admin_password),
            bootstrap_admin_telegram_id=os.getenv(
                "BOOTSTRAP_ADMIN_TELEGRAM_ID", defaults.bootstrap_admin_telegram_id
            ).strip(),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", defaults.telegram_bot_token).strip(),
            cloudflare_tunnel_token=os.getenv("CLOUDFLARE_TUNNEL_TOKEN", defaults.cloudflare_tunnel_token).strip(),
            public_base_url=public_base_url,
            trusted_proxy_headers=_bool("TRUSTED_PROXY_HEADERS", defaults.trusted_proxy_headers),
            log_level=os.getenv("LOG_LEVEL", defaults.log_level),
            data_dir=os.getenv("DATA_DIR", defaults.data_dir),
            backup_interval_hours=_int("BACKUP_INTERVAL_HOURS", defaults.backup_interval_hours),
            backup_retention_count=_int("BACKUP_RETENTION_COUNT", defaults.backup_retention_count),
            maintenance_interval_minutes=_int("MAINTENANCE_INTERVAL_MINUTES", defaults.maintenance_interval_minutes),
            heartbeat_retention_days=_int("HEARTBEAT_RETENTION_DAYS", defaults.heartbeat_retention_days),
            report_retention_days=_int("REPORT_RETENTION_DAYS", defaults.report_retention_days),
            audit_retention_days=_int("AUDIT_RETENTION_DAYS", defaults.audit_retention_days),
            outbox_retention_days=_int("OUTBOX_RETENTION_DAYS", defaults.outbox_retention_days),
            display_timezone=os.getenv("DISPLAY_TIMEZONE", defaults.display_timezone).strip() or defaults.display_timezone,
        )

    def validate(self) -> None:
        if self.environment == "production":
            if (
                self.secret_key in {"", "change-me", "changeme"}
                or self.secret_key.upper().startswith("REPLACE_")
                or len(self.secret_key) < 32
            ):
                raise RuntimeError("SECRET_KEY must be a random value of at least 32 characters.")
            if (
                not self.admin_password
                or self.admin_password.upper().startswith("REPLACE_")
                or len(self.admin_password) < 12
            ):
                raise RuntimeError("ADMIN_PASSWORD must contain at least 12 characters.")
        if not self.admin_username:
            raise RuntimeError("ADMIN_USERNAME cannot be empty.")
        if self.session_cookie_secure_mode not in {"auto", "always", "never"}:
            raise RuntimeError("Invalid session cookie secure mode.")
        if self.session_timeout_seconds <= self.heartbeat_interval_seconds:
            raise RuntimeError("SESSION_TIMEOUT_SECONDS must be greater than HEARTBEAT_INTERVAL_SECONDS.")
        if self.grace_period_hours < 0:
            raise RuntimeError("GRACE_PERIOD_HOURS cannot be negative.")
        if self.activation_key_ttl_hours < 1:
            raise RuntimeError("ACTIVATION_KEY_TTL_HOURS must be at least 1.")
        if self.backup_interval_hours < 1:
            raise RuntimeError("BACKUP_INTERVAL_HOURS must be at least 1.")
        if self.backup_retention_count < 2:
            raise RuntimeError("BACKUP_RETENTION_COUNT must be at least 2.")
        if self.maintenance_interval_minutes < 5:
            raise RuntimeError("MAINTENANCE_INTERVAL_MINUTES must be at least 5.")
        for name, value in {
            "HEARTBEAT_RETENTION_DAYS": self.heartbeat_retention_days,
            "REPORT_RETENTION_DAYS": self.report_retention_days,
            "AUDIT_RETENTION_DAYS": self.audit_retention_days,
            "OUTBOX_RETENTION_DAYS": self.outbox_retention_days,
        }.items():
            if value < 1:
                raise RuntimeError(f"{name} must be at least 1.")
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(self.display_timezone)
        except Exception as exc:
            raise RuntimeError("DISPLAY_TIMEZONE must be a valid IANA timezone.") from exc
        parsed = urlparse(self.public_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError("PUBLIC_BASE_URL must be a valid http:// or https:// URL.")

    @property
    def database_kind(self) -> str:
        if self.database_url.startswith("sqlite"):
            return "SQLite"
        return self.database_url.split(":", 1)[0].upper()

    def ensure_sqlite_parent(self) -> None:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            return
        raw_path = self.database_url[len(prefix) :]
        if raw_path == ":memory:":
            return
        Path(raw_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
