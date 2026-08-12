"""
services/scrcpy.py — Mirroring layar HP via scrcpy (cross-platform Ubuntu/Windows)

scrcpy adalah aplikasi desktop terpisah yang menampilkan layar HP di komputer.
Web app tidak bisa menanamkan jendela scrcpy ke dalam browser (batasan browser),
jadi pendekatannya: aplikasi MELUNCURKAN scrcpy untuk serial HP tertentu, dan
jendela scrcpy muncul terpisah. Tujuannya supaya user tidak perlu buka terminal
/ ketik perintah scrcpy manual — cukup klik tombol Mirror di aplikasi.

Anti jendela dobel:
- Aplikasi mengingat proses scrcpy yang sedang hidup untuk tiap serial.
- Klik Mirror lagi pada HP yang jendelanya masih terbuka → TIDAK buka jendela
  baru; mencoba memunculkan (focus) jendela yang sudah ada (best-effort).
- Jika jendela sebelumnya sudah ditutup → buka baru lagi.

Opsi hemat daya & anti-sleep (v1.1.2):
- Setting 'scrcpy_mode' menentukan flag tambahan yang dipakai saat launch:
    * "stay_awake" (default) → --stay-awake
        HP tidak akan sleep selama jendela mirror terbuka, jadi mouse &
        keyboard tetap responsif tanpa harus menyentuh HP.
    * "stay_awake_screen_off" → --stay-awake --turn-screen-off
        Sama seperti di atas, TAPI layar fisik HP dimatikan agar hemat
        listrik. Mirror di komputer tetap jalan normal.

Tuning performa realtime (PATCH v1.1.5):
- Setiap launch() SELALU menambahkan PERFORMANCE_ARGS (lihat definisinya di
  bawah) supaya mirror mendekati real-time di kombinasi USB kabel + HP kelas
  menengah-bawah (mis. Redmi 9T & sekelasnya). Sebelumnya scrcpy diluncurkan
  tanpa satupun flag performa (resolusi native + bitrate tak terbatas + fps
  tak terbatas + audio ikut di-stream), yang di HP ber-chipset budget bikin
  encoder HP keteteran dan delay terasa besar walau sudah pakai kabel USB.

Fungsi utama:
- get_scrcpy_path()  : path scrcpy (override dari settings / default sesuai OS)
- get_scrcpy_mode()  : mode aktif (stay_awake / stay_awake_screen_off)
- mode_args()        : daftar argumen scrcpy sesuai mode aktif
- is_available()     : cek scrcpy terinstall atau tidak
- launch(serial)     : luncurkan/aktifkan scrcpy untuk 1 serial (non-blocking)
- close(serial)      : tutup jendela scrcpy untuk 1 serial
- active_serials()   : daftar serial yang jendelanya sedang terbuka
- paste_clipboard()   : fokus scrcpy lalu kirim Ctrl+V dari clipboard PC
"""
import os
import platform
import re
import shutil
import subprocess
import threading
import time

from database.db import get_setting

# Registry proses scrcpy yang sedang hidup, per serial.
#   { serial: { "proc": Popen, "title": str } }
# Diakses lewat lock karena Flask bisa melayani >1 request paralel.
_PROCS = {}
_LOCK = threading.Lock()
_PASTE_LOCK = threading.Lock()

# Judul jendela unik supaya bisa dicari & difokuskan oleh window manager.
_TITLE_PREFIX = "RemoteHP-Mirror"

# ── Mode anti-sleep & hemat daya (v1.1.2) ──
# Nilai setting 'scrcpy_mode' yang valid beserta argumen scrcpy-nya.
SCRCPY_MODE_DEFAULT = "stay_awake"
SCRCPY_MODES = {
    # Anti-sleep saja: HP tetap "bangun" selama mirroring, layar HP tetap nyala.
    "stay_awake": ["--stay-awake"],
    # Anti-sleep + layar HP dimatikan (hemat listrik). Mirror di PC tetap jalan.
    "stay_awake_screen_off": ["--stay-awake", "--turn-screen-off"],
}

# ── Tuning performa mirror — REALTIME untuk USB + HP kelas menengah-bawah ──
# (PATCH v1.1.5) Target device: HP non-flagship (mis. Redmi 9T & sekelasnya —
# chipset MediaTek Helio G-series / Snapdragon 4xx), selalu disambung via
# kabel USB (bukan WiFi).
#
# Alasan tuning ini penting khusus utk HP kelas ini: hardware H.264 encoder
# di chipset budget MASIH ADA, tapi gampang "keteteran" kalau dipaksa encode
# resolusi native (1080p+) + bitrate tinggi + 60fps sekaligus. Begitu encoder
# keteteran, ia mulai antre/drop frame — itu yang terasa sebagai LAG, WALAUPUN
# sudah pakai kabel USB (jadi bukan masalah koneksi, tapi beban encode di HP).
# Menurunkan resolusi & bitrate & fps kerja encoder jauh lebih ringan, hasilnya
# delay-nya turun drastis mendekati real-time (biasanya <100ms via USB).
PERFORMANCE_ARGS = [
    "--video-codec=h264",     # paling ringan & pasti hardware-accelerated di chipset budget (hindari h265/av1 yang kadang jatuh ke software encode di chipset murah -> lebih lambat)
    "--max-size=720",         # turunkan sisi terpanjang video jadi 720px -> beban encode turun drastis dibanding native 1080p+
    "--video-bit-rate=2M",    # bitrate rendah -> buffer kecil -> delay kecil (2 Mbps masih cukup jernih utk kerja/monitoring, bukan nonton film)
    "--max-fps=30",           # 30fps cukup utk kerja & jauh lebih ringan drpd 60fps bagi encoder budget
    "--no-audio",             # skip 1 pipeline decode audio penuh -> kurangi overhead & potensi desync
    "--video-buffer=0",       # matikan buffer smoothing di sisi PC -> tampilkan frame secepat diterima (trade-off: sedikit lebih rentan micro-stutter drpd delay besar tapi mulus)
]


def get_scrcpy_path():
    """
    Tentukan path scrcpy.
    1. Pakai override dari settings ('scrcpy_path') jika diisi.
    2. Jika tidak, gunakan default sesuai OS.
    """
    custom = (get_setting("scrcpy_path") or "").strip()
    if custom:
        return custom
    if platform.system() == "Windows":
        return "scrcpy.exe"
    return "scrcpy"


def get_scrcpy_mode():
    """
    Ambil mode mirror aktif dari settings ('scrcpy_mode').
    Selalu mengembalikan nilai valid; fallback ke default jika kosong/tidak
    dikenal (mis. DB lama yang belum punya setting ini).
    """
    mode = (get_setting("scrcpy_mode") or "").strip()
    if mode not in SCRCPY_MODES:
        return SCRCPY_MODE_DEFAULT
    return mode


def mode_args():
    """Daftar argumen scrcpy sesuai mode aktif (mis. ['--stay-awake'])."""
    return list(SCRCPY_MODES[get_scrcpy_mode()])


def is_available():
    """
    Cek apakah scrcpy bisa ditemukan & dijalankan.
    Return dict: { ok: bool, version: str, error: str }
    """
    path = get_scrcpy_path()
    if os.path.sep not in path and not shutil.which(path):
        return {
            "ok": False,
            "version": None,
            "error": "scrcpy tidak ditemukan. Install scrcpy atau set path di Pengaturan.",
        }
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        first_line = (result.stdout or result.stderr or "").splitlines()
        version = first_line[0].strip() if first_line else "scrcpy"
        return {"ok": True, "version": version, "error": None}
    except FileNotFoundError:
        return {
            "ok": False,
            "version": None,
            "error": "scrcpy tidak ditemukan. Install scrcpy atau set path di Pengaturan.",
        }
    except subprocess.TimeoutExpired:
        return {"ok": True, "version": "scrcpy", "error": None}
    except Exception as e:
        return {"ok": False, "version": None, "error": str(e)}


def _window_title(serial, title):
    """Judul jendela unik per serial agar bisa dicari window manager."""
    label = title or serial or "HP"
    # Hindari karakter aneh di title
    safe = "".join(c for c in label if c.isalnum() or c in " -_.").strip()
    return f"{_TITLE_PREFIX}: {safe}"


def _is_alive(entry):
    """True jika proses scrcpy di entry masih berjalan."""
    proc = entry.get("proc") if entry else None
    return bool(proc) and proc.poll() is None


# Layout otomatis mirror (v1.34)
# Tujuan: tombol Mirror langsung merapikan ruang kerja. Browser Remote HP
# menempati sisi kiri, sedangkan scrcpy didok ke kanan setinggi area kerja
# monitor. Rasio HP dibaca dari `adb shell wm size`; fallback 9:20.
_DEFAULT_PHONE_RATIO = 9 / 20
_MIN_MIRROR_WIDTH = 360
_MAX_MIRROR_WIDTH_FRACTION = 0.45


def _device_portrait_ratio(serial):
    """Ambil rasio sisi pendek/panjang layar HP; fallback aman bila ADB gagal."""
    if not serial:
        return _DEFAULT_PHONE_RATIO
    try:
        # Import lokal menghindari ketergantungan silang saat modul dimuat.
        from services import adb as adb_service

        result = subprocess.run(
            [adb_service.get_adb_path(), "-s", serial, "shell", "wm", "size"],
            capture_output=True,
            text=True,
            timeout=4,
        )
        text = "\n".join(part for part in (result.stdout, result.stderr) if part)
        matches = re.findall(r"(\d+)\s*x\s*(\d+)", text)
        if matches:
            # Android menaruh "Override size" setelah "Physical size"; hasil
            # terakhir adalah ukuran efektif yang paling relevan.
            width, height = map(int, matches[-1])
            short, long = sorted((width, height))
            if short > 0 and long > 0:
                ratio = short / long
                if 0.30 <= ratio <= 0.80:
                    return ratio
    except Exception:
        pass
    return _DEFAULT_PHONE_RATIO


def _layout_from_work_area(work_area, serial=None, browser_hwnd=None):
    """Hitung geometri split kiri/kanan dari work area (left, top, right, bottom)."""
    left, top, right, bottom = work_area
    work_width = max(1, right - left)
    work_height = max(1, bottom - top)
    ratio = _device_portrait_ratio(serial)

    # Tambah sedikit ruang untuk frame/title bar scrcpy. Lebar dibatasi agar
    # browser tetap nyaman dipakai walau HP punya layar relatif lebar.
    mirror_width = int(round(work_height * ratio)) + 18
    mirror_width = max(_MIN_MIRROR_WIDTH, mirror_width)
    mirror_width = min(mirror_width, int(work_width * _MAX_MIRROR_WIDTH_FRACTION))
    browser_width = max(1, work_width - mirror_width)

    return {
        "work_left": left,
        "work_top": top,
        "work_width": work_width,
        "work_height": work_height,
        "browser_x": left,
        "browser_y": top,
        "browser_width": browser_width,
        "browser_height": work_height,
        "browser_hwnd": browser_hwnd,
        "mirror_x": left + browser_width,
        "mirror_y": top,
        "mirror_width": mirror_width,
        "mirror_height": work_height,
    }


def _windows_visible_windows():
    """Return [(hwnd, title)] untuk top-level window Windows yang terlihat."""
    if platform.system() != "Windows":
        return []
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        found = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        user32.EnumWindows.restype = wintypes.BOOL

        def enum_proc(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.strip()
            if title:
                found.append((int(hwnd), title))
            return True

        user32.EnumWindows(callback_type(enum_proc), 0)
        return found
    except Exception:
        return []


def _windows_find_window(title_part, exclude_prefix=None):
    """Cari HWND terlihat berdasarkan substring title, case-insensitive."""
    needle = (title_part or "").casefold()
    for hwnd, title in _windows_visible_windows():
        folded = title.casefold()
        if needle and needle not in folded:
            continue
        if exclude_prefix and folded.startswith(exclude_prefix.casefold()):
            continue
        return hwnd
    return None


def _windows_browser_window():
    """Cari jendela browser yang sedang menampilkan Remote HP."""
    # Title HTML selalu "Remote HP vX.Y". Exclude title khusus scrcpy.
    return _windows_find_window("Remote HP", exclude_prefix=_TITLE_PREFIX)


def _windows_work_area(hwnd=None):
    """Work area monitor tempat browser berada; fallback primary monitor."""
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        MONITOR_DEFAULTTOPRIMARY = 1
        user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        user32.MonitorFromWindow.restype = wintypes.HANDLE
        user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
        user32.GetMonitorInfoW.restype = wintypes.BOOL
        monitor = user32.MonitorFromWindow(wintypes.HWND(hwnd or 0), MONITOR_DEFAULTTOPRIMARY)
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if monitor and user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            rect = info.rcWork
            return int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)
    except Exception:
        pass
    # Fallback umum bila WinAPI gagal.
    return (0, 0, 1920, 1080)


def _linux_work_area():
    """Best-effort work area desktop Linux (X11/XWayland)."""
    try:
        if shutil.which("xprop"):
            result = subprocess.run(
                ["xprop", "-root", "_NET_WORKAREA"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            values = [int(x) for x in re.findall(r"-?\d+", result.stdout or "")]
            if len(values) >= 4 and values[2] > 0 and values[3] > 0:
                x, y, width, height = values[:4]
                return (x, y, x + width, y + height)
        if shutil.which("xdotool"):
            result = subprocess.run(
                ["xdotool", "getdisplaygeometry"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            parts = (result.stdout or "").split()
            if len(parts) >= 2:
                width, height = int(parts[0]), int(parts[1])
                return (0, 0, width, height)
    except Exception:
        pass
    return (0, 0, 1920, 1080)


def _recommended_layout(serial=None):
    """Geometri awal untuk argumen --window-* scrcpy."""
    system = platform.system()
    if system == "Windows":
        browser_hwnd = _windows_browser_window()
        return _layout_from_work_area(
            _windows_work_area(browser_hwnd), serial=serial, browser_hwnd=browser_hwnd
        )
    if system == "Linux":
        return _layout_from_work_area(_linux_work_area(), serial=serial)
    return None


def _windows_visible_frame_insets(hwnd):
    """Selisih outer window terhadap frame yang benar-benar terlihat.

    Windows 10/11 menyertakan resize border transparan dan bayangan DWM di
    ``GetWindowRect``. Jika koordinat outer window ditempatkan tepat di tepi
    monitor, frame visualnya masih tampak berjarak sekitar 7-10 px. Ambil
    ``DWMWA_EXTENDED_FRAME_BOUNDS`` agar layout dapat dikompensasi berdasarkan
    frame visual, bukan kotak transparan tersebut.
    """
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        dwmapi = ctypes.windll.dwmapi
        outer = wintypes.RECT()
        visible = wintypes.RECT()

        user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        user32.GetWindowRect.restype = wintypes.BOOL
        dwmapi.DwmGetWindowAttribute.argtypes = [
            wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
        ]
        dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long

        if not user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(outer)):
            return (0, 0, 0, 0)

        DWMWA_EXTENDED_FRAME_BOUNDS = 9
        result = dwmapi.DwmGetWindowAttribute(
            wintypes.HWND(hwnd),
            DWMWA_EXTENDED_FRAME_BOUNDS,
            ctypes.byref(visible),
            ctypes.sizeof(visible),
        )
        if result != 0:
            return (0, 0, 0, 0)

        # Batasi kompensasi agar data DWM yang aneh tidak dapat membuat window
        # membesar ekstrem. Resize border normal Windows hanya beberapa piksel.
        left = max(0, min(32, int(visible.left - outer.left)))
        top = max(0, min(32, int(visible.top - outer.top)))
        right = max(0, min(32, int(outer.right - visible.right)))
        bottom = max(0, min(32, int(outer.bottom - visible.bottom)))
        return (left, top, right, bottom)
    except Exception:
        return (0, 0, 0, 0)


def _windows_move_visible_frame(hwnd, x, y, width, height):
    """Pindahkan window sehingga frame visual tepat memenuhi target rectangle."""
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.MoveWindow.argtypes = [
            wintypes.HWND, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, wintypes.BOOL,
        ]
        user32.MoveWindow.restype = wintypes.BOOL

        inset_left, inset_top, inset_right, inset_bottom = _windows_visible_frame_insets(hwnd)
        outer_x = int(x) - inset_left
        outer_y = int(y) - inset_top
        outer_width = max(1, int(width) + inset_left + inset_right)
        outer_height = max(1, int(height) + inset_top + inset_bottom)
        return bool(user32.MoveWindow(
            wintypes.HWND(hwnd),
            outer_x,
            outer_y,
            outer_width,
            outer_height,
            True,
        ))
    except Exception:
        return False


def _arrange_windows_windows(win_title, serial=None):
    """Split browser di kiri dan dock scrcpy di kanan pada monitor yang sama."""
    try:
        import ctypes

        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.ShowWindow.restype = wintypes.BOOL
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow.restype = wintypes.BOOL
        mirror_hwnd = _windows_find_window(win_title)
        if not mirror_hwnd:
            return False
        browser_hwnd = _windows_browser_window()
        layout = _layout_from_work_area(
            _windows_work_area(browser_hwnd or mirror_hwnd),
            serial=serial,
            browser_hwnd=browser_hwnd,
        )

        SW_RESTORE = 9
        if browser_hwnd and browser_hwnd != mirror_hwnd:
            user32.ShowWindow(wintypes.HWND(browser_hwnd), SW_RESTORE)
            _windows_move_visible_frame(
                browser_hwnd,
                layout["browser_x"],
                layout["browser_y"],
                layout["browser_width"],
                layout["browser_height"],
            )

        user32.ShowWindow(wintypes.HWND(mirror_hwnd), SW_RESTORE)
        moved = _windows_move_visible_frame(
            mirror_hwnd,
            layout["mirror_x"],
            layout["mirror_y"],
            layout["mirror_width"],
            layout["mirror_height"],
        )
        user32.SetForegroundWindow(wintypes.HWND(mirror_hwnd))
        return bool(moved)
    except Exception:
        return False


def _linux_find_window_id(title_part, exclude_prefix=None):
    if not shutil.which("xdotool"):
        return None
    try:
        result = subprocess.run(
            ["xdotool", "search", "--name", title_part],
            capture_output=True,
            text=True,
            timeout=4,
        )
        ids = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
        for window_id in reversed(ids):
            if exclude_prefix:
                name = subprocess.run(
                    ["xdotool", "getwindowname", window_id],
                    capture_output=True,
                    text=True,
                    timeout=2,
                ).stdout.strip()
                if name.casefold().startswith(exclude_prefix.casefold()):
                    continue
            return window_id
    except Exception:
        pass
    return None


def _arrange_windows_linux(win_title, serial=None):
    """Best-effort split pada desktop Linux yang mengizinkan kontrol X11."""
    if not shutil.which("xdotool"):
        return False
    mirror_id = _linux_find_window_id(win_title)
    if not mirror_id:
        return False
    browser_id = _linux_find_window_id("Remote HP", exclude_prefix=_TITLE_PREFIX)
    layout = _layout_from_work_area(_linux_work_area(), serial=serial)
    try:
        if browser_id and browser_id != mirror_id:
            subprocess.run(
                [
                    "xdotool", "windowmove", browser_id,
                    str(layout["browser_x"]), str(layout["browser_y"]),
                    "windowsize", browser_id,
                    str(layout["browser_width"]), str(layout["browser_height"]),
                ],
                capture_output=True,
                timeout=5,
            )
        result = subprocess.run(
            [
                "xdotool", "windowmove", mirror_id,
                str(layout["mirror_x"]), str(layout["mirror_y"]),
                "windowsize", mirror_id,
                str(layout["mirror_width"]), str(layout["mirror_height"]),
                "windowactivate", "--sync", mirror_id,
            ],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _arrange_scrcpy_and_browser(win_title, serial=None):
    system = platform.system()
    if system == "Windows":
        return _arrange_windows_windows(win_title, serial=serial)
    if system == "Linux":
        return _arrange_windows_linux(win_title, serial=serial)
    return False


def _arrange_after_launch(win_title, serial=None):
    """Tunggu window scrcpy muncul, lalu terapkan layout. Berjalan di thread daemon."""
    for _ in range(40):  # maksimal sekitar 5 detik
        time.sleep(0.125)
        if _arrange_scrcpy_and_browser(win_title, serial=serial):
            return


def launch(serial=None, title=None, extra_args=None):
    """
    Luncurkan scrcpy untuk 1 HP (berdasarkan serial). NON-BLOCKING.

    Jika jendela untuk serial ini SUDAH terbuka & masih hidup → tidak membuka
    jendela baru, dan mencoba memunculkannya ke depan (best-effort).

    Return dict:
      { ok: bool, already_open: bool, focused: bool, error: str }
    """
    avail = is_available()
    if not avail["ok"]:
        return {"ok": False, "already_open": False, "focused": False, "error": avail["error"]}

    win_title = _window_title(serial, title)

    with _LOCK:
        entry = _PROCS.get(serial)
        if _is_alive(entry):
            # Sudah ada jendela hidup → jangan buka baru. Klik Mirror juga
            # merapikan ulang split browser + scrcpy, lalu memfokuskannya.
            saved_title = entry.get("title", win_title)
            focused = _arrange_scrcpy_and_browser(saved_title, serial=serial)
            if not focused:
                focused = _try_focus_window(saved_title)
            return {
                "ok": True,
                "already_open": True,
                "focused": focused,
                "error": None,
            }

        # Tidak ada / sudah mati → bersihkan lalu buka baru.
        if entry:
            _PROCS.pop(serial, None)

        path = get_scrcpy_path()
        cmd = [path]
        if serial:
            cmd += ["--serial", serial]
        cmd += ["--window-title", win_title]

        # Posisi awal v1.34: scrcpy langsung tampil di kanan setinggi work area.
        # Thread arranger di bawah akan menyempurnakan posisi setelah window siap
        # sekaligus merapikan browser Remote HP ke sisi kiri.
        layout = _recommended_layout(serial)
        if layout:
            cmd += [
                f"--window-x={layout['mirror_x']}",
                f"--window-y={layout['mirror_y']}",
                f"--window-width={layout['mirror_width']}",
                f"--window-height={layout['mirror_height']}",
            ]

        # Mode anti-sleep / hemat daya (v1.1.2): --stay-awake [+ --turn-screen-off]
        cmd += mode_args()
        # Tuning performa realtime utk USB + HP kelas bawah (PATCH v1.1.5)
        cmd += PERFORMANCE_ARGS
        if extra_args:
            cmd += list(extra_args)

        try:
            proc = _spawn_detached(cmd)
        except FileNotFoundError:
            return {"ok": False, "already_open": False, "focused": False,
                    "error": "scrcpy tidak ditemukan saat menjalankan."}
        except Exception as e:
            return {"ok": False, "already_open": False, "focused": False, "error": str(e)}

        _PROCS[serial] = {"proc": proc, "title": win_title}
        threading.Thread(
            target=_arrange_after_launch,
            args=(win_title, serial),
            daemon=True,
            name=f"scrcpy-layout-{serial or 'device'}",
        ).start()
        return {"ok": True, "already_open": False, "focused": False, "error": None}


def close(serial):
    """
    Tutup jendela scrcpy untuk 1 serial (jika ada).
    Return dict: { ok: bool, closed: bool }
    """
    with _LOCK:
        entry = _PROCS.pop(serial, None)
    if not entry:
        return {"ok": True, "closed": False}
    proc = entry.get("proc")
    if proc and proc.poll() is None:
        try:
            proc.terminate()
        except Exception:
            pass
    return {"ok": True, "closed": True}


def active_serials():
    """Daftar serial yang jendelanya sedang terbuka & hidup."""
    out = []
    with _LOCK:
        dead = []
        for serial, entry in _PROCS.items():
            if _is_alive(entry):
                out.append(serial)
            else:
                dead.append(serial)
        for s in dead:
            _PROCS.pop(s, None)
    return out


def paste_clipboard(serial=None, title=None, focus_delay_ms=0):
    """
    Fokuskan jendela scrcpy untuk HP yang dipilih lalu kirim Ctrl+V.

    Clipboard harus sudah diisi oleh browser sebelum fungsi ini dipanggil.
    Fungsi hanya memastikan proses teknis fokus + pengiriman shortcut berhasil;
    isi kolom aplikasi Android tetap diverifikasi secara visual oleh pengguna.

    Return dict:
      { ok: bool, focused: bool, pasted: bool, error: str }
    """
    if not serial:
        return {
            "ok": False,
            "focused": False,
            "pasted": False,
            "error": "Serial HP tidak tersedia.",
        }

    # Gunakan judul yang tersimpan saat scrcpy diluncurkan. Jika registry proses
    # kosong (mis. aplikasi Flask baru restart), bangun kembali judul dari data HP.
    win_title = _window_title(serial, title)
    with _LOCK:
        entry = _PROCS.get(serial)
        if entry and entry.get("title"):
            win_title = entry["title"]

    delay_ms = max(0, min(int(focus_delay_ms if focus_delay_ms is not None else 0), 1500))
    system = platform.system()

    # Satu operasi paste pada satu waktu agar fokus jendela tidak saling berebut.
    with _PASTE_LOCK:
        try:
            if system == "Windows":
                return _paste_clipboard_windows(win_title, delay_ms)
            if system == "Linux":
                return _paste_clipboard_linux(win_title, delay_ms)
            return {
                "ok": False,
                "focused": False,
                "pasted": False,
                "error": f"Tempel otomatis belum didukung di {system or 'OS ini'}.",
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "focused": False,
                "pasted": False,
                "error": "Timeout saat memfokuskan scrcpy atau mengirim Ctrl+V.",
            }
        except Exception as exc:
            return {
                "ok": False,
                "focused": False,
                "pasted": False,
                "error": f"Gagal menempelkan caption: {exc}",
            }


def _windows_focus_hwnd(hwnd):
    """Aktifkan HWND memakai WinAPI native tanpa menjalankan PowerShell.

    ``SetForegroundWindow`` dapat ditolak Windows ketika request berasal dari
    thread Flask yang bukan pemilik window aktif. Karena itu fungsi mencoba
    jalur cepat terlebih dahulu, lalu sementara menggabungkan input thread
    foreground/target sebagai fallback. Seluruh operasi memakai ``ctypes``
    bawaan Python sehingga tidak bergantung pada PATH atau executable eksternal.
    """
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        user32.IsWindow.argtypes = [wintypes.HWND]
        user32.IsWindow.restype = wintypes.BOOL
        user32.IsIconic.argtypes = [wintypes.HWND]
        user32.IsIconic.restype = wintypes.BOOL
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.ShowWindow.restype = wintypes.BOOL
        user32.BringWindowToTop.argtypes = [wintypes.HWND]
        user32.BringWindowToTop.restype = wintypes.BOOL
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow.restype = wintypes.BOOL
        user32.SetActiveWindow.argtypes = [wintypes.HWND]
        user32.SetActiveWindow.restype = wintypes.HWND
        user32.SetFocus.argtypes = [wintypes.HWND]
        user32.SetFocus.restype = wintypes.HWND
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.c_void_p]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
        user32.AttachThreadInput.restype = wintypes.BOOL
        kernel32.GetCurrentThreadId.restype = wintypes.DWORD

        target = wintypes.HWND(hwnd)
        if not user32.IsWindow(target):
            return False

        SW_RESTORE = 9
        if user32.IsIconic(target):
            user32.ShowWindow(target, SW_RESTORE)

        # Jalur tercepat; umumnya cukup bila scrcpy baru saja dipakai.
        user32.BringWindowToTop(target)
        user32.SetForegroundWindow(target)
        user32.SetActiveWindow(target)
        if int(user32.GetForegroundWindow() or 0) == int(hwnd):
            return True

        # Fallback untuk foreground-lock Windows.
        current_tid = int(kernel32.GetCurrentThreadId() or 0)
        foreground_hwnd = user32.GetForegroundWindow()
        foreground_tid = int(
            user32.GetWindowThreadProcessId(foreground_hwnd, None)
            if foreground_hwnd else 0
        )
        target_tid = int(user32.GetWindowThreadProcessId(target, None) or 0)
        attached = []
        try:
            for other_tid in (foreground_tid, target_tid):
                if other_tid and current_tid and other_tid != current_tid:
                    if user32.AttachThreadInput(current_tid, other_tid, True):
                        attached.append(other_tid)

            user32.BringWindowToTop(target)
            user32.SetForegroundWindow(target)
            user32.SetActiveWindow(target)
            user32.SetFocus(target)
        finally:
            for other_tid in reversed(attached):
                user32.AttachThreadInput(current_tid, other_tid, False)

        return int(user32.GetForegroundWindow() or 0) == int(hwnd)
    except Exception:
        return False


def _windows_send_ctrl_v():
    """Kirim Ctrl+V melalui WinAPI ``SendInput``; tanpa proses eksternal."""
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        ULONG_PTR = wintypes.WPARAM

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR),
            ]

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR),
            ]

        class HARDWAREINPUT(ctypes.Structure):
            _fields_ = [
                ("uMsg", wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD),
            ]

        class INPUT_UNION(ctypes.Union):
            _fields_ = [
                ("mi", MOUSEINPUT),
                ("ki", KEYBDINPUT),
                ("hi", HARDWAREINPUT),
            ]

        class INPUT(ctypes.Structure):
            _anonymous_ = ("u",)
            _fields_ = [("type", wintypes.DWORD), ("u", INPUT_UNION)]

        INPUT_KEYBOARD = 1
        KEYEVENTF_KEYUP = 0x0002
        VK_CONTROL = 0x11
        VK_V = 0x56

        events = (INPUT * 4)(
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_CONTROL, 0, 0, 0, 0)),
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_V, 0, 0, 0, 0)),
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_V, 0, KEYEVENTF_KEYUP, 0, 0)),
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0, 0)),
        )
        user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
        user32.SendInput.restype = wintypes.UINT
        sent = int(user32.SendInput(len(events), events, ctypes.sizeof(INPUT)))
        return sent == len(events)
    except Exception:
        return False


def _paste_clipboard_windows(win_title, delay_ms):
    """Aktifkan scrcpy dan kirim Ctrl+V via WinAPI native yang sangat cepat.

    Versi lama membuat proses ``powershell`` untuk setiap paste. Selain lambat,
    itu memunculkan ``[WinError 2]`` ketika PowerShell tidak ada di PATH.
    Implementasi ini hanya memakai library standar Python + user32.dll.
    """
    hwnd = _windows_find_window(win_title)
    if not hwnd:
        return {
            "ok": False,
            "focused": False,
            "pasted": False,
            "error": "Jendela scrcpy untuk HP ini tidak ditemukan. Buka Mirror terlebih dahulu.",
        }

    if not _windows_focus_hwnd(hwnd):
        return {
            "ok": False,
            "focused": False,
            "pasted": False,
            "error": "Jendela scrcpy ditemukan, tetapi gagal dipindahkan ke depan.",
        }

    # Default aplikasi adalah 0 ms. Parameter dipertahankan untuk kompatibilitas.
    if delay_ms > 0:
        time.sleep(delay_ms / 1000.0)

    if not _windows_send_ctrl_v():
        return {
            "ok": False,
            "focused": True,
            "pasted": False,
            "error": "Windows gagal mengirim Ctrl+V ke scrcpy.",
        }

    return {"ok": True, "focused": True, "pasted": True, "error": None}

def _paste_clipboard_linux(win_title, delay_ms):
    """Aktifkan jendela scrcpy dan kirim Ctrl+V memakai xdotool (X11/XWayland)."""
    if not shutil.which("xdotool"):
        return {
            "ok": False,
            "focused": False,
            "pasted": False,
            "error": "xdotool belum terpasang. Jalankan setup-ubuntu.sh lagi atau install: sudo apt install xdotool",
        }

    search = subprocess.run(
        ["xdotool", "search", "--name", win_title],
        capture_output=True,
        text=True,
        timeout=5,
    )
    window_ids = [line.strip() for line in search.stdout.splitlines() if line.strip()]
    if search.returncode != 0 or not window_ids:
        return {
            "ok": False,
            "focused": False,
            "pasted": False,
            "error": "Jendela scrcpy untuk HP ini tidak ditemukan. Buka Mirror terlebih dahulu.",
        }

    # Ambil hasil terakhir; umumnya ini jendela paling baru jika ada lebih dari satu.
    window_id = window_ids[-1]
    activate = subprocess.run(
        ["xdotool", "windowactivate", "--sync", window_id],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if activate.returncode != 0:
        err = (activate.stderr or activate.stdout or "").strip()
        return {
            "ok": False,
            "focused": False,
            "pasted": False,
            "error": err or "Jendela scrcpy ditemukan, tetapi gagal dipindahkan ke depan.",
        }

    if delay_ms > 0:
        time.sleep(delay_ms / 1000.0)
    paste = subprocess.run(
        ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if paste.returncode != 0:
        err = (paste.stderr or paste.stdout or "").strip()
        return {
            "ok": False,
            "focused": True,
            "pasted": False,
            "error": err or "Gagal mengirim Ctrl+V ke jendela scrcpy.",
        }
    return {"ok": True, "focused": True, "pasted": True, "error": None}


def _try_focus_window(win_title):
    """
    Best-effort: munculkan/aktifkan jendela scrcpy yang sudah ada.
    Gagal pun tidak masalah (jendela tetap ada, hanya tidak ter-fokus).
    Return True jika perintah fokus berhasil dijalankan.
    """
    system = platform.system()
    try:
        if system == "Linux":
            # wmctrl paling umum; cocokkan sebagian judul (-F butuh judul persis,
            # jadi pakai pencarian substring default).
            if shutil.which("wmctrl"):
                r = subprocess.run(
                    ["wmctrl", "-a", win_title],
                    capture_output=True, timeout=5,
                )
                if r.returncode == 0:
                    return True
            # Alternatif: xdotool
            if shutil.which("xdotool"):
                r = subprocess.run(
                    ["xdotool", "search", "--name", win_title,
                     "windowactivate", "--sync"],
                    capture_output=True, timeout=5,
                )
                return r.returncode == 0
            return False
        elif system == "Windows":
            hwnd = _windows_find_window(win_title)
            return bool(hwnd and _windows_focus_hwnd(hwnd))
        else:
            return False
    except Exception:
        return False


def _spawn_detached(cmd):
    """
    Jalankan proses scrcpy terlepas dari proses Flask, supaya:
    - request HTTP langsung kembali (tidak menunggu jendela ditutup)
    - jendela scrcpy tetap hidup walau request selesai
    Return objek Popen.
    Cross-platform (Windows vs POSIX).
    """
    if platform.system() == "Windows":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        return subprocess.Popen(
            cmd,
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    else:
        return subprocess.Popen(
            cmd,
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
