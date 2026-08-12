"""
services/adb.py — Semua perintah ADB (cross-platform Ubuntu/Windows)

Fungsi utama:
- get_adb_path()        : path adb (auto-detect / override dari settings)
- list_devices()        : daftar serial HP yang terhubung & status
- is_device_online()    : cek 1 device online/tidak
- push_file()           : push 1 file dari PC ke HP (FIFO — satu per satu)
- delete_file()         : hapus 1 file di HP
- ensure_target_dir()   : pastikan folder target di HP ada

Koneksi USB / WiFi (v1.43):
- get_connection_mode() : mode aktif tersimpan ('usb' / 'wifi'), default 'wifi'
- tcpip_enable()        : aktifkan mode TCP/IP di HP (WAJIB lewat USB dulu, 1x)
- pair_wifi()           : pairing manual pakai kode dari menu Wireless debugging
                          Android 11+ (TANPA kabel USB sama sekali)
- connect_wifi()        : `adb connect ip:port`
- disconnect_wifi()     : `adb disconnect ip:port` (atau semua bila kosong)
"""
import os
import platform
import re
import subprocess

from database.db import get_setting

# Timeout default untuk perintah adb (detik)
DEFAULT_TIMEOUT = 20
PUSH_TIMEOUT = 300  # push file video bisa besar
WIFI_TIMEOUT = 15   # koneksi/pairing WiFi biasanya cepat, tapi beri jeda utk jaringan lambat

# ── Mode koneksi (v1.43) ──
CONNECTION_MODE_DEFAULT = "wifi"
CONNECTION_MODES = {"usb", "wifi"}
DEFAULT_TCPIP_PORT = 5555


def get_adb_path():
    """
    Tentukan path adb.
    1. Pakai override dari settings jika diisi.
    2. Jika tidak, gunakan default sesuai OS.
    """
    custom = (get_setting("adb_path") or "").strip()
    if custom:
        return custom
    if platform.system() == "Windows":
        return "adb.exe"
    return "adb"


def get_hp_target_dir():
    """Folder target di HP, default /sdcard/DCIM/RemoteHP/"""
    d = (get_setting("hp_target_dir") or "").strip()
    if not d:
        d = "/sdcard/DCIM/RemoteHP/"
    if not d.endswith("/"):
        d += "/"
    return d


def _run(args, timeout=DEFAULT_TIMEOUT):
    """
    Jalankan perintah adb. Mengembalikan dict:
    { ok: bool, stdout: str, stderr: str, code: int }
    """
    adb = get_adb_path()
    cmd = [adb] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "code": result.returncode,
            "cmd": " ".join(cmd),
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"ADB tidak ditemukan (path: {adb}). Install ADB atau set path di Pengaturan.",
            "code": -1,
            "cmd": " ".join(cmd),
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"Perintah ADB timeout setelah {timeout}s.",
            "code": -2,
            "cmd": " ".join(cmd),
        }
    except Exception as e:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"Error menjalankan ADB: {e}",
            "code": -3,
            "cmd": " ".join(cmd),
        }


def _sh_quote(path):
    """
    Bungkus sebuah path/argumen agar AMAN saat dijalankan oleh shell DI ANDROID
    (lewat `adb shell ...`).

    KENAPA PERLU: pada `adb shell <cmd>`, semua argumen setelah "shell" digabung
    oleh ADB jadi SATU string perintah, lalu dijalankan ulang oleh /system/bin/sh
    di HP. Artinya karakter yang punya arti khusus di shell — spasi, tanda kurung
    `(` `)`, `&`, `;`, `'`, `"`, `*`, `$`, dll — akan ditafsirkan shell dan bikin
    error. Contoh nyata: file "grok-video (1).mp4" bikin `sh: syntax error:
    unexpected '('`. Membungkus path dalam kutip tunggal membuat shell
    memperlakukannya sebagai teks literal.

    Teknik: bungkus dengan kutip tunggal; satu-satunya karakter yang tak bisa
    ada di dalam kutip tunggal adalah kutip tunggal itu sendiri, jadi tiap `'`
    diganti dengan urutan `'\\''` (tutup kutip, kutip-tunggal ter-escape, buka
    kutip lagi) — pola standar POSIX shell.
    """
    return "'" + (path or "").replace("'", "'\\''") + "'"


def check_adb_available():
    """Cek apakah adb terinstall & bisa dipanggil. Return (ok, version_or_error)."""
    res = _run(["version"])
    if res["ok"]:
        first_line = res["stdout"].splitlines()[0] if res["stdout"] else "ADB tersedia"
        return True, first_line
    return False, res["stderr"]


def list_devices():
    """
    Daftar device terhubung.
    Return list of dict: [{ serial, status }]
    status: 'device' (online & authorized), 'unauthorized', 'offline'
    """
    res = _run(["devices"])
    devices = []
    if not res["ok"]:
        return {"ok": False, "error": res["stderr"], "devices": []}

    lines = res["stdout"].splitlines()
    # Baris pertama biasanya "List of devices attached"
    for line in lines[1:]:
        line = line.strip()
        if not line or "\t" not in line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            serial = parts[0].strip()
            status = parts[1].strip()
            devices.append({"serial": serial, "status": status})
    return {"ok": True, "error": None, "devices": devices}


def get_online_serials():
    """Set serial yang statusnya 'device' (siap dipakai)."""
    result = list_devices()
    if not result["ok"]:
        return set()
    return {d["serial"] for d in result["devices"] if d["status"] == "device"}


def is_device_online(serial):
    """Cek apakah 1 serial online & authorized."""
    if not serial:
        return False
    return serial in get_online_serials()


def ensure_target_dir(serial, target_dir=None):
    """Pastikan folder target di HP ada (mkdir -p)."""
    target_dir = target_dir or get_hp_target_dir()
    res = _run(["-s", serial, "shell", "mkdir", "-p", _sh_quote(target_dir)])
    return res


def scan_media(serial, remote_path):
    """
    Suruh Android (MediaStore) scan 1 file supaya langsung muncul di Galeri.

    Tanpa ini, adb push hanya menulis file ke filesystem tanpa memberi tahu
    MediaStore — jadi File Manager bisa lihat file-nya, tapi aplikasi Galeri
    (yang membaca dari MediaStore, bukan filesystem langsung) tidak akan
    menampilkannya sampai ada media scan (mis. HP di-restart).

    Path dibungkus _sh_quote() supaya nama file dengan spasi/kurung/karakter
    khusus (mis. "grok-video (1).mp4") tidak bikin shell Android error.

    Return dict hasil eksekusi (ok/stderr/dll), sama seperti _run().
    """
    return _run([
        "-s", serial, "shell", "am", "broadcast",
        "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
        "-d", _sh_quote(f"file://{remote_path}"),
    ])


def touch_file_now(serial, remote_path):
    """
    Set tanggal modifikasi file DI HP menjadi waktu sekarang (jam HP itu
    sendiri, lewat `touch` di shell Android — tidak menyentuh file asli di
    PC sama sekali).

    Perlu ini karena `adb push` MEMPERTAHANKAN tanggal modifikasi file
    sumber di PC. Kalau video dibuat/diedit beberapa hari lalu (mis. tanggal
    9) lalu baru di-push hari ini (tanggal 12), tanpa touch, file akan
    tercatat MediaStore dengan tanggal LAMA -> muncul di urutan BAWAH galeri
    (karena galeri umumnya urut berdasarkan tanggal terbaru). Dengan
    men-touch file di HP sebelum media scan, tanggalnya jadi "sekarang" ->
    otomatis tampil di URUTAN PALING ATAS (terbaru).

    Path dibungkus _sh_quote() supaya nama file dengan spasi/kurung/karakter
    khusus tidak bikin shell Android error.

    Return dict hasil eksekusi, sama seperti _run().
    """
    return _run(["-s", serial, "shell", "touch", _sh_quote(remote_path)])


def push_file(serial, local_path, target_dir=None):
    """
    Push SATU file dari PC ke HP. (FIFO — dipanggil satu per satu)
    Setelah push sukses:
      1. Timestamp file DI HP di-set ke waktu sekarang (touch_file_now) —
         supaya video selalu tampil di urutan PALING ATAS/TERBARU di galeri,
         apa pun tanggal asli file itu dibuat di PC.
      2. Trigger media scan (scan_media()) supaya file langsung muncul di
         aplikasi Galeri dengan tanggal yang sudah di-update itu.
    Return dict hasil eksekusi termasuk parsing kecepatan jika ada.
    """
    target_dir = target_dir or get_hp_target_dir()

    if not os.path.isfile(local_path):
        return {
            "ok": False,
            "stderr": f"File tidak ditemukan di PC: {local_path}",
            "stdout": "",
            "code": -10,
            "cmd": f"push {local_path}",
        }

    if not is_device_online(serial):
        return {
            "ok": False,
            "stderr": f"HP (serial {serial}) tidak online. Cek koneksi USB & USB Debugging.",
            "stdout": "",
            "code": -11,
            "cmd": f"push {local_path}",
        }

    # pastikan folder target ada
    ensure_target_dir(serial, target_dir)

    filename = os.path.basename(local_path)
    remote_path = target_dir + filename
    res = _run(["-s", serial, "push", local_path, remote_path], timeout=PUSH_TIMEOUT)
    res["remote_path"] = remote_path
    res["filename"] = filename

    if res["ok"]:
        touch_res = touch_file_now(serial, remote_path)
        res["touch_ok"] = touch_res["ok"]
        res["touch_stderr"] = touch_res["stderr"] if not touch_res["ok"] else ""

        scan_res = scan_media(serial, remote_path)
        res["media_scan_ok"] = scan_res["ok"]
        res["media_scan_stderr"] = scan_res["stderr"] if not scan_res["ok"] else ""
    else:
        res["touch_ok"] = None
        res["touch_stderr"] = ""
        res["media_scan_ok"] = None
        res["media_scan_stderr"] = ""

    return res


def _sql_escape(value):
    """Escape tanda kutip tunggal ala SQL (untuk klausa WHERE `content delete`)."""
    return (value or "").replace("'", "''")


def rescan_volume(serial):
    """
    Suruh MediaStore rescan SELURUH volume storage utama HP (semua
    foto/video/musik/dokumen di seluruh HP).

    ⚠️ SENGAJA TIDAK DIPAKAI di alur push/delete otomatis. Operasi ini
    memindai seluruh storage, jadi di HP dengan banyak file bisa makan waktu
    lama (belasan detik s/d menit) & membuat galeri lambat ter-update —
    pernah dicoba di v1.1.16 untuk delete, tapi justru bikin refresh jadi
    TIDAK realtime (v1.1.19 mengembalikannya ke scan bertarget per-file yang
    jauh lebih cepat). Fungsi ini dipertahankan hanya sebagai utilitas
    cadangan bila suatu saat perlu rescan menyeluruh secara manual.
    """
    return _run([
        "-s", serial, "shell", "content", "call",
        "--uri", "content://media",
        "--method", "scan_volume",
        "--arg", "external_primary",
    ])


def delete_file(serial, filename, target_dir=None):
    """
    Hapus SATU file di HP (di folder target).
    Dipanggil segera setelah 1 video selesai diupload.

    Setelah `rm`, file HILANG dari filesystem TAPI MediaStore (basis data
    yang dipakai aplikasi Galeri) masih menyimpan entri lamanya sampai ada
    yang memberi tahu. Untuk membersihkan entri itu SEGERA & CEPAT, 2 langkah
    yang keduanya HANYA menyentuh 1 entri/1 file (bukan scan seluruh HP):
      1. `content delete` langsung ke MediaStore ContentProvider dengan WHERE
         `_data='<path>'` — menghapus TEPAT 1 baris entri file itu dari basis
         data galeri. Operasi ini instan (cuma 1 baris DB), didukung Android
         7+/API 24+.
      2. Broadcast MEDIA_SCANNER_SCAN_FILE ke path file spesifik itu — memberi
         tahu scanner soal 1 file itu saja (bukan folder/volume). Ringan &
         cepat, jadi pelengkap kalau langkah 1 belum sepenuhnya nyantol di
         galeri vendor tertentu.

    CATATAN PENTING (kenapa TIDAK pakai scan_volume di sini):
    `content call --method scan_volume` memindai SELURUH storage HP (semua
    foto/video/musik/dokumen). Di HP yang isinya banyak, itu makan waktu lama
    (belasan detik s/d menit) & bikin galeri baru ke-update setelah scan
    raksasa selesai — persis gejala "harus tutup-buka aplikasi berkali-kali
    baru muncul". Karena di sini kita cuma mengubah 1 file, scan bertarget
    (langkah 1 & 2) jauh lebih tepat & jauh lebih cepat.
    """
    target_dir = target_dir or get_hp_target_dir()
    remote_path = target_dir + filename

    if not is_device_online(serial):
        return {
            "ok": False,
            "stderr": f"HP (serial {serial}) tidak online saat hapus file.",
            "stdout": "",
            "code": -11,
            "cmd": f"rm {remote_path}",
        }

    res = _run(["-s", serial, "shell", "rm", "-f", _sh_quote(remote_path)])
    res["remote_path"] = remote_path

    if res["ok"]:
        # 1) Hapus TEPAT 1 entri MediaStore (instan — cuma 1 baris DB).
        #    Quoting berlapis di sini:
        #    - Di level SQL (MediaStore): nilai path harus dalam kutip TUNGGAL
        #      SQL, dan kutip tunggal di dalam path di-escape ala SQL ('' ganda)
        #      lewat _sql_escape().
        #    - Di level SHELL Android: SELURUH argumen --where (yang mengandung
        #      kutip tunggal SQL, spasi, kurung, dst) dibungkus _sh_quote()
        #      supaya shell Android memperlakukannya sebagai satu teks literal
        #      dan tidak menafsirkan kurung/spasi (yang tadinya bikin
        #      "syntax error: unexpected '('"). _sh_quote otomatis meng-escape
        #      kutip tunggal SQL saat membungkus, jadi keduanya kompatibel.
        where_clause = "_data='" + _sql_escape(remote_path) + "'"
        content_res = _run([
            "-s", serial, "shell", "content", "delete",
            "--uri", "content://media/external/file",
            "--where", _sh_quote(where_clause),
        ])
        res["mediastore_clean_ok"] = content_res["ok"]
        res["mediastore_clean_stderr"] = content_res["stderr"] if not content_res["ok"] else ""

        # 2) Broadcast scan ke FILE SPESIFIK itu saja (ringan, bukan folder/volume).
        scan_res = scan_media(serial, remote_path)
        res["file_scan_ok"] = scan_res["ok"]
    else:
        res["mediastore_clean_ok"] = None
        res["mediastore_clean_stderr"] = ""
        res["file_scan_ok"] = None

    return res


def list_remote_files(serial, target_dir=None):
    """List file di folder target HP (untuk debug/verifikasi)."""
    target_dir = target_dir or get_hp_target_dir()
    res = _run(["-s", serial, "shell", "ls", "-1", _sh_quote(target_dir)])
    if not res["ok"]:
        return []
    return [f.strip() for f in res["stdout"].splitlines() if f.strip()]


# ════════════════════════════════════════
# KONEKSI USB / WiFi (v1.43)
# ════════════════════════════════════════
#
# ADB mendukung koneksi lewat jaringan WiFi ("adb over TCP/IP"), tapi ada 2
# jalur yang tersedia di Android, tergantung cara pairing pertama kali:
#
#   1) TCPIP DARI USB — HP disambung USB SEKALI, jalankan `adb tcpip 5555`
#      (mengaktifkan listener TCP di HP itu), lalu `adb connect <ip>:5555`.
#      Setelah ini HP boleh dicabut; sesi WiFi akan tetap hidup selama HP
#      tidak reboot / listener tidak mati. Ini paling gampang karena tidak
#      perlu buka menu Developer Options tiap kali.
#
#   2) PAIRING WiFi (Android 11+, TANPA kabel USB) — HP menampilkan kode
#      pairing 6 digit + ip:port khusus pairing di menu Setelan > Opsi
#      Pengembang > Debugging Nirkabel > "Pasangkan perangkat dengan kode
#      pairing". PC menjalankan `adb pair <ip:port_pairing> <kode>` SEKALI,
#      lalu `adb connect <ip:port_koneksi>` (port koneksi BEDA dari port
#      pairing, biasanya ditampilkan terpisah di layar yang sama).
#
# Kedua jalur menghasilkan device yang sama-sama muncul di `adb devices`
# dengan serial berformat "ip:port" (bukan serial USB biasa), sehingga semua
# fungsi lain di modul ini (push_file, scan_media, dst.) otomatis bekerja
# tanpa perubahan apa pun — mereka hanya butuh 'serial' yang valid & online.
#
# Setting yang dipakai (tersimpan permanen di tabel `settings`, BUKAN
# variabel sementara, sehingga tidak reset saat aplikasi ditutup):
#   - connection_mode   : "usb" atau "wifi" (default "wifi")
#   - wifi_last_ip      : IP:port terakhir yang berhasil connect (utk isi
#                         ulang otomatis di form pengaturan)


def get_connection_mode():
    """
    Ambil mode koneksi aktif dari settings ('connection_mode').
    Selalu mengembalikan nilai valid; fallback ke default ('wifi') jika
    kosong/tidak dikenal (mis. DB lama yang belum punya setting ini).
    """
    mode = (get_setting("connection_mode") or "").strip().lower()
    if mode not in CONNECTION_MODES:
        return CONNECTION_MODE_DEFAULT
    return mode


def _validate_ip_port(ip_port):
    """
    Validasi ringan format 'ip:port' atau 'host:port' sebelum dipakai di
    perintah shell. Mengembalikan (ok, pesan_error_jika_gagal).
    """
    value = (ip_port or "").strip()
    if not value:
        return False, "Alamat IP:Port tidak boleh kosong."
    # Longgar: terima IPv4 atau hostname, wajib ada titik dua + port numerik.
    if not re.match(r"^[A-Za-z0-9_.\-]+:\d{2,5}$", value):
        return False, "Format harus <ip>:<port>, contoh: 192.168.1.10:5555"
    return True, None


def tcpip_enable(serial, port=None):
    """
    Aktifkan mode TCP/IP di HP (`adb tcpip <port>`). WAJIB dijalankan lewat
    koneksi USB yang sedang aktif — ini "menyalakan" listener WiFi di HP.

    Setelah sukses, HP akan mulai menerima koneksi ADB lewat WiFi di port
    tsb selama HP tidak reboot. Panggil connect_wifi() setelahnya (boleh
    setelah kabel USB dicabut, asalkan HP & PC di jaringan WiFi yang sama).

    Return dict hasil eksekusi (ok/stdout/stderr/dll), sama seperti _run().
    """
    port = int(port or DEFAULT_TCPIP_PORT)
    if not serial:
        return {"ok": False, "stdout": "", "stderr": "Serial HP (USB) tidak tersedia.", "code": -20}
    if not is_device_online(serial):
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"HP (serial {serial}) tidak online via USB. Colokkan HP & aktifkan USB Debugging dulu.",
            "code": -21,
        }
    res = _run(["-s", serial, "tcpip", str(port)], timeout=WIFI_TIMEOUT)
    res["port"] = port
    return res


def connect_wifi(ip_port):
    """
    Sambungkan ke HP lewat WiFi (`adb connect <ip:port>`).
    Dipakai baik setelah tcpip_enable() maupun setelah pair_wifi().

    Return dict: { ok, stdout, stderr, code, ip_port }
    """
    ok, err = _validate_ip_port(ip_port)
    if not ok:
        return {"ok": False, "stdout": "", "stderr": err, "code": -22, "ip_port": ip_port}

    res = _run(["connect", ip_port], timeout=WIFI_TIMEOUT)
    res["ip_port"] = ip_port
    # `adb connect` kadang exit code 0 walau gagal (pesan error ada di stdout).
    combined = f"{res.get('stdout', '')} {res.get('stderr', '')}".lower()
    if "connected to" not in combined and "already connected" not in combined:
        res["ok"] = False
        if not res.get("stderr"):
            res["stderr"] = res.get("stdout") or "Gagal terhubung. Pastikan IP:Port benar & satu jaringan WiFi."
    if res["ok"]:
        set_setting_safe("wifi_last_ip", ip_port)
    return res


def pair_wifi(ip_port_pairing, pairing_code):
    """
    Pairing manual TANPA kabel USB (Android 11+), lewat kode 6 digit yang
    ditampilkan di menu Setelan > Opsi Pengembang > Debugging Nirkabel >
    "Pasangkan perangkat dengan kode pairing".

    `ip_port_pairing` adalah ip:port KHUSUS PAIRING yang tampil di layar
    yang sama (BEDA dari ip:port untuk connect_wifi() setelahnya).

    Return dict: { ok, stdout, stderr, code, ip_port }
    """
    ok, err = _validate_ip_port(ip_port_pairing)
    if not ok:
        return {"ok": False, "stdout": "", "stderr": err, "code": -23, "ip_port": ip_port_pairing}

    code = (pairing_code or "").strip()
    if not code or not code.isdigit():
        return {
            "ok": False,
            "stdout": "",
            "stderr": "Kode pairing harus berupa angka (lihat di HP: Debugging Nirkabel > Pasangkan dgn kode).",
            "code": -24,
            "ip_port": ip_port_pairing,
        }

    res = _run(["pair", ip_port_pairing, code], timeout=WIFI_TIMEOUT)
    res["ip_port"] = ip_port_pairing
    combined = f"{res.get('stdout', '')} {res.get('stderr', '')}".lower()
    if "successfully paired" not in combined:
        res["ok"] = False
        if not res.get("stderr"):
            res["stderr"] = res.get("stdout") or "Pairing gagal. Cek kode & IP:Port pairing masih berlaku (kode kedaluwarsa cepat)."
    return res


def disconnect_wifi(ip_port=None):
    """
    Putuskan koneksi WiFi. Jika ip_port kosong, putuskan SEMUA koneksi WiFi
    (`adb disconnect` tanpa argumen) — tidak memengaruhi HP yang tersambung
    via USB.

    Return dict hasil eksekusi.
    """
    args = ["disconnect"]
    if ip_port:
        ok, err = _validate_ip_port(ip_port)
        if not ok:
            return {"ok": False, "stdout": "", "stderr": err, "code": -25}
        args.append(ip_port)
    res = _run(args, timeout=WIFI_TIMEOUT)
    return res


def set_setting_safe(key, value):
    """Simpan setting tanpa membuat adb.py bergantung sirkular ke atas."""
    from database.db import set_setting as _set_setting
    _set_setting(key, value)
