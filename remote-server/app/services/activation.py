from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import ActivationKey, AppAuthorization, Device
from app.schemas import ActivateRequest
from app.security import generate_access_token, hash_access_token, token_prefix
from app.services.common import add_outbox
from app.utils import as_utc, utcnow


class ActivationError(Exception):
    def __init__(self, code: str, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def activate(db: Session, payload: ActivateRequest) -> tuple[str, Device]:
    now = utcnow()
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))

    key = db.scalar(select(ActivationKey).where(ActivationKey.code == payload.code))
    if key is None:
        db.rollback()
        raise ActivationError("code_invalid")
    if key.status != "pending":
        db.rollback()
        raise ActivationError(f"code_{key.status}")
    if as_utc(key.expires_at) is not None and as_utc(key.expires_at) <= now:
        key.status = "expired"
        db.commit()
        raise ActivationError("code_expired")
    if key.app_type != payload.app_type:
        db.rollback()
        raise ActivationError("code_app_mismatch")

    device = db.scalar(select(Device).where(Device.fingerprint_hash == payload.fingerprint_hash))
    if device is None:
        device = Device(
            fingerprint_hash=payload.fingerprint_hash,
            os_type=payload.os_type,
            os_info=payload.os_info,
            last_seen_at=now,
        )
        db.add(device)
        db.flush()
    else:
        device.os_type = payload.os_type
        device.os_info = payload.os_info
        device.last_seen_at = now

    existing = db.scalar(
        select(AppAuthorization).where(
            AppAuthorization.device_id == device.id,
            AppAuthorization.app_type == payload.app_type,
        )
    )

    raw_token = generate_access_token(payload.app_type)

    if existing is not None:
        # Fingerprint device ini SAMA dengan yang sudah tercatat -- ini bukan
        # device baru mencoba mengklaim slot orang lain, ini device asli yang
        # kehilangan token lokalnya (mis. client menghapus token karena gagal
        # didekripsi setelah restart, reinstall, dsb). Selama admin sudah
        # menerbitkan kode aktivasi BARU yang valid untuk app_type ini, itu
        # sudah cukup sebagai otorisasi eksplisit untuk menerbitkan token
        # pengganti. Terbitkan ulang pada row yang sama (bukan insert baru)
        # supaya UniqueConstraint(device_id, app_type) tetap terjaga, session
        # aktif direset, dan histori/statistik device tidak duplikat.
        existing.status = "active"
        existing.token_prefix = token_prefix(raw_token)
        existing.access_token_hash = hash_access_token(raw_token)
        existing.app_version = payload.app_version
        existing.activated_at = now
        existing.revoked_at = None
        existing.session_id = None
        existing.session_started_at = None
        existing.session_last_seen_at = None
        existing.session_ip = None
        key.status = "consumed"
        key.consumed_at = now
        key.consumed_by_device_id = device.id
        add_outbox(
            db,
            "device_token_reissued",
            {
                "device_id": device.id,
                "label": device.label or f"Device #{device.id}",
                "app_type": payload.app_type,
                "reissued_at": now.isoformat(),
            },
        )
        db.commit()
        db.refresh(device)
        return raw_token, device

    authorization = AppAuthorization(
        device_id=device.id,
        app_type=payload.app_type,
        status="active",
        token_prefix=token_prefix(raw_token),
        access_token_hash=hash_access_token(raw_token),
        app_version=payload.app_version,
    )
    db.add(authorization)
    key.status = "consumed"
    key.consumed_at = now
    key.consumed_by_device_id = device.id
    add_outbox(
        db,
        "device_activated",
        {
            "device_id": device.id,
            "label": device.label or f"Device #{device.id}",
            "app_type": payload.app_type,
            "activated_at": now.isoformat(),
        },
    )
    db.commit()
    db.refresh(device)
    return raw_token, device
