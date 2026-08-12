"""Kebijakan sesi upload Remote HP.

Mulai v1.41, semua sesi baru memakai tepat 24 video. Modul ini menjadi satu
sumber aturan di server agar UI lama, web client baru, dan Android client kelak
tidak dapat mengirim jumlah berbeda.
"""

POSTS_PER_SESSION = 24


def select_session_videos(uploadable_videos, *, has_subfolders):
    """Validasi dan pilih video untuk satu sesi baru.

    Untuk struktur subfolder, satu subfolder adalah satu batch sehingga jumlah
    video harus tepat 24. Untuk folder flat lama, server mengambil 24 video
    pertama agar instalasi yang masih memakai struktur lama tetap dapat dipakai.

    Return dict::
      {
        "ok": bool,
        "videos": list,
        "available_count": int,
        "selected_count": int,
        "remaining_count": int,
        "error": str | None,
      }
    """
    videos = list(uploadable_videos or [])
    available = len(videos)

    if has_subfolders:
        if available != POSTS_PER_SESSION:
            return {
                "ok": False,
                "videos": [],
                "available_count": available,
                "selected_count": 0,
                "remaining_count": 0,
                "error": (
                    f"Batch harus berisi tepat {POSTS_PER_SESSION} video siap. "
                    f"Saat ini tersedia {available} video."
                ),
            }
        selected = videos
    else:
        if available < POSTS_PER_SESSION:
            return {
                "ok": False,
                "videos": [],
                "available_count": available,
                "selected_count": 0,
                "remaining_count": 0,
                "error": (
                    f"Sesi membutuhkan {POSTS_PER_SESSION} video siap. "
                    f"Folder ini baru memiliki {available} video."
                ),
            }
        selected = videos[:POSTS_PER_SESSION]

    return {
        "ok": True,
        "videos": selected,
        "available_count": available,
        "selected_count": len(selected),
        "remaining_count": max(0, available - len(selected)),
        "error": None,
    }
