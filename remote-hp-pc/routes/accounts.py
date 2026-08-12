"""
routes/accounts.py — CRUD Akun TikTok (accounts) + Penempatan HP (placements)

v1.46 — AKUN LINTAS-HP:
Fakta lapangan: satu akun TikTok (mis. "anisa.567") kerap dipakai bergantian
di beberapa HP fisik yang berbeda (HP-1, HP-2, HP-3, ...) — bukan cuma
pindah permanen, tapi BISA ada di beberapa HP SEKALIGUS di saat yang sama.
Riwayat/histori upload akun itu harus tetap satu & utuh, tidak peduli sedang
diproses dari HP mana.

Struktur data (berubah total dari v1.1.7):
    accounts             : SATU baris = SATU identitas akun (kunci: username,
                            case-insensitive unik). Tidak lagi punya device_id.
    account_placements   : tabel penghubung many-to-many. Satu baris = "akun
                            X ditempatkan di HP Y, memakai slot aplikasi Z".
                            Satu akun boleh punya banyak placement (banyak
                            HP), satu HP boleh menampung banyak placement
                            (banyak akun). app_slot BOLEH BEDA per placement
                            (mis. anisa.567 pakai 'original' di HP-1 tapi
                            'kloning' di HP-2).

Aturan yang ditegakkan endpoint ini:
- app_slot wajib salah satu dari APP_SLOTS ('original' / 'kloning').
- Maksimal MAX_ACCOUNTS_PER_SLOT (8) placement per slot per HP (bukan per
  akun — akun yang sama dihitung lagi di tiap HP tempat ia ditempatkan).
- Username akun unik case-insensitive di seluruh sistem (1 username = 1
  akun). Menambah akun dengan username yang sudah ada akan MENAMBAH
  PLACEMENT BARU ke akun yang sudah ada itu (bukan membuat akun duplikat) —
  lihat create_account().
- Menghapus 1 placement (lewat DELETE /api/accounts/<id>/placements/<hp_id>)
  hanya melepas akun dari HP tsb; akun & seluruh riwayat/sesinya (menempel ke
  account_id yang stabil) tetap utuh selama masih ada placement lain, atau
  bahkan bila sudah tidak ada placement sama sekali.
"""
from flask import Blueprint, request, jsonify, current_app
from database.db import query, execute

accounts_bp = Blueprint("accounts", __name__, url_prefix="/api/accounts")


@accounts_bp.after_request
def _schedule_remote_sync_after_mutation(response):
    if request.method in {"POST", "PUT", "DELETE"} and response.status_code < 400:
        client = current_app.extensions.get("remote_server_client")
        if client is not None:
            client.request_data_sync()
    return response

# ── Konstanta slot aplikasi (dipakai juga oleh routes lain & frontend) ──
APP_SLOTS = ("original", "kloning")
APP_SLOT_LABELS = {
    "original": "Apk Original",
    "kloning": "Apk Kloning",
}
MAX_ACCOUNTS_PER_SLOT = 8
MAX_ACCOUNTS_PER_DEVICE = MAX_ACCOUNTS_PER_SLOT * len(APP_SLOTS)  # = 16

# Urutan tampil: original dulu, lalu kloning
_SLOT_ORDER_SQL = "CASE p.app_slot WHEN 'original' THEN 0 ELSE 1 END"


def _normalize_slot(value, default=None):
    """
    Normalisasi input app_slot dari request.
    Return slot valid, atau None jika tidak valid (dan default None).
    Beberapa ejaan umum diterima supaya API ramah dipakai manual.
    """
    if value is None or str(value).strip() == "":
        return default
    v = str(value).strip().lower()
    aliases = {
        "original": "original",
        "asli": "original",
        "utama": "original",
        "kloning": "kloning",
        "cloning": "kloning",
        "clone": "kloning",
        "klon": "kloning",
        "ganda": "kloning",
    }
    return aliases.get(v)


def _slot_count(device_id, app_slot, exclude_placement_id=None):
    """Jumlah PLACEMENT pada satu slot di satu HP (opsional: kecualikan 1 placement)."""
    if exclude_placement_id:
        row = query(
            "SELECT COUNT(*) AS c FROM account_placements WHERE device_id = ? AND app_slot = ? AND id != ?",
            (device_id, app_slot, exclude_placement_id),
            one=True,
        )
    else:
        row = query(
            "SELECT COUNT(*) AS c FROM account_placements WHERE device_id = ? AND app_slot = ?",
            (device_id, app_slot),
            one=True,
        )
    return row["c"] if row else 0


def _slot_full_error(app_slot):
    label = APP_SLOT_LABELS.get(app_slot, app_slot)
    return (
        f"{label} di HP ini sudah penuh "
        f"({MAX_ACCOUNTS_PER_SLOT}/{MAX_ACCOUNTS_PER_SLOT} akun). "
        f"Gunakan slot aplikasi satunya, atau hapus akun lama terlebih dahulu."
    )


def _account_with_placements(account_id):
    """Ambil 1 akun beserta seluruh placement-nya (list HP tempat ia ditempatkan)."""
    account = query(
        """
        SELECT a.*,
               (SELECT COUNT(*) FROM uploaded_videos uv WHERE uv.account_id = a.id) AS upload_count
        FROM accounts a WHERE a.id = ?
        """,
        (account_id,), one=True,
    )
    if not account:
        return None
    placements = query(
        """
        SELECT p.id AS placement_id, p.device_id, p.app_slot, p.created_at,
               d.name AS device_name, d.label AS device_label
        FROM account_placements p
        LEFT JOIN devices d ON d.id = p.device_id
        WHERE p.account_id = ?
        ORDER BY p.device_id
        """,
        (account_id,),
    )
    account["placements"] = placements
    return account


@accounts_bp.route("/slots", methods=["GET"])
def slot_info():
    """Info konstanta slot (untuk frontend / integrasi)."""
    return jsonify(
        {
            "slots": list(APP_SLOTS),
            "labels": APP_SLOT_LABELS,
            "max_per_slot": MAX_ACCOUNTS_PER_SLOT,
            "max_per_device": MAX_ACCOUNTS_PER_DEVICE,
        }
    )


@accounts_bp.route("", methods=["GET"])
def list_accounts():
    """
    List akun. Bisa filter by device_id dan/atau app_slot via query param —
    filter ini kini berbasis JOIN ke account_placements (v1.46), karena akun
    tidak lagi punya device_id langsung.

    Setiap baris hasil merepresentasikan SATU PLACEMENT (akun @ HP tertentu),
    supaya kompatibel dengan sidebar lama yang menampilkan akun terkelompok
    per HP. Field placement_id & device_id disertakan; akun yang sama akan
    muncul lagi di baris lain bila ditempatkan juga di HP lain.

    Bila device_id TIDAK dikirim, mengembalikan SEMUA placement dari SEMUA
    HP (dipakai untuk pencarian akun lintas-HP / validasi username unik).
    """
    device_id = request.args.get("device_id")
    app_slot = _normalize_slot(request.args.get("app_slot"))

    sql = f"""
        SELECT a.id, a.username, a.email, a.password, a.phone, a.notes, a.created_at,
               p.id AS placement_id, p.device_id, p.app_slot,
               (SELECT COUNT(*) FROM uploaded_videos uv WHERE uv.account_id = a.id) AS upload_count,
               (SELECT COUNT(*) FROM account_placements p2 WHERE p2.account_id = a.id) AS placement_count
        FROM account_placements p
        JOIN accounts a ON a.id = p.account_id
        WHERE 1 = 1
    """
    params = []
    if device_id:
        sql += " AND p.device_id = ?"
        params.append(device_id)
    if app_slot:
        sql += " AND p.app_slot = ?"
        params.append(app_slot)
    sql += f" ORDER BY {_SLOT_ORDER_SQL}, a.id ASC"

    rows = query(sql, tuple(params))
    for r in rows:
        # v1.46: penanda ringan untuk UI — akun ditempatkan di lebih dari 1 HP.
        r["_multi_hp"] = (r.get("placement_count") or 0) > 1
    return jsonify(rows)


@accounts_bp.route("/<int:account_id>", methods=["GET"])
def get_account(account_id):
    account = _account_with_placements(account_id)
    if not account:
        return jsonify({"error": "Akun tidak ditemukan"}), 404
    return jsonify(account)


@accounts_bp.route("", methods=["POST"])
def create_account():
    """
    Tambah akun BARU, atau TEMPATKAN akun yang SUDAH ADA (username sama,
    case-insensitive) ke sebuah HP baru (v1.46 — akun lintas-HP).

    Body: { device_id, app_slot, username, email?, password?, phone?, notes? }

    Alur:
      1. Cari akun dengan username sama (case-insensitive) di sistem.
      2. Jika BELUM ada akun tsb → buat akun baru + 1 placement di HP ini.
      3. Jika SUDAH ada akun tsb:
         a. Jika sudah punya placement di HP INI JUGA → tolak (409), akun ini
            sudah ada di HP ini, tidak perlu ditambah lagi.
         b. Jika belum punya placement di HP ini (tapi ada di HP lain) →
            LANGSUNG tambahkan placement baru di HP ini (akun kini ada di
            beberapa HP sekaligus). Tidak perlu konfirmasi tambahan karena
            ini memang perilaku yang diinginkan: 1 akun, banyak HP.
    """
    data = request.get_json() or {}
    device_id = data.get("device_id")
    username = (data.get("username") or "").strip()
    if not device_id:
        return jsonify({"error": "device_id wajib diisi"}), 400
    if not username:
        return jsonify({"error": "Username wajib diisi"}), 400

    app_slot = _normalize_slot(data.get("app_slot"), default="original")
    if app_slot not in APP_SLOTS:
        return jsonify(
            {"error": "Slot aplikasi tidak valid. Pilih 'original' atau 'kloning'."}
        ), 400

    device = query("SELECT id, name FROM devices WHERE id = ?", (device_id,), one=True)
    if not device:
        return jsonify({"error": "HP tidak ditemukan"}), 404

    if _slot_count(device_id, app_slot) >= MAX_ACCOUNTS_PER_SLOT:
        return jsonify({"error": _slot_full_error(app_slot)}), 400

    existing = query(
        "SELECT * FROM accounts WHERE LOWER(username) = LOWER(?)",
        (username,), one=True,
    )

    if existing:
        account_id = existing["id"]
        already_here = query(
            "SELECT id FROM account_placements WHERE account_id = ? AND device_id = ?",
            (account_id, device_id), one=True,
        )
        if already_here:
            return jsonify({
                "error": f"Akun '{existing['username']}' sudah ada di HP ini.",
            }), 409

        # Akun sudah ada (di HP lain) — tambahkan PLACEMENT BARU di HP ini.
        # Akun kini ditempatkan di lebih dari satu HP sekaligus.
        execute(
            "INSERT INTO account_placements (account_id, device_id, app_slot) VALUES (?, ?, ?)",
            (account_id, device_id, app_slot),
        )
        # Data profil (email/password/phone/notes) opsional diperbarui bila
        # dikirim & sebelumnya kosong — tidak menimpa data yang sudah terisi
        # tanpa sengaja, karena field ini milik akun, bukan milik placement.
        updates = {}
        for field in ("email", "password", "phone", "notes"):
            new_val = data.get(field)
            if new_val and not (existing.get(field) or "").strip():
                updates[field] = new_val
        if updates:
            execute(
                "UPDATE accounts SET email = ?, password = ?, phone = ?, notes = ? WHERE id = ?",
                (
                    updates.get("email", existing.get("email") or ""),
                    updates.get("password", existing.get("password") or ""),
                    updates.get("phone", existing.get("phone") or ""),
                    updates.get("notes", existing.get("notes") or ""),
                    account_id,
                ),
            )
        account = _account_with_placements(account_id)
        account["_placed_on_existing_account"] = True  # penanda untuk toast UI
        return jsonify(account), 201

    # Akun baru sepenuhnya: buat identitas akun + 1 placement pertama.
    new_id = execute(
        """INSERT INTO accounts (username, email, password, phone, notes)
           VALUES (?, ?, ?, ?, ?)""",
        (
            username,
            data.get("email", ""),
            data.get("password", ""),
            data.get("phone", ""),
            data.get("notes", ""),
        ),
    )
    execute(
        "INSERT INTO account_placements (account_id, device_id, app_slot) VALUES (?, ?, ?)",
        (new_id, device_id, app_slot),
    )
    account = _account_with_placements(new_id)
    return jsonify(account), 201


@accounts_bp.route("/<int:account_id>", methods=["PUT"])
def update_account(account_id):
    """
    Perbarui data profil akun (username/email/password/phone/notes).
    v1.46: TIDAK lagi menangani app_slot/device_id di sini — pindah/atur slot
    kini lewat endpoint placement (PUT /api/accounts/<id>/placements/<device_id>).
    """
    data = request.get_json() or {}
    account = query("SELECT * FROM accounts WHERE id = ?", (account_id,), one=True)
    if not account:
        return jsonify({"error": "Akun tidak ditemukan"}), 404

    # Cegah rename yang menabrak username akun lain (akan menciptakan 2
    # identitas akun berbeda dengan nama sama, merusak jaminan "1 akun = 1
    # riwayat" yang jadi dasar fitur akun lintas-HP).
    new_username = (data.get("username", account["username"]) or "").strip()
    if new_username and new_username.lower() != (account["username"] or "").lower():
        clash = query(
            "SELECT id, username FROM accounts WHERE LOWER(username) = LOWER(?) AND id != ?",
            (new_username, account_id), one=True,
        )
        if clash:
            return jsonify({
                "error": f"Username '{clash['username']}' sudah dipakai akun lain. Gunakan nama lain."
            }), 409

    execute(
        """UPDATE accounts
           SET username = ?, email = ?, password = ?, phone = ?, notes = ?
           WHERE id = ?""",
        (
            new_username or account["username"],
            data.get("email", account["email"]),
            data.get("password", account["password"]),
            data.get("phone", account["phone"]),
            data.get("notes", account["notes"]),
            account_id,
        ),
    )
    updated = _account_with_placements(account_id)
    return jsonify(updated)


@accounts_bp.route("/<int:account_id>", methods=["DELETE"])
def delete_account(account_id):
    """
    Hapus akun SEPENUHNYA dari sistem (semua placement, riwayat, & video
    ikut terhapus lewat ON DELETE CASCADE). Gunakan endpoint placement di
    bawah untuk sekadar melepas akun dari 1 HP saja tanpa menghapus akun.
    """
    account = query("SELECT * FROM accounts WHERE id = ?", (account_id,), one=True)
    if not account:
        return jsonify({"error": "Akun tidak ditemukan"}), 404
    execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    return jsonify({"ok": True})


# ════════════════════════════════════════
# PLACEMENT — kelola penempatan akun per HP (v1.46)
# ════════════════════════════════════════


@accounts_bp.route("/<int:account_id>/placements", methods=["POST"])
def add_placement(account_id):
    """
    Tempatkan akun yang SUDAH ADA ke HP tambahan.
    Body: { device_id, app_slot }
    (Setara dengan create_account() saat username sudah ada — endpoint ini
    disediakan sebagai jalan pintas eksplisit dari UI akun yang sedang dibuka.)
    """
    account = query("SELECT * FROM accounts WHERE id = ?", (account_id,), one=True)
    if not account:
        return jsonify({"error": "Akun tidak ditemukan"}), 404

    data = request.get_json() or {}
    device_id = data.get("device_id")
    if not device_id:
        return jsonify({"error": "device_id wajib diisi"}), 400
    app_slot = _normalize_slot(data.get("app_slot"), default="original")
    if app_slot not in APP_SLOTS:
        return jsonify({"error": "Slot aplikasi tidak valid."}), 400

    device = query("SELECT id FROM devices WHERE id = ?", (device_id,), one=True)
    if not device:
        return jsonify({"error": "HP tidak ditemukan"}), 404

    already = query(
        "SELECT id FROM account_placements WHERE account_id = ? AND device_id = ?",
        (account_id, device_id), one=True,
    )
    if already:
        return jsonify({"error": "Akun ini sudah ada di HP tersebut."}), 409

    if _slot_count(device_id, app_slot) >= MAX_ACCOUNTS_PER_SLOT:
        return jsonify({"error": _slot_full_error(app_slot)}), 400

    execute(
        "INSERT INTO account_placements (account_id, device_id, app_slot) VALUES (?, ?, ?)",
        (account_id, device_id, app_slot),
    )
    return jsonify(_account_with_placements(account_id)), 201


@accounts_bp.route("/<int:account_id>/placements/<int:device_id>", methods=["PUT"])
def update_placement(account_id, device_id):
    """Ubah slot aplikasi (original/kloning) akun ini KHUSUS di HP tersebut."""
    placement = query(
        "SELECT * FROM account_placements WHERE account_id = ? AND device_id = ?",
        (account_id, device_id), one=True,
    )
    if not placement:
        return jsonify({"error": "Akun ini tidak ditempatkan di HP tersebut."}), 404

    data = request.get_json() or {}
    new_slot = _normalize_slot(data.get("app_slot"), default=placement["app_slot"])
    if new_slot not in APP_SLOTS:
        return jsonify({"error": "Slot aplikasi tidak valid."}), 400

    if new_slot != placement["app_slot"]:
        used = _slot_count(device_id, new_slot, exclude_placement_id=placement["id"])
        if used >= MAX_ACCOUNTS_PER_SLOT:
            return jsonify({"error": _slot_full_error(new_slot)}), 400

    execute(
        "UPDATE account_placements SET app_slot = ? WHERE id = ?",
        (new_slot, placement["id"]),
    )
    return jsonify(_account_with_placements(account_id))


@accounts_bp.route("/<int:account_id>/placements/<int:device_id>", methods=["DELETE"])
def remove_placement(account_id, device_id):
    """
    Lepas akun dari SATU HP saja. Akun & seluruh riwayat/sesinya TETAP UTUH
    (menempel ke account_id yang tidak berubah) selama masih ada placement
    lain — atau bahkan bila ini placement terakhir (akun jadi "tanpa HP",
    riwayatnya tetap bisa dilihat, tinggal ditempatkan lagi kapan pun).
    """
    placement = query(
        "SELECT * FROM account_placements WHERE account_id = ? AND device_id = ?",
        (account_id, device_id), one=True,
    )
    if not placement:
        return jsonify({"error": "Akun ini tidak ditempatkan di HP tersebut."}), 404

    execute("DELETE FROM account_placements WHERE id = ?", (placement["id"],))

    remaining = query(
        "SELECT COUNT(*) AS c FROM account_placements WHERE account_id = ?",
        (account_id,), one=True,
    )["c"]
    return jsonify({"ok": True, "remaining_placements": remaining})
