from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AdminTelegramUser, IntegrationConfig, utcnow
from app.status_files import read_json

TELEGRAM_TOKEN_RE = re.compile(r"^[0-9]{6,15}:[A-Za-z0-9_-]{20,}$")
TELEGRAM_TOKEN_FIND_RE = re.compile(r"[0-9]{6,15}:[A-Za-z0-9_-]{20,}")
TELEGRAM_ID_RE = re.compile(r"^-?[0-9]{5,20}$")
CLOUDFLARE_TOKEN_FIND_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{70,}\b")
CLOUDFLARE_PROTOCOLS = {"auto", "http2", "quic"}
LOCAL_PUBLIC_URL = "http://100.113.142.11:8800"


class IntegrationConfigurationError(ValueError):
    pass


@dataclass(slots=True)
class IntegrationSecrets:
    telegram_token: str = ""
    cloudflare_token: str = ""


def _fernet(settings: Settings) -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(settings: Settings, value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    return _fernet(settings).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(settings: Settings, value: str | None) -> str:
    if not value:
        return ""
    try:
        return _fernet(settings).decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
        raise IntegrationConfigurationError("Secret integrasi tidak dapat dibuka.") from exc


def mask_secret(value: str | None) -> str:
    if not value:
        return "Belum disimpan"
    if len(value) <= 10:
        return "••••••••"
    return f"{value[:4]}••••••••{value[-4:]}"


def redact_sensitive(value: str | None) -> str | None:
    if not value:
        return value
    value = TELEGRAM_TOKEN_FIND_RE.sub("<telegram-token-disamarkan>", value)
    value = CLOUDFLARE_TOKEN_FIND_RE.sub("<cloudflare-token-disamarkan>", value)
    return value


def get_or_create_config(db: Session) -> IntegrationConfig:
    config = db.get(IntegrationConfig, 1)
    if config is not None:
        return config
    config = IntegrationConfig(id=1)
    db.add(config)
    try:
        db.flush()
        return config
    except IntegrityError:
        db.rollback()
        existing = db.get(IntegrationConfig, 1)
        if existing is None:
            raise
        return existing


def get_secrets(db: Session, settings: Settings) -> IntegrationSecrets:
    config = get_or_create_config(db)
    return IntegrationSecrets(
        telegram_token=decrypt_secret(settings, config.telegram_token_encrypted),
        cloudflare_token=decrypt_secret(settings, config.cloudflare_token_encrypted),
    )


def validate_telegram_token(token: str) -> str:
    token = token.strip()
    if not TELEGRAM_TOKEN_RE.fullmatch(token):
        raise IntegrationConfigurationError("Format token Telegram tidak valid.")
    return token


def validate_telegram_admin_id(value: str) -> str:
    value = value.strip()
    if not TELEGRAM_ID_RE.fullmatch(value):
        raise IntegrationConfigurationError("Telegram Admin ID harus berupa angka.")
    return value


def extract_cloudflare_token(value: str) -> str:
    """Accept either a raw token or the full command copied from Cloudflare."""
    value = value.strip()
    if not value:
        return ""
    match = CLOUDFLARE_TOKEN_FIND_RE.search(value)
    token = match.group(0) if match else value
    if len(token) < 80 or any(char.isspace() for char in token) or not token.startswith("eyJ"):
        raise IntegrationConfigurationError(
            "Token Cloudflare tidak valid. Tempel token eyJ... atau seluruh perintah Docker dari Cloudflare."
        )
    return token


def validate_cloudflare_protocol(value: str) -> str:
    value = value.strip().lower() or "auto"
    if value not in CLOUDFLARE_PROTOCOLS:
        raise IntegrationConfigurationError("Mode Cloudflare harus Auto, HTTP/2, atau QUIC.")
    return value


def normalize_public_url(value: str, *, allow_blank: bool = True) -> str:
    value = value.strip().rstrip("/")
    if not value:
        if allow_blank:
            return ""
        raise IntegrationConfigurationError("Hostname publik belum diisi.")
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise IntegrationConfigurationError(
            "Hostname publik tidak valid. Isi contoh: remote.domainkamu.com"
        )
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise IntegrationConfigurationError("Hostname publik tidak boleh berisi path, query, atau fragment.")
    return value


def validate_public_url(value: str, require_https: bool = False) -> str:
    value = value.strip().rstrip("/")
    parsed = urlparse(value)
    allowed = {"https"} if require_https else {"http", "https"}
    if parsed.scheme not in allowed or not parsed.netloc or parsed.username or parsed.password:
        hint = "https://" if require_https else "http:// atau https://"
        raise IntegrationConfigurationError(f"Public URL harus berupa alamat {hint} yang valid.")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise IntegrationConfigurationError("Public URL tidak boleh memiliki path, query, atau fragment.")
    return value


def save_telegram(
    db: Session,
    settings: Settings,
    *,
    enabled: bool,
    token: str,
    admin_id: str,
    admin_user_id: int,
    bot_username: str | None = None,
) -> IntegrationConfig:
    config = get_or_create_config(db)
    token = token.strip()
    admin_id = admin_id.strip()
    if token:
        config.telegram_token_encrypted = encrypt_secret(settings, validate_telegram_token(token))
    if enabled and not config.telegram_token_encrypted:
        raise IntegrationConfigurationError("Simpan token Telegram sebelum mengaktifkan bot.")
    if admin_id:
        config.telegram_admin_id = validate_telegram_admin_id(admin_id)
        config.telegram_pair_code = None
        config.telegram_pair_expires_at = None
    elif enabled and not config.telegram_admin_id:
        config.telegram_pair_code = f"{secrets.randbelow(100_000_000):08d}"
        config.telegram_pair_expires_at = utcnow() + timedelta(minutes=20)
    elif not enabled:
        config.telegram_pair_code = None
        config.telegram_pair_expires_at = None
    if bot_username is not None:
        config.telegram_bot_username = bot_username.strip().lstrip("@") or None
    config.telegram_enabled = enabled
    config.revision += 1
    config.updated_at = utcnow()
    config.updated_by_admin_id = admin_user_id
    if config.telegram_admin_id:
        telegram_admin = db.get(AdminTelegramUser, config.telegram_admin_id)
        if telegram_admin is None:
            db.add(AdminTelegramUser(telegram_id=config.telegram_admin_id, role="admin"))
    db.commit()
    db.refresh(config)
    return config


def clear_telegram(db: Session, *, admin_user_id: int) -> IntegrationConfig:
    config = get_or_create_config(db)
    config.telegram_enabled = False
    config.telegram_token_encrypted = None
    config.telegram_bot_username = None
    config.telegram_pair_code = None
    config.telegram_pair_expires_at = None
    config.revision += 1
    config.updated_at = utcnow()
    config.updated_by_admin_id = admin_user_id
    db.commit()
    db.refresh(config)
    return config


def save_cloudflare(
    db: Session,
    settings: Settings,
    *,
    enabled: bool,
    token: str,
    public_base_url: str,
    protocol: str,
    admin_user_id: int,
) -> IntegrationConfig:
    config = get_or_create_config(db)
    token = token.strip()
    if token:
        config.cloudflare_token_encrypted = encrypt_secret(settings, extract_cloudflare_token(token))
    if enabled and not config.cloudflare_token_encrypted:
        raise IntegrationConfigurationError("Tempel Tunnel Token sebelum mengaktifkan connector.")
    normalized_url = normalize_public_url(public_base_url, allow_blank=True)
    if normalized_url:
        config.public_base_url = normalized_url
    elif not config.public_base_url:
        config.public_base_url = LOCAL_PUBLIC_URL
    config.cloudflare_protocol = validate_cloudflare_protocol(protocol)
    config.cloudflare_enabled = enabled
    config.revision += 1
    config.updated_at = utcnow()
    config.updated_by_admin_id = admin_user_id
    db.commit()
    db.refresh(config)
    return config


def clear_cloudflare(db: Session, *, admin_user_id: int) -> IntegrationConfig:
    config = get_or_create_config(db)
    config.cloudflare_enabled = False
    config.cloudflare_token_encrypted = None
    config.cloudflare_protocol = "auto"
    config.public_base_url = LOCAL_PUBLIC_URL
    config.revision += 1
    config.updated_at = utcnow()
    config.updated_by_admin_id = admin_user_id
    db.commit()
    db.refresh(config)
    return config


def telegram_api(token: str, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    token = validate_telegram_token(token)
    body = None
    headers: dict[str, str] = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=body,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("description", str(exc))
        except Exception:
            detail = str(exc)
        raise IntegrationConfigurationError(f"Telegram menolak permintaan: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise IntegrationConfigurationError(f"Tidak dapat terhubung ke Telegram: {exc}") from exc
    if not result.get("ok"):
        raise IntegrationConfigurationError(str(result.get("description") or "Telegram API error"))
    return result


def telegram_get_me(token: str) -> dict[str, Any]:
    return dict(telegram_api(token, "getMe").get("result") or {})


def telegram_send_test(token: str, admin_id: str) -> None:
    telegram_api(
        token,
        "sendMessage",
        {
            "chat_id": validate_telegram_admin_id(admin_id),
            "text": "✅ Remote Server berhasil terhubung ke Telegram.",
        },
    )


def test_public_health(public_base_url: str) -> dict[str, Any]:
    base_url = normalize_public_url(public_base_url, allow_blank=False)
    request = urllib.request.Request(
        f"{base_url}/health",
        headers={"User-Agent": "Remote-Server/1.7"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
            status = response.status
    except urllib.error.HTTPError as exc:
        raise IntegrationConfigurationError(f"Domain merespons HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise IntegrationConfigurationError(f"Domain belum dapat menjangkau server: {exc}") from exc
    if status != 200 or not payload.get("ok"):
        raise IntegrationConfigurationError("Domain merespons, tetapi health check tidak valid.")
    return payload


def integration_status(settings: Settings) -> dict[str, Any]:
    result = read_json(Path(settings.data_dir) / "integration-status.json")
    for key in ("last_error",):
        result[key] = redact_sensitive(result.get(key))
    for name in ("telegram", "cloudflare"):
        section = result.get(name)
        if isinstance(section, dict):
            section["last_log"] = redact_sensitive(section.get("last_log"))
            if isinstance(section.get("recent_logs"), list):
                section["recent_logs"] = [redact_sensitive(item) for item in section["recent_logs"]]
    return result


def iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
