"""Storage configuration helper.

App ini jalan sebagai server lokal (localhost). User ingin bisa memilih lokasi
storage (uploads/temp/outputs) di drive/folder lain.

Catatan penting:
- Browser tidak bisa "browse folder server" langsung. Karena ini aplikasi lokal,
  kita sediakan endpoint yang membuka native dialog (tkinter) di mesin server.
- Selalu ada fallback: user bisa mengetik path secara manual.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Dict


BASE = Path(__file__).parents[1]  # .../app
DEFAULT_BASE = BASE / "storage"
CONFIG_FILE = BASE / "storage_config.json"


def _read_config() -> Dict[str, str]:
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        pass
    return {}


def get_storage_base() -> Path:
    cfg = _read_config()
    p = (cfg.get("storageBase") or "").strip()
    if p:
        try:
            return Path(p)
        except Exception:
            return DEFAULT_BASE
    return DEFAULT_BASE


def set_storage_base(path_str: str) -> Path:
    path_str = (path_str or "").strip()
    if not path_str:
        # reset to default
        if CONFIG_FILE.exists():
            try:
                CONFIG_FILE.unlink(missing_ok=True)
            except Exception:
                pass
        ensure_storage_dirs(DEFAULT_BASE)
        return DEFAULT_BASE

    base = Path(path_str)
    base.mkdir(parents=True, exist_ok=True)
    ensure_storage_dirs(base)
    CONFIG_FILE.write_text(json.dumps({"storageBase": str(base)}, ensure_ascii=False, indent=2), encoding="utf-8")
    return base


def ensure_storage_dirs(base: Path) -> Dict[str, Path]:
    uploads = base / "uploads"
    temp = base / "temp"
    outputs = base / "outputs"
    audio = base / "audio"
    uploads.mkdir(parents=True, exist_ok=True)
    temp.mkdir(parents=True, exist_ok=True)
    outputs.mkdir(parents=True, exist_ok=True)
    audio.mkdir(parents=True, exist_ok=True)
    return {"uploads": uploads, "temp": temp, "outputs": outputs, "audio": audio}


def list_subdirectories(path_str: Optional[str] = None) -> Dict[str, Any]:
    """Safely list directories under the given path.
    
    If path_str is empty/None, start from get_storage_base().
    """
    if not path_str:
        current = get_storage_base()
    else:
        try:
            current = Path(path_str).resolve()
        except Exception:
            current = get_storage_base()

    # Ensure path exists and is a directory
    if not current.exists() or not current.is_dir():
        # Fallback to DEFAULT_BASE if current does not exist
        current = DEFAULT_BASE
        current.mkdir(parents=True, exist_ok=True)

    subdirs = []
    try:
        for p in current.iterdir():
            if p.is_dir() and not p.name.startswith('.'):
                subdirs.append({
                    "name": p.name,
                    "path": str(p.absolute())
                })
    except Exception:
        pass

    subdirs.sort(key=lambda x: x["name"].lower())

    parent_path = None
    try:
        if current.parent != current:
            parent_path = str(current.parent.absolute())
    except Exception:
        pass

    return {
        "currentPath": str(current.absolute()),
        "parentPath": parent_path,
        "subdirs": subdirs
    }

