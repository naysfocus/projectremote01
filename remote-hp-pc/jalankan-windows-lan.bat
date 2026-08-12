@echo off
setlocal
cd /d "%~dp0"
set "REMOTE_HP_BIND=0.0.0.0"
set "REMOTE_HP_PORT=5001"
echo ============================================================
echo Remote HP v1.50 - LAN / Android Controller Mode
echo Web PC: http://localhost:5001
echo Android harus berada di LAN/Wi-Fi tepercaya yang sama.
echo ============================================================
call jalankan-windows.bat
