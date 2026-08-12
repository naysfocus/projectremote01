"""
database/db.py — Koneksi & inisialisasi SQLite untuk Remote HP
"""
import os
import sqlite3
import uuid
from contextlib import contextmanager

# Lokasi file database (di root project)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "remote_hp.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def get_db():
    """Buka koneksi baru ke database. Row sebagai dict-like (sqlite3.Row)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql, params=(), one=False):
    """Helper SELECT. Mengembalikan list dict (atau 1 dict jika one=True)."""
    conn = get_db()
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    result = [dict(r) for r in rows]
    if one:
        return result[0] if result else None
    return result


def execute(sql, params=()):
    """Helper INSERT/UPDATE/DELETE. Mengembalikan lastrowid."""
    conn = get_db()
    cur = conn.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id



@contextmanager
def transaction(immediate=False):
    """Transactional SQLite connection used by security-sensitive pairing flows."""
    conn = get_db()
    try:
        if immediate:
            conn.execute("BEGIN IMMEDIATE")
        else:
            conn.execute("BEGIN")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Buat semua tabel jika belum ada, lalu seed data default.

    Urutan penting:
      1) _migrate() — tambah kolom baru pada tabel LAMA lebih dulu, supaya
         index di schema.sql yang mereferensikan kolom baru (mis. batch_date)
         tidak gagal saat dijalankan pada DB v1.1.3.
      2) jalankan schema.sql (CREATE TABLE/INDEX IF NOT EXISTS) — aman untuk DB
         baru maupun lama yang sudah dimigrasi.
      3) seed data default.
    """
    _migrate()  # aman walau tabel belum ada (dilewati bila belum ada)
    conn = get_db()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    _seed_defaults()


def _table_exists(conn, table):
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None


def _column_exists(conn, table, column):
    """Cek apakah sebuah kolom sudah ada di tabel (untuk migrasi aman)."""
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def _migrate():
    """
    Migrasi ringan untuk DB lama.

    `CREATE TABLE IF NOT EXISTS` tidak menambah kolom pada tabel yang sudah ada,
    jadi kolom baru ditambahkan manual bila tabelnya ada tapi kolomnya belum.
    Bila tabel belum ada sama sekali (DB baru), langkah ini dilewati —
    schema.sql yang akan membuatnya lengkap. Idempotent.

    - v1.1.3 → v1.1.4 : kolom batch_date (upload_sessions, uploaded_videos)
    - v1.1.6 → v1.1.7 : kolom app_slot (accounts). Semua akun lama otomatis
      dianggap milik "Aplikasi Original" (nilai default 'original').
    """
    conn = get_db()
    try:
        if _table_exists(conn, "upload_sessions") and not _column_exists(
            conn, "upload_sessions", "batch_date"
        ):
            conn.execute("ALTER TABLE upload_sessions ADD COLUMN batch_date TEXT")
        if _table_exists(conn, "uploaded_videos") and not _column_exists(
            conn, "uploaded_videos", "batch_date"
        ):
            conn.execute("ALTER TABLE uploaded_videos ADD COLUMN batch_date TEXT")
        # v1.46: skema accounts berubah total (akun lintas-HP via
        # account_placements) — TIDAK ada migrasi otomatis dari skema lama
        # (device_id/app_slot langsung di tabel accounts), karena versi ini
        # dirilis saat database masih tahap testing. Kalau tabel `accounts`
        # lama (berisi kolom device_id) masih terdeteksi, drop supaya
        # schema.sql bisa membuat ulang dengan struktur baru — data lama
        # dianggap data uji coba, aman dihapus (sudah dikonfirmasi user).
        if _table_exists(conn, "accounts") and _column_exists(conn, "accounts", "device_id"):
            conn.execute("DROP TABLE IF EXISTS uploaded_videos")
            conn.execute("DROP TABLE IF EXISTS upload_sessions")
            conn.execute("DROP TABLE IF EXISTS accounts")

        # v1.48 -> v1.50: pisahkan IDENTITAS HP dari transport ADB.
        # Sebelumnya kolom `serial` diganti menjadi `ip:port` saat Wi-Fi aktif.
        # Akibatnya satu HP fisik terlihat seolah berubah identitas ketika pindah
        # USB <-> Wi-Fi. v1.50 mempertahankan `serial` untuk kompatibilitas,
        # tetapi runtime memakai usb_serial/wifi_endpoint dan stable_uid.
        if _table_exists(conn, "devices"):
            device_columns = {
                "stable_uid": "TEXT",
                "usb_serial": "TEXT",
                "wifi_endpoint": "TEXT",
                "preferred_transport": "TEXT DEFAULT 'auto'",
                "wifi_auto_reconnect": "INTEGER DEFAULT 1",
                "last_transport": "TEXT",
                "last_usb_seen_at": "DATETIME",
                "last_wifi_seen_at": "DATETIME",
            }
            for column, ddl in device_columns.items():
                if not _column_exists(conn, "devices", column):
                    conn.execute(f"ALTER TABLE devices ADD COLUMN {column} {ddl}")

            rows = conn.execute(
                "SELECT id, serial, stable_uid, usb_serial, wifi_endpoint, "
                "preferred_transport, wifi_auto_reconnect, last_transport FROM devices"
            ).fetchall()
            for row in rows:
                device_id = row[0]
                legacy = (row[1] or "").strip()
                stable_uid = (row[2] or "").strip() or str(uuid.uuid4())
                usb_serial = (row[3] or "").strip()
                wifi_endpoint = (row[4] or "").strip()
                preferred = (row[5] or "auto").strip().lower()
                auto_reconnect = 1 if row[6] is None else int(bool(row[6]))
                last_transport = (row[7] or "").strip().lower()

                if legacy:
                    if ":" in legacy and not wifi_endpoint:
                        wifi_endpoint = legacy
                        last_transport = last_transport or "wifi"
                    elif ":" not in legacy and not usb_serial:
                        usb_serial = legacy
                        last_transport = last_transport or "usb"
                if preferred not in {"auto", "wifi", "usb"}:
                    preferred = "auto"
                if last_transport not in {"wifi", "usb"}:
                    last_transport = None

                conn.execute(
                    """UPDATE devices
                       SET stable_uid = ?, usb_serial = ?, wifi_endpoint = ?,
                           preferred_transport = ?, wifi_auto_reconnect = ?, last_transport = ?
                       WHERE id = ?""",
                    (stable_uid, usb_serial or None, wifi_endpoint or None,
                     preferred, auto_reconnect, last_transport, device_id),
                )
        conn.commit()
    finally:
        conn.close()
    # v1.1.8 → v1.1.11: buang 3 caption seed LAMA yang over-claim, supaya seed
    # baru (netral) bisa terisi ulang. Dijalankan setelah koneksi di atas ditutup
    # karena memakai helper query/execute sendiri.
    _migrate_old_caption_seeds()
    _migrate_remove_maestro_settings()
    _migrate_remove_workflow_feature()


# Konten 3 caption seed LAMA (persis dari v1.1.6). Dipakai untuk mengenali &
# menghapusnya saat migrasi — HANYA yang cocok persis ini yang dihapus, jadi
# caption buatan user sendiri tidak akan ikut terhapus.
_OLD_SEED_CAPTIONS = [
    (
        "Produk ini bikin aku auto repeat order! Kualitasnya beneran bagus banget, "
        "worth it banget di harga segini"
    ),
    "Gak nyangka sebagus ini! Recommended banget buat kalian yang lagi cari produk berkualitas",
    "Wajib punya nih! Udah dipakai dan hasilnya memuaskan banget, langsung checkout aja",
]


def _migrate_old_caption_seeds():
    """
    Ganti caption bawaan lama (gaya over-claim/spam-affiliate) dengan gaya baru
    yang netral. Aman & idempotent:

    - Hanya menghapus baris yang ISINYA PERSIS sama dengan 3 seed lama, jadi
      caption yang dibuat/diedit user tidak tersentuh.
    - Setelah baris lama terhapus, bila akhirnya tabel jadi KOSONG,
      `_seed_defaults()` (yang jalan setelah ini) akan mengisi 10 template baru.
    - Bila user sudah menambah caption sendiri (tabel tidak akan kosong walau
      seed lama dihapus), maka seed baru TIDAK dipaksa masuk — menghormati data
      user. (User tetap bisa menambah manual dari daftar contoh di README.)
    """
    if not query("SELECT name FROM sqlite_master WHERE type='table' AND name='caption_templates'"):
        return
    for old_content in _OLD_SEED_CAPTIONS:
        row = query(
            "SELECT id FROM caption_templates WHERE content = ?",
            (old_content,),
            one=True,
        )
        if row:
            execute("DELETE FROM caption_templates WHERE content = ?", (old_content,))


def _migrate_remove_maestro_settings():
    """
    Bersihkan setting era Maestro (v1.1.7–v1.1.11) dari DB lama, sekarang tak
    terpakai sama sekali karena Maestro sudah dihapus total & digantikan
    perekam ADB murni (v1.1.12). Idempotent — aman dipanggil berkali-kali.
    """
    if not query("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"):
        return
    old_keys = [
        "maestro_path",
        "maestro_studio_path",
        "workflow_delay_min_ms",
        "workflow_delay_max_ms",
    ]
    for key in old_keys:
        execute("DELETE FROM settings WHERE key = ?", (key,))


def _migrate_remove_workflow_feature():
    """
    Fitur Workflow (rekam & eksekusi otomatisasi, baik era Maestro v1.1.7-11
    maupun era ADB murni v1.1.12-13) DIHAPUS TOTAL — sentuhan lewat mirror
    scrcpy ternyata tidak bisa direkam ADB (scrcpy menyuntik event lewat
    InputManager Android, bukan lewat device sentuh fisik yang didengarkan
    `getevent`), sehingga fitur ini tidak bisa diandalkan.

    Migrasi ini membersihkan sisa dari DB LAMA milik user yang sempat
    menjalankan versi tersebut:
    - Tabel `workflow_runs` (riwayat eksekusi) — dihapus total.
    - Setting `step_delay_min_ms` / `step_delay_max_ms` /
      `workflow_capture_elements_default` (era ADB murni) — dihapus.
    Idempotent — aman dipanggil berkali-kali, tidak error walau tabel/kolom
    sudah tidak ada.
    """
    if query("SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_runs'"):
        execute("DROP TABLE IF EXISTS workflow_runs")

    if query("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"):
        for key in ("step_delay_min_ms", "step_delay_max_ms", "workflow_capture_elements_default"):
            execute("DELETE FROM settings WHERE key = ?", (key,))


def _prepare_video_sources(storage_root):
    """Buat empat folder sumber dan migrasikan folder ``video`` lama dengan aman.

    Startup tidak dibatalkan bila drive/path lama sedang tidak tersedia. Panel
    Upload akan menampilkan error dan root dapat diperbaiki dari Pengaturan.
    """
    source_names = ("video-1", "video-2", "video-3", "video-4")
    try:
        os.makedirs(storage_root, exist_ok=True)
        for name in source_names:
            os.makedirs(os.path.join(storage_root, name), exist_ok=True)
    except OSError:
        return False

    # Kompatibilitas v1.30 hanya untuk folder bawaan project. Folder custom
    # tidak disentuh supaya data pengguna tidak berpindah diam-diam.
    old_video_dir = os.path.join(BASE_DIR, "video")
    first_source = os.path.join(storage_root, "video-1")
    if (
        os.path.abspath(storage_root) == os.path.abspath(BASE_DIR)
        and os.path.isdir(old_video_dir)
        and os.path.abspath(old_video_dir) != os.path.abspath(first_source)
    ):
        for entry in os.listdir(old_video_dir):
            if entry == "CARA-PAKAI-FOLDER-INI.txt":
                continue
            src = os.path.join(old_video_dir, entry)
            dst = os.path.join(first_source, entry)
            if not os.path.exists(dst):
                try:
                    os.replace(src, dst)
                except OSError:
                    pass
        try:
            remaining = [name for name in os.listdir(old_video_dir) if name != "CARA-PAKAI-FOLDER-INI.txt"]
            if not remaining:
                guide = os.path.join(old_video_dir, "CARA-PAKAI-FOLDER-INI.txt")
                if os.path.isfile(guide):
                    os.remove(guide)
                os.rmdir(old_video_dir)
        except OSError:
            pass
    return True


def _seed_defaults():
    """Isi settings default & contoh caption template jika kosong."""
    # v1.31: storage_path adalah ROOT yang menampung video-1 s.d. video-4.
    default_storage_root = BASE_DIR
    old_default_video_dir = os.path.join(BASE_DIR, "video")
    defaults = {
        "posting_hours": "09:00,12:00,15:00,18:00,21:00",
        "random_range": "15",
        "storage_path": default_storage_root,
        "adb_path": "",
        "scrcpy_path": "",
        "scrcpy_mode": "stay_awake",
        "hp_target_dir": "/sdcard/DCIM/RemoteHP/",
        # v1.43: mode koneksi HP — 'usb' atau 'wifi'. Default WiFi sesuai
        # permintaan. Nilai ini PERMANEN (tabel settings), jadi tidak balik
        # ke default lagi setelah aplikasi ditutup & dibuka ulang.
        "connection_mode": "wifi",
        "wifi_last_ip": "",
    }
    for key, value in defaults.items():
        existing = query("SELECT key FROM settings WHERE key = ?", (key,), one=True)
        if existing is None:
            execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))

    # v1.40: satu sumber aturan untuk komponen MM jadwal. Database lama dapat
    # menyimpan jam seperti 09:30 atau random_range 20/30. Keduanya dinormalisasi
    # saat startup untuk kompatibilitas setting lama. Sesi baru v1.41 memakai
    # slot jam 00–23 tetap dan hanya membaca batas MM 01..15 dari random_range.
    from services import scheduler as scheduler_svc

    hours_row = query("SELECT value FROM settings WHERE key = 'posting_hours'", one=True)
    normalized_hours = scheduler_svc.normalize_posting_hours(
        hours_row["value"] if hours_row else defaults["posting_hours"]
    )
    if not normalized_hours:
        normalized_hours = scheduler_svc.normalize_posting_hours(defaults["posting_hours"])
    execute(
        "UPDATE settings SET value = ? WHERE key = 'posting_hours'",
        (",".join(normalized_hours),),
    )

    range_row = query("SELECT value FROM settings WHERE key = 'random_range'", one=True)
    normalized_range = scheduler_svc.normalize_random_range(
        range_row["value"] if range_row else defaults["random_range"]
    )
    execute(
        "UPDATE settings SET value = ? WHERE key = 'random_range'",
        (str(normalized_range),),
    )

    # Migrasi setting lama. Default v1.30 menunjuk langsung ke BASE_DIR/video;
    # v1.31 menunjuk ke parent/root dan menyediakan empat sumber tetap.
    sp = query("SELECT value FROM settings WHERE key = 'storage_path'", one=True)
    current_storage = ((sp["value"] if sp else "") or "").strip()
    if not current_storage or os.path.abspath(current_storage) == os.path.abspath(old_default_video_dir):
        current_storage = default_storage_root
        execute("UPDATE settings SET value = ? WHERE key = 'storage_path'", (current_storage,))

    # Key lama berasal dari input path Panel 2 yang sudah dihapus.
    execute("DELETE FROM settings WHERE key = 'video_source_path'")
    _prepare_video_sources(current_storage)

    # Caption template contoh (hanya jika tabel kosong).
    # v1.1.8: gaya diubah total — TIDAK memuji/menyebut produk tertentu, tidak
    # menyuruh checkout, tidak mengklaim hasil. Fokus ke perilaku & psikologi
    # konsumen yang umum. Maksimal 3 hashtag netral per template.
    count = query("SELECT COUNT(*) AS c FROM caption_templates", one=True)
    if count and count["c"] == 0:
        samples = [
            ('Kadang sebelum belanja tuh aku scroll dulu lama-lama, baca-baca, padahal belum tentu jadi beli juga', '#fyp #belanjaonline #tips'),
            ('Pernah nggak, niatnya cuma mau lihat satu barang, eh keterusan sampai lupa waktu? relate banget nggak sih', '#fyp #relatable #kebiasaan'),
            ('Katanya salah satu alasan kita betah scroll itu karena tiap swipe ada kejutan baru. bikin susah berhenti ya', '#fyp #psikologi #kebiasaan'),
            ('Ada yang suka nyimpen wishlist panjang tapi ujungnya cuma diliatin aja? kadang ngeliatnya udah cukup bikin puas', '#fyp #relatable #wishlist'),
            ('Aku perhatiin, makin sering nunda bayar di menit terakhir, makin kelihatan mana yang beneran pengin dan mana yang cuma lapar mata', '#fyp #mindful #belanja'),
            ("Lapar mata pas malam hari tuh nyata ya. besok paginya suka mikir 'kok kemarin pengin banget'", '#fyp #relatable #kebiasaan'),
            ('Scroll pelan-pelan sambil rebahan tuh ternyata bisa jadi hiburan sendiri, walau nggak beli apa-apa', '#fyp #santai #relatable'),
            ("Kadang keranjang tuh isinya bukan rencana beli, tapi lebih ke 'nanti dipikirin lagi'. ada yang samaan?", '#fyp #relatable #belanjaonline'),
            ('Aku baru sadar, kebiasaan nyimpen barang di keranjang tapi didiemin berhari-hari itu ternyata banyak yang ngelakuin', '#fyp #relatable #belanjaonline'),
            ('Menariknya, scroll tanpa tujuan kadang malah bikin nemu hal yang nggak kepikiran sebelumnya', '#fyp #kebiasaan #catatan'),
            ('Belakangan aku coba biasain nunggu sehari dulu sebelum memutuskan, ternyata banyak yang akhirnya nggak jadi aku ambil', '#fyp #tips #mindful'),
            ("Aku coba bikin daftar 'mau ambil' dan nunggu seminggu. yang masih kepikiran setelah seminggu biasanya emang beneran perlu", '#fyp #tips #mindful'),
            ("Kebiasaan baru: sebelum ambil keputusan, aku tanya ke diri sendiri 'kalau ini harganya normal, masih mau nggak?' cukup ngebantu", '#fyp #tips #mindful'),
            ('Riset kecil-kecilan sebelum belanja tuh nenangin ya, minimal jadi lebih yakin sama pilihan sendiri', '#fyp #tips #belanja'),
            ("Aku belajar buat pisahin 'butuh sekarang' sama 'nanti juga masih bisa'. lumayan bikin lebih tenang milihnya", '#fyp #tips #mindful'),
            ("Jujur, kadang yang bikin lama itu bukan milih barangnya, tapi mikir 'butuh apa cuma pengin' hehe", '#fyp #relatable #belanja'),
            ('Semenjak nyatet apa aja yang mau dibeli, jadi lebih kelihatan mana kebutuhan mana keinginan', '#fyp #tips #mindful'),
            ('Nunggu semalam sebelum memutuskan tuh sederhana, tapi lumayan ngurangin nyesel di kemudian hari', '#fyp #tips #mindful'),
            ("Kadang keputusan paling bijak itu justru 'nggak sekarang', bukan 'nggak sama sekali'", '#fyp #mindful #catatan'),
            ('Aku suka tulis alasan kenapa mau beli sesuatu. kalau alasannya susah dicari, biasanya emang belum perlu', '#fyp #tips #mindful'),
            ('Menariknya, kadang keputusan belanja itu lebih soal timing dan mood daripada barangnya sendiri', '#fyp #belanja #catatan'),
            ('Ternyata mood pas lagi scroll ngaruh banget ke apa yang menarik di mata kita. kalian ngerasain juga nggak?', '#fyp #psikologikonsumen #relatable'),
            ('Belanja pas lagi capek sama belanja pas lagi santai tuh keputusannya beda banget ya. ada yang gitu juga?', '#fyp #tanya #kebiasaan'),
            ('Pas lagi banyak pikiran, aku perhatiin jadi lebih gampang tertarik beli hal-hal kecil. semacam pelarian ya', '#fyp #psikologi #relatable'),
            ('Belanja pas habis gajian sama pas pertengahan bulan tuh beda mindset banget nggak sih', '#fyp #relatable #kebiasaan'),
            ("Kadang kita beli bukan karena butuh barangnya, tapi karena pengin ngerasa 'hari ini udah usaha'", '#fyp #psikologi #catatan'),
            ('Aku sadar kalau lagi bosen, apa aja jadi kelihatan menarik buat dibeli. makanya sekarang lebih hati-hati pas bosen', '#fyp #mindful #relatable'),
            ('Mood bagus bikin lebih royal, mood jelek bikin cari hiburan. dua-duanya bisa bikin khilaf ya', '#fyp #psikologi #relatable'),
            ('Ternyata waktu paling rawan buatku itu malam menjelang tidur. kalian jam berapa?', '#fyp #tanya #kebiasaan'),
            ('Belanja pas lagi seneng tuh rasanya beda, kayak ngerayain. tapi tetap perlu direm sih hehe', '#fyp #relatable #santai'),
            ('Katanya harga yang diakhiri angka 9 itu terasa lebih murah walau bedanya cuma seratus perak. otak kita lucu ya', '#fyp #psikologi #fakta'),
            ('Katanya kita lebih gampang tertarik sama sesuatu yang terasa terbatas waktunya. makanya sering ngerasa buru-buru ya', '#fyp #psikologi #fakta'),
            ("Angka coret yang gede tuh secara nggak sadar bikin kita ngerasa 'sayang kalau dilewatin'. padahal belum tentu butuh", '#fyp #psikologikonsumen #catatan'),
            ("Menariknya, 'gratis ongkir' kadang bikin kita nambah barang cuma biar syaratnya kepenuhan. ada yang gini juga?", '#fyp #relatable #belanjaonline'),
            ("Kadang 'hemat sekian' bikin lupa kalau tetap aja itu pengeluaran. aku sering ketipu logika ini sih", '#fyp #psikologi #catatan'),
            ('Bundling tuh pinter ya, bikin kita ngerasa dapet banyak padahal mungkin nggak semua kepakai', '#fyp #psikologikonsumen #catatan'),
            ("Aku perhatiin, label 'paling laris' aja udah cukup bikin penasaran pengin lihat. sugesti emang kuat", '#fyp #psikologi #relatable'),
            ("Harga 'per hari cuma sekian' tuh bikin kelihatan murah, padahal kalau dijumlah setahun lumayan juga", '#fyp #psikologi #catatan'),
            ('Potongan harga gede kadang bikin kita ambil yang sebenernya nggak dicari dari awal. relate nggak?', '#fyp #relatable #belanja'),
            ("Ternyata ngeliat 'sisa sedikit' tuh memicu buru-buru, padahal kalau tenang mungkin nggak jadi ambil", '#fyp #psikologikonsumen #catatan'),
            ('Pernah merhatiin nggak, kalau lagi rame yang bahas sesuatu, kita jadi ikut penasaran walau awalnya biasa aja?', '#fyp #psikologikonsumen #relatable'),
            ('Katanya kalau lagi penasaran sama sesuatu, otak kita cenderung nyari-nyari alasan buat cari tahu lebih jauh', '#fyp #psikologi #catatanharian'),
            ('Lihat orang lain punya tuh kadang bikin kepikiran, padahal sebelumnya nggak kepikiran sama sekali', '#fyp #psikologi #relatable'),
            ('FOMO tuh nyata ya, takut ketinggalan bikin kita buru-buru mutusin. padahal santai juga nggak apa-apa', '#fyp #relatable #catatan'),
            ('Kadang yang bikin pengin bukan barangnya, tapi karena semua orang lagi ngomongin. ada yang samaan?', '#fyp #tanya #relatable'),
            ("Aku sadar sering kebawa tren sesaat. sekarang coba tanya dulu 'ini aku beneran suka atau ikut-ikutan?'", '#fyp #mindful #relatable'),
            ('Rekomendasi dari orang yang kita percaya tuh powerful banget ya, kadang lebih ngaruh dari iklan', '#fyp #psikologikonsumen #catatan'),
            ("Ternyata rasa 'pengin sama kayak yang lain' itu wajar, tinggal kita yang atur biar nggak berlebihan", '#fyp #psikologi #catatan'),
            ('Tren datang dan pergi, tapi yang beneran cocok sama kita biasanya bertahan. jadi nggak buru-buru ngikutin', '#fyp #mindful #catatan'),
            ('Kadang keputusan beli itu lebih soal pengin diterima daripada pengin barangnya. dalam ya kalau dipikir', '#fyp #psikologi #catatanharian'),
            ('Menariknya, kita cenderung lebih menghargai barang yang lama kita pertimbangkan daripada yang diambil buru-buru', '#fyp #psikologi #catatan'),
            ("Kadang yang kita cari bukan barangnya, tapi perasaan lega 'udah nemu yang pas'. prosesnya itu yang menarik buat dilihat", '#fyp #relatable #catatanharian'),
            ('Semakin ke sini aku sadar, belanja itu enak bukan cuma karena barangnya, tapi karena momen milih-milihnya juga', '#fyp #santai #relatable'),
            ('Barang yang kepakai tiap hari tuh biasanya bukan yang paling mahal, tapi yang paling pas sama kebutuhan', '#fyp #catatan #tips'),
            ('Aku belajar, kepuasan itu bukan dari seberapa banyak beli, tapi seberapa kepakai yang udah dibeli', '#fyp #mindful #catatan'),
            ('Kadang barang yang paling berkesan itu yang dibeli setelah nabung dan nunggu, bukan yang impulsif', '#fyp #catatan #relatable'),
            ('Ternyata ngerapiin dan pakai barang yang udah ada tuh kadang lebih memuaskan daripada nambah baru', '#fyp #mindful #catatan'),
            ('Aku perhatiin, semakin sedikit tapi kepakai semua, malah semakin tenang rasanya', '#fyp #mindful #catatan'),
            ('Barang bagus itu relatif ya, yang penting sesuai sama cara kita pakainya sehari-hari', '#fyp #catatan #tips'),
            ("Kepuasan belanja tuh cepet ilang kalau nggak kepakai. makanya sekarang mikirin 'nanti dipakai buat apa'", '#fyp #mindful #catatan'),
            ('Menurut kalian, lebih sering belanja karena butuh, atau karena kebetulan lihat pas lagi scroll?', '#fyp #tanya #belanjaonline'),
            ("Kalian tim langsung ambil pas nemu, atau tim masukin keranjang dulu buat 'didinginkan' semalam? aku tim kedua sih", '#fyp #tanya #belanjaonline'),
            ('Ada yang kayak aku, suka bandingin dulu beberapa pilihan sebelum akhirnya nentuin? penasaran aja rasanya', '#fyp #tipsbelanja #relatable'),
            ('Kalian paling sering khilaf belanja pas kondisi apa? aku pas lagi bosen sih jujur', '#fyp #tanya #relatable'),
            ('Tim catat dulu sebelum beli, atau tim ngalir aja? pengin tahu kebiasaan kalian', '#fyp #tanya #kebiasaan'),
            ('Kalau lagi ragu antara dua pilihan, kalian biasanya milih gimana? aku suka bingung sendiri', '#fyp #tanya #relatable'),
            ('Menurut kalian, wishlist itu buat direalisasiin atau buat ditampung aja biar lega? hehe', '#fyp #tanya #wishlist'),
            ('Kalian pernah nggak beli sesuatu terus nyesel, terus jadiin pelajaran? cerita dong', '#fyp #tanya #catatan'),
            ('Lebih suka belanja pas ada yang dicari, atau pas lagi santai lihat-lihat aja? aku dua-duanya sih', '#fyp #tanya #kebiasaan'),
            ('Kalian punya trik nggak biar nggak kalap pas lagi banyak yang menarik? bagi dong', '#fyp #tanya #tips'),
            ('Ternyata ngobrolin alasan di balik kebiasaan belanja itu seru juga. kalian paling sering khilaf pas kondisi apa?', '#fyp #tanya #relatable'),
            ("Makin ke sini aku makin suka proses 'riset dulu pelan-pelan' daripada buru-buru. lebih puas sama keputusannya", '#fyp #tips #belanja'),
            ('Aku nyoba nyatet pengeluaran kecil-kecil, dan kaget juga ternyata yang receh-receh numpuk banyak', '#fyp #catatan #tips'),
            ('Belajar dari kebiasaan sendiri tuh menarik ya, jadi lebih kenal apa yang bikin kita gampang tergoda', '#fyp #catatanharian #psikologi'),
            ("Kadang refleksi sederhana 'kemarin beli apa aja ya' bikin lebih sadar sama pola sendiri", '#fyp #mindful #catatan'),
            ("Aku mulai bedain 'seneng sesaat' sama 'kepakai jangka panjang'. lumayan ngubah cara milih", '#fyp #mindful #catatan'),
            ('Ternyata pelan-pelan ngerti diri sendiri tuh bikin belanja jadi lebih tenang, nggak buru-buru', '#fyp #catatanharian #mindful'),
            ("Nyatet keinginan tanpa buru-buru ambil tuh ternyata bikin lega juga, kayak udah 'diakui' aja gitu", '#fyp #mindful #catatan'),
            ('Aku perhatiin polanya: makin buru-buru mutusin, makin sering nyesel. jadi sekarang coba pelan aja', '#fyp #catatan #mindful'),
            ('Refleksi akhir bulan soal belanja tuh nggak enak diliat, tapi ngebantu banget buat besok-besok', '#fyp #catatan #tips'),
            ('Ada yang suka isi keranjang penuh terus ujungnya nggak jadi lanjut? kadang ngisi keranjangnya aja udah puas', '#fyp #relatable #belanjaonline'),
            ("Keranjang tuh kadang jadi tempat 'nampung mimpi' ya, bukan rencana beli beneran. relate nggak?", '#fyp #relatable #wishlist'),
            ('Aku sengaja diemin keranjang beberapa hari. kalau masih pengin, baru dipikir serius. lumayan nyaring', '#fyp #tips #mindful'),
            ('Wishlist panjang tuh nggak apa-apa kok, yang penting nggak semua harus jadi kenyataan sekaligus', '#fyp #wishlist #mindful'),
            ('Kadang ngehapus isi keranjang yang udah lama tuh rasanya lega, kayak beberes pikiran', '#fyp #relatable #mindful'),
            ('Aku suka pindahin keinginan ke catatan dulu, bukan langsung keranjang. jadi ada jeda buat mikir', '#fyp #tips #mindful'),
            ("Ngeliat wishlist minggu lalu terus mikir 'kok kemarin pengin ya' tuh sering kejadian nggak sih", '#fyp #relatable #catatan'),
            ('Keranjang penuh belum tentu dompet berkurang, kadang cuma penuh di rencana aja hehe', '#fyp #relatable #santai'),
            ('Aku bikin aturan: kalau lupa isi keranjang apa, berarti emang nggak sepenting itu. cukup works', '#fyp #tips #mindful'),
            ('Wishlist itu enaknya buat inget-inget, bukan buat dikejar semua. jadi nggak ngoyo', '#fyp #wishlist #mindful'),
            ('Bandingin beberapa pilihan sebelum nentuin tuh capek di awal, tapi tenang di akhir', '#fyp #tips #belanja'),
            ('Aku suka baca pengalaman orang dulu sebelum mutusin. bukan biar ragu, tapi biar lebih mantap', '#fyp #tips #belanja'),
            ('Kadang riset kebanyakan malah bikin makin bingung ya. ada titik di mana harus percaya pilihan sendiri', '#fyp #relatable #catatan'),
            ('Ngebandingin tuh sehat asal nggak kebablasan sampai lupa tujuannya apa. pernah gitu nggak?', '#fyp #tanya #tips'),
            ('Aku perhatiin, makin banyak pilihan malah makin susah mutusin. kadang sedikit pilihan lebih lega', '#fyp #psikologi #catatan'),
            ("Baca-baca dulu sebelum beli tuh kayak ngobrol sama diri sendiri soal 'ini beneran cocok nggak'", '#fyp #tips #mindful'),
            ('Riset itu bukan biar nunda terus, tapi biar pas mutusin nggak setengah hati', '#fyp #tips #belanja'),
            ("Kadang pilihan yang 'cukup baik' dan cepat lebih menenangkan daripada nyari yang 'paling sempurna'", '#fyp #psikologi #catatan'),
            ('Aku belajar berhenti riset pas udah nemu yang sesuai kebutuhan, biar nggak kejebak overthinking', '#fyp #mindful #tips'),
            ('Ngebandingin harga di beberapa tempat tuh lumayan, tapi hargai juga waktu sendiri ya', '#fyp #tips #catatan'),
            ('Aku bikin jeda 24 jam buat barang di atas nominal tertentu. sederhana tapi ngurangin impulsif', '#fyp #tips #mindful'),
            ('Matiin notifikasi penawaran tuh ternyata ngebantu banget biar nggak tiap saat tergoda', '#fyp #tips #kebiasaan'),
            ('Belanja pakai daftar tuh kelihatan kaku, tapi beneran bikin lebih fokus sama yang dibutuhin', '#fyp #tips #mindful'),
            ("Aku coba 'window shopping' aja dulu tanpa niat beli. lumayan buat nyalurin pengin tanpa keluar uang", '#fyp #tips #santai'),
            ('Nabung buat sesuatu yang beneran diincer tuh bikin pas dapetnya lebih berkesan', '#fyp #catatan #mindful'),
            ("Aku set budget bulanan buat 'senang-senang'. jadi tetap bisa menikmati tanpa kebablasan", '#fyp #tips #mindful'),
            ('Ternyata unfollow akun yang bikin gampang khilaf tuh salah satu self-care juga', '#fyp #tips #kebiasaan'),
            ('Bikin aturan sederhana buat diri sendiri tuh ngebantu, karena nggak semua keputusan perlu dipikir dari nol', '#fyp #mindful #tips'),
            ("Aku belajar bilang 'nanti dulu' ke diri sendiri. ternyata banyak keinginan yang hilang sendiri", '#fyp #mindful #catatan'),
            ('Pisahin uang buat kebutuhan dan keinginan tuh bikin lebih tenang pas mau jajan', '#fyp #tips #mindful'),
            ('Ada momen di mana kita cuma pengin lihat-lihat aja buat hiburan, tanpa niat beli apa-apa. valid banget sih itu', '#fyp #relatable #santai'),
            ('Kadang scroll toko online tuh kayak jalan-jalan santai, refreshing walau nggak ambil apa-apa', '#fyp #santai #relatable'),
            ('Nggak semua yang menarik harus dimiliki. kadang cukup dinikmati sekilas terus lanjut scroll', '#fyp #mindful #santai'),
            ('Pengin itu manusiawi kok, yang penting kita yang pegang kendali, bukan sebaliknya', '#fyp #mindful #catatan'),
            ('Belajar menikmati proses milih tanpa harus selalu beli tuh ternyata menyenangkan juga', '#fyp #santai #mindful'),
            ("Kadang keputusan paling pas hari ini cukup 'liat-liat aja dulu'. besok masih ada waktu", '#fyp #mindful #santai'),
            ('Nggak beli hari ini bukan berarti kalah, kadang itu justru menang lawan lapar mata', '#fyp #relatable #mindful'),
            ('Menikmati yang udah dipunya tuh salah satu bentuk cukup yang sering kelewat', '#fyp #mindful #catatan'),
            ('Kadang yang kita butuh cuma jeda sebentar sebelum mutusin, bukan buru-buru', '#fyp #mindful #tips'),
            ('Pelan-pelan aja sama diri sendiri, termasuk soal keinginan. nggak semua harus sekarang', '#fyp #mindful #catatanharian'),
        ]
        for content, hashtags in samples:
            execute(
                "INSERT INTO caption_templates (content, hashtags, is_active) VALUES (?, ?, 1)",
                (content, hashtags),
            )


def get_setting(key, default=None):
    """Ambil satu nilai setting."""
    row = query("SELECT value FROM settings WHERE key = ?", (key,), one=True)
    return row["value"] if row else default


def set_setting(key, value):
    """Set/update satu nilai setting."""
    existing = query("SELECT key FROM settings WHERE key = ?", (key,), one=True)
    if existing:
        execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
    else:
        execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))
