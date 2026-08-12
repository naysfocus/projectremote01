"""
routes/upload.py — Workflow upload FIFO (inti aplikasi)

State machine per sesi:
  pending → active (video dikirim & dikonfirmasi satu per satu) → finished

ATURAN KETAT (dari masterplan):
  - Video dikirim SATU per SATU (FIFO) — endpoint push hanya 1 video
  - Tombol "Video N Selesai" baru bisa setelah video N terkirim (status 'sent')
  - Setelah konfirmasi: hapus HP -> hapus PC -> catat DB (segera, tidak menumpuk)
  - Tombol "Selesai Sesi" baru bisa setelah semua video selesai
  - Subfolder dihapus dari PC setelah semua video selesai
  - Urutan video wajib urut (natural sort)
  - Guard: video sudah pernah upload tidak boleh diupload ulang

Status video:
  'waiting'  -> belum dikirim
  'sent'     -> sudah di-push ke HP, menunggu konfirmasi
  'done'     -> sudah dikonfirmasi, dihapus dari HP & PC, dicatat
"""
import os
import json
import logging

from flask import Blueprint, request, jsonify, current_app
from database.db import query, execute, get_setting, set_setting
from services import adb, folder, guard, caption as caption_svc, scheduler, scrcpy, device_connection
from services.session_policy import POSTS_PER_SESSION, select_session_videos

upload_bp = Blueprint("upload", __name__, url_prefix="/api/upload")
log = logging.getLogger(__name__)


def _remote_report(event_type, summary):
    """Antrekan laporan ke Remote Server tanpa memperlambat workflow lokal."""
    client = current_app.extensions.get("remote_server_client")
    if client is not None:
        try:
            client.queue_report(event_type, summary)
        except Exception as exc:
            log.warning("Laporan Remote Server ditunda karena antrean lokal gagal: %s", exc)

def _request_remote_sync(force=False, session_id=None):
    client = current_app.extensions.get("remote_server_client")
    if client is not None:
        try:
            client.request_data_sync(force=force, session_id=session_id)
        except Exception as exc:
            log.warning("Sinkronisasi data Remote Server ditunda: %s", exc)


def _get_session(session_id):
    return query("SELECT * FROM upload_sessions WHERE id = ?", (session_id,), one=True)


def _subfolder_sort_key(name):
    """Urutkan subfolder numerik dengan benar (1, 2, ..., 10 — bukan leksikal '1','10','2')."""
    try:
        return (0, int(name))
    except (TypeError, ValueError):
        return (1, str(name))


def _processed_subfolders(account_id, folder_path, batch_date=None):
    """
    Daftar subfolder yang sudah SELESAI diproses untuk folder ini.

    v1.1.4: pemrosesan di-scope PER TANGGAL BATCH. Sebuah subfolder (mis. "1/")
    dianggap "sudah diproses" hanya jika sesi yang menyelesaikannya memakai
    tanggal batch yang SAMA. Ini penting karena alur kerja memakai nama
    subfolder & nama file yang berulang tiap hari — tanpa scope tanggal,
    subfolder "1/" akan terkunci selamanya setelah dipakai sekali.

    Bila batch_date None (kompatibilitas lama), kembali ke perilaku lintas-tanggal.
    """
    if batch_date:
        rows = query(
            """
            SELECT DISTINCT subfolder FROM upload_sessions
            WHERE folder_path = ? AND status = 'finished' AND batch_date = ?
            """,
            (folder_path, batch_date),
        )
    else:
        rows = query(
            """
            SELECT DISTINCT subfolder FROM upload_sessions
            WHERE folder_path = ? AND status = 'finished'
            """,
            (folder_path,),
        )
    return [r["subfolder"] for r in rows]


def _locked_subfolders(folder_path, exclude_account_id=None):
    """
    Daftar subfolder di `folder_path` yang SEDANG DIPAKAI oleh sesi 'active'
    milik akun MANAPUN (v1.43 — perbaikan bug rebutan folder antar akun).

    Tanpa fungsi ini, subfolder yang sedang dikerjakan akun A (termasuk saat
    A "istirahat" di tengah sesi — statusnya tetap 'active' sampai
    selesai/dibatalkan) bisa ikut ditawarkan ke akun B karena
    _processed_subfolders() hanya melihat status 'finished'. Guard ini
    memastikan folder/subfolder terkunci PERSISTEN (berbasis tabel
    upload_sessions di database, bukan variabel sementara) selama sesi lain
    masih aktif — persis seperti yang diminta: terpisah per akun & tetap
    tersimpan walau ditinggal istirahat.

    exclude_account_id: kecualikan sesi milik akun ini sendiri, supaya akun
    yang SAMA tetap bisa melihat/melanjutkan subfolder yang ia pakai sendiri.

    Return: list of dict [{ subfolder, account_id, username }]
    """
    if exclude_account_id:
        rows = query(
            """
            SELECT s.subfolder, s.account_id, a.username
            FROM upload_sessions s
            LEFT JOIN accounts a ON a.id = s.account_id
            WHERE s.folder_path = ? AND s.status = 'active' AND s.account_id != ?
            """,
            (folder_path, exclude_account_id),
        )
    else:
        rows = query(
            """
            SELECT s.subfolder, s.account_id, a.username
            FROM upload_sessions s
            LEFT JOIN accounts a ON a.id = s.account_id
            WHERE s.folder_path = ? AND s.status = 'active'
            """,
            (folder_path,),
        )
    return [
        {"subfolder": r["subfolder"], "account_id": r["account_id"], "username": r.get("username") or "-"}
        for r in rows
    ]


def _video_state_key(session_id):
    return f"_session_videos_{session_id}"


def _load_video_state(session_id):
    raw = get_setting(_video_state_key(session_id))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _save_video_state(session_id, videos):
    set_setting(_video_state_key(session_id), json.dumps(videos, ensure_ascii=False))


def _clear_video_state(session_id):
    execute("DELETE FROM settings WHERE key = ?", (_video_state_key(session_id),))


# 0. VIDEO SOURCES — empat folder tetap dari root di Pengaturan
@upload_bp.route("/sources", methods=["GET"])
def get_video_sources():
    storage_root = (get_setting("storage_path") or "").strip()
    result = folder.list_video_sources(storage_root)
    result["posts_per_session"] = POSTS_PER_SESSION

    # v1.43: tandai sumber video yang sedang punya sesi AKTIF milik akun
    # manapun, supaya UI bisa menampilkan "sedang dipakai akun X" di grid
    # pemilihan sumber SEBELUM user scan — bukan cuma setelah scan.
    if result.get("ok") and result.get("sources"):
        for source in result["sources"]:
            active_rows = query(
                """
                SELECT s.account_id, a.username, COUNT(*) AS n
                FROM upload_sessions s
                LEFT JOIN accounts a ON a.id = s.account_id
                WHERE s.folder_path = ? AND s.status = 'active'
                GROUP BY s.account_id
                """,
                (source["path"],),
            )
            source["active_sessions"] = [
                {"account_id": r["account_id"], "username": r.get("username") or "-", "count": r["n"]}
                for r in active_rows
            ]

    return jsonify(result), (200 if result.get("ok") else 400)


# 1. SCAN FOLDER
@upload_bp.route("/scan", methods=["POST"])
def scan_folder():
    data = request.get_json() or {}
    folder_path = (data.get("folder_path") or "").strip()
    # Field policy dari client lama sengaja diabaikan. Mulai v1.41,
    # server menjadi satu-satunya sumber aturan: 24 video per sesi.
    # Tanggal batch (v1.1.4) — dipakai sebagai kunci anti-duplikasi & jadwal.
    batch_date = scheduler.valid_batch_date(data.get("batch_date"))
    # account_id (v1.43) — dipakai untuk PENGECUALIAN kunci folder: akun yang
    # sama boleh tetap melihat/melanjutkan subfolder yang ia pakai sendiri.
    account_id = data.get("account_id")

    if not batch_date:
        return jsonify({"error": "Tanggal wajib dipilih (Panel 1) sebelum scan folder"}), 400
    if not folder_path:
        return jsonify({"error": "folder_path wajib diisi"}), 400
    if not folder.path_exists(folder_path):
        return jsonify({"error": f"Folder tidak ditemukan: {folder_path}"}), 404

    processed = _processed_subfolders(None, folder_path, batch_date=batch_date)
    # v1.43: subfolder yang sedang dipakai sesi AKTIF akun lain dikunci —
    # supaya tidak ditawarkan lagi ke akun lain saat akun tsb "istirahat".
    locked_rows = _locked_subfolders(folder_path, exclude_account_id=account_id)
    locked_map = {row["subfolder"]: row for row in locked_rows}
    scan = folder.scan_subfolders(folder_path, processed_subfolders=processed, locked_subfolders=locked_map)

    if not scan["ok"]:
        return jsonify({"error": scan.get("error", "Gagal scan folder")}), 400

    # v1.45: AUTO-SKIP subfolder yang tidak memenuhi kriteria layak sesi.
    #
    # Sebelumnya sistem hanya berhenti di subfolder PERTAMA yang belum
    # 'processed' & tidak 'locked' (asal video_count > 0), lalu baru gagal
    # validasi 24-video SETELAH dipilih — sehingga kelihatan seperti macet,
    # padahal subfolder berikutnya (mis. yang isinya lengkap 24) bisa jadi
    # layak dipakai. Sekarang loop mencoba subfolder satu per satu secara
    # berurutan (nomor terkecil dulu) dan otomatis lanjut ke berikutnya bila:
    #   - subfolder sedang dikunci sesi aktif akun lain, ATAU
    #   - subfolder sudah selesai diproses (batch_date ini), ATAU
    #   - jumlah video siap upload (setelah dikurangi duplikat) TIDAK genap
    #     24 (baik kurang maupun lebih dari kebijakan sesi).
    # Semua subfolder yang dilewati dicatat di `skipped` beserta alasannya,
    # supaya pengguna tetap tahu kenapa — bukan cuma "loncat diam-diam".
    chosen = None
    skipped = []
    if scan["has_subfolders"]:
        candidates = sorted(
            scan["subfolders"], key=lambda sf: _subfolder_sort_key(sf["name"])
        )
        for sf in candidates:
            if sf["locked"]:
                skipped.append({
                    "name": sf["name"], "reason": "locked",
                    "message": f"Sedang dipakai sesi aktif akun '{sf.get('locked_by') or '-'}'",
                })
                continue
            if sf["processed"]:
                skipped.append({
                    "name": sf["name"], "reason": "processed",
                    "message": "Sudah selesai diproses untuk tanggal batch ini",
                })
                continue
            if sf["video_count"] <= 0:
                skipped.append({
                    "name": sf["name"], "reason": "empty",
                    "message": "Folder kosong / tidak ada video",
                })
                continue

            candidate_videos = folder.list_videos(sf["path"])
            candidate_guard = guard.filter_uploadable(candidate_videos, batch_date=batch_date)
            candidate_batch = select_session_videos(
                candidate_guard["uploadable"], has_subfolders=True,
            )
            if not candidate_batch["ok"]:
                skipped.append({
                    "name": sf["name"], "reason": "video_count_mismatch",
                    "message": candidate_batch["error"],
                })
                continue

            # Ketemu subfolder yang layak — pakai ini, hentikan loop.
            chosen = {
                "sf": sf,
                "videos": candidate_videos,
                "guard_result": candidate_guard,
                "batch": candidate_batch,
            }
            break

        if not chosen:
            # Tidak ada satu pun subfolder yang layak. Bedakan pesan supaya
            # jelas apakah karena semua terkunci, semua selesai, atau semua
            # jumlah videonya tidak pas.
            reasons = {s["reason"] for s in skipped}
            if reasons and reasons.issubset({"processed"}):
                message = "Semua subfolder sudah diproses"
            elif "locked" in reasons and reasons.issubset({"locked", "processed"}):
                message = "Subfolder yang tersisa sedang dipakai sesi aktif akun lain. Tunggu sampai sesi itu selesai/dibatalkan, atau pilih folder sumber video lain."
            elif "video_count_mismatch" in reasons:
                message = (
                    "Tidak ada subfolder yang siap: semua subfolder yang tersisa jumlah "
                    f"videonya tidak pas {POSTS_PER_SESSION} (setelah dikurangi duplikat), "
                    "sedang dipakai akun lain, atau sudah selesai diproses."
                )
            else:
                message = "Tidak ada subfolder yang siap dipakai saat ini."
            return jsonify({
                "ok": True, "has_subfolders": True, "all_done": True,
                "message": message,
                "subfolders": scan["subfolders"], "skipped_subfolders": skipped,
                "next_subfolder": None, "videos": [],
            })

        videos = chosen["videos"]
        subfolder_name = chosen["sf"]["name"]
        subfolder_path = chosen["sf"]["path"]
        guard_result = chosen["guard_result"]
        batch = chosen["batch"]
    else:
        videos = scan["videos_flat"]
        subfolder_name = "."
        subfolder_path = folder_path
        guard_result = guard.filter_uploadable(videos, batch_date=batch_date)
        batch = select_session_videos(guard_result["uploadable"], has_subfolders=False)

    # Saat valid, tampilkan hanya 24 video yang benar-benar akan masuk sesi.
    # Saat belum valid, tampilkan seluruh isi agar pengguna dapat melihat
    # kekurangan/kelebihan atau video yang terkena guard duplikasi.
    dup_names = {d["name"] for d in guard_result["duplicates"]}
    display_videos = batch["videos"] if batch["ok"] else videos
    video_list = []
    for v in display_videos:
        video_list.append({
            "name": v["name"], "path": v["path"], "size": v["size"],
            "size_human": v["size_human"], "is_duplicate": v["name"] in dup_names,
            "status": "waiting",
        })

    return jsonify({
        "ok": True, "has_subfolders": scan["has_subfolders"], "all_done": False,
        "subfolders": scan["subfolders"], "skipped_subfolders": skipped, "next_subfolder": subfolder_name,
        "subfolder_path": subfolder_path, "videos": video_list,
        "batch_date": batch_date,
        "posts_per_session": POSTS_PER_SESSION,
        "can_start": batch["ok"],
        "validation_error": batch["error"],
        "duplicate_count": len(dup_names),
        "available_count": batch["available_count"],
        "uploadable_count": batch["selected_count"],
        "remaining_count": batch["remaining_count"],
    })


# 2. START SESSION
@upload_bp.route("/start", methods=["POST"])
def start_session():
    data = request.get_json() or {}
    account_id = data.get("account_id")
    device_id = data.get("device_id")
    folder_path = (data.get("folder_path") or "").strip()
    subfolder = (data.get("subfolder") or "").strip()
    subfolder_path = (data.get("subfolder_path") or "").strip()
    # Policy dari client lama tidak lagi dipercaya; sesi baru selalu 24.
    # Tanggal batch (v1.1.4)
    batch_date = scheduler.valid_batch_date(data.get("batch_date"))

    if not batch_date:
        return jsonify({"error": "Tanggal wajib dipilih (Panel 1) sebelum memulai sesi"}), 400
    if not all([account_id, device_id, folder_path, subfolder_path]):
        return jsonify({"error": "Data tidak lengkap"}), 400

    account = query("SELECT * FROM accounts WHERE id = ?", (account_id,), one=True)
    device = query("SELECT * FROM devices WHERE id = ?", (device_id,), one=True)
    if not account or not device:
        return jsonify({"error": "Akun atau HP tidak ditemukan"}), 404

    active = query(
        "SELECT * FROM upload_sessions WHERE account_id = ? AND status = 'active'",
        (account_id,), one=True,
    )
    if active:
        return jsonify({
            "error": "Masih ada sesi aktif untuk akun ini. Selesaikan/batalkan dulu.",
            "active_session_id": active["id"]
        }), 409

    # v1.43: GUARD UTAMA anti-rebutan folder. Walau UI sudah menyaring
    # subfolder terkunci saat scan, tetap divalidasi ulang di sini (sumber
    # kebenaran terakhir) untuk mencegah race condition — misal 2 tab/browser
    # scan hampir bersamaan lalu keduanya mencoba start di subfolder yang sama.
    if subfolder and subfolder not in (".", ""):
        clash = query(
            """
            SELECT s.id, s.account_id, a.username
            FROM upload_sessions s
            LEFT JOIN accounts a ON a.id = s.account_id
            WHERE s.folder_path = ? AND s.subfolder = ? AND s.status = 'active' AND s.account_id != ?
            """,
            (folder_path, subfolder, account_id),
            one=True,
        )
        if clash:
            return jsonify({
                "error": (
                    f"Subfolder {subfolder}/ sedang dipakai sesi aktif akun "
                    f"'{clash.get('username') or '-'}'. Pilih subfolder/folder sumber lain, "
                    "atau tunggu sesi tersebut selesai/dibatalkan."
                ),
                "locked_by_account_id": clash["account_id"],
            }), 409

    videos = folder.list_videos(subfolder_path)
    if not videos:
        return jsonify({"error": "Tidak ada video dalam subfolder ini"}), 400

    guard_result = guard.filter_uploadable(videos, batch_date=batch_date)
    uploadable = guard_result["uploadable"]
    if not uploadable:
        return jsonify({
            "error": "Semua video di subfolder ini sudah pernah diupload untuk tanggal tersebut"
        }), 400

    batch = select_session_videos(
        uploadable,
        has_subfolders=(subfolder not in (".", "")),
    )
    if not batch["ok"]:
        return jsonify({
            "error": batch["error"],
            "posts_per_session": POSTS_PER_SESSION,
            "available_count": batch["available_count"],
        }), 400

    session_id = execute(
        """INSERT INTO upload_sessions (account_id, device_id, folder_path, subfolder, policy, batch_date, status)
           VALUES (?, ?, ?, ?, ?, ?, 'active')""",
        (account_id, device_id, folder_path, subfolder, POSTS_PER_SESSION, batch_date),
    )

    video_state = []
    for v in batch["videos"]:
        video_state.append({
            "name": v["name"], "path": v["path"],
            "size_human": v["size_human"], "status": "waiting",
        })
    _save_video_state(session_id, video_state)

    _remote_report("upload_session_started", {
        "local_session_id": session_id,
        "account_username": account["username"],
        "device_name": device["name"],
        "video_count": len(video_state),
        "batch_date": batch_date,
        "status": "active",
    })
    _request_remote_sync(session_id=session_id)

    caption = caption_svc.generate_caption()
    random_range = get_setting("random_range") or 15
    schedule = scheduler.generate_fixed_session_schedule(random_range)

    return jsonify({
        "ok": True, "session_id": session_id, "videos": video_state,
        "caption": caption, "schedule": schedule,
        "batch_date": batch_date,
        "policy": POSTS_PER_SESSION,
        "posts_per_session": POSTS_PER_SESSION,
        "target_dir": adb.get_hp_target_dir(),
        "skipped_duplicates": len(guard_result["duplicates"]),
    })


# 3. PUSH (FIFO)
@upload_bp.route("/push", methods=["POST"])
def push_video():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    index = data.get("index")

    session = _get_session(session_id)
    if not session:
        return jsonify({"error": "Sesi tidak ditemukan"}), 404
    if session["status"] != "active":
        return jsonify({"error": "Sesi tidak aktif"}), 400

    videos = _load_video_state(session_id)
    if videos is None:
        return jsonify({"error": "State video sesi tidak ditemukan"}), 400
    if index is None or index < 0 or index >= len(videos):
        return jsonify({"error": "Index video tidak valid"}), 400

    for i in range(index):
        if videos[i]["status"] != "done":
            return jsonify({"error": f"Video urutan ke-{i+1} belum selesai. Wajib urut (FIFO)."}), 400

    current = videos[index]
    if current["status"] == "done":
        return jsonify({"error": "Video ini sudah selesai"}), 400

    device = query("SELECT * FROM devices WHERE id = ?", (session["device_id"],), one=True)
    if not device:
        return jsonify({"error": "HP sesi tidak ditemukan"}), 404
    serial, connection = device_connection.active_target(device)
    if not serial:
        return jsonify({
            "error": "HP tidak online via ADB. Sambungkan Wi-Fi Debugging atau USB lalu coba lagi.",
            "connection": connection,
        }), 409
    device_connection.mark_seen(int(device["id"]), connection)

    result = adb.push_file(serial, current["path"])
    console_lines = [
        {"type": "cmd", "text": f"adb -s {serial} push {current['name']} {adb.get_hp_target_dir()}"},
    ]

    if not result["ok"]:
        console_lines.append({"type": "error", "text": f"x {result['stderr']}"})
        return jsonify({
            "ok": False, "error": result["stderr"], "console": console_lines,
            "video_status": "waiting"
        }), 502

    videos[index]["status"] = "sent"
    _save_video_state(session_id, videos)
    console_lines.append({"type": "ok", "text": f"OK 1 file pushed - {current['name']}"})

    if result.get("touch_ok"):
        console_lines.append({"type": "ok", "text": "OK Tanggal file di-update ke sekarang - biar muncul di urutan teratas Galeri"})
    elif result.get("touch_ok") is False:
        console_lines.append({
            "type": "warn",
            "text": f"! Gagal update tanggal file (tetap terkirim, tapi mungkin tidak di urutan teratas Galeri): {result.get('touch_stderr', '')}",
        })

    if result.get("media_scan_ok"):
        console_lines.append({"type": "ok", "text": "OK Media scan dikirim - file akan muncul di Galeri"})
    elif result.get("media_scan_ok") is False:
        console_lines.append({
            "type": "warn",
            "text": f"! Media scan gagal (file tetap terkirim, tapi mungkin belum muncul di Galeri): {result.get('media_scan_stderr', '')}",
        })

    return jsonify({
        "ok": True, "index": index, "video_status": "sent",
        "console": console_lines, "videos": videos,
    })


# 4. CONFIRM
@upload_bp.route("/confirm", methods=["POST"])
def confirm_video():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    index = data.get("index")

    session = _get_session(session_id)
    if not session:
        return jsonify({"error": "Sesi tidak ditemukan"}), 404
    if session["status"] != "active":
        return jsonify({"error": "Sesi tidak aktif"}), 400

    videos = _load_video_state(session_id)
    if videos is None or index is None or index < 0 or index >= len(videos):
        return jsonify({"error": "Index video tidak valid"}), 400

    current = videos[index]
    if current["status"] != "sent":
        return jsonify({"error": "Video belum terkirim ke HP. Kirim dulu sebelum konfirmasi."}), 400

    device = query("SELECT * FROM devices WHERE id = ?", (session["device_id"],), one=True)
    serial = None
    connection = None
    if device:
        serial, connection = device_connection.active_target(device)
        if serial:
            device_connection.mark_seen(int(device["id"]), connection)
    console_lines = []

    del_hp = adb.delete_file(serial, current["name"]) if serial else {
        "ok": False,
        "stderr": "HP sedang offline; file di HP tidak dapat dihapus otomatis.",
    }
    console_lines.append({"type": "cmd", "text": f"adb -s {serial} shell rm {adb.get_hp_target_dir()}{current['name']}"})
    if del_hp["ok"]:
        console_lines.append({"type": "ok", "text": f"OK Dihapus dari HP: {current['name']}"})
        if del_hp.get("mediastore_clean_ok"):
            console_lines.append({"type": "ok", "text": "OK Galeri di-refresh - file lama tidak akan nyangkut"})
        elif del_hp.get("mediastore_clean_ok") is False:
            console_lines.append({
                "type": "warn",
                "text": f"! Galeri mungkin belum ter-refresh sepenuhnya (biasanya membaik sendiri sebentar lagi): {del_hp.get('mediastore_clean_stderr', '')}",
            })
    else:
        console_lines.append({"type": "warn", "text": f"! Hapus HP: {del_hp['stderr']}"})

    del_pc = folder.delete_file(current["path"])
    if del_pc["ok"]:
        console_lines.append({"type": "ok", "text": f"OK Dihapus dari PC: {current['name']}"})
    else:
        console_lines.append({"type": "warn", "text": f"! Hapus PC: {del_pc['error']}"})

    # Tanggal batch diambil dari baris sesi (sumber tepercaya), bukan dari klien.
    batch_date = session["batch_date"] if "batch_date" in session.keys() else None
    execute(
        """INSERT INTO uploaded_videos (session_id, account_id, filename, filepath, batch_date)
           VALUES (?, ?, ?, ?, ?)""",
        (session_id, session["account_id"], current["name"], current["path"], batch_date),
    )
    console_lines.append({"type": "ok", "text": "OK Dicatat ke database"})

    videos[index]["status"] = "done"
    _save_video_state(session_id, videos)

    done_count = sum(1 for v in videos if v["status"] == "done")
    all_done = done_count == len(videos)
    # Progress terstruktur disinkronkan langsung; tidak memenuhi log aktivitas dengan 24 event per sesi.
    _request_remote_sync(session_id=session_id)

    return jsonify({
        "ok": True, "index": index, "video_status": "done",
        "console": console_lines, "videos": videos,
        "done_count": done_count, "total": len(videos), "all_done": all_done,
    })


# 5. FINISH
@upload_bp.route("/finish", methods=["POST"])
def finish_session():
    data = request.get_json() or {}
    session_id = data.get("session_id")

    session = _get_session(session_id)
    if not session:
        return jsonify({"error": "Sesi tidak ditemukan"}), 404

    videos = _load_video_state(session_id)
    if videos is None:
        return jsonify({"error": "State video sesi tidak ditemukan"}), 400

    not_done = [v["name"] for v in videos if v["status"] != "done"]
    if not_done:
        return jsonify({"error": f"Masih ada {len(not_done)} video belum selesai", "pending": not_done}), 400

    console_lines = []
    subfolder = session["subfolder"]
    folder_path = session["folder_path"]
    if subfolder and subfolder not in (".", ""):
        subfolder_path = os.path.join(folder_path, subfolder)
        if folder.path_exists(subfolder_path):
            del_sub = folder.delete_subfolder(subfolder_path)
            if del_sub["ok"]:
                console_lines.append({"type": "ok", "text": f"OK Subfolder {subfolder}/ dihapus dari PC"})
            else:
                console_lines.append({"type": "warn", "text": f"! {del_sub['error']}"})

    execute(
        "UPDATE upload_sessions SET status = 'finished', finished_at = CURRENT_TIMESTAMP WHERE id = ?",
        (session_id,),
    )

    account = query("SELECT * FROM accounts WHERE id = ?", (session["account_id"],), one=True)
    device = query("SELECT * FROM devices WHERE id = ?", (session["device_id"],), one=True)
    uploaded = query(
        "SELECT filename, uploaded_at FROM uploaded_videos WHERE session_id = ? ORDER BY id",
        (session_id,),
    )

    _clear_video_state(session_id)

    _remote_report("upload_session_completed", {
        "local_session_id": session_id,
        "account_username": account["username"] if account else "-",
        "device_name": device["name"] if device else "-",
        "video_count": len(uploaded),
        "batch_date": session.get("batch_date"),
        "status": "finished",
    })
    _request_remote_sync(session_id=session_id)

    return jsonify({
        "ok": True, "console": console_lines,
        "summary": {
            "session_id": session_id,
            "account": account["username"] if account else "-",
            "device": device["name"] if device else "-",
            "subfolder": subfolder, "video_count": len(uploaded),
            "videos": [u["filename"] for u in uploaded],
        },
    })


# 6. CANCEL
@upload_bp.route("/cancel", methods=["POST"])
def cancel_session():
    data = request.get_json() or {}
    session_id = data.get("session_id")

    session = _get_session(session_id)
    if not session:
        return jsonify({"error": "Sesi tidak ditemukan"}), 404

    videos = _load_video_state(session_id) or []
    sent_not_confirmed = [v["name"] for v in videos if v["status"] == "sent"]

    execute(
        "UPDATE upload_sessions SET status = 'cancelled', finished_at = CURRENT_TIMESTAMP WHERE id = ?",
        (session_id,),
    )
    _clear_video_state(session_id)

    account = query("SELECT username FROM accounts WHERE id = ?", (session["account_id"],), one=True)
    device = query("SELECT name FROM devices WHERE id = ?", (session["device_id"],), one=True)
    _remote_report("upload_session_cancelled", {
        "local_session_id": session_id,
        "account_username": account["username"] if account else "-",
        "device_name": device["name"] if device else "-",
        "video_count": sum(1 for video in videos if video.get("status") == "done"),
        "batch_date": session.get("batch_date"),
        "status": "cancelled",
    })
    _request_remote_sync(session_id=session_id)

    return jsonify({
        "ok": True,
        "warning": (
            f"{len(sent_not_confirmed)} video sudah terkirim ke HP tapi belum dikonfirmasi. "
            "Hapus manual dari galeri HP jika tidak jadi diupload."
            if sent_not_confirmed else None
        ),
        "sent_not_confirmed": sent_not_confirmed,
    })


# 7. STATE
@upload_bp.route("/state/<int:session_id>", methods=["GET"])
def get_state(session_id):
    session = _get_session(session_id)
    if not session:
        return jsonify({"error": "Sesi tidak ditemukan"}), 404
    videos = _load_video_state(session_id)
    return jsonify({"ok": True, "session": session, "videos": videos or []})


# 8. ACTIVE
@upload_bp.route("/active/<int:account_id>", methods=["GET"])
def get_active(account_id):
    session = query(
        "SELECT * FROM upload_sessions WHERE account_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
        (account_id,), one=True,
    )
    if not session:
        return jsonify({"ok": True, "has_active": False})
    videos = _load_video_state(session["id"])
    return jsonify({"ok": True, "has_active": True, "session": session, "videos": videos or []})


# 9. BROWSE — file picker folder
@upload_bp.route("/browse", methods=["POST"])
def browse_folder():
    data = request.get_json() or {}
    path = (data.get("path") or "").strip()
    if not path:
        path = os.path.expanduser("~")
    result = folder.list_directory(path)
    if not result["ok"]:
        return jsonify({"ok": False, "error": result.get("error")}), 404
    return jsonify(result)


# 10. REGEN CAPTION
@upload_bp.route("/regen-caption", methods=["GET"])
def regen_caption():
    return jsonify({"ok": True, "caption": caption_svc.generate_caption()})


# 11. TEMPEL CAPTION KE HP
@upload_bp.route("/paste-caption", methods=["POST"])
def paste_caption_to_phone():
    """
    Fokuskan scrcpy untuk HP pada sesi aktif lalu kirim Ctrl+V.

    Clipboard caption diisi lebih dulu oleh browser. Endpoint ini tidak membaca
    isi kolom TikTok; sukses berarti jendela scrcpy ditemukan, berhasil
    difokuskan, dan shortcut Ctrl+V berhasil dikirim oleh OS.
    """
    data = request.get_json() or {}
    session_id = data.get("session_id")
    index = data.get("index")

    try:
        session_id = int(session_id)
        index = int(index)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Session ID atau index video tidak valid"}), 400

    session = _get_session(session_id)
    if not session:
        return jsonify({"ok": False, "error": "Sesi tidak ditemukan"}), 404
    if session["status"] != "active":
        return jsonify({"ok": False, "error": "Sesi tidak aktif"}), 400

    videos = _load_video_state(session_id)
    if videos is None or index < 0 or index >= len(videos):
        return jsonify({"ok": False, "error": "Index video tidak valid"}), 400
    if videos[index].get("status") != "sent":
        return jsonify({
            "ok": False,
            "error": "Video aktif belum terkirim ke HP. Kirim video terlebih dahulu.",
        }), 400

    # Guard FIFO: index yang ditempel harus video pertama yang belum selesai.
    current_index = next(
        (i for i, video in enumerate(videos) if video.get("status") != "done"),
        -1,
    )
    if current_index != index:
        return jsonify({"ok": False, "error": "Video tidak sesuai urutan FIFO aktif"}), 409

    device = query("SELECT * FROM devices WHERE id = ?", (session["device_id"],), one=True)
    if not device:
        return jsonify({"ok": False, "error": "HP sesi tidak ditemukan"}), 404

    serial, connection = device_connection.active_target(device)
    if not serial:
        return jsonify({
            "ok": False,
            "error": "HP tidak online via ADB. Sambungkan Wi-Fi Debugging atau USB.",
            "connection": connection,
        }), 409
    device_connection.mark_seen(int(device["id"]), connection)

    result = scrcpy.paste_clipboard(
        serial=serial,
        title=device.get("name") or f"HP {device['id']}",
        focus_delay_ms=0,
    )
    if not result.get("ok"):
        return jsonify(result), 409

    return jsonify({
        "ok": True,
        "focused": bool(result.get("focused")),
        "pasted": bool(result.get("pasted")),
        "index": index,
        "error": None,
    })


# 12. REGEN SCHEDULE
@upload_bp.route("/regen-schedule", methods=["POST"])
def regen_schedule():
    data = request.get_json() or {}
    count = data.get("count")
    posting_hours = (get_setting("posting_hours") or "09:00,12:00,15:00,18:00,21:00")
    random_range = get_setting("random_range") or 15
    try:
        normalized_count = int(count)
    except (TypeError, ValueError):
        normalized_count = POSTS_PER_SESSION
    if normalized_count == POSTS_PER_SESSION:
        schedule = scheduler.generate_fixed_session_schedule(random_range)
    else:
        # Kompatibilitas sesi aktif lama yang dibuat sebelum kebijakan 24.
        schedule = scheduler.generate_schedule(
            posting_hours.split(","), random_range, count=normalized_count
        )
    return jsonify({"ok": True, "schedule": schedule})
