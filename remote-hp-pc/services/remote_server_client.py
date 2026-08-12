"""Client Remote Server untuk Remote HP.

Modul ini menangani aktivasi, sesi tunggal, heartbeat, grace period, revoke,
dan antrean laporan tanpa mengubah alur ADB/scrcpy aplikasi utama.
"""
from __future__ import annotations

import atexit
import base64
import ctypes
import hashlib
import json
import logging
import os
import platform
import re
import socket
import sqlite3
import threading
import time
import uuid

from services.remote_hp_data_sync import build_inventory_snapshot, build_session_rows, session_batches, session_reconcile_payload
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

APP_TYPE = "remote_hp"
APP_VERSION = "1.51.0"
DEFAULT_SERVER_URL = "https://remote.darda.uk"
DEFAULT_GRACE_HOURS = 3
DEFAULT_HEARTBEAT_SECONDS = 300
REQUEST_TIMEOUT = (5, 12)

log = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utcnow().isoformat()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _data_dir() -> Path:
    if os.name == "nt":
        root = Path(os.getenv("APPDATA") or Path.home())
        path = root / "RemoteHP"
    else:
        root = Path(os.getenv("XDG_CONFIG_HOME") or (Path.home() / ".config"))
        path = root / "remote-hp"
    path.mkdir(parents=True, exist_ok=True)
    try:
        path.chmod(0o700)
    except OSError:
        pass
    return path


def _machine_identity() -> str:
    parts: list[str] = [platform.system(), platform.machine()]
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                parts.append(str(winreg.QueryValueEx(key, "MachineGuid")[0]))
        except OSError:
            pass
    else:
        for candidate in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            try:
                value = Path(candidate).read_text(encoding="utf-8").strip()
                if value:
                    parts.append(value)
                    break
            except OSError:
                continue
    if len(parts) <= 2:
        parts.extend([socket.gethostname(), str(uuid.getnode())])
    return "|".join(parts)


def fingerprint_hash() -> str:
    raw = f"remote-hp|{_machine_identity()}".encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()


def os_type() -> str:
    return "windows" if os.name == "nt" else "linux"


def os_info() -> str:
    return f"{platform.system()} {platform.release()} {platform.machine()}"[:255]


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi_protect(value: str) -> str:
    if os.name != "nt":
        return value
    raw = value.encode("utf-8")
    in_buffer = ctypes.create_string_buffer(raw)
    in_blob = _DataBlob(len(raw), ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_char)))
    out_blob = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptProtectData(
        ctypes.byref(in_blob), "Remote HP", None, None, None, 0, ctypes.byref(out_blob)
    ):
        raise OSError("Windows gagal melindungi token Remote Server.")
    try:
        protected = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        return "dpapi:" + base64.b64encode(protected).decode("ascii")
    finally:
        kernel32.LocalFree(out_blob.pbData)


def _dpapi_unprotect(value: str) -> str:
    if os.name != "nt" or not value.startswith("dpapi:"):
        return value
    raw = base64.b64decode(value.split(":", 1)[1])
    in_buffer = ctypes.create_string_buffer(raw)
    in_blob = _DataBlob(len(raw), ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_char)))
    out_blob = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
    ):
        raise OSError("Windows gagal membuka token Remote Server.")
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData).decode("utf-8")
    finally:
        kernel32.LocalFree(out_blob.pbData)


class ClientStore:
    def __init__(self) -> None:
        self.path = _data_dir() / "remote-server-client.json"
        self._lock = threading.RLock()

    def load(self) -> dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                return {}
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                # File itu sendiri rusak/tidak terbaca sama sekali. Di sini saja
                # aman untuk mulai dari config kosong, karena tidak ada apapun
                # yang bisa diselamatkan dari file yang tidak valid.
                log.warning("Konfigurasi Remote Server tidak dapat dibaca: %s", exc)
                return {}

            protected = data.pop("access_token_protected", "")
            if protected:
                try:
                    data["access_token"] = _dpapi_unprotect(protected)
                except OSError as exc:
                    # Token gagal didekripsi (mis. DPAPI terikat ke user/sesi
                    # login yang berbeda setelah restart). Buang token itu saja
                    # supaya aplikasi meminta aktivasi ulang -- TAPI jangan buang
                    # field lain seperti fingerprint_hash/device_id/server_url,
                    # karena itu bukan yang gagal dibaca. Kalau seluruh config
                    # ikut dibuang, fingerprint akan dihitung ulang dari nol dan
                    # device ini akan terlihat seperti "device baru" bagi server,
                    # padahal token lama masih terdaftar di sana -- itu yang
                    # menyebabkan aktivasi ulang selalu ditolak "already_activated".
                    log.warning(
                        "Token Remote Server gagal didekripsi, token akan diminta "
                        "ulang tanpa mengubah identitas device: %s",
                        exc,
                    )
                    data.pop("access_token", None)
                    data["token_recovery_needed"] = True
            return data

    def save(self, data: dict[str, Any]) -> None:
        with self._lock:
            serializable = dict(data)
            raw_token = serializable.pop("access_token", "")
            if raw_token:
                serializable["access_token_protected"] = _dpapi_protect(raw_token)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(serializable, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            try:
                tmp.chmod(0o600)
            except OSError:
                pass
            os.replace(tmp, self.path)
            try:
                self.path.chmod(0o600)
            except OSError:
                pass


class ReportQueue:
    def __init__(self) -> None:
        self.path = _data_dir() / "remote-report-queue.sqlite3"
        self._lock = threading.RLock()
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_report_id TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def enqueue(self, event_type: str, summary: dict[str, Any]) -> str:
        report_id = str(uuid.uuid4())
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO reports (client_report_id, event_type, occurred_at, summary_json) VALUES (?, ?, ?, ?)",
                    (report_id, event_type, iso_now(), json.dumps(summary, ensure_ascii=False, default=str)),
                )
                conn.commit()
            finally:
                conn.close()
        return report_id

    def pending(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute("SELECT * FROM reports ORDER BY id LIMIT ?", (limit,)).fetchall()
            finally:
                conn.close()
        return [dict(row) for row in rows]

    def remove(self, ids: list[int]) -> None:
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(f"DELETE FROM reports WHERE id IN ({placeholders})", ids)
                conn.commit()
            finally:
                conn.close()

    def mark_failed(self, ids: list[int], error: str) -> None:
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    f"UPDATE reports SET attempts = attempts + 1, last_error = ? WHERE id IN ({placeholders})",
                    [error[:500], *ids],
                )
                conn.commit()
            finally:
                conn.close()

    def count(self) -> int:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute("SELECT COUNT(*) AS c FROM reports").fetchone()
            finally:
                conn.close()
        return int(row["c"] if row else 0)


class RemoteServerClient:
    def __init__(self, server_url: str = DEFAULT_SERVER_URL, *, register_atexit: bool = True) -> None:
        self.store = ClientStore()
        self.reports = ReportQueue()
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._data_sync_requested = threading.Event()
        self._force_data_sync = False
        self._pending_session_ids: set[int] = set()
        self._thread: threading.Thread | None = None
        self._http = requests.Session()
        self._config = self.store.load()
        self._config.setdefault("server_url", server_url.rstrip("/"))
        self._config.setdefault("fingerprint_hash", fingerprint_hash())
        self._config.setdefault("grace_period_hours", DEFAULT_GRACE_HOURS)
        self._config.setdefault("heartbeat_interval_seconds", DEFAULT_HEARTBEAT_SECONDS)
        self._status = "activation_required" if not self._config.get("access_token") else "connecting"
        self._message = "Masukkan kode aktivasi dari admin Remote Server."
        self._last_error = ""
        self._allowed = False
        self._next_heartbeat_at: datetime | None = None
        self._started_reported = False
        self.store.save(self._config)
        if register_atexit:
            atexit.register(self.shutdown)

    @property
    def server_url(self) -> str:
        return str(self._config.get("server_url") or DEFAULT_SERVER_URL).rstrip("/")

    @property
    def token(self) -> str:
        return str(self._config.get("access_token") or "")

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._worker, name="remote-server-client", daemon=True)
            self._thread.start()

    def is_allowed(self) -> bool:
        with self._lock:
            return self._allowed

    def public_status(self) -> dict[str, Any]:
        with self._lock:
            last_success = parse_datetime(self._config.get("last_success_at"))
            grace_until = self._grace_until()
            return {
                "ok": True,
                "activated": bool(self.token),
                "allowed": self._allowed,
                "status": self._status,
                "message": self._message,
                "last_error": self._last_error,
                "server_url": self.server_url,
                "device_id": self._config.get("device_id"),
                "fingerprint_short": self._config.get("fingerprint_hash", "")[:12],
                "last_online_at": last_success.isoformat() if last_success else None,
                "grace_until": grace_until.isoformat() if grace_until else None,
                "next_heartbeat_at": self._next_heartbeat_at.isoformat() if self._next_heartbeat_at else None,
                "queued_reports": self._queued_report_count(),
                "app_version": APP_VERSION,
                "last_data_sync_at": self._config.get("last_data_sync_at"),
                "last_data_sync_error": self._config.get("last_data_sync_error", ""),
            }

    def _queued_report_count(self) -> int:
        try:
            return self.reports.count()
        except sqlite3.Error:
            return 0

    def activate(self, code: str) -> dict[str, Any]:
        normalized = re.sub(r"\s+", "", (code or "").upper())
        if not 8 <= len(normalized) <= 16:
            return {"ok": False, "error": "Kode aktivasi harus terdiri dari 8–16 karakter."}
        payload = {
            "code": normalized,
            "app_type": APP_TYPE,
            "fingerprint_hash": self._config["fingerprint_hash"],
            "os_type": os_type(),
            "os_info": os_info(),
            "app_version": APP_VERSION,
        }
        try:
            response = self._http.post(
                f"{self.server_url}/api/v1/activate", json=payload, timeout=REQUEST_TIMEOUT
            )
            body = self._json(response)
        except requests.RequestException as exc:
            self._set_state("offline_blocked", False, "Remote Server tidak dapat dijangkau.", str(exc))
            return {"ok": False, "error": "Remote Server tidak dapat dijangkau. Periksa internet lalu coba lagi."}
        if response.status_code != 200 or not body.get("ok"):
            code_error = body.get("error") or body.get("detail") or f"HTTP {response.status_code}"
            messages = {
                "code_invalid": "Kode aktivasi tidak valid.",
                "code_consumed": "Kode aktivasi sudah pernah digunakan.",
                "code_expired": "Kode aktivasi sudah kedaluwarsa.",
                "code_cancelled": "Kode aktivasi telah dibatalkan.",
                "code_app_mismatch": "Kode ini bukan untuk aplikasi Remote HP.",
                "already_activated": "Komputer ini sudah pernah diaktivasi. Hubungi admin untuk pemulihan token.",
            }
            return {"ok": False, "error": messages.get(str(code_error), f"Aktivasi ditolak: {code_error}")}
        self._config.update(
            {
                "access_token": body["access_token"],
                "device_id": body.get("device_id"),
                "session_id": None,
                "inventory_digest": None,
                "session_digest": None,
                "last_data_sync_at": None,
                "last_full_reconcile_at": None,
            }
        )
        self.store.save(self._config)
        self._set_state("connecting", False, "Aktivasi berhasil. Membuka sesi Remote Server…")
        result = self.connect()
        self.request_data_sync(force=True)
        self._wake.set()
        return {"ok": result.get("ok", False), **result}

    def retry(self) -> dict[str, Any]:
        if not self.token:
            return {"ok": False, "error": "Aplikasi belum diaktivasi."}
        return self.connect()

    def connect(self) -> dict[str, Any]:
        if not self.token:
            self._set_state("activation_required", False, "Masukkan kode aktivasi dari admin Remote Server.")
            return {"ok": False, "error": "activation_required"}
        self._set_state("connecting", False, "Menghubungkan ke Remote Server…")
        saved_session = self._config.get("session_id")
        if saved_session:
            resumed = self._heartbeat_request(str(saved_session), allow_open_after_superseded=True)
            if resumed is not None:
                return resumed
        payload = {
            "fingerprint_hash": self._config["fingerprint_hash"],
            "app_version": APP_VERSION,
        }
        try:
            response = self._authorized_post("/api/v1/session/open", payload)
            body = self._json(response)
        except requests.RequestException as exc:
            return self._network_failure(exc)
        if response.status_code == 200 and body.get("status") == "active":
            self._config.update(
                {
                    "session_id": body.get("session_id"),
                    "grace_period_hours": int(body.get("grace_period_hours", DEFAULT_GRACE_HOURS)),
                    "heartbeat_interval_seconds": int(
                        body.get("heartbeat_interval_seconds", DEFAULT_HEARTBEAT_SECONDS)
                    ),
                    "session_timeout_seconds": int(body.get("session_timeout_seconds", 900)),
                    "last_success_at": iso_now(),
                }
            )
            self.store.save(self._config)
            self._mark_active("Remote Server terhubung.")
            self.request_data_sync(force=not bool(self._config.get("last_data_sync_at")))
            return {"ok": True, "status": "active"}
        return self._explicit_rejection(response.status_code, body)

    def queue_report(self, event_type: str, summary: dict[str, Any]) -> str:
        report_id = self.reports.enqueue(event_type, summary)
        self._wake.set()
        return report_id

    def request_data_sync(self, *, force: bool = False, session_id: int | None = None) -> None:
        """Schedule privacy-safe sync; normal progress sends only the changed session."""
        with self._lock:
            if force:
                self._force_data_sync = True
            if session_id is not None and int(session_id) > 0:
                self._pending_session_ids.add(int(session_id))
        self._data_sync_requested.set()
        self._wake.set()

    def shutdown(self) -> None:
        if self._stop.is_set():
            return
        self._stop.set()
        self._wake.set()
        if self.token and self._config.get("session_id"):
            try:
                try:
                    self.queue_report("app_stopped", {"app_version": APP_VERSION, "status": "closed"})
                    self._flush_reports()
                except (OSError, sqlite3.Error):
                    pass
                response = self._authorized_post(
                    "/api/v1/session/close",
                    {"session_id": self._config.get("session_id")},
                    timeout=(3, 4),
                )
                if response.status_code in {200, 403, 409}:
                    self._config["session_id"] = None
                    self.store.save(self._config)
            except Exception as exc:  # shutdown harus selalu best-effort
                log.debug("Gagal menutup sesi Remote Server saat shutdown: %s", exc)

    def _worker(self) -> None:
        if self.token:
            self.connect()
        while not self._stop.is_set():
            with self._lock:
                status = self._status
                interval = int(self._config.get("heartbeat_interval_seconds", DEFAULT_HEARTBEAT_SECONDS))
            wait_seconds = interval if status in {"active", "grace"} else 15
            self._next_heartbeat_at = utcnow() + timedelta(seconds=wait_seconds)
            self._wake.wait(wait_seconds)
            self._wake.clear()
            if self._stop.is_set():
                break
            if not self.token:
                continue
            if self._status == "active" and self._config.get("session_id"):
                self._heartbeat_request(str(self._config["session_id"]))
            elif self._status == "grace" and self._within_grace():
                self._heartbeat_request(str(self._config.get("session_id") or "")) if self._config.get("session_id") else self.connect()
            elif self._status in {"connecting", "offline_blocked", "server_error"}:
                self.connect()
            if self._status == "active":
                self._flush_reports()
                self._sync_remote_hp_data()

    def _heartbeat_request(self, session_id: str, allow_open_after_superseded: bool = False) -> dict[str, Any] | None:
        try:
            response = self._authorized_post(
                "/api/v1/session/heartbeat", {"session_id": session_id}
            )
            body = self._json(response)
        except requests.RequestException as exc:
            return self._network_failure(exc)
        if response.status_code == 200 and body.get("status") == "active":
            self._config["last_success_at"] = iso_now()
            self.store.save(self._config)
            self._mark_active("Remote Server terhubung.")
            self._flush_reports()
            self.request_data_sync()
            return {"ok": True, "status": "active"}
        if response.status_code == 409 and body.get("status") == "session_superseded" and allow_open_after_superseded:
            self._config["session_id"] = None
            self.store.save(self._config)
            return None
        return self._explicit_rejection(response.status_code, body)

    def _flush_reports(self) -> None:
        if self._status != "active" or not self.token:
            return
        rows = self.reports.pending(50)
        if not rows:
            return
        payload_reports = [
            {
                "client_report_id": row["client_report_id"],
                "event_type": row["event_type"],
                "occurred_at": row["occurred_at"],
                "summary": json.loads(row["summary_json"]),
            }
            for row in rows
        ]
        ids = [int(row["id"]) for row in rows]
        try:
            response = self._authorized_post("/api/v1/report", {"reports": payload_reports})
            body = self._json(response)
        except requests.RequestException as exc:
            self.reports.mark_failed(ids, str(exc))
            return
        if response.status_code == 200 and body.get("ok"):
            self.reports.remove(ids)
        elif response.status_code == 403:
            self.reports.mark_failed(ids, "revoked")
            self._set_state("revoked", False, "Akses Remote HP dicabut oleh admin.", "revoked")
        else:
            self.reports.mark_failed(ids, str(body.get("detail") or body.get("error") or response.status_code))

    def _sync_remote_hp_data(self) -> None:
        if self._status != "active" or not self.token:
            return
        now = utcnow()
        last_full = parse_datetime(self._config.get("last_full_reconcile_at"))
        periodic_full = not last_full or (now - last_full).total_seconds() >= 6 * 3600
        requested = self._data_sync_requested.is_set()
        with self._lock:
            force = bool(self._force_data_sync or periodic_full)
            pending_session_ids = set(self._pending_session_ids)
            self._pending_session_ids.clear()
            self._force_data_sync = False
        if not requested and not periodic_full:
            return
        self._data_sync_requested.clear()
        try:
            inventory_payload, inventory_digest = build_inventory_snapshot()
            if force or inventory_digest != self._config.get("inventory_digest"):
                response = self._authorized_post("/api/v1/remote-hp/inventory-sync", inventory_payload, timeout=(5, 30))
                body = self._json(response)
                if response.status_code == 403:
                    self._explicit_rejection(response.status_code, body)
                    return
                if response.status_code != 200 or not body.get("ok"):
                    raise RuntimeError(f"inventory_sync_http_{response.status_code}:{body}")
                self._config["inventory_digest"] = inventory_digest

            if force:
                rows, sessions_digest = build_session_rows()
                for payload in session_batches(rows):
                    response = self._authorized_post("/api/v1/remote-hp/session-sync", payload, timeout=(5, 45))
                    body = self._json(response)
                    if response.status_code == 403:
                        self._explicit_rejection(response.status_code, body)
                        return
                    if response.status_code != 200 or not body.get("ok"):
                        raise RuntimeError(f"session_sync_http_{response.status_code}:{body}")
                reconcile = self._authorized_post(
                    "/api/v1/remote-hp/session-reconcile", session_reconcile_payload(rows), timeout=(5, 45)
                )
                reconcile_body = self._json(reconcile)
                if reconcile.status_code == 403:
                    self._explicit_rejection(reconcile.status_code, reconcile_body)
                    return
                if reconcile.status_code != 200 or not reconcile_body.get("ok"):
                    raise RuntimeError(f"session_reconcile_http_{reconcile.status_code}:{reconcile_body}")
                self._config["session_digest"] = sessions_digest
            elif pending_session_ids:
                rows, _ = build_session_rows(pending_session_ids)
                for payload in session_batches(rows):
                    response = self._authorized_post("/api/v1/remote-hp/session-sync", payload, timeout=(5, 45))
                    body = self._json(response)
                    if response.status_code == 403:
                        self._explicit_rejection(response.status_code, body)
                        return
                    if response.status_code != 200 or not body.get("ok"):
                        raise RuntimeError(f"session_sync_http_{response.status_code}:{body}")

            self._config["last_data_sync_at"] = iso_now()
            self._config["last_data_sync_error"] = ""
            if force:
                self._config["last_full_reconcile_at"] = iso_now()
            self.store.save(self._config)
        except Exception as exc:
            # Operational sync failure must never interrupt ADB/scrcpy workflow.
            self._config["last_data_sync_error"] = str(exc)[:500]
            self.store.save(self._config)
            with self._lock:
                self._pending_session_ids.update(pending_session_ids)
                if force:
                    self._force_data_sync = True
            self._data_sync_requested.set()
            log.warning("Sinkronisasi inventaris/progres Remote HP ditunda: %s", exc)

    def _authorized_post(self, path: str, payload: dict[str, Any], timeout=REQUEST_TIMEOUT):
        return self._http.post(
            f"{self.server_url}{path}",
            json=payload,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=timeout,
        )

    @staticmethod
    def _json(response: requests.Response) -> dict[str, Any]:
        try:
            value = response.json()
            return value if isinstance(value, dict) else {}
        except ValueError:
            return {}

    def _mark_active(self, message: str) -> None:
        self._set_state("active", True, message)
        if not self._started_reported:
            self._started_reported = True
            self.reports.enqueue(
                "app_started",
                {"app_version": APP_VERSION, "os": os_info(), "status": "active"},
            )
            self.request_data_sync(force=not bool(self._config.get("last_data_sync_at")))

    def _explicit_rejection(self, status_code: int, body: dict[str, Any]) -> dict[str, Any]:
        status = str(body.get("status") or body.get("detail") or body.get("error") or "rejected")
        if status_code == 403 or status == "revoked":
            self._set_state("revoked", False, "Akses Remote HP dicabut oleh admin.", status)
            return {"ok": False, "status": "revoked", "error": self._message}
        if status_code == 409 and status in {"session_conflict", "session_superseded"}:
            self._set_state(
                "conflict",
                False,
                "Aplikasi terdeteksi aktif pada sesi lain. Tutup sesi lain atau tunggu admin memeriksa.",
                status,
            )
            return {"ok": False, "status": "conflict", "error": self._message}
        if status_code == 401:
            self._set_state(
                "invalid_token",
                False,
                "Token aktivasi tidak berlaku. Hubungi admin Remote Server.",
                status,
            )
            return {"ok": False, "status": "invalid_token", "error": self._message}
        self._set_state("server_error", False, "Remote Server menolak koneksi.", status)
        return {"ok": False, "status": "server_error", "error": self._message}

    def _network_failure(self, exc: Exception) -> dict[str, Any]:
        if self._within_grace():
            grace_until = self._grace_until()
            text = "Internet terputus. Remote HP tetap dapat dipakai dalam grace period."
            if grace_until:
                text += f" Batas: {grace_until.astimezone().strftime('%d-%m-%Y %H:%M')}."
            self._set_state("grace", True, text, str(exc))
            return {"ok": True, "status": "grace", "message": text}
        self._set_state(
            "offline_blocked",
            False,
            "Remote Server tidak dapat dijangkau dan grace period tidak tersedia atau sudah berakhir.",
            str(exc),
        )
        return {"ok": False, "status": "offline_blocked", "error": self._message}

    def _within_grace(self) -> bool:
        grace_until = self._grace_until()
        return bool(grace_until and utcnow() <= grace_until)

    def _grace_until(self) -> datetime | None:
        last_success = parse_datetime(self._config.get("last_success_at"))
        if not last_success:
            return None
        hours = int(self._config.get("grace_period_hours", DEFAULT_GRACE_HOURS))
        return last_success + timedelta(hours=hours)

    def _set_state(self, status: str, allowed: bool, message: str, error: str = "") -> None:
        with self._lock:
            self._status = status
            self._allowed = allowed
            self._message = message
            self._last_error = error[:500] if error else ""
