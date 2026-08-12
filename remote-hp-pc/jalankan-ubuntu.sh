#!/usr/bin/env bash
# ============================================================
#   Remote HP v1.50 - JALANKAN aplikasi (UBUNTU / LINUX)
#   Jalankan setiap kali ingin memakai aplikasi.
#   (Pastikan sudah menjalankan ./setup-ubuntu.sh satu kali)
# ============================================================
cd "$(dirname "$(readlink -f "$0")")"

G='\033[0;32m'; R='\033[0;31m'; N='\033[0m'

if [ ! -x ".venv/bin/python" ]; then
    echo
    echo "============================================================"
    echo -e "   ${R}Aplikasi belum di-setup.${N}"
    echo "   Jalankan dulu satu kali:  ./setup-ubuntu.sh"
    echo "============================================================"
    echo
    read -p "Tekan Enter untuk menutup..."
    exit 1
fi

echo
echo "============================================================"
echo -e "   ${G}REMOTE HP v1.50 sedang berjalan...${N}"
echo "   Buka di browser: http://localhost:5001"
echo
echo "   Browser akan terbuka otomatis sebentar lagi."
echo "   JANGAN tutup terminal ini selama memakai aplikasi."
echo "   Untuk berhenti: tekan Ctrl+C."
echo "============================================================"
echo

# Buka browser otomatis setelah 2 detik (beri waktu server start)
( sleep 2; xdg-open http://localhost:5001 >/dev/null 2>&1 || true ) &

exec ./.venv/bin/python app.py
