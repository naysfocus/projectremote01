from flask import Flask, render_template, request, jsonify, redirect, url_for
from pathlib import Path
import os
import shutil
import time
import threading
from services.job_manager import (
    start_job, get_status, request_stop, has_running_job,
    configure_reporter, stop_all_running_jobs,
)
from services.storage_config import get_storage_base, set_storage_base, ensure_storage_dirs, list_subdirectories
from services.calculator import calculate_estimates, estimate_output_size
from services.output_safety import LARGE_OUTPUT_WARNING_THRESHOLD, render_output_warning
from services.ffmpeg_worker import (
    probe_duration,
    detect_best_encoder,
    ffmpeg_version_string,
    resolve_parallel_workers,
    parse_output_profile,
    estimate_video_bitrate_bps,
    estimate_audio_bitrate_bps,
)

from services.remote_server_client import RemoteServerClient
from version import APP_VERSION, APP_NAME, REMOTE_SERVER_URL

ALLOWED_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
ALLOWED_AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
MAX_GRID_SIZE = 10

# Ensure storage folders exist (default or configured).
ensure_storage_dirs(get_storage_base())

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["JSON_AS_ASCII"] = False

remote_server_client = RemoteServerClient()
app.extensions["remote_server_client"] = remote_server_client
configure_reporter(remote_server_client.queue_report)


def _validate_grid_size(data):
    """Validate the public UI/API matrix contract: 1..10 rows and columns."""
    try:
        h = int((data or {}).get("h") or 0)
        v = int((data or {}).get("v") or 0)
    except (TypeError, ValueError):
        return "invalid_grid_size"
    if h < 1 or v < 1 or h > MAX_GRID_SIZE or v > MAX_GRID_SIZE:
        return f"grid_size_must_be_1_to_{MAX_GRID_SIZE}"
    return None


@app.before_request
def require_remote_server_access():
    allowed_paths = {"/activation", "/api/health"}
    allowed_prefixes = ("/static/", "/api/remote-auth/")
    if request.path in allowed_paths or request.path.startswith(allowed_prefixes):
        return None
    if remote_server_client.is_allowed():
        return None
    if request.path.startswith("/api/"):
        status = remote_server_client.public_status()
        return jsonify({
            "ok": False,
            "error": status["message"],
            "remote_auth_status": status["status"],
        }), 423
    return redirect(url_for("activation_page"))


@app.get("/api/health")
def api_health():
    return jsonify({"ok": True, "app": "video_matrix_generator", "version": APP_VERSION})


@app.get("/activation")
def activation_page():
    status = remote_server_client.public_status()
    if status["allowed"]:
        return redirect(url_for("index"))
    return render_template("activation.html", status=status)


@app.get("/api/remote-auth/status")
def remote_auth_status():
    return jsonify(remote_server_client.public_status())


@app.post("/api/remote-auth/activate")
def remote_auth_activate():
    data = request.get_json(silent=True) or {}
    result = remote_server_client.activate(str(data.get("code") or ""))
    return jsonify(result), (200 if result.get("ok") else 400)


@app.post("/api/remote-auth/retry")
def remote_auth_retry():
    result = remote_server_client.retry()
    return jsonify(result), (200 if result.get("ok") else 409)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/system")
def api_system():
    """Info sistem untuk UI (v1.4): encoder terdeteksi, CPU, versi ffmpeg.

    Deteksi encoder di-cache per proses server — panggilan pertama bisa
    memakan 1-2 detik (test encode), selanjutnya instan.
    """
    det = detect_best_encoder()
    return jsonify({
        "ok": True,
        "appVersion": APP_VERSION,
        "cpuThreads": os.cpu_count() or 1,
        "autoWorkers": resolve_parallel_workers("auto"),
        "ffmpeg": ffmpeg_version_string(),
        "encoder": det,
    })


@app.post("/api/upload")
def api_upload():
    """Receive a single video file upload and store it in /storage/uploads.

    Returns a server-side path (container path) that ffmpeg can read.
    """
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "missing_file"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"ok": False, "error": "empty_filename"}), 400

    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"ok": False, "error": f"invalid_ext:{ext}"}), 400

    label = (request.form.get("label") or "clip").strip().replace("/", "_")
    # keep filenames deterministic-ish for humans, but unique for safety
    safe_name = "".join(ch for ch in label if ch.isalnum() or ch in ("_", "-"))[:32] or "clip"
    storage = get_storage_base()
    ensure_storage_dirs(storage)
    out = storage / "uploads" / f"{safe_name}_{int(time.time()*1000)}{ext}"
    f.save(out)
    return jsonify({"ok": True, "path": str(out)})


@app.post("/api/upload_audio")
def api_upload_audio():
    """Terima 1 file audio dan simpan ke /storage/audio.

    Dipakai untuk mode audio Replace/Mix (v1.9): user bisa upload 1..n file
    audio yang di-rolling round-robin per output video hasil generate.
    """
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "missing_file"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"ok": False, "error": "empty_filename"}), 400

    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_AUDIO_EXT:
        return jsonify({"ok": False, "error": f"invalid_ext:{ext}"}), 400

    original_name = f.filename
    safe_name = "".join(ch for ch in Path(original_name).stem if ch.isalnum() or ch in ("_", "-"))[:40] or "audio"
    storage = get_storage_base()
    ensure_storage_dirs(storage)
    out = storage / "audio" / f"{safe_name}_{int(time.time()*1000)}{ext}"
    f.save(out)
    return jsonify({"ok": True, "path": str(out), "filename": original_name})


@app.get("/api/audio_list")
def api_audio_list():
    """Daftar semua file audio yang sudah diupload ke /storage/audio."""
    storage = get_storage_base()
    dirs = ensure_storage_dirs(storage)
    audio_dir = dirs["audio"]
    items = []
    try:
        for p in sorted(audio_dir.iterdir(), key=lambda x: x.stat().st_mtime):
            if p.is_file() and p.suffix.lower() in ALLOWED_AUDIO_EXT:
                items.append({"path": str(p), "filename": p.name, "sizeBytes": p.stat().st_size})
    except Exception:
        pass
    return jsonify({"ok": True, "items": items, "count": len(items)})


@app.delete("/api/audio_delete")
def api_audio_delete():
    """Hapus 1 file audio berdasarkan path (harus berada di dalam folder audio)."""
    data = request.get_json(force=True) or {}
    path_str = (data.get("path") or "").strip()
    if not path_str:
        return jsonify({"ok": False, "error": "missing_path"}), 400

    storage = get_storage_base()
    dirs = ensure_storage_dirs(storage)
    audio_dir = dirs["audio"].resolve()
    try:
        target = Path(path_str).resolve()
        target.relative_to(audio_dir)  # guard: harus di dalam folder audio
    except Exception:
        return jsonify({"ok": False, "error": "invalid_path"}), 400

    try:
        if target.exists():
            target.unlink()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.delete("/api/audio_clear")
def api_audio_clear():
    """Hapus SEMUA file audio yang sudah diupload."""
    storage = get_storage_base()
    dirs = ensure_storage_dirs(storage)
    audio_dir = dirs["audio"]
    removed = 0
    try:
        for p in audio_dir.iterdir():
            if p.is_file():
                try:
                    p.unlink()
                    removed += 1
                except Exception:
                    pass
    except Exception:
        pass
    return jsonify({"ok": True, "removed": removed})


@app.get("/api/storage")
def api_storage_get():
    base = get_storage_base()
    return jsonify({"ok": True, "storageBase": str(base)})


@app.post("/api/storage")
def api_storage_set():
    data = request.get_json(force=True)
    p = (data.get("path") or "").strip()
    base = set_storage_base(p)
    return jsonify({"ok": True, "storageBase": str(base)})


@app.get("/api/storage/list_dirs")
def api_storage_list_dirs():
    path = request.args.get("path") or ""
    try:
        res = list_subdirectories(path)
        return jsonify({"ok": True, **res})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


def _folder_stats(folder: Path) -> dict:
    """Get file count and total size for a folder (recursive)."""
    count = 0
    total_bytes = 0
    try:
        if folder.exists():
            for p in folder.rglob("*"):
                if p.is_file():
                    count += 1
                    try:
                        total_bytes += p.stat().st_size
                    except Exception:
                        pass
    except Exception:
        pass
    return {"count": count, "sizeBytes": total_bytes}


@app.get("/api/storage/usage")
def api_storage_usage():
    """Return disk usage stats for uploads, temp, outputs, and audio folders."""
    base = get_storage_base()
    return jsonify({
        "ok": True,
        "uploads": _folder_stats(base / "uploads"),
        "temp": _folder_stats(base / "temp"),
        "outputs": _folder_stats(base / "outputs"),
        "audio": _folder_stats(base / "audio"),
    })


@app.delete("/api/storage/clean")
def api_storage_clean():
    """Delete all contents of specified subfolders (uploads, outputs, or both)."""
    # v1.5 FIX: dulu folder bisa dibersihkan saat render berjalan — menghapus
    # uploads/temp di tengah job merusak render aktif (file perantara & klip
    # sumber hilang). Kini ditolak dengan pesan jelas selama ada job running.
    if has_running_job():
        return jsonify({"ok": False, "error": "job_running: hentikan render dulu sebelum membersihkan storage"}), 409

    data = request.get_json(force=True)
    targets = data.get("targets") or []
    allowed = {"uploads", "outputs", "temp", "audio"}
    base = get_storage_base()
    cleaned = []

    for t in targets:
        t = str(t).strip().lower()
        if t not in allowed:
            continue
        folder = base / t
        try:
            if folder.exists():
                shutil.rmtree(folder)
            folder.mkdir(parents=True, exist_ok=True)
            cleaned.append(t)
        except Exception as e:
            return jsonify({"ok": False, "error": f"clean_{t}_failed: {e}"}), 500

    return jsonify({"ok": True, "cleaned": cleaned})


@app.post("/api/calc")
def api_calc():
    data = request.get_json(force=True) or {}
    if error := _validate_grid_size(data):
        return jsonify({"ok": False, "error": error}), 400
    # Calculator is intentionally pure (no file I/O).
    return jsonify({"ok": True, **calculate_estimates(data)})


@app.post("/api/estimate_size")
def api_estimate_size():
    """Estimasi total ukuran file/folder output (v1.1).

    Memprobe durasi klip di grid untuk mendapatkan rata-rata durasi, lalu
    menghitung perkiraan ukuran per mode & total. Ukuran nyata bisa berbeda
    karena encoder memakai CRF (variable bitrate).
    """
    data = request.get_json(force=True) or {}
    if error := _validate_grid_size(data):
        return jsonify({"ok": False, "error": error}), 400
    grid = data.get("grid") or []

    # Kumpulkan path unik dari grid, lalu probe durasinya.
    paths = []
    for row in grid:
        for cell in (row or []):
            p = cell.get("path") if isinstance(cell, dict) else cell
            if p:
                paths.append(p)
    unique_paths = list(dict.fromkeys(paths))  # jaga urutan, buang duplikat

    durations = []
    missing = 0
    for p in unique_paths:
        d = probe_duration(p)
        if d > 0:
            durations.append(d)
        else:
            missing += 1

    avg_clip = (sum(durations) / len(durations)) if durations else 0.0

    payload = dict(data)
    payload["avgClipDuration"] = avg_clip

    # v1.6: bitrate estimasi diturunkan dari profil output yang dipilih user
    # (resolusi/fps/kualitas atau bitrate target), bukan lagi ~8 Mbps tetap.
    profile = parse_output_profile({"outputProfile": data.get("outputProfile")})
    # v1.9: audioMode menggantikan muteAudio bila tersedia (mute/keep/replace/mix).
    audio_mode = str(data.get("audioMode") or "").strip().lower()
    mute_audio = (audio_mode == "mute") if audio_mode else bool(data.get("muteAudio", True))
    payload["videoBitrate"] = estimate_video_bitrate_bps(profile)
    payload["audioBitrate"] = estimate_audio_bitrate_bps(profile, mute_audio)
    # Diteruskan agar UI menampilkan asumsi resolusi/fps yang benar.
    payload["width"] = profile.width
    payload["height"] = profile.height
    payload["fps"] = profile.fps
    payload["rateMode"] = profile.rate_mode
    payload["quality"] = profile.quality

    result = estimate_output_size(payload)
    result["ok"] = True
    result["probedClips"] = len(durations)
    result["missingClips"] = missing
    return jsonify(result)


@app.post("/api/start")
def api_start():
    data = request.get_json(force=True) or {}
    if error := _validate_grid_size(data):
        return jsonify({"ok": False, "error": error}), 400

    total_outputs, per_mode, confirmation_token = render_output_warning(data, calculate_estimates)
    supplied_confirmation = str(data.get("largeOutputConfirmation") or "")
    if total_outputs > LARGE_OUTPUT_WARNING_THRESHOLD and supplied_confirmation != confirmation_token:
        return jsonify({
            "ok": False,
            "error": "large_output_confirmation_required",
            "warning": {
                "threshold": LARGE_OUTPUT_WARNING_THRESHOLD,
                "totalOutputs": str(total_outputs),
                "perMode": {key: str(value) for key, value in per_mode.items()},
                "grid": f"{int(data.get('h') or 0)} × {int(data.get('v') or 0)}",
                "confirmationToken": confirmation_token,
            },
        }), 409

    job_id = start_job(data)
    return jsonify({"ok": True, "jobId": job_id})

@app.get("/api/status/<job_id>")
def api_status(job_id):
    return jsonify(get_status(job_id))

@app.post("/api/stop/<job_id>")
def api_stop(job_id):
    """STOP job yang sedang berjalan.

    Menghentikan proses render saat ini & menghapus file setengah jadi, tetapi
    TIDAK menghapus video yang sudah selesai. Video yang sudah jadi tetap ada di
    folder outputs/<run_tag>/...
    """
    return jsonify(request_stop(job_id))

def _access_monitor():
    """Hentikan render yang sedang berjalan jika revoke/conflict diterima."""
    had_access = False
    while True:
        allowed = remote_server_client.is_allowed()
        if had_access and not allowed:
            stop_all_running_jobs()
        had_access = allowed
        time.sleep(2)


if __name__ == "__main__":
    host, port = "0.0.0.0", 5000
    remote_server_client.start()
    threading.Thread(target=_access_monitor, name="remote-access-monitor", daemon=True).start()
    try:
        from waitress import serve
        print(f"{APP_NAME} v{APP_VERSION} — http://localhost:{port} (waitress)")
        print(f"Aktivasi dan sesi dikelola oleh {REMOTE_SERVER_URL}")
        serve(app, host=host, port=port, threads=8)
    except ImportError:
        print(f"{APP_NAME} v{APP_VERSION} — http://localhost:{port} (flask)")
        app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)
    finally:
        remote_server_client.shutdown()
