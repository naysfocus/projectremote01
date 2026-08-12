import itertools
from typing import Dict, List, Tuple, Any, Iterable


def _perm_count(n: int, k: int) -> int:
    """nPk (order matters, no replacement)."""
    if k < 0 or k > n:
        return 0
    out = 1
    for i in range(n, n - k, -1):
        out *= i
    return out


def _clip_counts(h: int, v: int) -> Dict[str, int]:
    """Output structure otomatis (sesuai request user).

    Konvensi dimensi:
    - h = Horizontal = jumlah kolom (angka: 1, 2, 3, ...)
    - v = Vertical   = jumlah baris (huruf: A, B, C, ...)

    Output structure (semua mode = keluarga horizontal, panjang output = h):
    - Horizontal                    = h  (1 baris penuh)
    - Campuran Horizontal           = h  (pilih 1 baris per kolom, urutan bebas)
    - Campuran Horizontal Linear    = h  (pilih 1 baris per kolom, urutan tetap 1..h)
    - Campuran Horizontal Linear Unik = h  (idem, tanpa baris/huruf berulang)
    """
    return {
        "horizontal": h,
        "mixHorizontal": h,
        "mixHorizontalLinear": h,
        "mixHorizontalLinearUnique": h,
    }


def calculate_estimates(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return max possible counts + validity per mode.

    Semua mode berada dalam keluarga "horizontal": urutan kolom mengikuti
    angka (1..h), dan yang bervariasi adalah baris/huruf yang dipilih di
    tiap kolom.

    Catatan:
    - Horizontal: permutasi dalam 1 baris (satu huruf) sepanjang h
    - Campuran Horizontal: untuk tiap kolom, pilih salah satu baris (baris
      bebas per kolom), lalu urutan tampil hasilnya JUGA diacak bebas
      (bukan cuma 1..h) — kombinasi baris duplikat difilter.
    - Campuran Horizontal Linear: untuk tiap kolom, pilih salah satu baris
      (baris bebas per kolom, boleh berulang), urutan tampil TETAP 1..h
      (linear, tidak diacak).
    - Campuran Horizontal Linear Unik: sama seperti Linear, tetapi baris
      (huruf) tidak boleh berulang dalam 1 output.
    """
    h = int(payload.get("h") or 0)  # jumlah kolom (angka)
    v = int(payload.get("v") or 0)  # jumlah baris (huruf)

    clips = _clip_counts(h, v)
    total_clips = h * v

    # Minimal 2 klip per output agar masuk akal untuk concat.
    horizontal_valid = h >= 2 and v >= 1
    mix_h_valid = h >= 2 and v >= 1
    mix_h_linear_valid = h >= 2 and v >= 1
    # Linear Unik butuh cukup huruf agar tidak ada pengulangan: v >= h.
    mix_h_linear_unique_valid = h >= 2 and v >= h

    horizontal_max = v * _perm_count(h, clips["horizontal"]) if horizontal_valid else 0

    # Campuran Horizontal (urutan tampil diacak bebas):
    # Untuk tiap kolom (1..h), pilih salah satu baris (0..v-1): v^h kemungkinan set.
    # Set berisi h klip (1 per kolom), lalu urutan bebas: h!
    # (Generator sesungguhnya memfilter set yang mengandung baris duplikat,
    # jadi jumlah realnya bisa lebih kecil dari angka teoretis ini.)
    mix_h_max = (v ** h) * _perm_count(h, clips["mixHorizontal"]) if mix_h_valid else 0

    # Campuran Horizontal — Linear (urutan tampil TETAP 1..h, baris boleh berulang):
    # Untuk tiap kolom, bebas pilih 1 dari v baris → v^h kombinasi, tanpa faktor h!.
    mix_h_linear_max = (v ** h) if mix_h_linear_valid else 0

    # Campuran Horizontal — Linear Unik (urutan tampil TETAP 1..h, baris TIDAK boleh berulang):
    # nPk = v! / (v-h)! — kolom 1 pilih dari v huruf, kolom 2 dari sisa (v-1), dst.
    mix_h_linear_unique_max = _perm_count(v, h) if mix_h_linear_unique_valid else 0

    return {
        "clipCounts": clips,
        "valid": {
            "horizontal": horizontal_valid,
            "mixHorizontal": mix_h_valid,
            "mixHorizontalLinear": mix_h_linear_valid,
            "mixHorizontalLinearUnique": mix_h_linear_unique_valid,
        },
        "max": {
            "horizontal": horizontal_max,
            "mixHorizontal": mix_h_max,
            "mixHorizontalLinear": mix_h_linear_max,
            "mixHorizontalLinearUnique": mix_h_linear_unique_max,
        },
    }


def _cell_path(cell: Any) -> str | None:
    if not cell:
        return None
    if isinstance(cell, str):
        return cell
    return cell.get("path")


def _build_videos_by_color(grid: List[List[Any]], h: int, v: int) -> Dict[str, List[str]]:
    """grid = V baris x H kolom.

    Return: {"A": [A1..Ah], "B": [B1..Bh], ...}
    """
    colors = [chr(ord("A") + i) for i in range(v)]
    videos_by_color: Dict[str, List[str]] = {}

    for r, c_name in enumerate(colors):
        row = grid[r] if r < len(grid) else []
        paths: List[str] = []
        for c in range(h):
            p = _cell_path(row[c]) if c < len(row) else None
            if not p:
                raise ValueError(f"missing_clip:{c_name}{c+1}")
            paths.append(p)
        videos_by_color[c_name] = paths

    return videos_by_color


def _gen_horizontal(videos_by_color: Dict[str, List[str]], h: int, v: int) -> Iterable[List[str]]:
    # Horizontal: untuk setiap baris, semua permutasi dari klip di baris tsb
    colors = [chr(ord("A") + i) for i in range(v)]
    for c in colors:
        clips = videos_by_color[c]
        for perm in itertools.permutations(clips, h):
            yield list(perm)


def _gen_mix_horizontal(videos_by_color: Dict[str, List[str]], h: int, v: int) -> Iterable[List[str]]:
    """Campuran Horizontal: baris bebas per kolom, urutan bebas.

    Untuk tiap kolom, pilih salah satu baris (A..), sehingga mendapatkan 1 klip per kolom.
    Lalu permutasikan semua klip tersebut (panjang = h).
    """
    colors = [chr(ord("A") + i) for i in range(v)]
    # pilih baris (warna) untuk tiap kolom
    for chosen_rows in itertools.product(range(v), repeat=h):
        base = [videos_by_color[colors[chosen_rows[col_idx]]][col_idx] for col_idx in range(h)]
        # anti-duplikasi dalam 1 output
        if len(set(base)) != len(base):
            continue
        for perm in itertools.permutations(base, h):
            yield list(perm)


def _gen_mix_horizontal_linear(videos_by_color: Dict[str, List[str]], h: int, v: int) -> Iterable[List[str]]:
    """Campuran Horizontal — Linear: baris bebas per kolom, urutan TETAP 1..h.

    Untuk tiap kolom (1..h), bebas pilih salah satu baris (A..), boleh
    berulang antar kolom. Urutan tampil hasil SELALU mengikuti urutan
    kolom asli (1,2,3,...,h) — tidak ada permutasi urutan tampil.
    """
    colors = [chr(ord("A") + i) for i in range(v)]
    for chosen_rows in itertools.product(range(v), repeat=h):
        base = [videos_by_color[colors[chosen_rows[col_idx]]][col_idx] for col_idx in range(h)]
        yield base


def _gen_mix_horizontal_linear_unique(videos_by_color: Dict[str, List[str]], h: int, v: int) -> Iterable[List[str]]:
    """Campuran Horizontal — Linear Unik: baris bebas per kolom (tanpa
    pengulangan huruf), urutan TETAP 1..h.

    Sama seperti Linear, tetapi tiap huruf/baris hanya boleh dipakai
    sekali per output (tidak boleh duplikat).
    """
    colors = [chr(ord("A") + i) for i in range(v)]
    for chosen_rows in itertools.permutations(range(v), h):
        base = [videos_by_color[colors[chosen_rows[col_idx]]][col_idx] for col_idx in range(h)]
        yield base


def estimate_output_size(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Estimasi ukuran file/folder output per mode (v1.1).

    Rumus:
      durasi 1 output = (klip per output untuk mode itu) x (rata-rata durasi klip)
      ukuran 1 output = (bitrate video [+ audio]) x durasi / 8   (byte)
      total per mode  = ukuran 1 output x jumlah output (dibatasi batch bila ada)

    Input `payload`:
      - h, v
      - modes: {horizontal, mixHorizontal, mixHorizontalLinear, mixHorizontalLinearUnique} (bool)
      - batch: {enabled, size}
      - muteAudio: bool (kompatibilitas mundur)
      - audioMode: "mute" | "keep" | "replace" | "mix" (v1.9, dipakai bila ada)
      - avgClipDuration: float (detik) — rata-rata durasi klip di grid
      - videoBitrate / audioBitrate (opsional, bps) untuk override estimasi

    Return dict:
      {
        perMode: { mode: {outputs, perOutputBytes, totalBytes, ...} },
        grandTotalBytes, grandTotalOutputs,
        assumptions: {...}
      }
    """
    h = int(payload.get("h") or 0)
    v = int(payload.get("v") or 0)
    modes = payload.get("modes") or {}
    # v1.9: audioMode menggantikan muteAudio bila tersedia. Semua mode
    # selain "mute" menghasilkan output ber-audio (untuk estimasi ukuran).
    audio_mode = payload.get("audioMode")
    if audio_mode:
        mute_audio = str(audio_mode).strip().lower() == "mute"
    else:
        mute_audio = bool(payload.get("muteAudio", True))
    avg_clip = float(payload.get("avgClipDuration") or 0.0)

    # Bitrate asumsi (diturunkan dari profil output oleh pemanggil/worker).
    # Fallback default v1.6 = 720p @24fps kualitas seimbang (~2 Mbps / 128 kbps).
    video_bps = int(payload.get("videoBitrate") or 2_000_000)
    audio_bps = 0 if mute_audio else int(payload.get("audioBitrate") or 128_000)
    total_bps = video_bps + audio_bps

    estimates = calculate_estimates({"h": h, "v": v})
    clip_counts = estimates["clipCounts"]   # klip per output per mode
    max_counts = estimates["max"]
    valid = estimates["valid"]

    # Batch limit (opsional).
    batch = payload.get("batch") or {}
    limit_enabled = bool(batch.get("enabled"))
    try:
        limit_size = int(batch.get("size") or 0)
    except Exception:
        limit_size = 0
    if not limit_enabled or limit_size < 0:
        limit_size = 0

    per_mode: Dict[str, Any] = {}
    grand_total_bytes = 0
    grand_total_outputs = 0

    for mode in ("horizontal", "mixHorizontal", "mixHorizontalLinear", "mixHorizontalLinearUnique"):
        if not modes.get(mode) or not valid.get(mode):
            continue
        outputs_max = int(max_counts.get(mode) or 0)
        outputs = min(outputs_max, limit_size) if limit_size > 0 else outputs_max

        clips_per_output = int(clip_counts.get(mode) or 0)
        duration_per_output = clips_per_output * avg_clip  # detik
        per_output_bytes = int(total_bps * duration_per_output / 8)  # bit → byte
        total_bytes = per_output_bytes * outputs

        per_mode[mode] = {
            "outputs": outputs,
            "outputsMax": outputs_max,
            "clipsPerOutput": clips_per_output,
            "durationPerOutput": round(duration_per_output, 2),
            "perOutputBytes": per_output_bytes,
            "totalBytes": total_bytes,
        }
        grand_total_bytes += total_bytes
        grand_total_outputs += outputs

    return {
        "perMode": per_mode,
        "grandTotalBytes": grand_total_bytes,
        "grandTotalOutputs": grand_total_outputs,
        "assumptions": {
            "videoBitrate": video_bps,
            "audioBitrate": audio_bps,
            "avgClipDuration": round(avg_clip, 3),
            "muteAudio": mute_audio,
            # v1.6: resolusi/fps/rate-control diteruskan agar UI menampilkan
            # asumsi yang benar (bukan lagi 1080×1920 @30fps hardcoded).
            "width": int(payload.get("width") or 0) or None,
            "height": int(payload.get("height") or 0) or None,
            "fps": int(payload.get("fps") or 0) or None,
            "rateMode": payload.get("rateMode") or None,
            "quality": payload.get("quality"),
        },
    }


def build_job_plan(payload: Dict[str, Any]) -> Tuple[Dict[str, Iterable[List[str]]], Dict[str, Any]]:
    """Build generators per mode + meta untuk progress dan output folder."""
    h = int(payload["h"])
    v = int(payload["v"])
    modes = payload.get("modes") or {}
    folder_policy = str(payload.get("folderPolicy") or "all").strip().lower()
    grid = payload.get("grid") or []

    # Batch limit (opsional): jika enabled, batasi jumlah output per mode.
    batch = payload.get("batch") or {}
    limit_enabled = bool(batch.get("enabled"))
    try:
        limit_size = int(batch.get("size") or 0)
    except Exception:
        limit_size = 0
    if not limit_enabled:
        limit_size = 0

    videos_by_color = _build_videos_by_color(grid, h=h, v=v)
    estimates = calculate_estimates({"h": h, "v": v})
    clip_counts = estimates["clipCounts"]

    sequences_by_mode: Dict[str, Iterable[List[str]]] = {}
    effective_max: Dict[str, int] = {}
    def _apply_limit(mode_key: str, seq: Iterable[List[str]]) -> Iterable[List[str]]:
        est_max = int((estimates.get("max") or {}).get(mode_key) or 0)
        if limit_size > 0:
            effective_max[mode_key] = min(est_max, limit_size)
            return itertools.islice(seq, effective_max[mode_key])
        effective_max[mode_key] = est_max
        return seq

    if modes.get("horizontal") and estimates["valid"]["horizontal"]:
        sequences_by_mode["horizontal"] = _apply_limit("horizontal", _gen_horizontal(videos_by_color, h=h, v=v))
    if modes.get("mixHorizontal") and estimates["valid"]["mixHorizontal"]:
        sequences_by_mode["mixHorizontal"] = _apply_limit("mixHorizontal", _gen_mix_horizontal(videos_by_color, h=h, v=v))
    if modes.get("mixHorizontalLinear") and estimates["valid"]["mixHorizontalLinear"]:
        sequences_by_mode["mixHorizontalLinear"] = _apply_limit("mixHorizontalLinear", _gen_mix_horizontal_linear(videos_by_color, h=h, v=v))
    if modes.get("mixHorizontalLinearUnique") and estimates["valid"]["mixHorizontalLinearUnique"]:
        sequences_by_mode["mixHorizontalLinearUnique"] = _apply_limit("mixHorizontalLinearUnique", _gen_mix_horizontal_linear_unique(videos_by_color, h=h, v=v))

    # v1.4: daftar klip unik dari grid (urutan dijaga) — dipakai worker untuk
    # tahap normalisasi 1x per klip pada metode render "fast".
    grid_paths: List[str] = []
    for paths in videos_by_color.values():
        for p in paths:
            if p not in grid_paths:
                grid_paths.append(p)

    meta = {
        "h": h,
        "v": v,
        "folderPolicy": folder_policy,
        "muteAudio": bool(payload.get("muteAudio", True)),
        "clipCounts": clip_counts,
        "estimates": estimates,
        "effectiveMax": effective_max,
        "gridPaths": grid_paths,
        "batch": {
            "enabled": limit_size > 0,
            "size": int(limit_size or 0),
        },
    }
    return sequences_by_mode, meta
