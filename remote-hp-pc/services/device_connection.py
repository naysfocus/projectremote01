"""Device identity and ADB transport resolution for Remote HP v1.50.

A physical handset is represented by the stable local ``devices.id`` and
``stable_uid``. USB serials and Wi-Fi ``ip:port`` endpoints are transports,
not identities. This module keeps transport switching out of the upload and
scrcpy workflows so they can always ask for one currently usable ADB target.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

from database.db import execute, query
from services import adb

VALID_TRANSPORTS = {"auto", "wifi", "usb"}
RECONNECT_INTERVAL_SECONDS = 30
RECONNECT_BACKOFF_SECONDS = 60


def utc_now_sql() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def normalize_preference(value: Any) -> str:
    value = str(value or "auto").strip().lower()
    return value if value in VALID_TRANSPORTS else "auto"


def transport_fields(device: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (usb_serial, wifi_endpoint) with legacy ``serial`` fallback."""
    legacy = str(device.get("serial") or "").strip()
    usb_serial = str(device.get("usb_serial") or "").strip() or None
    wifi_endpoint = str(device.get("wifi_endpoint") or "").strip() or None
    if legacy:
        if ":" in legacy and not wifi_endpoint:
            wifi_endpoint = legacy
        elif ":" not in legacy and not usb_serial:
            usb_serial = legacy
    return usb_serial, wifi_endpoint


def connection_snapshot(
    device: dict[str, Any], online_serials: set[str] | None = None
) -> dict[str, Any]:
    """Build current transport state for a DB device row.

    Preference affects which online transport wins, but is not a hard lock:
    if the preferred transport is unavailable and the fallback is online,
    Remote HP continues using the fallback instead of blocking the workflow.
    """
    if online_serials is None:
        online_serials = adb.get_online_serials()
    usb_serial, wifi_endpoint = transport_fields(device)
    usb_online = bool(usb_serial and usb_serial in online_serials)
    wifi_online = bool(wifi_endpoint and wifi_endpoint in online_serials)
    preference = normalize_preference(device.get("preferred_transport"))

    if preference == "usb":
        order = (("usb", usb_serial, usb_online), ("wifi", wifi_endpoint, wifi_online))
    else:
        # auto deliberately prefers wireless once it is configured. This is
        # the cable-free default while preserving USB as a recovery path.
        order = (("wifi", wifi_endpoint, wifi_online), ("usb", usb_serial, usb_online))

    active_transport = None
    active_serial = None
    for transport, serial, online in order:
        if serial and online:
            active_transport = transport
            active_serial = serial
            break

    return {
        "online": bool(active_serial),
        "active_transport": active_transport,
        "active_serial": active_serial,
        "preferred_transport": preference,
        "usb_serial": usb_serial,
        "wifi_endpoint": wifi_endpoint,
        "usb_online": usb_online,
        "wifi_online": wifi_online,
        "wifi_auto_reconnect": bool(device.get("wifi_auto_reconnect", 1)),
        "stable_uid": device.get("stable_uid"),
        "last_transport": device.get("last_transport"),
        "last_usb_seen_at": device.get("last_usb_seen_at"),
        "last_wifi_seen_at": device.get("last_wifi_seen_at"),
    }


def active_target(device: dict[str, Any], online_serials: set[str] | None = None) -> tuple[str | None, dict[str, Any]]:
    snapshot = connection_snapshot(device, online_serials)
    return snapshot["active_serial"], snapshot


def active_target_for_id(device_id: int) -> tuple[str | None, dict[str, Any] | None, dict[str, Any] | None]:
    device = query("SELECT * FROM devices WHERE id = ?", (device_id,), one=True)
    if not device:
        return None, None, None
    target, snapshot = active_target(device)
    return target, snapshot, device


def mark_seen(device_id: int, snapshot: dict[str, Any]) -> None:
    """Persist last-seen transport metadata without changing device identity."""
    now = utc_now_sql()
    if snapshot.get("wifi_online"):
        execute(
            "UPDATE devices SET last_wifi_seen_at = ?, last_transport = ? WHERE id = ?",
            (now, snapshot.get("active_transport") or "wifi", device_id),
        )
    if snapshot.get("usb_online"):
        execute(
            "UPDATE devices SET last_usb_seen_at = ?, last_transport = COALESCE(?, last_transport) WHERE id = ?",
            (now, snapshot.get("active_transport"), device_id),
        )


def enrich_device(device: dict[str, Any], online_serials: set[str] | None = None, persist_seen: bool = False) -> dict[str, Any]:
    snapshot = connection_snapshot(device, online_serials)
    result = dict(device)
    result.update(snapshot)
    # ``serial`` remains in responses for old front-end/client compatibility,
    # but represents the current active target when one is online.
    result["serial"] = snapshot["active_serial"] or snapshot["usb_serial"] or snapshot["wifi_endpoint"] or device.get("serial")
    if persist_seen and snapshot["online"]:
        mark_seen(int(device["id"]), snapshot)
    return result


def reconnect_device(device: dict[str, Any]) -> dict[str, Any]:
    endpoint = transport_fields(device)[1]
    if not endpoint:
        return {"ok": False, "error": "HP belum memiliki endpoint Wi-Fi.", "ip_port": None}
    result = adb.connect_wifi(endpoint)
    if result.get("ok"):
        now = utc_now_sql()
        execute(
            "UPDATE devices SET last_wifi_seen_at = ?, last_transport = 'wifi' WHERE id = ?",
            (now, int(device["id"])),
        )
    return result


class WirelessAdbManager:
    """Low-frequency reconnect loop for known Wi-Fi ADB endpoints.

    It never scans the LAN and never changes a handset identity. It only calls
    ``adb connect`` for endpoints explicitly saved by the operator. Attempts
    are rate-limited per handset to avoid aggressive polling.
    """

    def __init__(self, interval: int = RECONNECT_INTERVAL_SECONDS, backoff: int = RECONNECT_BACKOFF_SECONDS):
        self.interval = max(10, int(interval))
        self.backoff = max(self.interval, int(backoff))
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_attempt: dict[int, float] = {}
        self._lock = threading.RLock()

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._worker, name="wireless-adb-manager", daemon=True)
            self._thread.start()

    def shutdown(self) -> None:
        self._stop.set()
        self._wake.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)

    def request_reconnect(self) -> None:
        self._wake.set()

    def run_once(self) -> None:
        devices = query(
            "SELECT * FROM devices WHERE wifi_endpoint IS NOT NULL AND TRIM(wifi_endpoint) <> '' AND COALESCE(wifi_auto_reconnect,1) = 1"
        )
        if not devices:
            return
        online = adb.get_online_serials()
        now_monotonic = time.monotonic()
        for device in devices:
            endpoint = transport_fields(device)[1]
            if not endpoint:
                continue
            device_id = int(device["id"])
            usb_serial, _ = transport_fields(device)
            if endpoint in online:
                snapshot = connection_snapshot(device, online)
                mark_seen(device_id, snapshot)
                continue
            # If USB is currently the explicitly preferred and available path,
            # there is no need to hammer Wi-Fi. Auto/wifi still keeps Wi-Fi warm.
            pref = normalize_preference(device.get("preferred_transport"))
            if pref == "usb" and usb_serial and usb_serial in online:
                continue
            last = self._last_attempt.get(device_id, 0.0)
            if now_monotonic - last < self.backoff:
                continue
            self._last_attempt[device_id] = now_monotonic
            result = adb.connect_wifi(endpoint)
            if result.get("ok"):
                online.add(endpoint)
                execute(
                    "UPDATE devices SET last_wifi_seen_at = ?, last_transport = 'wifi' WHERE id = ?",
                    (utc_now_sql(), device_id),
                )

    def _worker(self) -> None:
        # Delay the first pass slightly so ADB/server startup is not blocked.
        self._stop.wait(2.0)
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception:
                # Reconnect is convenience, never a reason to crash Remote HP.
                pass
            self._wake.wait(self.interval)
            self._wake.clear()
