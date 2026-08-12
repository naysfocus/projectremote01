"""Output-count safety warning for Video Mixer.

The threshold is intentionally a warning, not a hard limit. The confirmation
hash binds approval to the exact render configuration submitted by the UI.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

LARGE_OUTPUT_WARNING_THRESHOLD = 30_000
_MODE_KEYS = (
    "horizontal",
    "mixHorizontal",
    "mixHorizontalLinear",
    "mixHorizontalLinearUnique",
)


def render_output_warning(
    data: dict[str, Any],
    calculate_estimates: Callable[[dict[str, Any]], dict[str, Any]],
) -> tuple[int, dict[str, int], str]:
    estimates = calculate_estimates(data or {})
    maximums = estimates.get("max") or {}
    valid = estimates.get("valid") or {}
    modes = (data or {}).get("modes") or {}
    batch = (data or {}).get("batch") or {}
    limit_enabled = bool(batch.get("enabled"))
    try:
        limit_size = int(batch.get("size") or 0)
    except (TypeError, ValueError):
        limit_size = 0
    if not limit_enabled or limit_size <= 0:
        limit_size = 0

    per_mode: dict[str, int] = {}
    total = 0
    for key in _MODE_KEYS:
        if not modes.get(key) or not valid.get(key):
            continue
        count = int(maximums.get(key) or 0)
        if limit_size > 0:
            count = min(count, limit_size)
        per_mode[key] = count
        total += count

    safety_payload = {
        "h": int((data or {}).get("h") or 0),
        "v": int((data or {}).get("v") or 0),
        "modes": {key: bool(modes.get(key)) for key in sorted(modes)},
        "batch": {"enabled": limit_enabled, "size": limit_size},
        "audioMode": str((data or {}).get("audioMode") or ""),
        "encoderMode": str((data or {}).get("encoderMode") or ""),
        "renderMethod": str((data or {}).get("renderMethod") or ""),
        "parallelWorkers": str((data or {}).get("parallelWorkers") or ""),
        "outputProfile": (data or {}).get("outputProfile") or {},
        "folderPolicy": str((data or {}).get("folderPolicy") or ""),
        "grid": (data or {}).get("grid") or [],
        "total": str(total),
    }
    canonical = json.dumps(
        safety_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    signature = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return total, per_mode, signature
