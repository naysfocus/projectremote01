"""Remote HP v1.50 trusted-LAN API for the Android Controller."""
from __future__ import annotations

import time
from functools import wraps
from ipaddress import ip_address
from threading import RLock

from flask import Blueprint, g, jsonify, request

from services import mobile_api, pairing

mobile_bp = Blueprint("mobile", __name__, url_prefix="/api/mobile/v1")
_pair_lock = RLock()
_pair_attempts: dict[str, list[float]] = {}


def _private_or_loopback(value: str | None) -> bool:
    if not value:
        return False
    try:
        addr = ip_address(value)
        return addr.is_loopback or addr.is_private or addr.is_link_local
    except ValueError:
        return value == "localhost"


def _error(exc):
    return jsonify(exc.payload), exc.status_code


def _rate_key() -> str:
    return request.remote_addr or "unknown"


def _pair_rate_limited(key: str) -> bool:
    now = time.monotonic()
    with _pair_lock:
        recent = [stamp for stamp in _pair_attempts.get(key, []) if now - stamp < 300]
        _pair_attempts[key] = recent
        return len(recent) >= 8


def _record_pair_failure(key: str) -> None:
    with _pair_lock:
        _pair_attempts.setdefault(key, []).append(time.monotonic())


def _clear_pair_failures(key: str) -> None:
    with _pair_lock:
        _pair_attempts.pop(key, None)


def _reject_forbidden_fields(data):
    forbidden = {"device_id", "serial", "usb_serial", "wifi_endpoint", "folder_path", "source_path", "batch_path", "filepath", "path", "storage_root", "token_hash"}
    supplied = sorted(key for key in forbidden if key in data)
    if supplied:
        raise mobile_api.MobileAPIError("Mobile API tidak menerima identitas HP atau filesystem path dari Android", 400, forbidden_fields=supplied)


@mobile_bp.before_request
def authenticate_mobile_request():
    if not _private_or_loopback(request.remote_addr):
        return jsonify({"ok": False, "error": "Mobile API hanya tersedia di jaringan lokal tepercaya"}), 403
    if request.endpoint == "mobile.pair":
        return None
    try:
        g.mobile_client = pairing.authenticate_bearer(request.headers.get("Authorization"))
    except pairing.PairingError as exc:
        return _error(exc)


def _owned_session(fn):
    @wraps(fn)
    def wrapped(session_id, *args, **kwargs):
        try:
            mobile_api.assert_session_owner(session_id, g.mobile_client["device_id"])
        except mobile_api.MobileAPIError as exc:
            return _error(exc)
        return fn(session_id, *args, **kwargs)
    return wrapped


@mobile_bp.post("/pair")
def pair():
    key = _rate_key()
    if _pair_rate_limited(key):
        return jsonify({"ok": False, "error": "Terlalu banyak percobaan pairing. Coba lagi beberapa menit kemudian."}), 429
    data = request.get_json(silent=True) or {}
    try:
        result = pairing.pair_mobile_client(data.get("code"), data.get("app_device_uuid"), data.get("display_name"), data.get("app_version"))
        _clear_pair_failures(key)
        return jsonify(result), 201
    except pairing.PairingError as exc:
        _record_pair_failure(key)
        return _error(exc)


@mobile_bp.get("/bootstrap")
def bootstrap():
    client = g.mobile_client
    return jsonify({
        "ok": True, "api_version": "v1", "server_version": "1.50",
        "client": {"id": client["id"], "display_name": client["display_name"], "app_version": client.get("app_version") or ""},
        "device": {"id": client["device_id"], "name": client["device_name"]},
        "active_session": mobile_api.active_session(client["device_id"]),
        "overlay_contract": {"version": "1.0", "compact_primary_actions": 1, "auto_click_tiktok": False, "accessibility_service": False},
    })


@mobile_bp.get("/accounts")
def accounts():
    return jsonify(mobile_api.list_accounts(g.mobile_client["device_id"]))


@mobile_bp.get("/collections")
def collections():
    try: return jsonify(mobile_api.list_collections())
    except mobile_api.MobileAPIError as exc: return _error(exc)


@mobile_bp.get("/collections/<int:collection_id>/batches")
def batches(collection_id):
    try: return jsonify(mobile_api.list_batches(collection_id, g.mobile_client["device_id"]))
    except mobile_api.MobileAPIError as exc: return _error(exc)


@mobile_bp.post("/sessions")
def create_session():
    data = request.get_json(silent=True) or {}
    try:
        _reject_forbidden_fields(data)
        return jsonify(mobile_api.create_session(int(data.get("account_id")), g.mobile_client["device_id"], int(data.get("collection_id")), data.get("subfolder") or ".", data.get("batch_date"))), 201
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Akun dan sumber video wajib dipilih"}), 400
    except mobile_api.MobileAPIError as exc: return _error(exc)


@mobile_bp.get("/sessions/active")
def active_session():
    return jsonify({"ok": True, "active_session": mobile_api.active_session(g.mobile_client["device_id"])})


@mobile_bp.get("/sessions/<int:session_id>")
@_owned_session
def get_session(session_id):
    return jsonify(mobile_api.session_payload(session_id, g.mobile_client["device_id"]))


@mobile_bp.post("/sessions/<int:session_id>/push")
@_owned_session
def push(session_id):
    data = request.get_json(silent=True) or {}
    try:
        _reject_forbidden_fields(data)
        return jsonify(mobile_api.push(session_id, g.mobile_client["device_id"], data.get("expected_position")))
    except mobile_api.MobileAPIError as exc: return _error(exc)


@mobile_bp.post("/sessions/<int:session_id>/caption-ready")
@_owned_session
def caption_ready(session_id):
    data = request.get_json(silent=True) or {}
    try:
        _reject_forbidden_fields(data)
        return jsonify(mobile_api.mark_caption_ready(session_id, g.mobile_client["device_id"], data.get("expected_position"), data.get("method") or "copied"))
    except mobile_api.MobileAPIError as exc: return _error(exc)


@mobile_bp.post("/sessions/<int:session_id>/confirm")
@_owned_session
def confirm(session_id):
    data = request.get_json(silent=True) or {}
    try:
        _reject_forbidden_fields(data)
        return jsonify(mobile_api.confirm(session_id, g.mobile_client["device_id"], data.get("expected_position")))
    except mobile_api.MobileAPIError as exc: return _error(exc)


@mobile_bp.post("/sessions/<int:session_id>/finish")
@_owned_session
def finish(session_id):
    try: return jsonify(mobile_api.finish(session_id, g.mobile_client["device_id"]))
    except mobile_api.MobileAPIError as exc: return _error(exc)


@mobile_bp.post("/sessions/<int:session_id>/cancel")
@_owned_session
def cancel(session_id):
    try: return jsonify(mobile_api.cancel(session_id, g.mobile_client["device_id"]))
    except mobile_api.MobileAPIError as exc: return _error(exc)
