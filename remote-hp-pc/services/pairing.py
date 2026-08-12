"""Secure pairing and mobile-client authentication for Remote HP v1.50.

Pairing codes are short-lived, one-time credentials. Their HMAC digest is stored
in SQLite; the plaintext is returned only once to the local Super Admin. Mobile
bearer tokens are high-entropy values and only their SHA-256 digest is stored.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from database import db

PAIRING_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
PAIRING_CODE_LENGTH = 8
DEFAULT_PAIRING_MINUTES = 10
MAX_PAIRING_MINUTES = 30
AUTH_CACHE_SECONDS = 15.0
LAST_SEEN_WRITE_SECONDS = 60.0
_TOKEN_PREFIX = "rhp1_"
_UUID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")

_cache_lock = threading.RLock()
_auth_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
_last_seen_write: Dict[int, float] = {}


class PairingError(Exception):
    def __init__(self, message: str, status_code: int = 400, **extra: Any):
        super().__init__(message)
        self.status_code = status_code
        self.payload = {"ok": False, "error": message, **extra}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _secret_path() -> Path:
    configured = (os.environ.get("REMOTE_HP_PAIRING_SECRET_FILE") or "").strip()
    return Path(configured) if configured else Path(db.BASE_DIR) / ".remote_hp_pairing_secret"


def _pairing_secret() -> bytes:
    env_value = (os.environ.get("REMOTE_HP_PAIRING_SECRET") or "").strip()
    if env_value:
        return hashlib.sha256(env_value.encode("utf-8")).digest()

    path = _secret_path()
    try:
        raw = path.read_bytes()
        if len(raw) >= 32:
            return raw[:32]
    except FileNotFoundError:
        pass

    raw = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        fd = os.open(str(path), flags, 0o600)
        try:
            os.write(fd, raw)
        finally:
            os.close(fd)
    except FileExistsError:
        raw = path.read_bytes()[:32]
    except OSError:
        # Read-only installs can still pair during this process. Admin is warned
        # through diagnostics/documentation that active codes will not survive a
        # process restart when the secret cannot be persisted.
        return raw
    return raw


def normalize_code(value: Any) -> str:
    code = "".join(ch for ch in str(value or "").upper() if ch.isalnum())
    if len(code) != PAIRING_CODE_LENGTH or any(ch not in PAIRING_CODE_ALPHABET for ch in code):
        raise PairingError("Kode pairing tidak valid", 400)
    return code


def format_code(code: str) -> str:
    return f"{code[:4]}-{code[4:]}"


def _code_hash(code: str) -> str:
    return hmac.new(_pairing_secret(), code.encode("ascii"), hashlib.sha256).hexdigest()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _clean_uuid(value: Any) -> str:
    app_uuid = str(value or "").strip()
    if not _UUID_RE.fullmatch(app_uuid):
        raise PairingError(
            "app_device_uuid wajib 8–128 karakter dan hanya boleh berisi huruf, angka, titik, garis, titik dua, atau underscore"
        )
    return app_uuid


def _clean_label(value: Any, fallback: str, limit: int = 80) -> str:
    label = " ".join(str(value or "").strip().split())
    return (label or fallback)[:limit]


def _client_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": int(row["id"]),
        "device_id": int(row["device_id"]),
        "device_name": row.get("device_name") or "HP",
        "display_name": row.get("display_name") or "Android",
        "status": row.get("status") or "active",
        "token_prefix": row.get("token_prefix") or "",
        "paired_at": row.get("paired_at"),
        "last_seen_at": row.get("last_seen_at"),
        "revoked_at": row.get("revoked_at"),
        "app_version": row.get("app_version") or "",
        "overlay_contract_version": row.get("overlay_contract_version") or "1.0",
    }


def create_pairing_code(device_id: Any, expires_minutes: Any = DEFAULT_PAIRING_MINUTES) -> Dict[str, Any]:
    try:
        device_id = int(device_id)
        expires_minutes = int(expires_minutes or DEFAULT_PAIRING_MINUTES)
    except (TypeError, ValueError):
        raise PairingError("HP atau masa berlaku pairing tidak valid")
    if expires_minutes < 1 or expires_minutes > MAX_PAIRING_MINUTES:
        raise PairingError(f"Masa berlaku pairing harus 1–{MAX_PAIRING_MINUTES} menit")

    device = db.query("SELECT id, name FROM devices WHERE id=?", (device_id,), one=True)
    if not device:
        raise PairingError("HP tidak ditemukan", 404)

    now = _utcnow()
    expires_at = now + timedelta(minutes=expires_minutes)
    with db.transaction(immediate=True) as conn:
        # Hanya satu code aktif per HP agar operator tidak bingung. Code lama
        # dibatalkan tanpa memengaruhi client yang sudah paired.
        conn.execute(
            """UPDATE mobile_pairing_codes SET revoked_at=?
               WHERE device_id=? AND used_at IS NULL AND revoked_at IS NULL AND expires_at>?""",
            (_iso(now), device_id, _iso(now)),
        )
        for _ in range(12):
            code = "".join(secrets.choice(PAIRING_CODE_ALPHABET) for _ in range(PAIRING_CODE_LENGTH))
            digest = _code_hash(code)
            exists = conn.execute(
                "SELECT id FROM mobile_pairing_codes WHERE code_hash=?", (digest,)
            ).fetchone()
            if not exists:
                break
        else:
            raise PairingError("Gagal membuat kode pairing unik", 500)
        cur = conn.execute(
            """INSERT INTO mobile_pairing_codes
               (device_id, code_hash, code_hint, expires_at)
               VALUES (?, ?, ?, ?)""",
            (device_id, digest, code[-2:], _iso(expires_at)),
        )
        pairing_id = cur.lastrowid

    return {
        "ok": True,
        "pairing": {
            "id": pairing_id,
            "device_id": device_id,
            "device_name": device["name"],
            "code": format_code(code),
            "expires_at": _iso(expires_at),
            "expires_minutes": expires_minutes,
            "one_time": True,
        },
    }


def pair_mobile_client(
    code: Any,
    app_device_uuid: Any,
    display_name: Any = None,
    app_version: Any = None,
) -> Dict[str, Any]:
    normalized = normalize_code(code)
    app_uuid = _clean_uuid(app_device_uuid)
    now = _utcnow()
    digest = _code_hash(normalized)
    raw_token = _TOKEN_PREFIX + secrets.token_urlsafe(32)
    token_digest = token_hash(raw_token)
    token_prefix = raw_token[:12]
    display = _clean_label(display_name, "Android Remote HP")
    version = _clean_label(app_version, "", limit=40)

    with db.transaction(immediate=True) as conn:
        pairing = conn.execute(
            """SELECT p.*, d.name AS device_name
               FROM mobile_pairing_codes p
               JOIN devices d ON d.id=p.device_id
               WHERE p.code_hash=?""",
            (digest,),
        ).fetchone()
        if not pairing:
            raise PairingError("Kode pairing salah atau sudah tidak berlaku", 401)
        if pairing["used_at"]:
            raise PairingError("Kode pairing sudah digunakan", 409)
        if pairing["revoked_at"]:
            raise PairingError("Kode pairing sudah dibatalkan", 410)
        expires = _parse_iso(pairing["expires_at"])
        if not expires or expires <= now:
            raise PairingError("Kode pairing sudah kedaluwarsa", 410)

        existing = conn.execute(
            "SELECT id FROM mobile_clients WHERE app_device_uuid=?", (app_uuid,)
        ).fetchone()
        if existing:
            client_id = int(existing["id"])
            conn.execute(
                """UPDATE mobile_clients SET device_id=?, display_name=?, token_hash=?,
                   token_prefix=?, status='active', paired_at=?, last_seen_at=?,
                   revoked_at=NULL, app_version=?, overlay_contract_version='1.0'
                   WHERE id=?""",
                (
                    int(pairing["device_id"]), display, token_digest, token_prefix,
                    _iso(now), _iso(now), version, client_id,
                ),
            )
        else:
            cur = conn.execute(
                """INSERT INTO mobile_clients
                   (device_id, app_device_uuid, display_name, token_hash, token_prefix,
                    status, paired_at, last_seen_at, app_version, overlay_contract_version)
                   VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, '1.0')""",
                (
                    int(pairing["device_id"]), app_uuid, display, token_digest,
                    token_prefix, _iso(now), _iso(now), version,
                ),
            )
            client_id = cur.lastrowid
        conn.execute(
            "UPDATE mobile_pairing_codes SET used_at=? WHERE id=? AND used_at IS NULL",
            (_iso(now), int(pairing["id"])),
        )
        row = conn.execute(
            """SELECT c.*, d.name AS device_name FROM mobile_clients c
               JOIN devices d ON d.id=c.device_id WHERE c.id=?""",
            (client_id,),
        ).fetchone()

    clear_auth_cache()
    return {
        "ok": True,
        "token": raw_token,
        "token_type": "Bearer",
        "client": _client_payload(dict(row)),
        "security": {
            "token_returned_once": True,
            "store_with_android_keystore": True,
            "trusted_lan_only": True,
        },
    }


def authenticate_bearer(header_value: Any) -> Dict[str, Any]:
    header = str(header_value or "").strip()
    if not header.lower().startswith("bearer "):
        raise PairingError("Bearer token wajib dikirim", 401)
    token = header[7:].strip()
    if not token.startswith(_TOKEN_PREFIX) or len(token) < 32:
        raise PairingError("Bearer token tidak valid", 401)
    digest = token_hash(token)
    now_mono = time.monotonic()

    with _cache_lock:
        cached = _auth_cache.get(digest)
        if cached and cached[0] > now_mono:
            return dict(cached[1])
        if cached:
            _auth_cache.pop(digest, None)

    row = db.query(
        """SELECT c.*, d.name AS device_name FROM mobile_clients c
           JOIN devices d ON d.id=c.device_id
           WHERE c.token_hash=? AND c.status='active' AND c.revoked_at IS NULL""",
        (digest,),
        one=True,
    )
    if not row:
        raise PairingError("Token mobile tidak valid atau sudah dicabut", 401)
    payload = _client_payload(row)
    payload["token_hash"] = digest

    with _cache_lock:
        _auth_cache[digest] = (now_mono + AUTH_CACHE_SECONDS, dict(payload))
        last_write = _last_seen_write.get(payload["id"], 0.0)
        should_write = now_mono - last_write >= LAST_SEEN_WRITE_SECONDS
        if should_write:
            _last_seen_write[payload["id"]] = now_mono
    if should_write:
        try:
            db.execute(
                "UPDATE mobile_clients SET last_seen_at=CURRENT_TIMESTAMP WHERE id=? AND status='active'",
                (payload["id"],),
            )
        except Exception:
            # last_seen is diagnostic metadata and must never break the workflow.
            pass
    return payload


def clear_auth_cache(client_id: Optional[int] = None) -> None:
    with _cache_lock:
        if client_id is None:
            _auth_cache.clear()
            _last_seen_write.clear()
            return
        doomed = [key for key, value in _auth_cache.items() if int(value[1]["id"]) == int(client_id)]
        for key in doomed:
            _auth_cache.pop(key, None)
        _last_seen_write.pop(int(client_id), None)


def revoke_client(client_id: Any) -> Dict[str, Any]:
    try:
        client_id = int(client_id)
    except (TypeError, ValueError):
        raise PairingError("Mobile client tidak valid")
    now = _iso(_utcnow())
    with db.transaction(immediate=True) as conn:
        row = conn.execute("SELECT id, status FROM mobile_clients WHERE id=?", (client_id,)).fetchone()
        if not row:
            raise PairingError("Mobile client tidak ditemukan", 404)
        conn.execute(
            """UPDATE mobile_clients SET status='revoked', revoked_at=?, token_hash=NULL
               WHERE id=?""",
            (now, client_id),
        )
    clear_auth_cache(client_id)
    return {"ok": True, "client_id": client_id, "revoked": True}


def revoke_pairing_code(pairing_id: Any) -> Dict[str, Any]:
    try:
        pairing_id = int(pairing_id)
    except (TypeError, ValueError):
        raise PairingError("Pairing code tidak valid")
    now = _iso(_utcnow())
    with db.transaction(immediate=True) as conn:
        row = conn.execute("SELECT id, used_at FROM mobile_pairing_codes WHERE id=?", (pairing_id,)).fetchone()
        if not row:
            raise PairingError("Pairing code tidak ditemukan", 404)
        if row["used_at"]:
            raise PairingError("Pairing code sudah digunakan dan tidak perlu dibatalkan", 409)
        conn.execute(
            "UPDATE mobile_pairing_codes SET revoked_at=COALESCE(revoked_at, ?) WHERE id=?",
            (now, pairing_id),
        )
    return {"ok": True, "pairing_id": pairing_id, "revoked": True}


def pairing_status() -> Dict[str, Any]:
    now = _utcnow()
    code_rows = db.query(
        """SELECT p.id, p.device_id, p.code_hint, p.expires_at, p.used_at,
                  p.revoked_at, p.created_at, d.name AS device_name
           FROM mobile_pairing_codes p JOIN devices d ON d.id=p.device_id
           ORDER BY p.id DESC LIMIT 50"""
    )
    codes = []
    for row in code_rows:
        expires = _parse_iso(row.get("expires_at"))
        if row.get("used_at"):
            status = "used"
        elif row.get("revoked_at"):
            status = "revoked"
        elif not expires or expires <= now:
            status = "expired"
        else:
            status = "active"
        codes.append({
            "id": row["id"],
            "device_id": row["device_id"],
            "device_name": row.get("device_name") or "HP",
            "code_hint": f"••••-••{row.get('code_hint') or '••'}",
            "expires_at": row.get("expires_at"),
            "created_at": row.get("created_at"),
            "used_at": row.get("used_at"),
            "revoked_at": row.get("revoked_at"),
            "status": status,
        })
    clients = [
        _client_payload(row)
        for row in db.query(
            """SELECT c.*, d.name AS device_name FROM mobile_clients c
               JOIN devices d ON d.id=c.device_id ORDER BY c.id DESC"""
        )
    ]
    devices = db.query("SELECT id, name FROM devices ORDER BY id")
    return {
        "ok": True,
        "devices": devices,
        "pairing_codes": codes,
        "clients": clients,
        "contract": {
            "pairing_code_one_time": True,
            "pairing_code_default_minutes": DEFAULT_PAIRING_MINUTES,
            "pairing_code_max_minutes": MAX_PAIRING_MINUTES,
            "token_stored_as_hash": True,
            "device_id_derived_from_token": True,
            "trusted_lan_only": True,
            "overlay_ux_contract": "1.0",
        },
    }
