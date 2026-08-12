"""Trusted-LAN Mobile API adapter for Remote HP v1.50.

The Android controller never supplies an ADB serial or filesystem path. Its
bearer token fixes the handset identity. This module adapts the stable v1.50
upload engine to a small state-driven API for the floating Android overlay.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from flask import current_app

from database import db
from services import adb, caption as caption_svc, device_connection, folder, guard, scheduler
from services.session_policy import POSTS_PER_SESSION, select_session_videos


class MobileAPIError(Exception):
    def __init__(self, message: str, status_code: int = 400, **extra: Any):
        super().__init__(message)
        self.status_code = status_code
        self.payload = {"ok": False, "error": message, **extra}


def _upload_module():
    # Deferred import avoids making the mobile service a dependency of the web
    # upload route while still sharing the certified v1.50 session-state store.
    from routes import upload as upload_route
    return upload_route


def _report(event_type: str, summary: dict[str, Any]) -> None:
    client = current_app.extensions.get("remote_server_client")
    if client is None:
        return
    try:
        client.queue_report(event_type, summary)
    except Exception:
        pass


def _sync(session_id: int | None = None, force: bool = False) -> None:
    client = current_app.extensions.get("remote_server_client")
    if client is None:
        return
    try:
        client.request_data_sync(force=force, session_id=session_id)
    except Exception:
        pass


def _source_map() -> dict[int, dict[str, Any]]:
    root = (db.get_setting("storage_path") or "").strip()
    result = folder.list_video_sources(root)
    if not result.get("ok"):
        raise MobileAPIError(result.get("error") or "Sumber video tidak tersedia", 409)
    return {int(row["id"]): row for row in result.get("sources") or []}


def list_accounts(device_id: int) -> dict[str, Any]:
    rows = db.query(
        """SELECT a.id, a.username, p.app_slot
           FROM account_placements p
           JOIN accounts a ON a.id=p.account_id
           WHERE p.device_id=? ORDER BY a.username COLLATE NOCASE""",
        (device_id,),
    )
    return {
        "ok": True,
        "accounts": [
            {"id": int(row["id"]), "username": row["username"], "app_slot": row.get("app_slot") or "original"}
            for row in rows
        ],
    }


MOBILE_SETUP_CACHE_KEY = "_mobile_setup_cache_v1"


def refresh_setup_cache() -> dict[str, Any]:
    """Scan video sources only from an explicit PC-admin action.

    Android setup endpoints read this cache and never trigger a filesystem scan.
    Session creation still revalidates the selected batch before locking it.
    """
    sources = _source_map()
    collections: list[dict[str, Any]] = []
    batches_by_collection: dict[str, list[dict[str, Any]]] = {}
    for source_id, row in sorted(sources.items()):
        source_path = row.get("path")
        batches: list[dict[str, Any]] = []
        if source_path and os.path.isdir(source_path):
            scan = folder.scan_subfolders(source_path, processed_subfolders=[], locked_subfolders={})
            if scan.get("ok") and scan.get("has_subfolders"):
                for idx, sf in enumerate(scan.get("subfolders") or [], start=1):
                    count = int(sf.get("video_count") or 0)
                    status = "ready" if count == POSTS_PER_SESSION else "incomplete"
                    batches.append({
                        "id": idx,
                        "subfolder": str(sf.get("name") or ""),
                        "status": status,
                        "video_count": count,
                        "available": status == "ready",
                    })
            elif scan.get("ok"):
                count = len(folder.list_videos(source_path))
                batches.append({
                    "id": 1,
                    "subfolder": ".",
                    "status": "ready" if count >= POSTS_PER_SESSION else "incomplete",
                    "video_count": count,
                    "available": count >= POSTS_PER_SESSION,
                })
        ready_count = sum(1 for batch in batches if batch["available"])
        collections.append({
            "id": source_id,
            "name": row.get("label") or f"Video {source_id}",
            "ready_count": ready_count,
            "available": ready_count > 0,
        })
        batches_by_collection[str(source_id)] = batches
    cached_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "version": 1,
        "cached_at": cached_at,
        "collections": collections,
        "batches": batches_by_collection,
    }
    db.set_setting(MOBILE_SETUP_CACHE_KEY, json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return {"ok": True, **payload, "posts_per_session": POSTS_PER_SESSION}


def _setup_cache() -> dict[str, Any]:
    raw = db.get_setting(MOBILE_SETUP_CACHE_KEY)
    if not raw:
        return {"version": 1, "cached_at": None, "collections": [], "batches": {}}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {"version": 1, "cached_at": None, "collections": [], "batches": {}}
    except Exception:
        return {"version": 1, "cached_at": None, "collections": [], "batches": {}}


def list_collections() -> dict[str, Any]:
    cache = _setup_cache()
    return {
        "ok": True,
        "scan_mode": "pc_admin_cache",
        "cached_at": cache.get("cached_at"),
        "collections": cache.get("collections") or [],
        "posts_per_session": POSTS_PER_SESSION,
    }


def list_batches(collection_id: int, device_id: int | None = None) -> dict[str, Any]:
    # device_id is accepted for contract compatibility but Android does not scan
    # or mutate the collection. Session creation performs the authoritative lock.
    cache = _setup_cache()
    collections = {int(row.get("id")): row for row in cache.get("collections") or [] if row.get("id") is not None}
    collection = collections.get(int(collection_id))
    if not collection:
        raise MobileAPIError("Koleksi belum ada di cache PC. Refresh cache Android dari Pengaturan Remote HP.", 409)
    rows = list((cache.get("batches") or {}).get(str(int(collection_id))) or [])
    return {
        "ok": True,
        "scan_mode": "pc_admin_cache",
        "cached_at": cache.get("cached_at"),
        "collection_id": int(collection_id),
        "batches": rows,
        "posts_per_session": POSTS_PER_SESSION,
    }


def _placement(account_id: int, device_id: int) -> dict[str, Any] | None:
    return db.query(
        """SELECT p.id, p.app_slot, a.username FROM account_placements p
           JOIN accounts a ON a.id=p.account_id
           WHERE p.account_id=? AND p.device_id=?""",
        (account_id, device_id), one=True,
    )


def create_session(account_id: int, device_id: int, collection_id: int, subfolder: str, batch_date: str) -> dict[str, Any]:
    batch_date = scheduler.valid_batch_date(batch_date)
    if not batch_date:
        raise MobileAPIError("Tanggal batch wajib dipilih")
    placement = _placement(int(account_id), int(device_id))
    if not placement:
        raise MobileAPIError("Akun tidak tersedia pada HP hasil pairing", 403)
    active = db.query("SELECT id FROM upload_sessions WHERE account_id=? AND status='active' ORDER BY id DESC LIMIT 1", (account_id,), one=True)
    if active:
        raise MobileAPIError("Akun masih mempunyai sesi aktif", 409, active_session_id=int(active["id"]))
    source = _source_map().get(int(collection_id))
    if not source:
        raise MobileAPIError("Sumber video tidak ditemukan", 404)
    root = source["path"]
    subfolder = str(subfolder or ".").strip() or "."
    target = root if subfolder == "." else os.path.join(root, subfolder)
    if not os.path.isdir(target):
        raise MobileAPIError("Batch tidak ditemukan pada sumber video", 404)
    videos = folder.list_videos(target)
    batch = select_session_videos(guard.filter_uploadable(videos, batch_date=batch_date)["uploadable"], has_subfolders=subfolder != ".")
    if not batch.get("ok"):
        raise MobileAPIError(batch.get("error") or f"Batch harus berisi {POSTS_PER_SESSION} video", 409)
    # Guard same physical batch against another active session.
    clash = db.query(
        "SELECT id FROM upload_sessions WHERE folder_path=? AND subfolder=? AND status='active' AND account_id!=?",
        (root, subfolder, account_id), one=True,
    )
    if clash:
        raise MobileAPIError("Batch sedang digunakan sesi aktif lain", 409)
    session_id = db.execute(
        """INSERT INTO upload_sessions(account_id,device_id,folder_path,subfolder,policy,batch_date,status)
           VALUES(?,?,?,?,?,?,'active')""",
        (account_id, device_id, root, subfolder, POSTS_PER_SESSION, batch_date),
    )
    schedule = scheduler.generate_fixed_session_schedule(db.get_setting("random_range") or 15)
    state = []
    for index, video in enumerate(batch["videos"]):
        schedule_row = schedule[index] if index < len(schedule) else {}
        state.append({
            "name": video["name"], "path": video["path"], "size_human": video.get("size_human") or "",
            "status": "waiting", "caption_ready": False, "mobile_caption": None,
            "scheduled_label": schedule_row.get("label") or "", "scheduled_time": schedule_row.get("time") or "",
        })
    upload = _upload_module()
    upload._save_video_state(session_id, state)
    _report("upload_session_started", {
        "local_session_id": session_id, "account_username": placement["username"],
        "device_name": (db.query("SELECT name FROM devices WHERE id=?", (device_id,), one=True) or {}).get("name", "-"),
        "video_count": len(state), "batch_date": batch_date, "status": "active", "controller": "android",
    })
    _sync(session_id=session_id)
    return session_payload(session_id, device_id)


def assert_session_owner(session_id: int, device_id: int) -> dict[str, Any]:
    row = db.query("SELECT * FROM upload_sessions WHERE id=?", (session_id,), one=True)
    if not row:
        raise MobileAPIError("Sesi tidak ditemukan", 404)
    if int(row["device_id"]) != int(device_id):
        raise MobileAPIError("Sesi bukan milik HP hasil pairing", 403)
    return row


def active_session(device_id: int) -> dict[str, Any] | None:
    row = db.query("SELECT id FROM upload_sessions WHERE device_id=? AND status='active' ORDER BY id DESC LIMIT 1", (device_id,), one=True)
    return session_payload(int(row["id"]), device_id) if row else None


def _ensure_enriched_state(session_id: int, videos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changed = False
    if not videos:
        return videos
    schedule_missing = any("scheduled_time" not in row for row in videos)
    schedule_rows = scheduler.generate_fixed_session_schedule(db.get_setting("random_range") or 15) if schedule_missing else []
    for index, row in enumerate(videos):
        if "caption_ready" not in row:
            row["caption_ready"] = False; changed = True
        if "mobile_caption" not in row:
            row["mobile_caption"] = None; changed = True
        if "scheduled_time" not in row:
            sched = schedule_rows[index] if index < len(schedule_rows) else {}
            row["scheduled_time"] = sched.get("time") or ""; row["scheduled_label"] = sched.get("label") or ""; changed = True
    if changed:
        _upload_module()._save_video_state(session_id, videos)
    return videos


def current_position(session_id: int, device_id: int) -> int:
    assert_session_owner(session_id, device_id)
    videos = _ensure_enriched_state(session_id, _upload_module()._load_video_state(session_id) or [])
    return next((i for i, row in enumerate(videos) if row.get("status") != "done"), len(videos))


def assert_expected_position(actual: int, expected: Any) -> None:
    try:
        expected = int(expected)
    except (TypeError, ValueError):
        raise MobileAPIError("Posisi video wajib dikirim", 400)
    if expected != actual:
        raise MobileAPIError("Sesi berubah — muat ulang", 409, current_position=actual)


def _caption_payload(caption: Any) -> str:
    if not caption:
        return ""
    if isinstance(caption, dict):
        return str(caption.get("full") or "\n\n".join(x for x in [caption.get("content"), caption.get("hashtags")] if x) or "").strip()
    return str(caption).strip()


def session_payload(session_id: int, device_id: int) -> dict[str, Any]:
    session = assert_session_owner(session_id, device_id)
    videos = _ensure_enriched_state(session_id, _upload_module()._load_video_state(session_id) or [])
    account = db.query("SELECT id,username FROM accounts WHERE id=?", (session["account_id"],), one=True) or {}
    source_id = None
    source_name = os.path.basename(session.get("folder_path") or "")
    for sid, source in _source_map().items():
        if os.path.abspath(source["path"]) == os.path.abspath(session["folder_path"]):
            source_id, source_name = sid, source.get("label") or source_name
            break
    current_idx = next((i for i, row in enumerate(videos) if row.get("status") != "done"), None)
    current = None
    next_action = "finish" if current_idx is None else "push"
    if current_idx is not None:
        row = videos[current_idx]
        if row.get("status") == "sent":
            if not row.get("mobile_caption"):
                row["mobile_caption"] = caption_svc.generate_caption()
                _upload_module()._save_video_state(session_id, videos)
            next_action = "confirm" if row.get("caption_ready") else "caption_ready"
        current = {
            "id": current_idx + 1,
            "position": current_idx,
            "number": current_idx + 1,
            "filename": row.get("name") or "Video",
            "status": row.get("status") or "waiting",
            "caption": {"full": _caption_payload(row.get("mobile_caption"))},
            "caption_ready": bool(row.get("caption_ready")),
            "caption_ready_at": "ready" if row.get("caption_ready") else None,
            "scheduled_label": row.get("scheduled_label") or "",
            "scheduled_time": row.get("scheduled_time") or "",
        }
    done = sum(1 for row in videos if row.get("status") == "done")
    return {
        "ok": True,
        "session": {
            "id": int(session_id), "status": session.get("status") or "active",
            "account": {"id": int(account.get("id") or session["account_id"]), "username": account.get("username") or "Akun"},
            "collection": {"id": source_id or 0, "name": source_name, "batch": session.get("subfolder") or "."},
            "batch": session.get("subfolder") or ".", "batch_date": session.get("batch_date") or "",
            "done_count": done, "total": len(videos), "current_position": current_idx, "next_action": next_action,
        },
        "current_item": current,
        "overlay": {"next_action": next_action, "done_count": done, "total": len(videos)},
    }


def push(session_id: int, device_id: int, expected_position: int) -> dict[str, Any]:
    session = assert_session_owner(session_id, device_id)
    if session.get("status") != "active": raise MobileAPIError("Sesi tidak aktif", 409)
    videos = _ensure_enriched_state(session_id, _upload_module()._load_video_state(session_id) or [])
    pos = next((i for i, row in enumerate(videos) if row.get("status") != "done"), len(videos))
    assert_expected_position(pos, expected_position)
    if pos >= len(videos): raise MobileAPIError("Semua video sudah selesai", 409)
    row = videos[pos]
    if row.get("status") == "sent": return session_payload(session_id, device_id)
    device = db.query("SELECT * FROM devices WHERE id=?", (device_id,), one=True)
    serial, connection = device_connection.active_target(device or {})
    if not serial: raise MobileAPIError("HP tidak terdeteksi ADB", 409, connection=connection)
    result = adb.push_file(serial, row["path"])
    if not result.get("ok"): raise MobileAPIError("Kirim gagal — coba lagi", 502)
    row["status"] = "sent"
    row["caption_ready"] = False
    row["mobile_caption"] = caption_svc.generate_caption()
    _upload_module()._save_video_state(session_id, videos)
    payload = session_payload(session_id, device_id)
    # Android copies caption immediately from the successful Push response,
    # before it marks caption-ready. Keep a top-level compatibility payload
    # so the overlay never copies an empty pre-push caption.
    payload["caption"] = {"full": _caption_payload(row.get("mobile_caption"))}
    return payload


def mark_caption_ready(session_id: int, device_id: int, expected_position: int, method: str = "copied") -> dict[str, Any]:
    videos = _ensure_enriched_state(session_id, _upload_module()._load_video_state(session_id) or [])
    pos = current_position(session_id, device_id); assert_expected_position(pos, expected_position)
    if pos >= len(videos) or videos[pos].get("status") != "sent": raise MobileAPIError("Video belum terkirim", 409)
    videos[pos]["caption_ready"] = True; videos[pos]["caption_method"] = str(method or "copied")[:32]
    _upload_module()._save_video_state(session_id, videos)
    return session_payload(session_id, device_id)


def confirm(session_id: int, device_id: int, expected_position: int) -> dict[str, Any]:
    session = assert_session_owner(session_id, device_id)
    videos = _ensure_enriched_state(session_id, _upload_module()._load_video_state(session_id) or [])
    pos = next((i for i, row in enumerate(videos) if row.get("status") != "done"), len(videos)); assert_expected_position(pos, expected_position)
    if pos >= len(videos): raise MobileAPIError("Semua video sudah selesai", 409)
    row = videos[pos]
    if row.get("status") != "sent": raise MobileAPIError("Video belum terkirim", 409)
    if not row.get("caption_ready"): raise MobileAPIError("Caption belum siap", 409)
    device = db.query("SELECT * FROM devices WHERE id=?", (device_id,), one=True)
    serial, connection = device_connection.active_target(device or {})
    if serial:
        device_connection.mark_seen(device_id, connection)
        adb.delete_file(serial, row["name"])
    # Keep same behavior as PC flow: local file deletion happens on confirmation.
    deletion = folder.delete_file(row["path"])
    if not deletion.get("ok") and os.path.exists(row["path"]):
        raise MobileAPIError("Video belum selesai di server", 500)
    db.execute(
        "INSERT INTO uploaded_videos(session_id,account_id,filename,filepath,batch_date) VALUES(?,?,?,?,?)",
        (session_id, session["account_id"], row["name"], row["path"], session.get("batch_date")),
    )
    row["status"] = "done"; _upload_module()._save_video_state(session_id, videos)
    _sync(session_id=session_id)
    return session_payload(session_id, device_id)


def finish(session_id: int, device_id: int) -> dict[str, Any]:
    session = assert_session_owner(session_id, device_id)
    videos = _upload_module()._load_video_state(session_id) or []
    if any(row.get("status") != "done" for row in videos): raise MobileAPIError("Masih ada video belum selesai", 409)
    subfolder = session.get("subfolder") or "."
    if subfolder != ".":
        path = os.path.join(session["folder_path"], subfolder)
        if folder.path_exists(path): folder.delete_subfolder(path)
    db.execute("UPDATE upload_sessions SET status='finished', finished_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
    _upload_module()._clear_video_state(session_id)
    account = db.query("SELECT username FROM accounts WHERE id=?", (session["account_id"],), one=True) or {}
    _report("upload_session_completed", {"local_session_id": session_id, "account_username": account.get("username") or "-", "video_count": len(videos), "batch_date": session.get("batch_date"), "status": "finished", "controller": "android"})
    _sync(session_id=session_id)
    return {"ok": True, "summary": {"session_id": session_id, "video_count": len(videos)}}


def cancel(session_id: int, device_id: int) -> dict[str, Any]:
    session = assert_session_owner(session_id, device_id)
    videos = _upload_module()._load_video_state(session_id) or []
    db.execute("UPDATE upload_sessions SET status='cancelled', finished_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
    _upload_module()._clear_video_state(session_id)
    _report("upload_session_cancelled", {"local_session_id": session_id, "video_count": sum(1 for x in videos if x.get("status") == "done"), "batch_date": session.get("batch_date"), "status": "cancelled", "controller": "android"})
    _sync(session_id=session_id)
    return {"ok": True, "sent_not_confirmed_count": sum(1 for x in videos if x.get("status") == "sent")}
