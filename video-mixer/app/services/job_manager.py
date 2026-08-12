import re, uuid, threading, time
from pathlib import Path
from services.calculator import build_job_plan
from services.ffmpeg_worker import process_job
from services.storage_config import get_storage_base

JOBS = {}

_REPORTER = None


def configure_reporter(reporter):
    """Pasang callback laporan Remote Server tanpa mengikat worker ke HTTP client."""
    global _REPORTER
    _REPORTER = reporter


def _report_completed_job(job_id):
    if not _REPORTER:
        return
    job = JOBS.get(job_id) or {}
    if job.get("status") != "done":
        return
    meta = job.get("meta") or {}
    output_dir = str(meta.get("outputDir") or "")
    video_count = 0
    if output_dir:
        try:
            video_count = sum(1 for item in Path(output_dir).rglob("*.mp4") if item.is_file())
        except OSError:
            video_count = int(job.get("done") or 0)
    modes = [name for name, value in (job.get("perMode") or {}).items() if int(value.get("total") or 0) > 0]
    duration = max(0.0, float(job.get("finishedAt") or time.time()) - float(job.get("startedAt") or job.get("createdAt") or time.time()))
    summary = {
        "mode": "+".join(modes) if modes else "unknown",
        "video_count": int(video_count),
        "duration_seconds": round(duration, 3),
        "run_tag": str(meta.get("runTag") or job_id),
        "client_timezone": str(meta.get("clientTimeZone") or ""),
        "client_utc_offset_minutes": int(meta.get("clientUtcOffsetMinutes") or 0),
        "client_local_started_at": str(meta.get("clientLocalStartedAt") or ""),
    }
    try:
        _REPORTER("generate_completed", summary)
    except Exception:
        # Pelaporan tidak boleh membuat render yang sudah selesai berubah error.
        pass


# v1.5 FIX: waitress melayani request dengan banyak thread. Dua /api/start
# bersamaan bisa menambah key JOBS di tengah iterasi _prune_finished_jobs()
# → "RuntimeError: dictionary changed size during iteration". Semua operasi
# tambah/pangkas registry kini dilindungi lock.
_JOBS_LOCK = threading.Lock()

# v1.4: jangan biarkan riwayat job menumpuk tanpa batas di RAM.
MAX_FINISHED_JOBS = 15


def _prune_finished_jobs_locked():
    """Simpan hanya N job terakhir yang sudah selesai/batal/error.

    Harus dipanggil dengan _JOBS_LOCK sudah dipegang.
    """
    finished = [
        (jid, j) for jid, j in JOBS.items()
        if j.get("status") in ("done", "cancelled", "error")
    ]
    if len(finished) <= MAX_FINISHED_JOBS:
        return
    finished.sort(key=lambda kv: kv[1].get("finishedAt") or kv[1].get("createdAt") or 0)
    for jid, _ in finished[: len(finished) - MAX_FINISHED_JOBS]:
        JOBS.pop(jid, None)


def has_running_job() -> bool:
    """True bila masih ada job berstatus running (dipakai guard /api/storage/clean)."""
    with _JOBS_LOCK:
        return any(j.get("status") == "running" for j in JOBS.values())


def start_job(payload):
    job_id = uuid.uuid4().hex[:10]

    # Freeze storage base + run folder tag pada saat job dimulai.
    # Tag timestamp aman untuk Windows (hindari ':' dan karakter ilegal lainnya).
    run_tag = time.strftime("%Y%m%d_%H%M%S")
    storage_base = str(get_storage_base())
    new_job = {
        "status": "running",
        "createdAt": time.time(),
        "startedAt": None,
        "finishedAt": None,
        "done": 0,
        "total": 0,
        "progress": 0,
        "etaSeconds": None,
        # v1.4: tahap proses ("prepare" = normalisasi klip, "render" = output).
        "phase": "prepare",
        "prep": {"done": 0, "total": 0},
        "logs": [],
        "perMode": {},
        "meta": {},
        # v1.1: sinyal STOP. Worker memeriksa flag ini di antara video (dan saat
        # membunuh proses ffmpeg yang sedang berjalan) agar bisa berhenti cepat.
        "cancelRequested": False,
    }
    with _JOBS_LOCK:
        JOBS[job_id] = new_job
        _prune_finished_jobs_locked()

    def runner():
        try:
            sequences_by_mode, meta = build_job_plan(payload)

            # Inject meta tambahan untuk worker.
            meta = dict(meta or {})
            meta["runTag"] = run_tag
            meta["storageBase"] = storage_base
            # v1.1.2: pilihan encoder dari UI ("auto" | "nvenc" | "vaapi" | "cpu").
            meta["encoderMode"] = str(payload.get("encoderMode") or "auto").strip().lower()
            # v1.4: metode render ("fast" | "classic") + jumlah worker paralel
            # ("auto" | "1".."4"). Default aman & kompatibel mundur.
            meta["renderMethod"] = str(payload.get("renderMethod") or "fast").strip().lower()
            meta["parallelWorkers"] = str(payload.get("parallelWorkers") or "auto").strip().lower()
            # v1.6: profil output (resolusi/fps/kualitas/bitrate). Worker
            # memvalidasi & memberi default (720p @24fps) bila kosong/tak lengkap.
            op = payload.get("outputProfile")
            meta["outputProfile"] = op if isinstance(op, dict) else {}
            # v1.9: mode audio ("mute" | "keep" | "replace" | "mix") + daftar
            # path audio eksternal (dipakai untuk replace/mix, rolling round-robin).
            meta["audioMode"] = str(payload.get("audioMode") or ("keep" if not payload.get("muteAudio", True) else "mute")).strip().lower()
            audio_files = payload.get("audioFiles") or []
            meta["audioFiles"] = [str(p) for p in audio_files if p]
            meta["clientTimeZone"] = str(payload.get("clientTimeZone") or "")[:80]
            try:
                meta["clientUtcOffsetMinutes"] = int(payload.get("clientUtcOffsetMinutes") or 0)
            except (TypeError, ValueError):
                meta["clientUtcOffsetMinutes"] = 0
            meta["clientLocalStartedAt"] = str(payload.get("clientLocalStartedAt") or "")[:64]
            client_run_tag = str(payload.get("clientRunTag") or "")
            if re.fullmatch(r"\d{8}_\d{6}", client_run_tag):
                meta["runTag"] = client_run_tag
            JOBS[job_id]["meta"] = meta

            # Karena sequences bisa berupa generator (streaming), total harus diambil dari estimasi.
            # Jika ada batch limit, gunakan effectiveMax agar progress akurat.
            eff = meta.get("effectiveMax") or {}
            est = (meta.get("estimates") or {}).get("max") or {}
            JOBS[job_id]["perMode"] = {
                m: {"done": 0, "total": int(eff.get(m, est.get(m) or 0) or 0)}
                for m in sequences_by_mode.keys()
            }
            JOBS[job_id]["total"] = sum(v["total"] for v in JOBS[job_id]["perMode"].values())
            JOBS[job_id]["startedAt"] = time.time()
            process_job(job_id, sequences_by_mode, JOBS)
            _report_completed_job(job_id)
        except Exception as e:
            JOBS[job_id]["status"] = "error"
            JOBS[job_id]["logs"].append(str(e))
            JOBS[job_id]["finishedAt"] = time.time()

    threading.Thread(target=runner, daemon=True).start()
    return job_id


def request_stop(job_id):
    """Minta job berhenti (STOP).

    Menandai cancelRequested = True. Worker akan:
      - membunuh proses ffmpeg yang sedang berjalan,
      - menghapus file setengah jadi,
      - berhenti tanpa menyentuh video yang SUDAH selesai.
    """
    job = JOBS.get(job_id)
    if not job:
        return {"ok": False, "error": "unknown_job"}
    if job.get("status") != "running":
        return {"ok": True, "status": job.get("status"), "alreadyStopped": True}
    job["cancelRequested"] = True
    return {"ok": True, "status": "stopping"}


def stop_all_running_jobs():
    """Hentikan semua render aktif ketika akses Remote Server dicabut."""
    stopped = []
    with _JOBS_LOCK:
        ids = [jid for jid, job in JOBS.items() if job.get("status") == "running"]
    for job_id in ids:
        result = request_stop(job_id)
        if result.get("ok"):
            stopped.append(job_id)
    return stopped


def get_status(job_id):
    return JOBS.get(job_id, {"status": "unknown"})
