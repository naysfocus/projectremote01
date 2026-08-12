@echo off
REM ============================================================
REM   Remote HP v1.50 - JALANKAN aplikasi (WINDOWS)
REM   Klik 2x file ini setiap kali ingin memakai aplikasi.
REM   (Pastikan sudah menjalankan setup-windows.bat satu kali)
REM ============================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo ============================================================
    echo    Aplikasi belum di-setup.
    echo    Silakan KLIK 2x dulu file: setup-windows.bat
    echo ============================================================
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo    REMOTE HP v1.50 sedang berjalan...
echo    Buka di browser: http://localhost:5001
echo.
echo    Browser akan terbuka otomatis sebentar lagi.
echo    JANGAN tutup jendela ini selama memakai aplikasi.
echo    Untuk berhenti: tutup jendela ini atau tekan Ctrl+C.
echo ============================================================
echo.

REM Buka browser otomatis setelah 2 detik (server butuh waktu start)
start "" /b cmd /c "timeout /t 2 >nul & start http://localhost:5001"

call ".venv\Scripts\python.exe" app.py

echo.
echo Aplikasi berhenti.
pause
