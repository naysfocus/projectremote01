"""routes/devices.py — CRUD HP + transport ADB USB/Wi-Fi (v1.50)."""
from __future__ import annotations

import re
import uuid

from flask import Blueprint, current_app, jsonify, request

from database.db import execute, get_setting, query, set_setting
from services import adb, scrcpy
from services import device_connection as conn


devices_bp = Blueprint("devices", __name__, url_prefix="/api/devices")


@devices_bp.after_request
def _schedule_remote_sync_after_mutation(response):
    if request.method in {"POST", "PUT", "DELETE"} and response.status_code < 400:
        client = current_app.extensions.get("remote_server_client")
        if client is not None:
            client.request_data_sync()
        manager = current_app.extensions.get("wireless_adb_manager")
        if manager is not None:
            manager.request_reconnect()
    return response


def _device_or_404(device_id: int):
    device = query("SELECT * FROM devices WHERE id = ?", (device_id,), one=True)
    if not device:
        return None, (jsonify({"ok": False, "error": "HP tidak ditemukan"}), 404)
    return device, None


def _split_legacy_serial(value: str | None):
    serial = str(value or "").strip()
    if not serial:
        return None, None
    return (None, serial) if ":" in serial else (serial, None)


@devices_bp.route("", methods=["GET"])
def list_devices():
    """List HP beserta status transport aktual dan jumlah akun."""
    rows = query(
        """
        SELECT d.*,
               (SELECT COUNT(*) FROM account_placements p WHERE p.device_id = d.id) AS account_count,
               (SELECT COUNT(*) FROM account_placements p WHERE p.device_id = d.id AND p.app_slot = 'original') AS account_count_original,
               (SELECT COUNT(*) FROM account_placements p WHERE p.device_id = d.id AND p.app_slot = 'kloning')  AS account_count_kloning
        FROM devices d
        ORDER BY d.id ASC
        """
    )
    online = adb.get_online_serials()
    persist = request.args.get("check_status") == "1"
    return jsonify([conn.enrich_device(row, online, persist_seen=persist) for row in rows])


@devices_bp.route("/status", methods=["GET"])
def device_status():
    available, info = adb.check_adb_available()
    raw = adb.list_devices()
    online = adb.get_online_serials()
    managed = [conn.enrich_device(row, online, persist_seen=True) for row in query("SELECT * FROM devices ORDER BY id")]
    return jsonify(
        {
            "ok": True,
            "adb_available": available,
            "adb_info": info,
            "devices_connected": raw.get("devices", []),
            "serials_online": sorted(online),
            "managed_devices": managed,
            "error": raw.get("error"),
        }
    )


@devices_bp.route("/scrcpy-status", methods=["GET"])
def scrcpy_status():
    return jsonify(scrcpy.is_available())


@devices_bp.route("/<int:device_id>/connection", methods=["GET"])
def device_connection(device_id):
    device, error = _device_or_404(device_id)
    if error:
        return error
    return jsonify({"ok": True, **conn.connection_snapshot(device)})


@devices_bp.route("/<int:device_id>/mirror", methods=["POST"])
def mirror_device(device_id):
    device, error = _device_or_404(device_id)
    if error:
        return error
    target, snapshot = conn.active_target(device)
    if not target:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "HP tidak online via ADB. Sambungkan Wi-Fi Debugging atau USB lalu coba lagi.",
                    "connection": snapshot,
                }
            ),
            409,
        )
    result = scrcpy.launch(serial=target, title=device.get("name") or f"HP {device_id}")
    if not result["ok"]:
        return jsonify(result), 500
    conn.mark_seen(device_id, snapshot)
    return jsonify(
        {
            "ok": True,
            "already_open": result.get("already_open", False),
            "focused": result.get("focused", False),
            "transport": snapshot.get("active_transport"),
            "serial": target,
            "error": None,
        }
    )


@devices_bp.route("/detect", methods=["GET"])
def detect_devices():
    """Deteksi seluruh target ADB dan tandai yang sudah terkait ke HP lokal."""
    result = adb.list_devices()
    if not result["ok"]:
        return jsonify({"ok": False, "error": result.get("error"), "available": []})
    registered = set()
    for row in query("SELECT serial, usb_serial, wifi_endpoint FROM devices"):
        for key in ("serial", "usb_serial", "wifi_endpoint"):
            value = str(row.get(key) or "").strip()
            if value:
                registered.add(value)
    available = []
    for dev in result["devices"]:
        serial = dev["serial"]
        available.append(
            {
                "serial": serial,
                "status": dev["status"],
                "transport": "wifi" if ":" in serial else "usb",
                "registered": serial in registered,
            }
        )
    return jsonify({"ok": True, "error": None, "available": available})


# ---------------------------------------------------------------------------
# Koneksi USB / Wi-Fi
# ---------------------------------------------------------------------------
# Global connection_mode dipertahankan hanya sebagai default/kompatibilitas.
# v1.50 menggunakan preferred_transport PER HP dan fallback otomatis.


@devices_bp.route("/connection-mode", methods=["GET"])
def get_connection_mode():
    return jsonify(
        {
            "ok": True,
            "connection_mode": adb.get_connection_mode(),
            "wifi_last_ip": get_setting("wifi_last_ip") or "",
            "per_device_transport": True,
        }
    )


@devices_bp.route("/connection-mode", methods=["POST"])
def set_connection_mode():
    data = request.get_json() or {}
    mode = str(data.get("mode") or "").strip().lower()
    if mode not in adb.CONNECTION_MODES:
        return jsonify({"ok": False, "error": "Mode harus 'usb' atau 'wifi'."}), 400
    set_setting("connection_mode", mode)
    return jsonify({"ok": True, "connection_mode": mode})


@devices_bp.route("/<int:device_id>/connection-preference", methods=["POST"])
def set_connection_preference(device_id):
    device, error = _device_or_404(device_id)
    if error:
        return error
    data = request.get_json() or {}
    preference = conn.normalize_preference(data.get("preferred_transport", device.get("preferred_transport")))
    auto_reconnect = 1 if data.get("wifi_auto_reconnect", device.get("wifi_auto_reconnect", 1)) else 0
    execute(
        "UPDATE devices SET preferred_transport = ?, wifi_auto_reconnect = ? WHERE id = ?",
        (preference, auto_reconnect, device_id),
    )
    updated = query("SELECT * FROM devices WHERE id = ?", (device_id,), one=True)
    return jsonify({"ok": True, **conn.connection_snapshot(updated)})


@devices_bp.route("/<int:device_id>/wifi/enable-from-usb", methods=["POST"])
def wifi_enable_from_usb(device_id):
    """Aktifkan ADB TCP/IP dari USB sekali, lalu simpan endpoint Wi-Fi."""
    device, error = _device_or_404(device_id)
    if error:
        return error
    usb_serial, _ = conn.transport_fields(device)
    online = adb.get_online_serials()
    if not usb_serial or usb_serial not in online:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "HP harus online via USB untuk jalur otomatis. Colok kabel dan aktifkan USB Debugging terlebih dahulu.",
                }
            ),
            400,
        )

    data = request.get_json() or {}
    ip = str(data.get("ip") or "").strip()
    try:
        port = int(data.get("port") or adb.DEFAULT_TCPIP_PORT)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Port Wi-Fi tidak valid."}), 400

    if not ip:
        detect = adb._run(["-s", usb_serial, "shell", "ip", "route"])
        match = re.search(r"src\s+(\d+\.\d+\.\d+\.\d+)", detect.get("stdout", ""))
        if match:
            ip = match.group(1)
        else:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "IP Wi-Fi HP tidak terdeteksi otomatis. Isi IP HP dari detail jaringan Wi-Fi.",
                    }
                ),
                400,
            )

    tcpip_res = adb.tcpip_enable(usb_serial, port=port)
    if not tcpip_res["ok"]:
        return jsonify({"ok": False, "error": tcpip_res["stderr"], "step": "tcpip"}), 400

    endpoint = f"{ip}:{port}"
    connect_res = adb.connect_wifi(endpoint)
    if not connect_res["ok"]:
        return jsonify({"ok": False, "error": connect_res["stderr"], "step": "connect"}), 400

    execute(
        """UPDATE devices
           SET usb_serial = ?, wifi_endpoint = ?, preferred_transport = 'wifi',
               wifi_auto_reconnect = 1, last_transport = 'wifi',
               last_usb_seen_at = CURRENT_TIMESTAMP, last_wifi_seen_at = CURRENT_TIMESTAMP,
               serial = CASE WHEN serial IS NULL OR TRIM(serial) = '' OR instr(serial, ':') > 0 THEN ? ELSE serial END
           WHERE id = ?""",
        (usb_serial, endpoint, usb_serial, device_id),
    )
    return jsonify({"ok": True, "ip_port": endpoint, "usb_serial": usb_serial, "stable_uid": device.get("stable_uid")})


@devices_bp.route("/wifi/pair", methods=["POST"])
def wifi_pair():
    data = request.get_json() or {}
    pairing_ip_port = str(data.get("pairing_ip_port") or "").strip()
    pairing_code = str(data.get("pairing_code") or "").strip()
    res = adb.pair_wifi(pairing_ip_port, pairing_code)
    if not res["ok"]:
        return jsonify({"ok": False, "error": res["stderr"]}), 400
    return jsonify({"ok": True})


@devices_bp.route("/<int:device_id>/wifi/connect", methods=["POST"])
def wifi_connect(device_id):
    """Connect endpoint Wi-Fi ke HP TERDAFTAR tanpa mengganti identitas HP."""
    device, error = _device_or_404(device_id)
    if error:
        return error
    data = request.get_json() or {}
    endpoint = str(data.get("ip_port") or device.get("wifi_endpoint") or "").strip()
    res = adb.connect_wifi(endpoint)
    if not res["ok"]:
        return jsonify({"ok": False, "error": res["stderr"]}), 400
    legacy = str(device.get("serial") or "").strip()
    execute(
        """UPDATE devices
           SET wifi_endpoint = ?, preferred_transport = 'wifi', wifi_auto_reconnect = 1,
               last_transport = 'wifi', last_wifi_seen_at = CURRENT_TIMESTAMP,
               serial = CASE WHEN serial IS NULL OR TRIM(serial) = '' THEN ? ELSE serial END
           WHERE id = ?""",
        (endpoint, endpoint if not legacy else legacy, device_id),
    )
    return jsonify({"ok": True, "ip_port": endpoint, "stable_uid": device.get("stable_uid")})


@devices_bp.route("/<int:device_id>/wifi/reconnect", methods=["POST"])
def wifi_reconnect(device_id):
    device, error = _device_or_404(device_id)
    if error:
        return error
    result = conn.reconnect_device(device)
    if not result.get("ok"):
        return jsonify({"ok": False, "error": result.get("stderr") or result.get("error") or "Reconnect gagal"}), 400
    updated = query("SELECT * FROM devices WHERE id = ?", (device_id,), one=True)
    return jsonify({"ok": True, **conn.connection_snapshot(updated)})


@devices_bp.route("/<int:device_id>/wifi/disconnect", methods=["POST"])
def wifi_disconnect(device_id):
    device, error = _device_or_404(device_id)
    if error:
        return error
    endpoint = conn.transport_fields(device)[1]
    if not endpoint:
        return jsonify({"ok": True, "disconnected": False})
    res = adb.disconnect_wifi(endpoint)
    return jsonify({"ok": bool(res.get("ok", True)), "disconnected": bool(res.get("ok", True)), "ip_port": endpoint})


@devices_bp.route("/<int:device_id>", methods=["GET"])
def get_device(device_id):
    device, error = _device_or_404(device_id)
    if error:
        return error
    return jsonify(conn.enrich_device(device))


@devices_bp.route("", methods=["POST"])
def create_device():
    data = request.get_json() or {}
    name = str(data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Nama HP wajib diisi"}), 400
    legacy = str(data.get("serial") or "").strip()
    legacy_usb, legacy_wifi = _split_legacy_serial(legacy)
    usb_serial = str(data.get("usb_serial") or legacy_usb or "").strip() or None
    wifi_endpoint = str(data.get("wifi_endpoint") or legacy_wifi or "").strip() or None
    preferred = conn.normalize_preference(data.get("preferred_transport") or "auto")
    stable_uid = str(uuid.uuid4())
    compatibility_serial = usb_serial or wifi_endpoint or ""
    new_id = execute(
        """INSERT INTO devices
           (name, serial, label, notes, stable_uid, usb_serial, wifi_endpoint,
            preferred_transport, wifi_auto_reconnect)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            name,
            compatibility_serial,
            data.get("label", ""),
            data.get("notes", ""),
            stable_uid,
            usb_serial,
            wifi_endpoint,
            preferred,
            1 if data.get("wifi_auto_reconnect", True) else 0,
        ),
    )
    device = query("SELECT * FROM devices WHERE id = ?", (new_id,), one=True)
    return jsonify(conn.enrich_device(device)), 201


@devices_bp.route("/<int:device_id>", methods=["PUT"])
def update_device(device_id):
    data = request.get_json() or {}
    device, error = _device_or_404(device_id)
    if error:
        return error

    legacy_input = data.get("serial")
    usb_serial = data.get("usb_serial", device.get("usb_serial"))
    wifi_endpoint = data.get("wifi_endpoint", device.get("wifi_endpoint"))
    if legacy_input is not None and "usb_serial" not in data and "wifi_endpoint" not in data:
        legacy_usb, legacy_wifi = _split_legacy_serial(str(legacy_input))
        if legacy_usb is not None:
            usb_serial = legacy_usb
        elif legacy_wifi is not None:
            wifi_endpoint = legacy_wifi
    usb_serial = str(usb_serial or "").strip() or None
    wifi_endpoint = str(wifi_endpoint or "").strip() or None
    preferred = conn.normalize_preference(data.get("preferred_transport", device.get("preferred_transport")))
    auto_reconnect = 1 if data.get("wifi_auto_reconnect", device.get("wifi_auto_reconnect", 1)) else 0
    # Bila request UI v1.50 memang mengirim field transport, nilai kosong berarti
    # operator sengaja menghapus transport tersebut. Jangan hidupkan kembali
    # `serial` legacy, karena itu akan membuat endpoint lama muncul sebagai
    # fallback palsu. Request client lama yang sama sekali tidak menyentuh
    # field transport tetap mempertahankan serial kompatibilitasnya.
    touches_transport = any(key in data for key in ("serial", "usb_serial", "wifi_endpoint"))
    compatibility_serial = (usb_serial or wifi_endpoint or "") if touches_transport else str(device.get("serial") or "")

    execute(
        """UPDATE devices SET name = ?, serial = ?, label = ?, notes = ?,
           usb_serial = ?, wifi_endpoint = ?, preferred_transport = ?, wifi_auto_reconnect = ?
           WHERE id = ?""",
        (
            data.get("name", device["name"]),
            compatibility_serial,
            data.get("label", device.get("label")),
            data.get("notes", device.get("notes")),
            usb_serial,
            wifi_endpoint,
            preferred,
            auto_reconnect,
            device_id,
        ),
    )
    updated = query("SELECT * FROM devices WHERE id = ?", (device_id,), one=True)
    return jsonify(conn.enrich_device(updated))


@devices_bp.route("/<int:device_id>", methods=["DELETE"])
def delete_device(device_id):
    device, error = _device_or_404(device_id)
    if error:
        return error
    endpoint = conn.transport_fields(device)[1]
    if endpoint:
        adb.disconnect_wifi(endpoint)
    execute("DELETE FROM devices WHERE id = ?", (device_id,))
    return jsonify({"ok": True})
