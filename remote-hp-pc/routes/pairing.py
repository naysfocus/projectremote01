"""PC-side management endpoints for Remote HP Android pairing."""
from __future__ import annotations

import base64
import io
import socket
from ipaddress import ip_address
from urllib.parse import urlencode

from flask import Blueprint, jsonify, request

from services import mobile_api, pairing

pairing_bp = Blueprint("pairing", __name__, url_prefix="/api/pairing")


def _is_loopback(value: str | None) -> bool:
    if not value:
        return False
    try:
        return ip_address(value).is_loopback
    except ValueError:
        return value == "localhost"


@pairing_bp.before_request
def pc_only_pairing_management():
    # Pairing-code creation/revoke is a PC admin action. Android only uses
    # /api/mobile/v1/pair with the one-time code. Keeping this blueprint on
    # loopback prevents another LAN device from minting its own pairing code.
    if not _is_loopback(request.remote_addr):
        return jsonify({"ok": False, "error": "Pengelolaan pairing hanya dapat dilakukan dari PC Remote HP"}), 403


def _lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("1.1.1.1", 80))
        ip = sock.getsockname()[0]
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    finally:
        sock.close()
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return "127.0.0.1"


def _error(exc: pairing.PairingError):
    return jsonify(exc.payload), exc.status_code


def _qr_data_uri(text: str) -> str | None:
    try:
        import qrcode
        image = qrcode.make(text)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return "data:image/png;base64," + encoded
    except Exception:
        return None


@pairing_bp.get("")
def status():
    payload = pairing.pairing_status()
    payload["lan_server_url"] = f"http://{_lan_ip()}:5001"
    cache = mobile_api.list_collections()
    payload["setup_cache"] = {
        "cached_at": cache.get("cached_at"),
        "ready_collections": sum(1 for row in cache.get("collections") or [] if row.get("available")),
    }
    return jsonify(payload)


@pairing_bp.post("/codes")
def create_code():
    data = request.get_json(silent=True) or {}
    try:
        result = pairing.create_pairing_code(data.get("device_id"), data.get("expires_minutes"))
    except pairing.PairingError as exc:
        return _error(exc)
    row = result["pairing"]
    server_url = str(data.get("server_url") or f"http://{_lan_ip()}:5001").strip().rstrip("/")
    if not server_url.startswith(("http://", "https://")):
        server_url = "http://" + server_url
    uri = "remotehp://pair?" + urlencode({"server": server_url, "code": row["code"]})
    row["server_url"] = server_url
    row["pairing_uri"] = uri
    row["qr_data_uri"] = _qr_data_uri(uri)
    row["instructions"] = "Scan QR dengan kamera Android atau masukkan alamat PC dan kode secara manual."
    return jsonify(result), 201


@pairing_bp.delete("/codes/<int:pairing_id>")
def revoke_code(pairing_id):
    try: return jsonify(pairing.revoke_pairing_code(pairing_id))
    except pairing.PairingError as exc: return _error(exc)


@pairing_bp.post("/clients/<int:client_id>/revoke")
def revoke_client(client_id):
    try: return jsonify(pairing.revoke_client(client_id))
    except pairing.PairingError as exc: return _error(exc)


@pairing_bp.post("/setup-cache/refresh")
def refresh_setup_cache():
    try:
        return jsonify(mobile_api.refresh_setup_cache())
    except mobile_api.MobileAPIError as exc:
        return jsonify(exc.payload), exc.status_code
