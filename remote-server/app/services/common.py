from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, NotificationOutbox


def add_outbox(db: Session, event_type: str, payload: dict[str, Any]) -> None:
    db.add(NotificationOutbox(event_type=event_type, payload_json=json.dumps(payload, separators=(",", ":"))))


def add_audit(
    db: Session,
    *,
    actor_type: str,
    actor_id: str | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_json=json.dumps(metadata or {}, separators=(",", ":")),
        )
    )
