#!/usr/bin/env bash
# ============================================================
#   Remote HP v1.50 - SETUP untuk UBUNTU / LINUX
#   Jalankan SATU KALI di komputer baru.
#
#   Cara menjalankan (pilih salah satu):
#     A. Klik 2x file ini, pilih "Run in Terminal" / "Jalankan di Terminal"
#     B. Buka Terminal di folder ini, lalu ketik:
#            chmod +x setup-ubuntu.sh
#            ./setup-ubuntu.sh
#
#   Script ini menyiapkan semua kebutuhan aplikasi:
#     - Python 3 + venv + pip   (otomatis diinstall kalau belum ada)
#     - Virtual environment (.venv) khusus aplikasi ini
#     - Library Python (Flask)
#     - ADB (Android Debug Bridge) untuk koneksi ke HP
#     - scrcpy untuk mirroring (menampilkan) layar HP di komputer
# ============================================================
set -e

# Pindah ke folder tempat script ini berada
cd "$(dirname "$(readlink -f "$0")")"

# Warna biar enak dibaca
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; B='\033[1;34m'; N='\033[0m'

echo
echo "============================================================"
echo "   REMOTE HP - SETUP UBUNTU / LINUX"
echo "============================================================"
echo
echo "  Folder aplikasi:"
echo "    $(pwd)"
echo

# Deteksi apakah perlu sudo (kalau bukan root)
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
fi

# ---------- 1. CEK & SIAPKAN PYTHON 3 (+ venv + pip) ----------
echo -e "${B}[1/5]${N} Mengecek Python 3 (beserta venv & pip)..."

NEED_APT=0
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "    ${Y}Python 3 belum terpasang.${N}"
    NEED_APT=1
else
    PYVER="$(python3 --version 2>&1)"
    echo -e "    ${G}OK${N} - $PYVER ditemukan."
    # Modul venv harus ada
    if ! python3 -m venv --help >/dev/null 2>&1; then
        echo -e "    ${Y}Modul venv belum ada.${N}"
        NEED_APT=1
    fi
    # Modul ensurepip harus ada (ini yang sering hilang di Ubuntu -> venv tanpa pip)
    if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
        echo -e "    ${Y}Modul pip/ensurepip belum lengkap.${N}"
        NEED_APT=1
    fi
fi

if [ "$NEED_APT" -eq 1 ]; then
    if command -v apt-get >/dev/null 2>&1; then
        echo "    Menginstall python3, venv, dan pip (butuh password sudo)..."
        $SUDO apt-get update
        $SUDO apt-get install -y python3 python3-venv python3-pip
        echo -e "    ${G}OK${N} - Python 3 + venv + pip siap."
    else
        echo -e "    ${R}Tidak menemukan 'apt-get'.${N}"
        echo "    Distro Anda mungkin bukan Ubuntu/Debian."
        echo "    Install paket berikut manual lalu jalankan lagi:"
        echo "      python3, python3-venv, python3-pip"
        exit 1
    fi
fi
echo

# ---------- 2. BUAT / PERBAIKI VIRTUAL ENVIRONMENT ----------
echo -e "${B}[2/5]${N} Menyiapkan virtual environment (.venv)..."

# Cek apakah .venv yang ada benar-benar sehat (punya python DAN pip).
VENV_OK=0
if [ -x ".venv/bin/python" ]; then
    if ./.venv/bin/python -m pip --version >/dev/null 2>&1; then
        VENV_OK=1
    fi
fi

if [ "$VENV_OK" -eq 1 ]; then
    echo -e "    ${G}OK${N} - .venv sudah ada & sehat, dilewati."
else
    if [ -e ".venv" ]; then
        echo -e "    ${Y}.venv lama rusak/tidak lengkap (tanpa pip) -> dibuat ulang.${N}"
        rm -rf .venv
    fi
    python3 -m venv .venv
    echo -e "    ${G}OK${N} - .venv dibuat."

    # Jaring pengaman: kalau venv ternyata tetap tanpa pip, pasang via ensurepip.
    if ! ./.venv/bin/python -m pip --version >/dev/null 2>&1; then
        echo -e "    ${Y}pip belum ada di .venv, memasang lewat ensurepip...${N}"
        ./.venv/bin/python -m ensurepip --upgrade >/dev/null 2>&1 || true
    fi
fi

# Verifikasi terakhir: pip WAJIB ada sebelum lanjut.
if ! ./.venv/bin/python -m pip --version >/dev/null 2>&1; then
    echo
    echo -e "    ${R}GAGAL menyiapkan pip di dalam .venv.${N}"
    echo "    Coba jalankan perintah ini lalu ulangi setup:"
    echo "      sudo apt-get install --reinstall python3-venv python3-pip"
    exit 1
fi
echo

# ---------- 3. INSTALL DEPENDENCY ----------
echo -e "${B}[3/5]${N} Menginstall library yang dibutuhkan..."
./.venv/bin/python -m pip install --upgrade pip >/dev/null 2>&1 || true
./.venv/bin/python -m pip install -r requirements.txt
echo -e "    ${G}OK${N} - Semua library terpasang."
echo

# ---------- 4. CEK ADB ----------
echo -e "${B}[4/5]${N} Mengecek ADB (Android Debug Bridge)..."
if command -v adb >/dev/null 2>&1; then
    echo -e "    ${G}OK${N} - ADB ditemukan: $(adb --version 2>/dev/null | head -n1)"
else
    echo -e "    ${Y}ADB belum terpasang.${N} ADB dibutuhkan untuk mengirim video ke HP."
    if command -v apt-get >/dev/null 2>&1; then
        echo "    Menginstall ADB lewat apt (android-tools-adb)..."
        $SUDO apt-get install -y android-tools-adb
        echo -e "    ${G}OK${N} - ADB terpasang."
    else
        echo "    Install ADB manual sesuai distro Anda, contoh:"
        echo "      Fedora:  sudo dnf install android-tools"
        echo "      Arch  :  sudo pacman -S android-tools"
        echo "    (Atau isi lokasi adb lewat menu Pengaturan di aplikasi nanti)"
    fi
fi
echo

# ---------- 5. CEK scrcpy (mirroring layar HP) ----------
echo -e "${B}[5/5]${N} Mengecek scrcpy (mirroring layar HP)..."
if command -v scrcpy >/dev/null 2>&1; then
    echo -e "    ${G}OK${N} - scrcpy ditemukan: $(scrcpy --version 2>/dev/null | head -n1)"
else
    echo -e "    ${Y}scrcpy belum terpasang.${N} Dibutuhkan untuk tombol 'Mirror' layar HP."
    if command -v apt-get >/dev/null 2>&1; then
        echo "    Menginstall scrcpy lewat apt..."
        $SUDO apt-get install -y scrcpy
        echo -e "    ${G}OK${N} - scrcpy terpasang."
        # wmctrl (opsional) untuk memunculkan jendela mirror yang sudah ada.
        # Tidak wajib; anti jendela-dobel tetap jalan tanpa ini.
        if ! command -v wmctrl >/dev/null 2>&1; then
            $SUDO apt-get install -y wmctrl >/dev/null 2>&1 || true
        fi
    else
        echo "    Install scrcpy manual sesuai distro Anda, contoh:"
        echo "      Fedora:  sudo dnf install scrcpy"
        echo "      Arch  :  sudo pacman -S scrcpy"
        echo "      (atau snap: sudo snap install scrcpy)"
        echo "    (Atau isi lokasi scrcpy lewat menu Pengaturan di aplikasi nanti)"
    fi
fi

# xdotool dibutuhkan fitur "Tempel ke HP" untuk memfokuskan scrcpy dan
# mengirim Ctrl+V pada Ubuntu/X11 atau XWayland. wmctrl tetap dipasang sebagai
# helper fokus jendela Mirror. Jalankan juga bila scrcpy sudah terpasang.
if command -v apt-get >/dev/null 2>&1; then
    MISSING_DESKTOP_TOOLS=""
    command -v xdotool >/dev/null 2>&1 || MISSING_DESKTOP_TOOLS="$MISSING_DESKTOP_TOOLS xdotool"
    command -v wmctrl  >/dev/null 2>&1 || MISSING_DESKTOP_TOOLS="$MISSING_DESKTOP_TOOLS wmctrl"
    if [ -n "$MISSING_DESKTOP_TOOLS" ]; then
        echo "    Menginstall alat kontrol jendela:$MISSING_DESKTOP_TOOLS"
        $SUDO apt-get install -y $MISSING_DESKTOP_TOOLS
        echo -e "    ${G}OK${N} - Alat Tempel ke HP siap."
    fi
else
    if ! command -v xdotool >/dev/null 2>&1; then
        echo -e "    ${Y}xdotool belum ada.${N} Install manual agar fitur Tempel ke HP bekerja."
    fi
fi
echo

# Pastikan skrip jalankan bisa dieksekusi
chmod +x ./jalankan-ubuntu.sh 2>/dev/null || true

echo "============================================================"
echo -e "   ${G}SETUP SELESAI!${N}"
echo "============================================================"
echo
echo "  Mulai sekarang, untuk MENJALANKAN aplikasi cukup jalankan:"
echo "      ./jalankan-ubuntu.sh"
echo "  (atau klik 2x file jalankan-ubuntu.sh -> Run in Terminal)"
echo
echo "  Aplikasi akan terbuka di browser: http://localhost:5001"
echo "============================================================"
echo
echo "============================================================"
echo
