@echo off
REM ============================================================
REM   Remote HP v1.50 - SETUP untuk WINDOWS
REM   Cukup KLIK 2x file ini SATU KALI di komputer baru.
REM   Script ini akan menyiapkan semua yang dibutuhkan aplikasi:
REM     - Winget (Windows Package Manager) - dicoba dipasang otomatis bila belum ada
REM     - Python (kalau belum ada, otomatis diinstall via winget)
REM     - Virtual environment (.venv) khusus aplikasi ini
REM     - Library Python yang dibutuhkan (Flask)
REM     - Cek ADB (Android Debug Bridge) untuk koneksi ke HP
REM     - Cek scrcpy untuk mirroring (menampilkan) layar HP di komputer
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo    REMOTE HP - SETUP WINDOWS
echo ============================================================
echo.
echo  Folder aplikasi:
echo    %cd%
echo.

REM ---------- 1. CEK / INSTALL WINGET (Windows Package Manager) ----------
echo [1/6] Mengecek Winget ^(Windows Package Manager^)...
where winget >nul 2>&1
if !errorlevel!==0 (
    echo    OK - winget ditemukan.
) else (
    echo    winget belum terdeteksi. Mencoba memasang otomatis lewat App Installer...
    powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; $ErrorActionPreference='SilentlyContinue'; if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { Get-AppxPackage -AllUsers Microsoft.DesktopAppInstaller | ForEach-Object { try { Add-AppxPackage -DisableDevelopmentMode -Register ($_.InstallLocation + '\AppXManifest.xml') -ErrorAction Stop } catch {} } }; if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { $tmp = Join-Path $env:TEMP 'rhp_winget'; New-Item -ItemType Directory -Force -Path $tmp | Out-Null; try { Invoke-WebRequest -Uri 'https://aka.ms/Microsoft.VCLibs.x64.14.00.Desktop.appx' -OutFile (Join-Path $tmp 'vclibs.appx') -UseBasicParsing; Add-AppxPackage -Path (Join-Path $tmp 'vclibs.appx') -ErrorAction SilentlyContinue } catch {}; try { Invoke-WebRequest -Uri 'https://aka.ms/getwinget' -OutFile (Join-Path $tmp 'winget.msixbundle') -UseBasicParsing; Add-AppxPackage -Path (Join-Path $tmp 'winget.msixbundle') -ErrorAction Stop } catch { Write-Host ('Gagal memasang winget otomatis: ' + $_.Exception.Message) } }"
    REM winget terpasang sbg App Execution Alias di %LOCALAPPDATA%\Microsoft\WindowsApps,
    REM folder yg BIASANYA sudah ada di PATH -> coba pakai langsung tanpa restart jendela.
    set "PATH=!PATH!;%LOCALAPPDATA%\Microsoft\WindowsApps"
    where winget >nul 2>&1
    if !errorlevel!==0 (
        echo    OK - winget berhasil dipasang ^& langsung terdeteksi.
    ) else (
        echo    Belum berhasil memasang winget otomatis di komputer ini.
        echo    Install manual: buka Microsoft Store, cari App Installer, klik Install.
        echo    Atau unduh file .msixbundle dari https://github.com/microsoft/winget-cli/releases
        echo    lalu klik 2x untuk memasangnya.
        echo    Setelah terpasang, TUTUP dan buka ulang jendela ini, lalu jalankan setup
        echo    ini lagi supaya ADB/scrcpy bisa ikut dipasang otomatis lewat winget.
    )
)
echo.

REM ---------- 2. CEK PYTHON ----------
echo [2/6] Mengecek Python...
set "PY_CMD="

REM Coba 'py' launcher dulu (paling andal di Windows), lalu 'python'
py -3 --version >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=py -3"
) else (
    python --version >nul 2>&1
    if !errorlevel!==0 (
        REM Hindari 'python' palsu dari Microsoft Store stub
        for /f "delims=" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
        echo !PYVER! | find "Python" >nul
        if !errorlevel!==0 set "PY_CMD=python"
    )
)

if not defined PY_CMD (
    echo.
    echo    Python BELUM terpasang. Mencoba menginstall otomatis...
    echo.
    where winget >nul 2>&1
    if !errorlevel!==0 (
        echo    Menginstall Python 3.12 lewat winget ^(ikuti popup jika muncul^)...
        winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
        echo.
        echo    ============================================================
        echo     Python sudah diinstall.
        echo     TUTUP jendela ini, lalu KLIK 2x lagi setup-windows.bat
        echo     ^(diperlukan agar Windows mengenali Python yang baru^).
        echo    ============================================================
        echo.
        pause
        exit /b 0
    ) else (
        echo    winget tidak tersedia di komputer ini.
        echo.
        echo    Silakan install Python secara manual:
        echo      1. Buka https://www.python.org/downloads/
        echo      2. Download Python 3.10 atau lebih baru
        echo      3. Saat install, CENTANG "Add Python to PATH"
        echo      4. Setelah selesai, jalankan lagi setup-windows.bat
        echo.
        pause
        exit /b 1
    )
)

for /f "delims=" %%v in ('%PY_CMD% --version 2^>^&1') do set "PYVER=%%v"
echo    OK - !PYVER! ditemukan.
echo.

REM ---------- 3. BUAT / PERBAIKI VIRTUAL ENVIRONMENT ----------
echo [3/6] Menyiapkan virtual environment ^(.venv^)...
set "VENV_OK=0"
if exist ".venv\Scripts\python.exe" (
    REM Cek apakah .venv yang ada benar-benar sehat (punya pip)
    call ".venv\Scripts\python.exe" -m pip --version >nul 2>&1
    if !errorlevel!==0 (
        set "VENV_OK=1"
        echo    OK - .venv sudah ada ^& sehat, dilewati.
    )
)

if "!VENV_OK!"=="0" (
    if exist ".venv" (
        echo    .venv lama rusak/tidak lengkap ^(tanpa pip^) - dibuat ulang.
        rmdir /s /q ".venv"
    )
    %PY_CMD% -m venv .venv
    if !errorlevel! neq 0 (
        echo.
        echo    GAGAL membuat virtual environment.
        echo    Pastikan Python terpasang dengan benar lalu coba lagi.
        echo.
        pause
        exit /b 1
    )
    echo    OK - .venv dibuat.

    REM Jaring pengaman: pastikan pip ada di dalam .venv
    call ".venv\Scripts\python.exe" -m pip --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo    Memasang pip lewat ensurepip...
        call ".venv\Scripts\python.exe" -m ensurepip --upgrade >nul 2>&1
    )
)

REM Verifikasi terakhir: pip WAJIB ada sebelum lanjut
call ".venv\Scripts\python.exe" -m pip --version >nul 2>&1
if !errorlevel! neq 0 (
    echo.
    echo    GAGAL menyiapkan pip di dalam .venv.
    echo    Hapus folder .venv lalu jalankan lagi setup-windows.bat
    echo.
    pause
    exit /b 1
)
echo.

REM ---------- 4. INSTALL DEPENDENCY ----------
echo [4/6] Menginstall library yang dibutuhkan...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo.
    echo    GAGAL menginstall library.
    echo    Cek koneksi internet lalu jalankan lagi setup-windows.bat
    echo.
    pause
    exit /b 1
)
echo    OK - Semua library terpasang.
echo.

REM ---------- 5. CEK ADB ----------
echo [5/6] Mengecek ADB ^(Android Debug Bridge^)...
where adb >nul 2>&1
if !errorlevel!==0 (
    echo    OK - ADB ditemukan di PATH.
) else (
    echo    PERHATIAN: ADB belum ada di PATH.
    echo.
    echo    ADB dibutuhkan agar aplikasi bisa mengirim video ke HP.
    echo    Mencoba menginstall otomatis lewat winget...
    where winget >nul 2>&1
    if !errorlevel!==0 (
        winget install -e --id Google.PlatformTools --accept-source-agreements --accept-package-agreements
        echo.
        echo    Jika berhasil, TUTUP dan buka ulang jendela agar ADB dikenali.
    ) else (
        echo    winget tidak tersedia. Install ADB manual:
        echo      1. Download: https://developer.android.com/tools/releases/platform-tools
        echo      2. Ekstrak ke folder ^(mis. C:\platform-tools^)
        echo      3. Tambahkan folder itu ke PATH Windows
        echo    ^(Atau nanti isi lokasi adb.exe lewat menu Pengaturan di aplikasi^)
    )
)
echo.

REM ---------- 6. CEK scrcpy (mirroring layar HP) ----------
echo [6/6] Mengecek scrcpy ^(mirroring layar HP^)...
where scrcpy >nul 2>&1
if !errorlevel!==0 (
    echo    OK - scrcpy ditemukan di PATH.
) else (
    echo    PERHATIAN: scrcpy belum ada di PATH.
    echo.
    echo    scrcpy dibutuhkan untuk tombol "Mirror" layar HP.
    echo    Mencoba menginstall otomatis lewat winget...
    where winget >nul 2>&1
    if !errorlevel!==0 (
        winget install -e --id Genymobile.scrcpy --accept-source-agreements --accept-package-agreements
        echo.
        echo    Jika berhasil, TUTUP dan buka ulang jendela agar scrcpy dikenali.
    ) else (
        echo    winget tidak tersedia. Install scrcpy manual:
        echo      1. Download: https://github.com/Genymobile/scrcpy/releases
        echo      2. Ekstrak ke folder ^(mis. C:\scrcpy^)
        echo      3. Tambahkan folder itu ke PATH Windows
        echo    ^(Atau nanti isi lokasi scrcpy.exe lewat menu Pengaturan di aplikasi^)
    )
)
echo.

echo ============================================================
echo    SETUP SELESAI!
echo ============================================================
echo.
echo  Mulai sekarang, untuk MENJALANKAN aplikasi cukup
echo  KLIK 2x file:  jalankan-windows.bat
echo.
echo  Aplikasi akan terbuka di browser: http://localhost:5001
echo ============================================================
echo.
echo ============================================================
echo.
pause
