"""Build privacy-safe Remote HP inventory and upload snapshots for Remote Server.

Passwords, email addresses, phone numbers, captions, filenames, and video files
are intentionally excluded. The server receives only operational metadata.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from database.db import query
from services import adb, device_connection


def _iso_utc(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
    if dt.tzinfo is None:
        # SQLite CURRENT_TIMESTAMP is UTC even though it is stored without an offset.
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_inventory_snapshot() -> tuple[dict[str, Any], str]:
    online_serials = adb.get_online_serials()
    devices = query("SELECT * FROM devices ORDER BY id")
    accounts = query("SELECT id, username, created_at FROM accounts ORDER BY id")
    placements = query(
        "SELECT id, account_id, device_id, app_slot, created_at FROM account_placements ORDER BY id"
    )

    handsets = []
    for row in devices:
        connection = device_connection.connection_snapshot(row, online_serials)
        # v1.7 keeps physical handset identity separate from ADB transport.
        reported_serial = connection.get("active_serial") or connection.get("usb_serial") or connection.get("wifi_endpoint") or row.get("serial")
        handsets.append(
            {
                "client_device_id": int(row["id"]),
                "name": str(row.get("name") or f"HP #{row['id']}")[:160],
                "serial": (str(reported_serial or "").strip()[:255] or None),
                "stable_uid": (str(connection.get("stable_uid") or "").strip()[:80] or None),
                "usb_serial": (str(connection.get("usb_serial") or "").strip()[:255] or None),
                "wifi_endpoint": (str(connection.get("wifi_endpoint") or "").strip()[:255] or None),
                "preferred_transport": connection.get("preferred_transport") or "auto",
                "active_transport": connection.get("active_transport"),
                "active_serial": (str(connection.get("active_serial") or "").strip()[:255] or None),
                "label": (str(row.get("label") or "").strip()[:160] or None),
                "online": bool(connection.get("online")),
                "created_at": _iso_utc(row.get("created_at")),
            }
        )
    safe_accounts = [
        {
            "client_account_id": int(row["id"]),
            "username": str(row.get("username") or f"akun-{row['id']}")[:255],
            "created_at": _iso_utc(row.get("created_at")),
        }
        for row in accounts
    ]
    safe_placements = [
        {
            "client_placement_id": int(row["id"]),
            "client_account_id": int(row["account_id"]),
            "client_device_id": int(row["device_id"]),
            "app_slot": "kloning" if row.get("app_slot") == "kloning" else "original",
            "created_at": _iso_utc(row.get("created_at")),
        }
        for row in placements
    ]
    mobile_rows = query(
        """SELECT id, device_id, display_name, status, paired_at, last_seen_at,
                  app_version, overlay_contract_version
           FROM mobile_clients ORDER BY id"""
    )
    safe_mobile_clients = [
        {
            "client_mobile_id": int(row["id"]),
            "client_device_id": int(row["device_id"]),
            "display_name": str(row.get("display_name") or f"Android #{row['id']}")[:160],
            "status": "revoked" if row.get("status") == "revoked" else "active",
            "app_version": (str(row.get("app_version") or "").strip()[:64] or None),
            "overlay_contract_version": (str(row.get("overlay_contract_version") or "").strip()[:32] or None),
            "paired_at": _iso_utc(row.get("paired_at")),
            "last_seen_at": _iso_utc(row.get("last_seen_at")),
        }
        for row in mobile_rows
    ]
    content = {
        "handsets": handsets,
        "accounts": safe_accounts,
        "placements": safe_placements,
        "mobile_clients": safe_mobile_clients,
    }
    payload = {
        "snapshot_id": f"inventory-{uuid.uuid4()}",
        "synced_at": datetime.now(timezone.utc).isoformat(),
        **content,
    }
    return payload, _digest(content)


def build_session_rows(session_ids: set[int] | list[int] | tuple[int, ...] | None = None) -> tuple[list[dict[str, Any]], str]:
    where_sql = ""
    params: tuple[Any, ...] = ()
    if session_ids is not None:
        normalized_ids = sorted({int(value) for value in session_ids if int(value) > 0})
        if not normalized_ids:
            return [], _digest([])
        where_sql = f"WHERE s.id IN ({','.join('?' for _ in normalized_ids)})"
        params = tuple(normalized_ids)
    rows = query(
        f"""
        SELECT s.id, s.account_id, s.device_id, s.subfolder,
               s.policy, s.batch_date, s.status, s.started_at, s.finished_at,
               a.username AS account_username,
               d.name AS device_name,
               COALESCE(p.app_slot, 'original') AS app_slot,
               (SELECT COUNT(*) FROM uploaded_videos uv WHERE uv.session_id = s.id) AS completed_count
        FROM upload_sessions s
        JOIN accounts a ON a.id = s.account_id
        JOIN devices d ON d.id = s.device_id
        LEFT JOIN account_placements p ON p.account_id = s.account_id AND p.device_id = s.device_id
        {where_sql}
        ORDER BY s.id
        """,
        params,
    )
    result: list[dict[str, Any]] = []
    for row in rows:
        status = str(row.get("status") or "pending").lower()
        if status not in {"pending", "active", "finished", "cancelled", "failed"}:
            status = "pending"
        # Directory paths and source filenames stay local. Only the logical
        # subfolder label is allowed, and it is omitted when empty.
        folder_name = str(row.get("subfolder") or "").strip()
        result.append(
            {
                "client_session_id": int(row["id"]),
                "client_account_id": int(row["account_id"]),
                "client_device_id": int(row["device_id"]),
                "account_username": str(row.get("account_username") or f"akun-{row['account_id']}")[:255],
                "device_name": str(row.get("device_name") or f"HP #{row['device_id']}")[:160],
                "app_slot": "kloning" if row.get("app_slot") == "kloning" else "original",
                "batch_date": row.get("batch_date") or None,
                "status": status,
                "planned_count": max(0, int(row.get("policy") or 0)),
                "completed_count": max(0, int(row.get("completed_count") or 0)),
                "failed_count": 0,
                "folder_name": folder_name[:255] or None,
                "started_at": _iso_utc(row.get("started_at")),
                "finished_at": _iso_utc(row.get("finished_at")),
            }
        )
    return result, _digest(result)


def session_batches(rows: list[dict[str, Any]], batch_size: int = 200):
    for start in range(0, len(rows), batch_size):
        yield {
            "sync_id": f"sessions-{uuid.uuid4()}",
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "sessions": rows[start : start + batch_size],
        }


def session_reconcile_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "reconcile_id": f"reconcile-{uuid.uuid4()}",
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "present_session_ids": [int(row["client_session_id"]) for row in rows],
    }
