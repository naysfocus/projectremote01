"""
services/folder.py — Manajemen folder video output Video Mixer

Struktur yang dibaca:
storage/outputs/
└── 20240623_115500/           ← run_tag
    ├── horizontal/            ← mode folder
    │   ├── video_0001.mp4     ← struktur flat lama; diproses per 24 video
    ├── vertikal/
    │   ├── 1/                 ← satu batch baru; wajib tepat 24 video
    │   │   ├── video_0001.mp4
    │   ├── 2/
    │   └── 3/

Fungsi utama:
- list_run_tags()       : daftar run_tag (timestamp) dalam storage
- list_modes()          : daftar mode folder dalam 1 run_tag
- scan_subfolders()     : daftar subfolder numerik + status
- next_subfolder()      : subfolder terkecil yang belum diproses
- list_videos()         : daftar video dalam folder (urut)
- delete_subfolder()    : hapus subfolder (setelah semua video selesai)
"""
import os
import re
import shutil

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
VIDEO_SOURCE_NAMES = ("video-1", "video-2", "video-3", "video-4")


def ensure_video_sources(root_path):
    """Pastikan root dan empat folder sumber video tersedia."""
    raw_root = str(root_path or "").strip()
    if not raw_root:
        return {"ok": False, "error": "Root folder video belum diatur", "sources": []}
    root_path = os.path.abspath(os.path.expanduser(os.path.expandvars(raw_root)))
    try:
        os.makedirs(root_path, exist_ok=True)
        sources = []
        for index, dirname in enumerate(VIDEO_SOURCE_NAMES, start=1):
            source_path = os.path.join(root_path, dirname)
            os.makedirs(source_path, exist_ok=True)
            sources.append({
                "id": index,
                "label": f"Video {index}",
                "dirname": dirname,
                "path": source_path,
            })
        return {"ok": True, "root_path": root_path, "sources": sources}
    except OSError as exc:
        return {
            "ok": False,
            "root_path": root_path,
            "sources": [],
            "error": f"Tidak dapat membuat folder sumber video: {exc}",
        }


def list_video_sources(root_path):
    """Daftar empat sumber video beserta ringkasan isi masing-masing."""
    ensured = ensure_video_sources(root_path)
    if not ensured["ok"]:
        return ensured

    enriched = []
    for source in ensured["sources"]:
        scan = scan_subfolders(source["path"])
        if scan.get("has_subfolders"):
            subfolder_count = len(scan.get("subfolders", []))
            video_count = sum(sf.get("video_count", 0) for sf in scan.get("subfolders", []))
        else:
            subfolder_count = 0
            video_count = len(scan.get("videos_flat", []))
        enriched.append({
            **source,
            "subfolder_count": subfolder_count,
            "video_count": video_count,
        })
    return {"ok": True, "root_path": ensured["root_path"], "sources": enriched}


def _human_size(num_bytes):
    """Format ukuran file jadi human readable."""
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024.0:
            if unit == "B":
                return f"{int(num_bytes)} {unit}"
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def is_video(filename):
    return os.path.splitext(filename)[1].lower() in VIDEO_EXTS


def path_exists(path):
    return bool(path) and os.path.exists(path)


def list_directory(path):
    """
    List isi 1 directory (folder & file video) untuk file picker.
    Return dict: { ok, path, parent, folders[], videos[] }
    """
    if not path or not os.path.isdir(path):
        return {"ok": False, "error": "Folder tidak ditemukan", "path": path}

    folders = []
    videos = []
    try:
        for entry in sorted(os.listdir(path)):
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                folders.append({"name": entry, "path": full})
            elif is_video(entry):
                size = os.path.getsize(full)
                videos.append(
                    {"name": entry, "path": full, "size": size, "size_human": _human_size(size)}
                )
    except PermissionError:
        return {"ok": False, "error": "Akses folder ditolak", "path": path}

    parent = os.path.dirname(path.rstrip(os.sep))
    return {
        "ok": True,
        "path": path,
        "parent": parent,
        "folders": folders,
        "videos": videos,
    }


def list_videos(folder_path):
    """
    Daftar video dalam 1 folder, URUT berdasarkan nama (natural sort).
    Return list of dict: { name, path, size, size_human }
    """
    if not folder_path or not os.path.isdir(folder_path):
        return []

    files = [f for f in os.listdir(folder_path) if is_video(f)]
    files = _natural_sort(files)

    videos = []
    for f in files:
        full = os.path.join(folder_path, f)
        size = os.path.getsize(full)
        videos.append(
            {"name": f, "path": full, "size": size, "size_human": _human_size(size)}
        )
    return videos


def _natural_sort(items):
    """
    Sort natural: video_0001, video_0002, ..., video_0010 (bukan lexikografik).
    """
    def key(s):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

    return sorted(items, key=key)


def _numeric_subfolders(folder_path):
    """
    Daftar subfolder yang namanya angka (1, 2, 3, ...), urut menaik.
    Return list of (int_value, name, full_path).
    """
    result = []
    if not os.path.isdir(folder_path):
        return result
    for entry in os.listdir(folder_path):
        full = os.path.join(folder_path, entry)
        if os.path.isdir(full) and entry.isdigit():
            result.append((int(entry), entry, full))
    result.sort(key=lambda x: x[0])
    return result


def scan_subfolders(folder_path, processed_subfolders=None, locked_subfolders=None):
    """
    Scan subfolder numerik dalam folder mode.
    processed_subfolders: set/list nama subfolder yang sudah selesai (dari DB).
    locked_subfolders: dict {nama_subfolder: info} yang sedang dipakai sesi
        AKTIF akun lain (v1.43) — subfolder ini ditandai 'locked' agar tidak
        ditawarkan lagi ke akun lain, walau belum berstatus 'finished'.

    Return dict:
    {
      ok, has_subfolders, mode_type ('subfolder'|'flat'),
      subfolders: [{ name, path, video_count, processed, locked, locked_by }],
      videos_flat: [...]   (jika struktur flat lama)
    }
    """
    processed = set(str(s) for s in (processed_subfolders or []))
    locked = dict(locked_subfolders or {})

    if not folder_path or not os.path.isdir(folder_path):
        return {"ok": False, "error": "Folder tidak ditemukan", "subfolders": []}

    numeric = _numeric_subfolders(folder_path)

    if numeric:
        subfolders = []
        for _, name, full in numeric:
            vids = list_videos(full)
            lock_info = locked.get(name)
            subfolders.append(
                {
                    "name": name,
                    "path": full,
                    "video_count": len(vids),
                    "processed": name in processed,
                    "locked": bool(lock_info),
                    "locked_by": lock_info.get("username") if lock_info else None,
                }
            )
        return {
            "ok": True,
            "has_subfolders": True,
            "mode_type": "subfolder",
            "subfolders": subfolders,
            "videos_flat": [],
        }
    else:
        # Tidak ada subfolder numerik → mode flat kompatibilitas lama
        vids = list_videos(folder_path)
        return {
            "ok": True,
            "has_subfolders": False,
            "mode_type": "flat",
            "subfolders": [],
            "videos_flat": vids,
        }


def next_subfolder(folder_path, processed_subfolders=None, locked_subfolders=None):
    """
    Cari subfolder TERKECIL yang belum diproses, TIDAK sedang dikunci sesi
    aktif akun lain (v1.43), & masih punya video.
    Return dict subfolder atau None.
    """
    scan = scan_subfolders(folder_path, processed_subfolders, locked_subfolders)
    if not scan["ok"]:
        return None
    if not scan["has_subfolders"]:
        return None
    for sf in scan["subfolders"]:
        if not sf["processed"] and not sf["locked"] and sf["video_count"] > 0:
            return sf
    return None


def delete_subfolder(subfolder_path):
    """
    Hapus subfolder (shutil.rmtree). Dipakai setelah semua video selesai.
    Return dict { ok, error }.
    """
    if not subfolder_path or not os.path.isdir(subfolder_path):
        return {"ok": False, "error": "Subfolder tidak ditemukan"}
    try:
        shutil.rmtree(subfolder_path)
        return {"ok": True, "error": None}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def delete_file(filepath):
    """
    Hapus 1 file video dari PC (os.remove).
    Dipanggil segera setelah 1 video selesai diupload.
    """
    if not filepath or not os.path.isfile(filepath):
        return {"ok": False, "error": "File tidak ditemukan di PC"}
    try:
        os.remove(filepath)
        return {"ok": True, "error": None}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def folder_is_empty(folder_path):
    """Cek apakah folder kosong (tidak ada file/subfolder)."""
    if not os.path.isdir(folder_path):
        return True
    return len(os.listdir(folder_path)) == 0
