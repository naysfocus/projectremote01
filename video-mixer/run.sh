#!/usr/bin/env bash
# Video Mixer v1.22.1 — Linux start helper
set -euo pipefail
cd "$(dirname "$0")"

export HOST_OS_TYPE=linux
export HOST_OS_INFO="Linux host via Docker"

if [ -e /dev/dri/renderD128 ]; then
  export RENDER_GID="$(stat -c '%g' /dev/dri/renderD128)"
  echo "GPU render node terdeteksi: /dev/dri/renderD128 (GID ${RENDER_GID})"
  docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
else
  echo "Tidak ada /dev/dri/renderD128 — encoder memakai CPU."
  docker compose up -d --build
fi

printf '\nVideo Mixer siap: http://localhost:5000\n'
printf 'Penggunaan pertama akan menampilkan halaman aktivasi Remote Server.\n'
printf 'Lihat log: docker compose logs -f app\n'
