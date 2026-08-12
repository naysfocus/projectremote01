@echo off
setlocal
cd /d "%~dp0"
set HOST_OS_TYPE=windows
set HOST_OS_INFO=Windows host via Docker Desktop

echo Menjalankan Video Mixer v1.22.1...
docker compose up -d --build
if errorlevel 1 (
  echo.
  echo Gagal menjalankan container. Periksa Docker Desktop lalu jalankan kembali.
  pause
  exit /b 1
)

echo.
echo Video Mixer siap di http://localhost:5000
echo Penggunaan pertama akan menampilkan halaman aktivasi Remote Server.
start "" http://localhost:5000
endlocal
