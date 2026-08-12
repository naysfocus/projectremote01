"""FFmpeg worker — v1.7

Perubahan v1.7 (perbaikan bug FREEZE acak pada metode "fast"):

  GEJALA: sebagian output metode "fast" (concat-copy) freeze di posisi & durasi
  acak (awal/tengah/akhir, sebentar atau beberapa klip).

  AKAR MASALAH: durasi tiap segmen di concat list ditulis eksplisit dari jumlah
  frame. Sampai v1.6 jumlah frame dibaca dari METADATA `nb_frames` (header MP4).
  Untuk libx264 metadata itu tepat, tetapi encoder HARDWARE (VAAPI/NVENC) dan
  sebagian muxer menuliskannya SALAH atau KOSONG. Bila directive `duration`
  tidak sama persis dengan panjang segmen sebenarnya, concat demuxer menyisakan
  celah di sambungan → frame terakhir segmen ditahan (FREEZE). Karena tiap klip
  bisa meleset beda-beda, freeze tampak acak.

  PERBAIKAN:
    - Durasi segmen dihitung dari jumlah frame EKSAK hasil DEKODE
      (`ffprobe -count_frames` → nb_read_frames), bukan metadata. Selalu tepat
      untuk encoder apa pun; dijalankan sekali per klip unik (murah).
      Lihat `_probe_frames_accurate`.
    - File perantara dipaksa CFR sempurna mulai dari 0 (`setpts=N/fps/TB`) dan
      tanpa edit-list/delay awal (`-avoid_negative_ts make_zero`, muxdelay 0),
      supaya offset presentasi dari encoder hardware tidak menyisakan celah.
  Diverifikasi bebas-celah untuk kasus mute, ber-audio, dan berbagai fps.

Perubahan besar v1.4 (kecepatan & stabilitas, hasil visual identik):

1. RENDER DUA TAHAP ("fast", default):
   - Tahap 1: setiap klip UNIK dinormalisasi SEKALI (scale/pad/fps/SAR/format
     + encode H.264) menjadi file perantara di temp/<job>/norm/.
   - Tahap 2: setiap output digabung dari file perantara memakai concat
     DEMUXER dengan "-c:v copy" (remux, tanpa re-encode video).
   Karena semua segmen dihasilkan encoder yang sama dengan parameter identik
   (resolusi, fps CFR, SAR, GOP, timescale) dan tiap file diawali keyframe
   IDR, sambungan tetap mulus tanpa freeze — masalah freeze lama terjadi
   karena stream-copy pada sumber yang TIDAK seragam, bukan karena remux itu
   sendiri. Untuk batch ribuan output dari klip yang sama, kerja encode turun
   drastis (tiap klip di-encode 1x, bukan ribuan kali).
   Audio (bila tidak mute): video tetap copy, audio di-encode ulang AAC saat
   remux (murah) supaya timestamp antar segmen selalu rapi.
   Metode "classic" (re-encode penuh per output, perilaku v1.3) tetap
   tersedia dari UI, dan otomatis dipakai sebagai FALLBACK per-output bila
   remux gagal.

2. WORKER PARALEL: beberapa proses ffmpeg berjalan bersamaan (default Auto —
   menyesuaikan jumlah thread CPU). Saat paralel, tiap proses dibatasi
   `-threads` supaya total tidak oversubscribe. Penomoran file tetap
   deterministik (indeks ditetapkan saat antre, bukan saat selesai).

3. CACHE ffprobe: durasi & deteksi audio di-cache per (path, size, mtime).
   Sebelumnya _probe_has_audio dipanggil untuk tiap klip pada TIAP output —
   ribuan spawn ffprobe yang mubazir.

4. PRIORITAS PROSES: ffmpeg dijalankan dengan `nice -n 10` (POSIX) agar
   desktop tetap responsif selama render panjang.

5. Perbaikan kecil: flag `-vsync` (deprecated, dobel dengan -fps_mode)
   dihapus; `-nostdin` ditambahkan (aman untuk proses background); temp
   intermediates selalu dibersihkan (rmtree) di akhir job.

Kompatibel mundur: payload lama tanpa renderMethod/parallelWorkers otomatis
memakai default; detect_best_encoder, probe_duration, EST_* tetap diekspor.
"""

import os
import shutil
import signal
import subprocess
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from services.storage_config import ensure_storage_dirs


def _mode_dir_name(mode: str) -> str:
    return {
        "horizontal": "horizontal",
        "mixHorizontal": "campuran_horizontal",
        "mixHorizontalLinear": "campuran_horizontal_linear",
        "mixHorizontalLinearUnique": "campuran_horizontal_linear_unik",
    }.get(mode, mode)


# ---------------------------------------------------------------------------
# Target normalisasi output — KONFIGURABEL sejak v1.6.
#
# Klip sumber bisa punya resolusi / fps / pixel format / SAR / audio yang
# berbeda-beda. Semua klip dinormalisasi ke parameter yang SAMA (satu profil)
# sehingga sambungan concat benar-benar kontinu (tanpa freeze).
#
# Sampai v1.5 profil ini di-hardcode 1080x1920 @30fps CRF20 — boros untuk
# sumber 720p bitrate rendah. Mulai v1.6 profil dipilih dari UI; DEFAULT
# disetel setara sumber umum (720x1280 @24fps, kualitas seimbang) supaya
# tidak ada upscale/bitrate berlebih. Nilai lama tetap bisa dipilih.
# ---------------------------------------------------------------------------

# Default profil (setara sumber 720p yang umum dipakai).
DEFAULT_W = 720
DEFAULT_H = 1280
DEFAULT_FPS = 24
DEFAULT_RATE_MODE = "crf"      # "crf" (kualitas tetap) | "bitrate" (target)
DEFAULT_QUALITY = 23           # CRF/CQ/QP — 23 ~ setara sumber, hemat
DEFAULT_VIDEO_BITRATE_K = 2000  # kbps, dipakai saat rate_mode="bitrate"
DEFAULT_AUDIO_BITRATE_K = 128   # kbps (dulu 192) — cukup & setara sumber
DEFAULT_AUDIO_RATE = 48000      # Hz — 48k mengikuti sumber (hindari resample)
DEFAULT_AUDIO_CHANNELS = 2      # stereo

TARGET_SAR = "1"                # square pixels (tetap)
TICKS_PER_FRAME = 512           # timescale = 512 * fps → tiap frame = 512 tick

# Batas aman.
MIN_DIM, MAX_DIM = 16, 4320
MIN_FPS, MAX_FPS = 1, 120
MIN_QUALITY, MAX_QUALITY = 0, 51
MIN_VBR_K, MAX_VBR_K = 100, 200_000
MIN_ABR_K, MAX_ABR_K = 16, 1024

VALID_RATE_MODES = {"crf", "bitrate"}


class OutputProfile:
    """Parameter normalisasi output untuk satu job (v1.6).

    Semua pembangun perintah ffmpeg memakai profil ini alih-alih konstanta
    global, sehingga resolusi/fps/kualitas/bitrate bisa dipilih per job.
    """

    __slots__ = (
        "width", "height", "fps", "rate_mode", "quality",
        "video_bitrate_k", "audio_bitrate_k", "audio_rate", "audio_channels",
    )

    def __init__(
        self,
        width: int = DEFAULT_W,
        height: int = DEFAULT_H,
        fps: int = DEFAULT_FPS,
        rate_mode: str = DEFAULT_RATE_MODE,
        quality: int = DEFAULT_QUALITY,
        video_bitrate_k: int = DEFAULT_VIDEO_BITRATE_K,
        audio_bitrate_k: int = DEFAULT_AUDIO_BITRATE_K,
        audio_rate: int = DEFAULT_AUDIO_RATE,
        audio_channels: int = DEFAULT_AUDIO_CHANNELS,
    ) -> None:
        # Dimensi genap (H.264 yuv420p wajib genap).
        self.width = _clamp_even(width, MIN_DIM, MAX_DIM, DEFAULT_W)
        self.height = _clamp_even(height, MIN_DIM, MAX_DIM, DEFAULT_H)
        self.fps = _clamp_int(fps, MIN_FPS, MAX_FPS, DEFAULT_FPS)
        rm = str(rate_mode or DEFAULT_RATE_MODE).strip().lower()
        self.rate_mode = rm if rm in VALID_RATE_MODES else DEFAULT_RATE_MODE
        self.quality = _clamp_int(quality, MIN_QUALITY, MAX_QUALITY, DEFAULT_QUALITY)
        self.video_bitrate_k = _clamp_int(video_bitrate_k, MIN_VBR_K, MAX_VBR_K, DEFAULT_VIDEO_BITRATE_K)
        self.audio_bitrate_k = _clamp_int(audio_bitrate_k, MIN_ABR_K, MAX_ABR_K, DEFAULT_AUDIO_BITRATE_K)
        self.audio_rate = _clamp_int(audio_rate, 8000, 192000, DEFAULT_AUDIO_RATE)
        self.audio_channels = _clamp_int(audio_channels, 1, 2, DEFAULT_AUDIO_CHANNELS)

    @property
    def timescale(self) -> int:
        """Timescale mp4 seragam: 512 tick per frame untuk fps berapa pun."""
        return TICKS_PER_FRAME * self.fps

    @property
    def maxrate_k(self) -> int:
        return max(self.video_bitrate_k, int(round(self.video_bitrate_k * 1.45)))

    @property
    def bufsize_k(self) -> int:
        return self.video_bitrate_k * 2

    def summary(self) -> str:
        rc = (
            f"CRF {self.quality}" if self.rate_mode == "crf"
            else f"bitrate {self.video_bitrate_k} kbps"
        )
        return f"{self.width}x{self.height} @{self.fps}fps · {rc}"

    def as_dict(self) -> Dict[str, object]:
        return {
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "rateMode": self.rate_mode,
            "quality": self.quality,
            "videoBitrateK": self.video_bitrate_k,
            "audioBitrateK": self.audio_bitrate_k,
            "audioRate": self.audio_rate,
            "audioChannels": self.audio_channels,
            "timescale": self.timescale,
        }


def _clamp_int(val, lo: int, hi: int, default: int) -> int:
    try:
        n = int(round(float(val)))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _clamp_even(val, lo: int, hi: int, default: int) -> int:
    n = _clamp_int(val, lo, hi, default)
    if n % 2 != 0:
        n -= 1  # bulatkan ke bawah ke genap terdekat
    return max(lo, n)


def parse_output_profile(meta: Optional[Dict]) -> OutputProfile:
    """Bangun OutputProfile dari meta job (payload UI).

    Menerima dict di meta["outputProfile"]; semua field opsional dan
    tervalidasi/di-clamp. Payload lama tanpa outputProfile → profil default
    (720p @24fps, kualitas seimbang), sehingga tetap kompatibel mundur.
    """
    op = (meta or {}).get("outputProfile") or {}
    if not isinstance(op, dict):
        op = {}
    return OutputProfile(
        width=op.get("width", DEFAULT_W),
        height=op.get("height", DEFAULT_H),
        fps=op.get("fps", DEFAULT_FPS),
        rate_mode=op.get("rateMode", DEFAULT_RATE_MODE),
        quality=op.get("quality", DEFAULT_QUALITY),
        video_bitrate_k=op.get("videoBitrateK", DEFAULT_VIDEO_BITRATE_K),
        audio_bitrate_k=op.get("audioBitrateK", DEFAULT_AUDIO_BITRATE_K),
        audio_rate=op.get("audioRate", DEFAULT_AUDIO_RATE),
        audio_channels=op.get("audioChannels", DEFAULT_AUDIO_CHANNELS),
    )


def estimate_video_bitrate_bps(profile: OutputProfile) -> int:
    """Perkiraan bitrate video (bps) untuk estimasi ukuran output.

    - rate_mode "bitrate": pakai target bitrate langsung (akurat).
    - rate_mode "crf": heuristik bits-per-pixel-per-frame. Pada CRF 23,
      720x1280@24 ≈ 2 Mbps (setara sumber). Tiap -6 CRF ≈ 2× bitrate.
      Angka ini cenderung sedikit lebih besar dari kenyataan (aman).
    """
    if profile.rate_mode == "bitrate":
        return int(profile.video_bitrate_k * 1000)
    base_crf = 23
    base_bpp = 0.09  # bit / pixel / frame @ CRF 23
    bpp = base_bpp * (2.0 ** ((base_crf - profile.quality) / 6.0))
    return int(profile.width * profile.height * profile.fps * bpp)


def estimate_audio_bitrate_bps(profile: OutputProfile, mute_audio: bool) -> int:
    return 0 if mute_audio else int(profile.audio_bitrate_k * 1000)


# ---------------------------------------------------------------------------
# Estimasi ukuran output — konstanta fallback (kompatibilitas import lama).
# Nilai sebenarnya kini diturunkan dari OutputProfile lewat helper di atas.
# ---------------------------------------------------------------------------
EST_VIDEO_BITRATE_BPS = DEFAULT_VIDEO_BITRATE_K * 1000   # ~2 Mbps (default 720p)
EST_AUDIO_BITRATE_BPS = DEFAULT_AUDIO_BITRATE_K * 1000   # 128 kbps (bila tidak mute)

# ---------------------------------------------------------------------------
# Hardware video encoding (v1.1.2) — mekanisme deteksi tidak berubah.
# ---------------------------------------------------------------------------
VALID_ENCODER_MODES = {"auto", "nvenc", "vaapi", "cpu"}
VALID_RENDER_METHODS = {"fast", "classic"}
DEFAULT_VAAPI_DEVICE = "/dev/dri/renderD128"

_ENCODER_DETECT_CACHE: Optional[Dict[str, Optional[str]]] = None
_ENCODER_DETECT_LOCK = threading.Lock()

_FFMPEG_VERSION_CACHE: Optional[str] = None

# Cache hasil ffprobe per file: key = (path, size, mtime).
_PROBE_LOCK = threading.Lock()
_DURATION_CACHE: Dict[Tuple[str, int, int], float] = {}
_HAS_AUDIO_CACHE: Dict[Tuple[str, int, int], bool] = {}


# ============================================================================
# Util umum
# ============================================================================

def _nice_prefix() -> List[str]:
    """Prefix `nice -n 10` (POSIX) supaya render tidak membuat desktop lag."""
    if os.name == "posix" and shutil.which("nice"):
        return ["nice", "-n", "10"]
    return []


def _probe_cache_key(path: str) -> Tuple[str, int, int]:
    try:
        st = os.stat(path)
        return (str(path), int(st.st_size), int(st.st_mtime))
    except Exception:
        return (str(path), -1, -1)


def ffmpeg_version_string() -> str:
    """Baris versi ffmpeg (di-cache), untuk info sistem di UI."""
    global _FFMPEG_VERSION_CACHE
    if _FFMPEG_VERSION_CACHE is not None:
        return _FFMPEG_VERSION_CACHE
    try:
        out = subprocess.run(
            ["ffmpeg", "-hide_banner", "-version"],
            capture_output=True, text=True, timeout=10,
        )
        first = (out.stdout or "").splitlines()
        _FFMPEG_VERSION_CACHE = first[0].strip() if first else "ffmpeg (versi tidak diketahui)"
    except Exception:
        _FFMPEG_VERSION_CACHE = "ffmpeg tidak ditemukan"
    return _FFMPEG_VERSION_CACHE


def resolve_parallel_workers(pref: Optional[str]) -> int:
    """Terjemahkan pilihan UI ('auto' | '1'..'4') menjadi jumlah worker.

    Auto: kira-kira 1 worker per 6 thread CPU, dibatasi 1..4. Contoh:
    6 thread -> 1, 12 thread (Ryzen 5 5600G) -> 2, 24 thread -> 4.
    Konservatif secara RAM: tiap worker adalah satu proses ffmpeg.
    """
    raw = str(pref or "auto").strip().lower()
    if raw != "auto":
        try:
            n = int(raw)
            return max(1, min(4, n))
        except Exception:
            pass
    threads = os.cpu_count() or 1
    return max(1, min(4, threads // 6))


def _thread_cap_args(workers: int) -> List[str]:
    """Batas thread per proses ffmpeg saat paralel (hindari oversubscribe).

    1 worker: biarkan ffmpeg memakai semua thread (perilaku lama).
    >1 worker: bagi rata thread CPU, minimal 2 per proses.
    """
    if workers <= 1:
        return []
    threads = os.cpu_count() or 1
    per = max(2, threads // workers)
    return [
        "-threads", str(per),
        "-filter_threads", str(per),
        "-filter_complex_threads", str(per),
    ]


# ============================================================================
# Deteksi encoder (mekanisme v1.1.2, dipertahankan)
# ============================================================================

def _ffmpeg_encoders_output() -> str:
    try:
        out = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=15,
        )
        return out.stdout or ""
    except Exception:
        return ""


def _find_vaapi_devices() -> List[str]:
    devices: List[str] = []
    try:
        dri = Path("/dev/dri")
        if dri.exists():
            for p in sorted(dri.glob("renderD*")):
                try:
                    if os.access(p, os.R_OK | os.W_OK):
                        devices.append(str(p))
                except Exception:
                    pass
    except Exception:
        pass
    return devices


def _nvidia_gpu_name() -> str:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        lines = [ln.strip() for ln in (out.stdout or "").splitlines() if ln.strip()]
        if out.returncode == 0 and lines:
            return lines[0]
    except Exception:
        pass
    return "NVIDIA GPU"


def _vaapi_gpu_vendor(device: str) -> str:
    try:
        node = os.path.basename(device)
        with open(f"/sys/class/drm/{node}/device/vendor", encoding="ascii") as f:
            vid = f.read().strip().lower()
        return {
            "0x1002": "AMD/ATI",
            "0x8086": "Intel",
            "0x10de": "NVIDIA",
        }.get(vid, f"vendor {vid}")
    except Exception:
        return "GPU"


def _test_encode(args_before_input: List[str], vf: Optional[str], encoder_args: List[str]) -> Tuple[bool, str]:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-nostdin"]
    cmd += args_before_input
    cmd += ["-f", "lavfi", "-i", "color=c=black:s=320x240:r=30:d=0.2"]
    if vf:
        cmd += ["-vf", vf]
    cmd += ["-frames:v", "3"]
    cmd += encoder_args
    cmd += ["-f", "null", "-"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        return out.returncode == 0, (out.stderr or "").strip()
    except Exception as e:
        return False, str(e)


def detect_best_encoder(force_refresh: bool = False) -> Dict[str, Optional[str]]:
    """Deteksi encoder H.264 terbaik (nvenc -> vaapi -> cpu), hasil di-cache."""
    global _ENCODER_DETECT_CACHE
    with _ENCODER_DETECT_LOCK:
        if _ENCODER_DETECT_CACHE is not None and not force_refresh:
            return _ENCODER_DETECT_CACHE

        reasons: List[str] = []
        encoders = _ffmpeg_encoders_output()

        # --- 1) NVENC (NVIDIA) --------------------------------------------
        if "h264_nvenc" in encoders:
            ok, _err = _test_encode(
                [],
                None,
                ["-c:v", "h264_nvenc", "-preset", "p4", "-tune", "hq",
                 "-rc", "vbr", "-cq", "20", "-b:v", "0", "-pix_fmt", "yuv420p"],
            )
            if ok:
                _ENCODER_DETECT_CACHE = {
                    "mode": "nvenc",
                    "device": None,
                    "label": _nvidia_gpu_name(),
                    "reason": "",
                }
                return _ENCODER_DETECT_CACHE
            reasons.append(
                "h264_nvenc ada di build ffmpeg tetapi test encode gagal "
                "(driver NVIDIA / GPU tidak tersedia)"
            )
        else:
            reasons.append("h264_nvenc tidak ada di build ffmpeg")

        # --- 2) VAAPI (AMD / Intel) ----------------------------------------
        if "h264_vaapi" in encoders:
            devices = _find_vaapi_devices()
            if devices:
                picked: Optional[str] = None
                for dev in devices:
                    ok, _err = _test_encode(
                        ["-vaapi_device", dev],
                        "format=nv12,hwupload",
                        ["-c:v", "h264_vaapi", "-qp", "20"],
                    )
                    if ok:
                        picked = dev
                        break
                if picked:
                    _ENCODER_DETECT_CACHE = {
                        "mode": "vaapi",
                        "device": picked,
                        "label": f"{_vaapi_gpu_vendor(picked)} — {picked}",
                        "reason": "",
                    }
                    return _ENCODER_DETECT_CACHE
                reasons.append(
                    "h264_vaapi ada tetapi test encode gagal di semua render node "
                    "(driver VAAPI belum terpasang / GPU tidak kompatibel)"
                )
            else:
                reasons.append(
                    "h264_vaapi ada tetapi /dev/dri/renderD* tidak ditemukan atau "
                    "tidak bisa diakses (cek device mapping & permission)"
                )
        else:
            reasons.append("h264_vaapi tidak ada di build ffmpeg")

        # --- 3) Fallback: CPU (libx264) -------------------------------------
        _ENCODER_DETECT_CACHE = {
            "mode": "cpu",
            "device": None,
            "label": "libx264",
            "reason": "; ".join(reasons),
        }
        return _ENCODER_DETECT_CACHE


# ============================================================================
# ffprobe (dengan cache)
# ============================================================================

def _probe_has_audio(path: str) -> bool:
    """Cek stream audio. Hasil DI-CACHE per (path, size, mtime)."""
    key = _probe_cache_key(path)
    with _PROBE_LOCK:
        if key in _HAS_AUDIO_CACHE:
            return _HAS_AUDIO_CACHE[key]
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=index",
                "-of", "csv=p=0",
                str(path),
            ],
            capture_output=True, text=True,
        )
        result = bool(out.stdout.strip())
    except Exception:
        result = False
    with _PROBE_LOCK:
        _HAS_AUDIO_CACHE[key] = result
    return result


def _probe_video_frames(path: str) -> int:
    """Jumlah frame stream video (dari metadata mp4; instan). 0 bila gagal."""
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=nb_frames",
                "-of", "csv=p=0",
                str(path),
            ],
            capture_output=True, text=True,
        )
        val = (out.stdout or "").strip()
        return int(val) if val.isdigit() else 0
    except Exception:
        return 0


def _probe_frames_accurate(path: str) -> int:
    """Jumlah frame video EKSAK dengan mendekode (nb_read_frames).

    v1.7 FIX (freeze acak metode "fast"): durasi tiap segmen di concat list
    dihitung dari jumlah frame. Sampai v1.6 dipakai `nb_frames` (metadata
    header MP4). Untuk libx264 metadata itu benar, tetapi encoder HARDWARE
    (VAAPI/NVENC) dan sebagian muxer menuliskannya SALAH atau kosong. Bila
    `nb_frames` meleset, directive `duration` tidak sama dengan panjang segmen
    sebenarnya → concat demuxer menyisakan celah di sambungan → frame terakhir
    segmen ditahan (FREEZE) selama selisihnya. Karena tiap klip bisa meleset
    beda-beda, freeze tampak acak posisi & durasinya.

    `-count_frames` benar-benar mendekode dan MENGHITUNG frame, jadi selalu
    tepat untuk encoder apa pun. Dijalankan sekali per klip unik (bukan per
    output), jadi biayanya kecil. Fallback ke metadata lalu 0 bila gagal.
    """
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-count_frames",
                "-show_entries", "stream=nb_read_frames",
                "-of", "csv=p=0",
                str(path),
            ],
            capture_output=True, text=True,
        )
        val = (out.stdout or "").strip()
        if val.isdigit() and int(val) > 0:
            return int(val)
    except Exception:
        pass
    return _probe_video_frames(path)  # fallback: metadata


def probe_duration(path: str) -> float:
    """Durasi video (detik) via ffprobe. Hasil DI-CACHE. Return 0.0 bila gagal."""
    key = _probe_cache_key(path)
    with _PROBE_LOCK:
        if key in _DURATION_CACHE:
            return _DURATION_CACHE[key]
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                str(path),
            ],
            capture_output=True, text=True,
        )
        val = (out.stdout or "").strip()
        result = float(val) if val else 0.0
    except Exception:
        result = 0.0
    with _PROBE_LOCK:
        _DURATION_CACHE[key] = result
    return result


# ============================================================================
# Pembangun perintah ffmpeg
# ============================================================================

def _resolve_encoder_for_cmd(encoder_mode: str, vaapi_device: Optional[str]) -> Tuple[str, Optional[str]]:
    mode = (encoder_mode or "auto").strip().lower()
    if mode not in VALID_ENCODER_MODES:
        mode = "auto"
    if mode == "auto":
        det = detect_best_encoder()  # cached
        mode = det["mode"]
        if vaapi_device is None:
            vaapi_device = det.get("device")
    if mode == "vaapi" and not vaapi_device:
        devs = _find_vaapi_devices()
        vaapi_device = devs[0] if devs else DEFAULT_VAAPI_DEVICE
    return mode, vaapi_device


def _video_encoder_args(mode: str, profile: OutputProfile, for_intermediate: bool = False) -> List[str]:
    """Argumen encoder H.264 per mode, mengikuti OutputProfile (v1.6).

    Rate control:
      - profile.rate_mode == "crf": kualitas tetap (CRF/CQ/QP = profile.quality).
      - profile.rate_mode == "bitrate": VBR terbatas dengan target bitrate
        (b:v + maxrate + bufsize) — memenuhi permintaan kontrol bitrate.

    GOP mengikuti fps (1 keyframe/detik), sc_threshold 0 agar keyframe
    deterministik. Untuk file perantara metode "fast" ditambah `-bf 0`
    (tanpa B-frame). Dengan CFR + timescale 512×fps, tiap frame tepat 512
    tick dan durasi segmen = jumlah_frame × 512 — sambungan concat copy jadi
    presisi matematis (tanpa DTS tumpang tindih akibat delay B-frame).
    """
    extra = ["-bf", "0"] if for_intermediate else []
    g = str(profile.fps)
    bitrate_mode = profile.rate_mode == "bitrate"
    vbk = f"{profile.video_bitrate_k}k"
    maxk = f"{profile.maxrate_k}k"
    bufk = f"{profile.bufsize_k}k"

    if mode == "nvenc":
        rc = (
            ["-rc", "vbr", "-b:v", vbk, "-maxrate", maxk, "-bufsize", bufk]
            if bitrate_mode else
            ["-rc", "vbr", "-cq", str(profile.quality), "-b:v", "0"]
        )
        return extra + [
            "-fps_mode", "cfr",
            "-c:v", "h264_nvenc",
            "-preset", "p4",
            "-tune", "hq",
            *rc,
            "-pix_fmt", "yuv420p",
            "-g", g,
            "-keyint_min", g,
            "-sc_threshold", "0",
        ]
    if mode == "vaapi":
        rc = (
            ["-rc_mode", "VBR", "-b:v", vbk, "-maxrate", maxk]
            if bitrate_mode else
            ["-rc_mode", "CQP", "-qp", str(profile.quality)]
        )
        return extra + [
            "-fps_mode", "cfr",
            "-c:v", "h264_vaapi",
            *rc,
            "-g", g,
            "-keyint_min", g,
        ]
    # CPU (libx264). Catatan v1.4: '-vsync cfr' lama dihapus karena dobel
    # dengan '-fps_mode cfr' (deprecated di ffmpeg baru); hasil identik.
    rc = (
        ["-b:v", vbk, "-maxrate", maxk, "-bufsize", bufk]
        if bitrate_mode else
        ["-crf", str(profile.quality)]
    )
    return extra + [
        "-fps_mode", "cfr",
        "-c:v", "libx264",
        "-preset", "veryfast",
        *rc,
        "-pix_fmt", "yuv420p",
        "-g", g,
        "-keyint_min", g,
        "-sc_threshold", "0",
    ]


def _norm_video_filter(profile: OutputProfile) -> str:
    return (
        f"scale={profile.width}:{profile.height}:force_original_aspect_ratio=decrease,"
        f"pad={profile.width}:{profile.height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setsar={TARGET_SAR},"
        f"fps={profile.fps},"
        f"format=yuv420p"
    )


def _build_normalize_cmd(
    src: str,
    outfile: Path,
    want_audio: bool,
    src_has_audio: bool,
    encoder_mode: str,
    vaapi_device: Optional[str],
    workers: int,
    profile: OutputProfile,
) -> List[str]:
    """Tahap 1 (fast): normalisasi SATU klip sumber ke file perantara.

    Bila output butuh audio tetapi klip sumber tidak punya audio, track sunyi
    (anullsrc) disuntikkan supaya SEMUA file perantara seragam ber-audio —
    dengan ini remux tahap 2 selalu konsisten. (Di v1.3, satu klip tanpa
    audio membuat SELURUH output kehilangan audio; perilaku baru lebih baik.)
    """
    mode, vaapi_device = _resolve_encoder_for_cmd(encoder_mode, vaapi_device)

    cmd: List[str] = _nice_prefix() + [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostdin",
    ]
    if mode == "vaapi":
        cmd += ["-vaapi_device", str(vaapi_device)]
    cmd += _thread_cap_args(workers)

    cmd += ["-i", str(src)]
    silent_input = want_audio and not src_has_audio
    if silent_input:
        # PENTING: anullsrc adalah sumber TAK BERUJUNG. Tanpa batas durasi,
        # kombinasi lavfi tak berujung + -shortest bisa deadlock (ffmpeg
        # menunggu interleave selamanya). Input dibatasi sedikit LEBIH
        # panjang dari video, lalu -shortest memotong pas di akhir video.
        dur = probe_duration(src)
        bound = (dur + 1.0) if dur > 0 else 3600.0
        cmd += ["-f", "lavfi", "-t", f"{bound:.3f}", "-i", f"anullsrc=r={profile.audio_rate}:cl=stereo"]

    # v1.7 FIX (freeze acak): setelah normalisasi + fps CFR, PTS di-SET ULANG
    # menjadi N/fps eksak (setpts=N/FR/TB). Ini menjamin file perantara benar-
    # benar CFR mulai dari 0 tanpa offset/edit-list — penting untuk encoder
    # hardware (VAAPI/NVENC) yang kadang menyisakan delay/edit-list sehingga
    # presentasi bergeser dan concat-copy menyisakan celah (freeze) di
    # sambungan. Untuk libx264 hasilnya identik (sudah rapi).
    v_filter = f"{_norm_video_filter(profile)},setpts=N/{profile.fps}/TB"
    filt_parts: List[str] = [f"[0:v]{v_filter}[v]"]
    video_label = "[v]"
    if mode == "vaapi":
        filt_parts.append("[v]format=nv12,hwupload[vhw]")
        video_label = "[vhw]"

    if want_audio:
        a_src = "[1:a]" if silent_input else "[0:a]"
        filt_parts.append(
            f"{a_src}"
            f"aformat=sample_rates={profile.audio_rate}:channel_layouts=stereo,"
            f"asetpts=N/SR/TB"
            f"[a]"
        )

    cmd += ["-filter_complex", ";".join(filt_parts), "-map", video_label]
    if want_audio:
        cmd += ["-map", "[a]"]
        if silent_input:
            cmd += ["-shortest"]

    cmd += _video_encoder_args(mode, profile, for_intermediate=True)
    if want_audio:
        cmd += ["-c:a", "aac", "-b:a", f"{profile.audio_bitrate_k}k",
                "-ar", str(profile.audio_rate), "-ac", str(profile.audio_channels)]

    # v1.7 FIX: hindari edit-list / delay awal di file perantara MP4 supaya
    # concat-copy tidak menyisakan celah presentasi di sambungan.
    cmd += [
        "-avoid_negative_ts", "make_zero",
        "-muxpreload", "0",
        "-muxdelay", "0",
        "-video_track_timescale", str(profile.timescale),
        str(outfile),
    ]
    return cmd


def _concat_list_text(entries: List[Tuple[Path, str]]) -> str:
    """Isi file daftar untuk concat demuxer. Kutip tunggal di-escape aman.

    Tiap entri = (path, durasi_video_eksak). Directive `duration` ditulis
    eksplisit: durasi kontainer mp4 = max(video, audio), dan audio AAC selalu
    dibulatkan ke kelipatan 1024 sampel sehingga sedikit lebih panjang dari
    video. Tanpa directive ini concat demuxer meng-offset segmen berikutnya
    memakai durasi audio -> timestamp video tumpang tindih di sambungan.

    v1.7: `durasi_video_eksak` = jumlah_frame_terdekode / fps, dengan jumlah
    frame diambil dari `_probe_frames_accurate` (mendekode, bukan metadata
    `nb_frames`). Ini WAJIB tepat: bila directive `duration` lebih besar dari
    panjang segmen sebenarnya, concat menyisakan celah -> frame terakhir
    ditahan (FREEZE); bila lebih kecil, segmen berikutnya tumpang tindih ->
    frame drop. Karena file perantara CFR (tiap frame 512 tick), durasi eksak =
    kelipatan bulat 512 tick sehingga sambungan mulus.
    """
    lines = []
    for f, dur in entries:
        p = str(f).replace("'", "'\\''")
        lines.append(f"file '{p}'")
        if dur:
            lines.append(f"duration {dur}")
    return "\n".join(lines) + "\n"


def _build_remux_cmd(list_file: Path, outfile: Path, want_audio: bool, profile: OutputProfile) -> List[str]:
    """Tahap 2 (fast): gabung file perantara TANPA re-encode video.

    Video: stream copy (nyaris secepat kecepatan disk).
    Audio: di-encode ulang AAC (sangat murah) supaya timestamp antar segmen
    selalu rapat — menghindari selisih kecil akibat AAC priming samples.
    """
    cmd: List[str] = _nice_prefix() + [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostdin",
        "-fflags", "+genpts",
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c:v", "copy",
    ]
    if want_audio:
        cmd += [
            "-c:a", "aac", "-b:a", f"{profile.audio_bitrate_k}k",
            "-ar", str(profile.audio_rate), "-ac", str(profile.audio_channels),
            # Audio di-encode ulang; async=1 merapikan selisih kecil (AAC
            # padding per segmen) supaya A/V tetap terkunci sinkron.
            "-af", "aresample=async=1:first_pts=0",
        ]
    else:
        cmd += ["-an"]
    cmd += [
        "-video_track_timescale", str(profile.timescale),
        "-movflags", "+faststart",
        str(outfile),
    ]
    return cmd


def _build_concat_cmd(
    seq: List[str],
    outfile: Path,
    mute_audio: bool,
    profile: OutputProfile,
    encoder_mode: str = "auto",
    vaapi_device: Optional[str] = None,
    workers: int = 1,
) -> List[str]:
    """Metode "classic" (perilaku v1.3): normalize + concat filter + re-encode
    penuh dalam SATU perintah per output. Dipertahankan sebagai pilihan UI dan
    sebagai fallback otomatis bila remux fast gagal untuk sebuah output.
    """
    n = len(seq)
    mode, vaapi_device = _resolve_encoder_for_cmd(encoder_mode, vaapi_device)

    cmd: List[str] = _nice_prefix() + [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostdin",
    ]
    if mode == "vaapi":
        cmd += ["-vaapi_device", str(vaapi_device)]
    cmd += _thread_cap_args(workers)

    want_audio = not mute_audio
    if want_audio:
        want_audio = all(_probe_has_audio(p) for p in seq)  # kini murah (cache)

    for p in seq:
        cmd += ["-i", str(p)]

    filt_parts: List[str] = []
    concat_inputs = ""
    for idx in range(n):
        filt_parts.append(f"[{idx}:v]{_norm_video_filter(profile)}[v{idx}]")
        concat_inputs += f"[v{idx}]"
        if want_audio:
            filt_parts.append(
                f"[{idx}:a]"
                f"aformat=sample_rates={profile.audio_rate}:channel_layouts=stereo,"
                f"asetpts=N/SR/TB"
                f"[a{idx}]"
            )
            concat_inputs += f"[a{idx}]"

    if want_audio:
        filt_parts.append(f"{concat_inputs}concat=n={n}:v=1:a=1[outv][outa]")
    else:
        filt_parts.append(f"{concat_inputs}concat=n={n}:v=1:a=0[outv]")

    video_out_label = "[outv]"
    if mode == "vaapi":
        filt_parts.append("[outv]format=nv12,hwupload[outvhw]")
        video_out_label = "[outvhw]"

    cmd += ["-filter_complex", ";".join(filt_parts), "-map", video_out_label]
    if want_audio:
        cmd += ["-map", "[outa]"]

    cmd += _video_encoder_args(mode, profile)
    if want_audio:
        cmd += ["-c:a", "aac", "-b:a", f"{profile.audio_bitrate_k}k",
                "-ar", str(profile.audio_rate), "-ac", str(profile.audio_channels)]

    cmd += [
        "-video_track_timescale", str(profile.timescale),
        "-movflags", "+faststart",
        str(outfile),
    ]
    return cmd


# ============================================================================
# Audio eksternal — Replace/Mix (v1.9)
# ============================================================================
#
# Mode audio kini ada 4: mute, keep (perilaku lama, tidak berubah), replace,
# dan mix. Untuk replace/mix, video hasil gabungan (tahap render biasa,
# selalu memakai audio ASLI klip seperti mode "keep") diproses ULANG dengan
# 1 file audio eksternal yang membentang di sepanjang durasi output.
#
# Durasi: audio lebih panjang dari video -> dipotong ikut video (via
# -shortest pada replace, atau `duration=first` pada mix filter amix).
# Audio lebih pendek -> dibiarkan apa adanya, sisa durasi video jadi hening
# (TIDAK di-loop). Volume dibiarkan natural, tanpa normalisasi/EQ apa pun.

def _build_audio_overlay_cmd(
    video_in: Path,
    audio_in: str,
    outfile: Path,
    audio_mode: str,          # "replace" | "mix"
    video_has_audio: bool,    # True bila video_in punya track audio (mode "keep")
    profile: "OutputProfile",
) -> List[str]:
    """Bangun command ffmpeg untuk menempelkan/mixing audio eksternal ke 1
    video hasil gabungan yang sudah jadi. Video di-copy (tidak di-re-encode)
    supaya cepat & tanpa penurunan kualitas tambahan.
    """
    cmd: List[str] = _nice_prefix() + [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostdin",
        "-i", str(video_in),
        "-i", str(audio_in),
    ]

    audio_codec_args = [
        "-c:a", "aac", "-b:a", f"{profile.audio_bitrate_k}k",
        "-ar", str(profile.audio_rate), "-ac", str(profile.audio_channels),
    ]

    if audio_mode == "mix" and video_has_audio:
        # Mix: audio asli video + audio eksternal digabung apa adanya
        # (tanpa normalisasi volume). Durasi ikut video (input pertama):
        # bila audio eksternal lebih pendek -> sisa hening; lebih panjang
        # -> ujungnya dipotong (duration=first berhenti saat input [0:a] habis).
        filt = (
            f"[1:a]aformat=sample_rates={profile.audio_rate}:channel_layouts=stereo[ext];"
            f"[0:a][ext]amix=inputs=2:duration=first:dropout_transition=0,"
            f"aformat=sample_rates={profile.audio_rate}:channel_layouts=stereo[outa]"
        )
        cmd += [
            "-filter_complex", filt,
            "-map", "0:v", "-map", "[outa]",
            "-c:v", "copy",
        ] + audio_codec_args
    else:
        # Replace (atau Mix tapi video sumbernya tidak punya audio sama
        # sekali, jadi otomatis setara Replace): video dari input 0, audio
        # SEPENUHNYA dari file eksternal. -shortest memotong ujung audio
        # yang lebih panjang dari video; audio yang lebih pendek dibiarkan
        # (sisa durasi video jadi hening, TIDAK di-loop karena tanpa -stream_loop).
        cmd += [
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy",
        ] + audio_codec_args + ["-shortest"]

    cmd += [
        "-video_track_timescale", str(profile.timescale),
        "-movflags", "+faststart",
        str(outfile),
    ]
    return cmd


def _resolve_audio_list(meta: Dict) -> List[str]:
    """Daftar path audio eksternal dari meta job (sudah divalidasi ada file)."""
    items = meta.get("audioFiles") or []
    out: List[str] = []
    for p in items:
        try:
            if p and Path(p).exists():
                out.append(str(p))
        except Exception:
            continue
    return out


# ============================================================================
# Eksekusi proses (dukungan STOP) — mekanisme v1.1, dipertahankan
# ============================================================================

def _is_cancelled(job_id: str, JOBS: dict) -> bool:
    job = JOBS.get(job_id) or {}
    return bool(job.get("cancelRequested"))


def _run_ffmpeg_cancellable(cmd: List[str], job_id: str, JOBS: dict):
    """Jalankan ffmpeg; bisa dihentikan lewat flag cancelRequested.

    Return (returncode, stderr_text, cancelled_bool).

    v1.5 FIX: dulu stdout & stderr memakai PIPE tetapi baru dibaca SETELAH
    `proc.wait()` selesai. Bila ffmpeg memuntahkan output lebih besar dari
    buffer pipe OS (mis. input korup yang menghasilkan ribuan baris error
    decode), ffmpeg terblokir menulis, wait() tidak pernah kembali, dan job
    menggantung selamanya (Stop pun tidak bersih). Kini stderr dikuras oleh
    thread latar sepanjang proses berjalan dan stdout (tidak dipakai ffmpeg)
    dibuang ke DEVNULL — deadlock tidak mungkin terjadi.
    """
    popen_kwargs = dict(stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if os.name == "posix":
        popen_kwargs["start_new_session"] = True  # setsid → grup proses terpisah

    proc = subprocess.Popen(cmd, **popen_kwargs)

    err_chunks: List[bytes] = []

    def _drain_stderr():
        try:
            while True:
                chunk = proc.stderr.read(65536)
                if not chunk:
                    break
                # Batasi total yang disimpan (log hanya butuh cuplikan akhir).
                err_chunks.append(chunk)
                if len(err_chunks) > 64:
                    del err_chunks[0]
        except Exception:
            pass

    drainer = threading.Thread(target=_drain_stderr, daemon=True)
    drainer.start()

    def _collect_err() -> str:
        drainer.join(timeout=3)
        try:
            proc.stderr.close()
        except Exception:
            pass
        return b"".join(err_chunks).decode("utf-8", "ignore")

    while True:
        try:
            proc.wait(timeout=0.2)
            break  # selesai normal
        except subprocess.TimeoutExpired:
            if _is_cancelled(job_id, JOBS):
                _terminate_process(proc)
                err_text = _collect_err()
                return (proc.returncode if proc.returncode is not None else -1, err_text, True)

    err_text = _collect_err()
    return (proc.returncode, err_text, False)


def _terminate_process(proc: subprocess.Popen) -> None:
    try:
        if os.name == "posix":
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    proc.kill()
        else:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


# ============================================================================
# Proses job utama
# ============================================================================

def process_job(job_id: str, sequences_by_mode: Dict[str, Iterable[List[str]]], JOBS: dict) -> None:
    """Render seluruh output untuk satu job.

    Alur "fast" (default):
      Tahap 1 — normalisasi tiap klip unik (paralel, encoder GPU/CPU).
      Tahap 2 — remux tiap output (paralel, video copy) + fallback classic
                per-output bila remux gagal.
    Alur "classic": identik v1.3 (re-encode penuh per output), kini bisa
    paralel & memakai cache probe.

    STOP: flag cancelRequested dicek sebelum tiap unit kerja dan dipantau
    selama proses ffmpeg berjalan; file setengah jadi dihapus; video yang
    sudah selesai tidak disentuh.
    """
    job = JOBS[job_id]
    meta = job.get("meta") or {}
    mute_audio = bool(meta.get("muteAudio", True))

    # v1.9: mode audio ("mute" | "keep" | "replace" | "mix"). Default "mute"
    # untuk kompatibilitas mundur (payload lama tanpa audioMode).
    audio_mode = str(meta.get("audioMode") or ("mute" if mute_audio else "keep")).strip().lower()
    if audio_mode not in ("mute", "keep", "replace", "mix"):
        audio_mode = "mute"
    # Replace/Mix butuh audio ASLI klip ikut di tahap render biasa (dipakai
    # utk Mix, dan agar video_has_audio bisa dideteksi) — perlakukan seperti
    # "keep" di tahap render normal, baru diproses ulang di tahap 3.
    mute_audio = (audio_mode == "mute")
    audio_files = _resolve_audio_list(meta)
    audio_overlay_active = audio_mode in ("replace", "mix") and len(audio_files) > 0
    if audio_mode in ("replace", "mix") and not audio_files:
        job["logs"].append(
            f"⚠ Mode audio '{audio_mode}' dipilih tetapi tidak ada file audio ter-upload — "
            f"dilewati, output memakai audio asli klip (setara mode 'keep')."
        )
    # Rolling round-robin: output ke-N (lintas SEMUA mode kombinasi, sesuai
    # urutan render) memakai audioFiles[N % len(audioFiles)]. Counter global
    # per job, thread-safe (banyak worker render paralel).
    audio_rr_lock = threading.Lock()
    audio_rr_counter = {"n": 0}

    def _next_audio_path() -> Optional[str]:
        # Dipanggil di titik SUBMIT tugas (bukan saat render selesai) agar
        # rolling round-robin deterministik meski render berjalan paralel
        # dan urutan penyelesaian antar thread bisa acak.
        if not audio_overlay_active:
            return None
        with audio_rr_lock:
            idx = audio_rr_counter["n"] % len(audio_files)
            audio_rr_counter["n"] += 1
        return audio_files[idx]

    # v1.6: profil output (resolusi/fps/kualitas/bitrate) dipilih dari UI.
    # Payload lama tanpa outputProfile → default 720p @24fps (setara sumber).
    profile = parse_output_profile(meta)
    meta["outputProfileActive"] = profile.as_dict()

    render_method = str(meta.get("renderMethod", "fast") or "fast").strip().lower()
    if render_method not in VALID_RENDER_METHODS:
        render_method = "fast"

    workers = resolve_parallel_workers(meta.get("parallelWorkers"))
    meta["parallelWorkersActive"] = workers

    # ------------------------------------------------------------------
    # Resolusi encoder (log transparan, mekanisme v1.1.2 dipertahankan).
    # ------------------------------------------------------------------
    encoder_pref = str(meta.get("encoderMode", "auto") or "auto").strip().lower()
    if encoder_pref not in VALID_ENCODER_MODES:
        encoder_pref = "auto"

    detected = detect_best_encoder()
    if encoder_pref == "auto":
        active_encoder = detected["mode"]
        active_vaapi_device = detected.get("device")
        if active_encoder == "nvenc":
            job["logs"].append(f"Encoder terpilih: nvenc ({detected['label']})")
        elif active_encoder == "vaapi":
            job["logs"].append(f"Encoder terpilih: vaapi ({detected['label']})")
        else:
            job["logs"].append("Encoder terpilih: cpu (libx264, GPU tidak terdeteksi)")
            if detected.get("reason"):
                job["logs"].append(f"Detail deteksi GPU: {detected['reason']}")
    else:
        active_encoder = encoder_pref
        active_vaapi_device = detected.get("device") if detected.get("mode") == "vaapi" else None
        label = {"nvenc": "NVENC dipilih manual", "vaapi": "VAAPI dipilih manual",
                 "cpu": "libx264, dipilih manual"}.get(active_encoder, active_encoder)
        job["logs"].append(f"Encoder terpilih: {active_encoder} ({label})")
        if active_encoder in ("nvenc", "vaapi") and detected.get("mode") != active_encoder:
            job["logs"].append(
                f"⚠ Peringatan: {active_encoder} dipaksa manual tetapi tidak lolos deteksi otomatis "
                f"({detected.get('reason') or 'tidak tersedia'}). Bila encode gagal, "
                f"tiap video otomatis di-retry sekali memakai CPU."
            )
    meta["encoderActive"] = active_encoder
    meta["renderMethodActive"] = render_method

    method_label = (
        "cepat (normalisasi 1x + gabung tanpa re-encode)"
        if render_method == "fast" else "klasik (re-encode penuh per video)"
    )
    job["logs"].append(f"Metode render: {method_label} | Worker paralel: {workers}")

    audio_note_map = {
        "mute": "mute",
        "keep": f"audio asli klip, {profile.audio_bitrate_k} kbps @ {profile.audio_rate/1000:.0f} kHz",
        "replace": f"audio diganti track eksternal ({len(audio_files)} file, rolling)" if audio_overlay_active else "audio asli klip (fallback, tidak ada file audio)",
        "mix": f"audio asli klip + track eksternal di-mix ({len(audio_files)} file, rolling)" if audio_overlay_active else "audio asli klip (fallback, tidak ada file audio)",
    }
    audio_note = audio_note_map.get(audio_mode, "mute")
    job["logs"].append(f"Profil output: {profile.summary()} · {audio_note}")

    # ------------------------------------------------------------------
    # Folder management policy (tidak berubah).
    # ------------------------------------------------------------------
    folder_policy = str(meta.get("folderPolicy") or "all").strip().lower()
    wrap_size = 0
    if folder_policy in {"all", "0", "", "semua"}:
        wrap_size = 0
    else:
        digits = "".join(ch for ch in folder_policy if ch.isdigit())
        try:
            wrap_size = int(digits) if digits else 0
        except Exception:
            wrap_size = 0
        if wrap_size < 0:
            wrap_size = 0

    storage_base = Path(meta.get("storageBase") or Path(__file__).parents[1] / "storage")
    dirs = ensure_storage_dirs(storage_base)

    run_tag = (meta.get("runTag") or time.strftime("%Y%m%d_%H%M%S")).strip()
    run_dir = dirs["outputs"] / run_tag
    if run_dir.exists():
        run_dir = dirs["outputs"] / f"{run_tag}_{job_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    tmp_dir = dirs["temp"] / job_id
    norm_dir = tmp_dir / "norm"
    list_dir = tmp_dir / "lists"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Keputusan audio global (fast): output ber-audio bila TIDAK mute.
    # Klip sumber tanpa audio diberi track sunyi saat normalisasi sehingga
    # semua segmen seragam.
    # ------------------------------------------------------------------
    want_audio = not mute_audio

    # ------------------------------------------------------------------
    # TAHAP 1 (fast): normalisasi klip unik.
    # ------------------------------------------------------------------
    norm_map: Dict[str, Optional[Tuple[Path, str]]] = {}
    cancelled = False

    counter_lock = threading.Lock()
    sample_times: List[float] = []

    def _update_eta_locked():
        if len(sample_times) < 3:
            return
        avg = sum(sample_times) / len(sample_times)
        remaining = max(0, job["total"] - job["done"])
        # v1.5 FIX: dengan N worker paralel, N output berjalan bersamaan —
        # tanpa pembagian ini ETA membengkak N kali lipat dari kenyataan.
        job["etaSeconds"] = int(remaining * avg / max(1, workers))

    if render_method == "fast":
        unique_clips: List[str] = list(meta.get("gridPaths") or [])
        if not unique_clips:
            # fallback: kumpulkan dari sequences tidak mungkin (generator) —
            # gridPaths selalu diisi build_job_plan v1.4; guard untuk payload
            # tak lazim: pindah ke classic.
            render_method = "classic"
            meta["renderMethodActive"] = "classic"
            job["logs"].append("⚠ Daftar klip grid tidak tersedia — beralih ke metode klasik.")

    if render_method == "fast" and not cancelled:
        norm_dir.mkdir(parents=True, exist_ok=True)
        list_dir.mkdir(parents=True, exist_ok=True)

        total_prep = len(unique_clips)
        job["phase"] = "prepare"
        job["prep"] = {"done": 0, "total": total_prep}
        job["logs"].append(f"Tahap 1/2 — Normalisasi {total_prep} klip unik (encode 1x per klip)...")

        prep_t0 = time.time()

        def _normalize_one(idx_path: Tuple[int, str]) -> Tuple[str, Optional[Path]]:
            # v1.5 FIX: exception tak terduga di worker thread dulu merambat
            # saat hasil pool.map() dikonsumsi → job langsung error tanpa log
            # yang jelas dan progres tidak konsisten. Kini ditangkap: klip
            # dicatat gagal, dan output yang memakainya jatuh ke metode klasik.
            try:
                return _normalize_one_impl(idx_path)
            except Exception as e:
                src = idx_path[1]
                job["logs"].append(f"✖ Error internal saat normalisasi {Path(src).name}: {e!r}")
                with counter_lock:
                    job["prep"]["done"] += 1
                return src, None

        def _normalize_one_impl(idx_path: Tuple[int, str]) -> Tuple[str, Optional[Path]]:
            idx, src = idx_path
            if _is_cancelled(job_id, JOBS):
                return src, None
            dst = norm_dir / f"norm_{idx:03}.mp4"
            has_audio = _probe_has_audio(src) if want_audio else False
            attempts = [active_encoder]
            if active_encoder in ("nvenc", "vaapi"):
                attempts.append("cpu")
            for attempt_no, enc in enumerate(attempts):
                cmd = _build_normalize_cmd(
                    src, dst, want_audio, has_audio,
                    encoder_mode=enc, vaapi_device=active_vaapi_device,
                    workers=workers, profile=profile,
                )
                rc, err_text, was_cancelled = _run_ffmpeg_cancellable(cmd, job_id, JOBS)
                if was_cancelled:
                    try:
                        dst.unlink(missing_ok=True)
                    except Exception:
                        pass
                    return src, None
                if rc == 0:
                    if attempt_no > 0:
                        job["logs"].append(
                            f"✔ Normalisasi {Path(src).name} berhasil setelah fallback ke CPU."
                        )
                    # v1.7 FIX: hitung durasi segmen dari jumlah frame EKSAK
                    # (dekode), bukan metadata nb_frames yang bisa salah pada
                    # encoder hardware → mencegah celah/freeze di sambungan.
                    nframes = _probe_frames_accurate(dst)
                    dur_str = f"{nframes / profile.fps:.6f}" if nframes > 0 else ""
                    with counter_lock:
                        job["prep"]["done"] += 1
                    return src, (dst, dur_str)
                if attempt_no + 1 < len(attempts):
                    err_lines = (err_text or "").strip().splitlines()
                    err_snip = err_lines[-1][:300] if err_lines else "unknown error"
                    job["logs"].append(
                        f"⚠ Encoder {enc} gagal menormalisasi {Path(src).name} "
                        f"(exit {rc}): {err_snip} — retry pakai CPU (libx264)."
                    )
                    try:
                        dst.unlink(missing_ok=True)
                    except Exception:
                        pass
            err_lines = (err_text or "").strip().splitlines()
            err_snip = err_lines[-1][:300] if err_lines else "unknown error"
            job["logs"].append(
                f"✖ Klip {Path(src).name} gagal dinormalisasi: {err_snip} — "
                f"output yang memakai klip ini akan dirender dengan metode klasik."
            )
            try:
                dst.unlink(missing_ok=True)
            except Exception:
                pass
            with counter_lock:
                job["prep"]["done"] += 1
            return src, None

        if workers > 1 and total_prep > 1:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for src, dst in pool.map(_normalize_one, list(enumerate(unique_clips))):
                    norm_map[src] = dst
        else:
            for item in enumerate(unique_clips):
                src, dst = _normalize_one(item)
                norm_map[src] = dst

        if _is_cancelled(job_id, JOBS):
            cancelled = True
        else:
            ok_n = sum(1 for v in norm_map.values() if v is not None)
            job["logs"].append(
                f"Tahap 1 selesai dalam {time.time() - prep_t0:.1f}s "
                f"({ok_n}/{total_prep} klip siap). Tahap 2/2 — merender output..."
            )

    job["phase"] = "render"

    # ------------------------------------------------------------------
    # TAHAP 2: render tiap output (paralel, penomoran deterministik).
    # ------------------------------------------------------------------
    def _render_one(mode: str, i: int, seq: List[str], audio_path: Optional[str]) -> None:
        # v1.5 FIX: exception tak terduga dulu tertelan diam-diam oleh future
        # dari pool.submit() → counter tidak naik, output "hilang" tanpa jejak,
        # dan bar progres tidak pernah mencapai 100%. Kini dicatat di log dan
        # progres tetap konsisten.
        try:
            _render_one_impl(mode, i, seq, audio_path)
        except Exception as e:
            job["logs"].append(f"✖ Error internal pada {mode}/video_{i:04}.mp4: {e!r}")
            with counter_lock:
                job["done"] += 1
                job["progress"] = (job["done"] / job["total"]) if job["total"] else 0
                pm = job["perMode"].get(mode)
                if pm is not None:
                    pm["done"] = pm.get("done", 0) + 1
                _update_eta_locked()

    def _render_one_impl(mode: str, i: int, seq: List[str], audio_path: Optional[str]) -> None:
        nonlocal cancelled
        if _is_cancelled(job_id, JOBS):
            cancelled = True
            return

        t0 = time.time()

        mode_dir = run_dir / _mode_dir_name(mode)
        target_dir = mode_dir
        if wrap_size > 0:
            bundle_idx = ((i - 1) // wrap_size) + 1
            target_dir = mode_dir / str(bundle_idx)
        target_dir.mkdir(parents=True, exist_ok=True)

        outfile = target_dir / f"video_{i:04}.mp4"

        returncode, stderr_text, was_cancelled = -1, "", False
        used_cpu_fallback = False
        used_classic_fallback = False

        # --- Jalur cepat: remux dari file perantara -----------------------
        fast_ok = False
        if render_method == "fast":
            norm_entries = [norm_map.get(p) for p in seq]
            if all(e is not None for e in norm_entries):
                list_file = list_dir / f"{mode}_{i:06}.txt"
                try:
                    list_file.write_text(_concat_list_text(list(norm_entries)), encoding="utf-8")
                except Exception as e:
                    stderr_text = f"gagal menulis daftar concat: {e}"
                else:
                    cmd = _build_remux_cmd(list_file, outfile, want_audio, profile)
                    returncode, stderr_text, was_cancelled = _run_ffmpeg_cancellable(cmd, job_id, JOBS)
                    fast_ok = (returncode == 0 and not was_cancelled)
                    if not fast_ok and not was_cancelled:
                        err_lines = (stderr_text or "").strip().splitlines()
                        err_snip = err_lines[-1][:300] if err_lines else "unknown error"
                        job["logs"].append(
                            f"⚠ Remux cepat gagal pada {mode}/video_{i:04}.mp4 "
                            f"(exit {returncode}): {err_snip} — fallback re-encode penuh."
                        )
                        used_classic_fallback = True
                        try:
                            outfile.unlink(missing_ok=True)
                        except Exception:
                            pass
                finally:
                    try:
                        list_file.unlink(missing_ok=True)
                    except Exception:
                        pass
            else:
                used_classic_fallback = True  # ada klip yang gagal dinormalisasi

        # --- Jalur klasik (metode classic ATAU fallback) -------------------
        if not fast_ok and not was_cancelled:
            attempts = [active_encoder]
            if active_encoder in ("nvenc", "vaapi"):
                attempts.append("cpu")
            for attempt_no, enc in enumerate(attempts):
                cmd = _build_concat_cmd(
                    list(seq), outfile, mute_audio,
                    profile=profile,
                    encoder_mode=enc, vaapi_device=active_vaapi_device,
                    workers=workers,
                )
                returncode, stderr_text, was_cancelled = _run_ffmpeg_cancellable(cmd, job_id, JOBS)
                if was_cancelled:
                    break
                if returncode == 0:
                    used_cpu_fallback = attempt_no > 0
                    break
                if attempt_no + 1 < len(attempts):
                    err_lines = (stderr_text or "").strip().splitlines()
                    err_snip = err_lines[-1][:300] if err_lines else "unknown error"
                    job["logs"].append(
                        f"⚠ Encoder {enc} gagal pada {mode}/video_{i:04}.mp4 "
                        f"(exit {returncode}): {err_snip} — retry pakai CPU (libx264)."
                    )
                    try:
                        outfile.unlink(missing_ok=True)
                    except Exception:
                        pass

            if used_cpu_fallback:
                job["logs"].append(
                    f"✔ {mode}/video_{i:04}.mp4 berhasil di-encode setelah fallback ke CPU."
                )
            elif used_classic_fallback and returncode == 0:
                job["logs"].append(
                    f"✔ {mode}/video_{i:04}.mp4 berhasil lewat re-encode penuh (fallback)."
                )

        if returncode != 0:
            msg = (stderr_text or "").strip() or f"ffmpeg_failed:{mode}:{i}"
            job["logs"].append(msg[:800])
            # keep going per spec

        # --- Tahap 3: overlay audio eksternal (Replace/Mix) ----------------
        # Video final sudah berisi audio ASLI klip (diperlakukan seperti mode
        # "keep" di tahap render di atas). Untuk Replace/Mix, video ini
        # diproses ULANG dengan 1 file audio eksternal (rolling round-robin
        # per output), video di-copy (tidak di-re-encode lagi).
        if returncode == 0 and audio_overlay_active and not was_cancelled:
            if audio_path:
                video_has_audio = _probe_has_audio(str(outfile))
                tmp_audio_out = target_dir / f".video_{i:04}_audio_tmp.mp4"
                cmd = _build_audio_overlay_cmd(
                    outfile, audio_path, tmp_audio_out,
                    audio_mode=audio_mode,
                    video_has_audio=video_has_audio,
                    profile=profile,
                )
                a_rc, a_err, a_cancelled = _run_ffmpeg_cancellable(cmd, job_id, JOBS)
                if a_cancelled:
                    try:
                        tmp_audio_out.unlink(missing_ok=True)
                    except Exception:
                        pass
                    was_cancelled = True
                elif a_rc == 0:
                    try:
                        outfile.unlink(missing_ok=True)
                        tmp_audio_out.rename(outfile)
                    except Exception as e:
                        job["logs"].append(
                            f"⚠ Gagal mengganti {mode}/video_{i:04}.mp4 dengan hasil audio overlay: {e!r}"
                        )
                        try:
                            tmp_audio_out.unlink(missing_ok=True)
                        except Exception:
                            pass
                else:
                    err_lines = (a_err or "").strip().splitlines()
                    err_snip = err_lines[-1][:300] if err_lines else "unknown error"
                    job["logs"].append(
                        f"⚠ Overlay audio ({audio_mode}) gagal pada {mode}/video_{i:04}.mp4 "
                        f"(exit {a_rc}): {err_snip} — video tetap disimpan dengan audio asli klip."
                    )
                    try:
                        tmp_audio_out.unlink(missing_ok=True)
                    except Exception:
                        pass

        if was_cancelled:
            try:
                if outfile.exists():
                    outfile.unlink(missing_ok=True)
            except Exception:
                pass
            if wrap_size > 0:
                try:
                    if target_dir.exists() and not any(target_dir.iterdir()):
                        target_dir.rmdir()
                except Exception:
                    pass
            job["logs"].append(
                f"STOP: dihentikan saat memproses {mode} video_{i:04}.mp4 (file setengah jadi dihapus)."
            )
            cancelled = True
            return

        dt = time.time() - t0
        with counter_lock:
            if returncode == 0 and len(sample_times) < 12:
                sample_times.append(dt)
            job["done"] += 1
            job["progress"] = (job["done"] / job["total"]) if job["total"] else 0
            pm = job["perMode"].get(mode)
            if pm is not None:
                pm["done"] = pm.get("done", 0) + 1
            _update_eta_locked()

    try:
        if not cancelled:
            if workers > 1:
                pool = ThreadPoolExecutor(max_workers=workers)
                inflight = set()
                try:
                    for mode, sequences in sequences_by_mode.items():
                        if cancelled or _is_cancelled(job_id, JOBS):
                            break
                        (run_dir / _mode_dir_name(mode)).mkdir(parents=True, exist_ok=True)
                        for i, seq in enumerate(sequences, 1):
                            if cancelled or _is_cancelled(job_id, JOBS):
                                break
                            # Antrean terbatas: generator besar tidak
                            # dimaterialisasi ke RAM.
                            while len(inflight) >= workers * 2:
                                done_set, inflight = wait(inflight, return_when=FIRST_COMPLETED)
                            audio_path = _next_audio_path()
                            inflight.add(pool.submit(_render_one, mode, i, list(seq), audio_path))
                    if inflight:
                        wait(inflight)
                finally:
                    pool.shutdown(wait=True)
            else:
                for mode, sequences in sequences_by_mode.items():
                    if cancelled:
                        break
                    (run_dir / _mode_dir_name(mode)).mkdir(parents=True, exist_ok=True)
                    for i, seq in enumerate(sequences, 1):
                        if cancelled or _is_cancelled(job_id, JOBS):
                            cancelled = True
                            break
                        audio_path = _next_audio_path()
                        _render_one(mode, i, list(seq), audio_path)

        if _is_cancelled(job_id, JOBS):
            cancelled = True

        meta["outputDir"] = str(run_dir)
        if cancelled:
            job["status"] = "cancelled"
            job["etaSeconds"] = None
            done_n = job["done"]
            job["logs"].append(f"Proses dihentikan. {done_n} video selesai tetap disimpan di: {run_dir}")
        else:
            job["status"] = "done"
            job["etaSeconds"] = 0
        job["finishedAt"] = time.time()
    finally:
        # Bersihkan SEMUA file sementara job ini (termasuk hasil normalisasi
        # tahap 1 yang bisa berukuran besar).
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
