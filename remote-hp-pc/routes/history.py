"""
routes/history.py — Riwayat upload

Endpoint:
- GET /api/history             : list sesi (filter: device_id, account_id, date)
- GET /api/history/<id>        : detail 1 sesi + daftar video
- GET /api/history/recent      : riwayat terbaru (untuk panel kanan Upload)
- GET /api/history/stats       : statistik hari ini (dinamis)
"""
from flask import Blueprint, request, jsonify, current_app
from database.db import query

history_bp = Blueprint("history", __name__, url_prefix="/api/history")


@history_bp.after_request
def _schedule_remote_sync_after_history_change(response):
    if request.method == "DELETE" and response.status_code < 400:
        client = current_app.extensions.get("remote_server_client")
        if client is not None:
            client.request_data_sync(force=True)
    return response


@history_bp.route("", methods=["GET"])
def list_history():
    """
    List sesi upload yang sudah selesai/dibatalkan.
    Filter opsional via query param: device_id, account_id, date (YYYY-MM-DD).
    """
    device_id = request.args.get("device_id")
    account_id = request.args.get("account_id")
    app_slot = (request.args.get("app_slot") or "").strip().lower()
    date = request.args.get("date")

    sql = """
        SELECT s.*,
               a.username AS account_username,
               p.app_slot AS account_app_slot,
               d.name AS device_name,
               d.label AS device_label,
               (SELECT COUNT(*) FROM uploaded_videos uv WHERE uv.session_id = s.id) AS video_count
        FROM upload_sessions s
        LEFT JOIN accounts a ON a.id = s.account_id
        LEFT JOIN devices d  ON d.id = s.device_id
        LEFT JOIN account_placements p ON p.account_id = s.account_id AND p.device_id = s.device_id
        WHERE s.status IN ('finished', 'cancelled')
    """
    params = []

    if device_id:
        sql += " AND s.device_id = ?"
        params.append(device_id)
    if account_id:
        sql += " AND s.account_id = ?"
        params.append(account_id)
    if app_slot in ("original", "kloning"):
        # v1.1.7: filter berdasarkan slot aplikasi (original / kloning) —
        # v1.46: slot kini berasal dari account_placements pada HP sesi itu.
        sql += " AND p.app_slot = ?"
        params.append(app_slot)
    if date:
        # cocokkan tanggal pada finished_at (atau started_at jika belum ada)
        sql += " AND DATE(COALESCE(s.finished_at, s.started_at)) = ?"
        params.append(date)

    sql += " ORDER BY COALESCE(s.finished_at, s.started_at) DESC, s.id DESC"

    sessions = query(sql, tuple(params))
    return jsonify({"ok": True, "sessions": sessions, "count": len(sessions)})


@history_bp.route("/<int:session_id>", methods=["GET"])
def session_detail(session_id):
    """Detail 1 sesi + daftar video yang diupload."""
    session = query(
        """
        SELECT s.*,
               a.username AS account_username,
               a.email AS account_email,
               p.app_slot AS account_app_slot,
               d.name AS device_name,
               d.serial AS device_serial
        FROM upload_sessions s
        LEFT JOIN accounts a ON a.id = s.account_id
        LEFT JOIN devices d  ON d.id = s.device_id
        LEFT JOIN account_placements p ON p.account_id = s.account_id AND p.device_id = s.device_id
        WHERE s.id = ?
        """,
        (session_id,),
        one=True,
    )
    if not session:
        return jsonify({"error": "Sesi tidak ditemukan"}), 404

    videos = query(
        "SELECT * FROM uploaded_videos WHERE session_id = ? ORDER BY id",
        (session_id,),
    )
    return jsonify({"ok": True, "session": session, "videos": videos})


@history_bp.route("/recent", methods=["GET"])
def recent_history():
    """
    Riwayat terbaru (untuk panel kanan halaman Upload).
    Default 5 sesi terakhir yang finished.
    """
    limit = request.args.get("limit", 5)
    try:
        limit = int(limit)
    except (ValueError, TypeError):
        limit = 5

    sessions = query(
        """
        SELECT s.*,
               a.username AS account_username,
               p.app_slot AS account_app_slot,
               d.name AS device_name,
               (SELECT COUNT(*) FROM uploaded_videos uv WHERE uv.session_id = s.id) AS video_count
        FROM upload_sessions s
        LEFT JOIN accounts a ON a.id = s.account_id
        LEFT JOIN devices d  ON d.id = s.device_id
        LEFT JOIN account_placements p ON p.account_id = s.account_id AND p.device_id = s.device_id
        WHERE s.status = 'finished'
        ORDER BY s.finished_at DESC, s.id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return jsonify({"ok": True, "sessions": sessions})


@history_bp.route("/uploaded-dates", methods=["GET"])
def uploaded_dates():
    """
    Daftar tanggal (batch_date) di mana SEBUAH akun sudah punya video
    terupload — dipakai untuk menandai kalender (hijau) di panel Upload,
    supaya user tahu akun itu SUDAH pernah upload di tanggal tsb & bisa
    menghindari double upload.

    Query param WAJIB: account_id
    Return: { ok, account_id, dates: ["YYYY-MM-DD", ...], counts: {date: n} }

    Catatan: ini murni PENANDA VISUAL, bukan pemblokir. User tetap boleh
    memilih tanggal yang sudah hijau & upload lagi (mis. setelah menghapus
    jadwal yang salah lalu upload ulang).
    """
    account_id = request.args.get("account_id", type=int)
    if not account_id:
        return jsonify({"ok": False, "error": "account_id wajib diisi.", "dates": []}), 400

    # Ambil tanggal batch unik dari video yang sudah terupload untuk akun ini,
    # beserta jumlah video per tanggal (informasi tambahan untuk tooltip).
    rows = query(
        """
        SELECT batch_date, COUNT(*) AS n
        FROM uploaded_videos
        WHERE account_id = ? AND batch_date IS NOT NULL AND batch_date <> ''
        GROUP BY batch_date
        ORDER BY batch_date
        """,
        (account_id,),
    )

    dates = [r["batch_date"] for r in rows]
    counts = {r["batch_date"]: r["n"] for r in rows}
    return jsonify({"ok": True, "account_id": account_id, "dates": dates, "counts": counts})


@history_bp.route("/uploaded-dates", methods=["DELETE"])
def clear_uploaded_date():
    """
    Hapus CATATAN histori upload sebuah akun pada SATU tanggal tertentu.
    Dipakai saat user membatalkan jadwal (mis. salah upload untuk besok) &
    ingin menghilangkan penanda hijau supaya tanggal itu 'bersih' lagi.

    PENTING: ini hanya menghapus CATATAN di database aplikasi (uploaded_videos
    & sesi terkait pada tanggal itu untuk akun tsb) — TIDAK menyentuh apa pun
    di HP atau di TikTok Studio. Penjadwalan di TikTok Studio tetap perlu
    dibatalkan sendiri oleh user di aplikasi TikTok.

    Body JSON: { account_id, date }  (date = "YYYY-MM-DD")
    Return: { ok, deleted_videos, deleted_sessions }
    """
    data = request.get_json() or {}
    account_id = data.get("account_id")
    date = (data.get("date") or "").strip()
    if not account_id or not date:
        return jsonify({"ok": False, "error": "account_id & date wajib diisi."}), 400

    from database.db import execute
    # Hitung dulu untuk info balikan
    vids = query(
        "SELECT COUNT(*) AS n FROM uploaded_videos WHERE account_id = ? AND batch_date = ?",
        (account_id, date), one=True,
    )
    sess = query(
        "SELECT COUNT(*) AS n FROM upload_sessions WHERE account_id = ? AND batch_date = ?",
        (account_id, date), one=True,
    )
    deleted_videos = vids["n"] if vids else 0
    deleted_sessions = sess["n"] if sess else 0

    # Hapus video pada tanggal itu, lalu sesi pada tanggal itu (untuk akun ini).
    execute(
        "DELETE FROM uploaded_videos WHERE account_id = ? AND batch_date = ?",
        (account_id, date),
    )
    execute(
        "DELETE FROM upload_sessions WHERE account_id = ? AND batch_date = ?",
        (account_id, date),
    )

    return jsonify({
        "ok": True,
        "deleted_videos": deleted_videos,
        "deleted_sessions": deleted_sessions,
    })


@history_bp.route("/stats", methods=["GET"])
def stats():
    """
    Statistik hari ini (dinamis):
    - upload_today: jumlah video diupload hari ini
    - accounts_done_today: jumlah akun yang menyelesaikan sesi hari ini
    - active_sessions: jumlah sesi yang sedang aktif
    - total_uploads: total video sepanjang waktu
    """
    upload_today = query(
        "SELECT COUNT(*) AS c FROM uploaded_videos WHERE DATE(uploaded_at) = DATE('now', 'localtime')",
        one=True,
    )["c"]

    accounts_done_today = query(
        """
        SELECT COUNT(DISTINCT account_id) AS c FROM upload_sessions
        WHERE status = 'finished' AND DATE(finished_at) = DATE('now', 'localtime')
        """,
        one=True,
    )["c"]

    active_sessions = query(
        "SELECT COUNT(*) AS c FROM upload_sessions WHERE status = 'active'",
        one=True,
    )["c"]

    total_uploads = query(
        "SELECT COUNT(*) AS c FROM uploaded_videos", one=True
    )["c"]

    return jsonify(
        {
            "ok": True,
            "upload_today": upload_today,
            "accounts_done_today": accounts_done_today,
            "active_sessions": active_sessions,
            "total_uploads": total_uploads,
        }
    )
