"""
routes/settings.py — Pengaturan aplikasi + endpoint jadwal generator
(Diperkaya penuh untuk caption template CRUD di checkpoint v1.05)
"""
from flask import Blueprint, request, jsonify, send_file
from database.db import query, execute, get_setting, set_setting, DB_PATH, BASE_DIR
from services import scheduler, caption as caption_svc, folder as folder_svc
from services.session_policy import POSTS_PER_SESSION
import os
from datetime import datetime

settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")


@settings_bp.route("/backup-db", methods=["GET"])
def backup_db():
    """Unduh file database SQLite sebagai backup."""
    if not os.path.isfile(DB_PATH):
        return jsonify({"error": "Database belum ada"}), 404
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(
        DB_PATH,
        as_attachment=True,
        download_name=f"remote_hp_backup_{stamp}.db",
        mimetype="application/x-sqlite3",
    )


@settings_bp.route("", methods=["GET"])
def get_all_settings():
    rows = query("SELECT key, value FROM settings WHERE key NOT LIKE '_session_%'")
    response = {r["key"]: r["value"] for r in rows}
    response["posts_per_session"] = POSTS_PER_SESSION
    response["schedule_mode"] = "fixed_24"
    response.setdefault("connection_mode", "wifi")
    return jsonify(response)


@settings_bp.route("", methods=["POST"])
def update_settings():
    data = request.get_json() or {}
    valid_scrcpy_modes = {"stay_awake", "stay_awake_screen_off"}
    source_result = None
    for key, value in data.items():
        if key.startswith("_session_"):
            continue
        if key in {"posts_per_session", "schedule_mode"}:
            # Read-only capability server; tidak dapat diubah oleh client.
            continue
        if key == "video_source_path":
            continue
        if key == "scrcpy_mode" and str(value) not in valid_scrcpy_modes:
            value = "stay_awake"
        if key == "connection_mode" and str(value).strip().lower() not in {"usb", "wifi"}:
            value = "wifi"
        if key == "posting_hours":
            normalized_hours = scheduler.normalize_posting_hours(value)
            if not normalized_hours:
                return jsonify({"error": "Isi minimal satu jam posting yang valid"}), 400
            value = ",".join(normalized_hours)
        if key == "random_range":
            # v1.40: komponen MM jadwal selalu dibatasi 01..15.
            value = str(scheduler.normalize_random_range(value))
        if key == "storage_path":
            value = str(value or "").strip() or BASE_DIR
            source_result = folder_svc.ensure_video_sources(value)
            if not source_result.get("ok"):
                return jsonify({"error": source_result.get("error")}), 400
        set_setting(key, str(value))
    rows = query("SELECT key, value FROM settings WHERE key NOT LIKE '_session_%'")
    response = {r["key"]: r["value"] for r in rows}
    response["posts_per_session"] = POSTS_PER_SESSION
    response["schedule_mode"] = "fixed_24"
    if source_result:
        response["video_sources"] = source_result.get("sources", [])
    return jsonify(response)


# ════════════════════════════════════════
# JADWAL GENERATOR (standalone)
# ════════════════════════════════════════
@settings_bp.route("/schedule/generate", methods=["POST"])
def generate_schedule_endpoint():
    """
    Generate jadwal acak dari input user (tidak menyimpan apa pun).
    Body: { hours: "09:00,12:00,...", range: 15, count: 5 }
    """
    data = request.get_json() or {}
    hours = data.get("hours")
    range_minutes = data.get("range", 15)
    count = data.get("count")

    # Jika hours tidak dikirim sama sekali, pakai default. Jika dikirim tapi
    # kosong/whitespace, tolak (user sengaja mengosongkan).
    if hours is None:
        hours = "09:00,12:00,15:00,18:00,21:00"

    if isinstance(hours, str):
        hours_list = [h.strip() for h in hours.split(",") if h.strip()]
    else:
        hours_list = [str(h).strip() for h in hours if str(h).strip()]

    if not hours_list:
        return jsonify({"error": "Isi minimal satu jam posting"}), 400

    schedule = scheduler.generate_schedule(hours_list, range_minutes, count=count)
    return jsonify({"ok": True, "schedule": schedule})


@settings_bp.route("/schedule/save-default", methods=["POST"])
def save_schedule_default():
    """
    Simpan jam posting & rentang sebagai default aplikasi.
    Body: { hours, range }
    """
    data = request.get_json() or {}
    hours = data.get("hours")
    range_minutes = data.get("range")

    if hours is not None:
        normalized_hours = scheduler.normalize_posting_hours(hours)
        if not normalized_hours:
            return jsonify({"error": "Isi minimal satu jam posting yang valid"}), 400
        set_setting("posting_hours", ",".join(normalized_hours))
    if range_minutes is not None:
        set_setting("random_range", str(scheduler.normalize_random_range(range_minutes)))

    return jsonify(
        {
            "ok": True,
            "posting_hours": get_setting("posting_hours"),
            "random_range": get_setting("random_range"),
        }
    )


# ════════════════════════════════════════
# TEMPLATE CAPTION (CRUD) — v1.1.8
# ════════════════════════════════════════
@settings_bp.route("/captions", methods=["GET"])
def list_captions():
    """Semua template caption (aktif & nonaktif) untuk halaman Pengaturan."""
    return jsonify({"ok": True, "templates": caption_svc.list_templates()})


@settings_bp.route("/captions/check", methods=["POST"])
def check_caption():
    """
    Cek apakah teks caption mengandung kata/frasa berisiko (over-claim, klaim
    hasil, ajakan checkout). Hanya untuk PERINGATAN — tidak menyimpan apa pun.
    Body: { content, hashtags? }
    """
    data = request.get_json() or {}
    text = (data.get("content") or "")
    if data.get("hashtags"):
        text = text + " " + str(data.get("hashtags"))
    return jsonify({"ok": True, "check": caption_svc.flag_risky_caption(text)})


@settings_bp.route("/captions", methods=["POST"])
def create_caption():
    """
    Tambah template caption baru.
    Body: { content, hashtags?, is_active? }
    Respons menyertakan hasil pemeriksaan risiko (untuk ditampilkan sbg warning).
    """
    data = request.get_json() or {}
    content = (data.get("content") or "").strip()
    hashtags = (data.get("hashtags") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "Isi caption tidak boleh kosong."}), 400

    is_active = 1 if data.get("is_active", True) else 0
    new_id = execute(
        "INSERT INTO caption_templates (content, hashtags, is_active) VALUES (?, ?, ?)",
        (content, hashtags, is_active),
    )
    tpl = query("SELECT * FROM caption_templates WHERE id = ?", (new_id,), one=True)
    check = caption_svc.flag_risky_caption(content + " " + hashtags)
    return jsonify({"ok": True, "template": tpl, "check": check}), 201


@settings_bp.route("/captions/<int:tpl_id>", methods=["PUT"])
def update_caption(tpl_id):
    """Ubah 1 template caption. Body: { content?, hashtags?, is_active? }"""
    data = request.get_json() or {}
    tpl = query("SELECT * FROM caption_templates WHERE id = ?", (tpl_id,), one=True)
    if not tpl:
        return jsonify({"ok": False, "error": "Template tidak ditemukan."}), 404

    content = data.get("content", tpl["content"])
    hashtags = data.get("hashtags", tpl["hashtags"])
    is_active = tpl["is_active"]
    if "is_active" in data:
        is_active = 1 if data.get("is_active") else 0

    if content is not None and not str(content).strip():
        return jsonify({"ok": False, "error": "Isi caption tidak boleh kosong."}), 400

    execute(
        "UPDATE caption_templates SET content = ?, hashtags = ?, is_active = ? WHERE id = ?",
        (str(content).strip(), str(hashtags or "").strip(), is_active, tpl_id),
    )
    updated = query("SELECT * FROM caption_templates WHERE id = ?", (tpl_id,), one=True)
    check = caption_svc.flag_risky_caption(
        (updated["content"] or "") + " " + (updated["hashtags"] or "")
    )
    return jsonify({"ok": True, "template": updated, "check": check})


@settings_bp.route("/captions/<int:tpl_id>", methods=["DELETE"])
def delete_caption(tpl_id):
    """Hapus 1 template caption."""
    tpl = query("SELECT * FROM caption_templates WHERE id = ?", (tpl_id,), one=True)
    if not tpl:
        return jsonify({"ok": False, "error": "Template tidak ditemukan."}), 404
    execute("DELETE FROM caption_templates WHERE id = ?", (tpl_id,))
    return jsonify({"ok": True})


# Batas wajar untuk unggah file caption (mencegah file raksasa).
_MAX_CAPTION_FILE_BYTES = 1 * 1024 * 1024  # 1 MB
_MAX_CAPTIONS_PER_UPLOAD = 1000


@settings_bp.route("/captions/upload", methods=["POST"])
def upload_captions():
    """
    Unggah banyak caption sekaligus dari file .md / .txt (atau teks tempel).

    Body JSON: {
      "text": "<isi file>",            # WAJIB — isi mentah file
      "mode": "append" | "replace",    # append (default) = tambah; replace = ganti semua
    }

    Format file diurai oleh caption_svc.parse_caption_file() (tiap caption
    dipisah baris kosong; baris berawalan '#' = hashtag). Mengembalikan
    ringkasan: berapa caption ditambahkan, dilewati, dan berapa yang
    ter-flag berpotensi berisiko (over-claim) sebagai PERINGATAN saja.
    """
    data = request.get_json() or {}
    text = data.get("text", "")
    mode = (data.get("mode") or "append").strip().lower()
    if mode not in ("append", "replace"):
        mode = "append"

    if not isinstance(text, str) or not text.strip():
        return jsonify({"ok": False, "error": "File/teks kosong. Tidak ada yang diunggah."}), 400
    if len(text.encode("utf-8")) > _MAX_CAPTION_FILE_BYTES:
        return jsonify({"ok": False, "error": "Ukuran file terlalu besar (maksimal 1 MB)."}), 400

    parsed = caption_svc.parse_caption_file(text)
    captions = parsed["captions"]
    if not captions:
        return jsonify({
            "ok": False,
            "error": "Tidak ada caption yang terbaca dari file. Pastikan tiap caption dipisah baris kosong.",
        }), 400
    if len(captions) > _MAX_CAPTIONS_PER_UPLOAD:
        return jsonify({
            "ok": False,
            "error": f"Terlalu banyak caption dalam 1 file (maks {_MAX_CAPTIONS_PER_UPLOAD}).",
        }), 400

    # Mode replace: kosongkan dulu semua template lama.
    replaced_count = 0
    if mode == "replace":
        old = query("SELECT COUNT(*) AS n FROM caption_templates", one=True)
        replaced_count = old["n"] if old else 0
        execute("DELETE FROM caption_templates")

    added = 0
    risky_count = 0
    for c in captions:
        execute(
            "INSERT INTO caption_templates (content, hashtags, is_active) VALUES (?, ?, 1)",
            (c["content"], c["hashtags"]),
        )
        added += 1
        if caption_svc.flag_risky_caption(c["content"] + " " + c["hashtags"])["risky"]:
            risky_count += 1

    return jsonify({
        "ok": True,
        "mode": mode,
        "added": added,
        "skipped_empty": parsed["skipped_empty"],
        "replaced": replaced_count,
        "risky_count": risky_count,
        "total_now": (query("SELECT COUNT(*) AS n FROM caption_templates", one=True) or {}).get("n", added),
    })


@settings_bp.route("/captions/all", methods=["DELETE"])
def delete_all_captions():
    """Hapus SEMUA template caption (dipakai tombol 'Hapus Semua' di UI)."""
    old = query("SELECT COUNT(*) AS n FROM caption_templates", one=True)
    count = old["n"] if old else 0
    execute("DELETE FROM caption_templates")
    return jsonify({"ok": True, "deleted": count})
