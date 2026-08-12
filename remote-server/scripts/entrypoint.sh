#!/bin/sh
set -eu

umask 077
mkdir -p /data /data/backups
python -m app.runtime_bootstrap

# Load secrets generated inside the persistent Docker volume.
set -a
# shellcheck disable=SC1091
. "${RUNTIME_CONFIG_FILE:-/data/runtime.env}"
set +a

chown -R app:app /data

gosu app alembic upgrade head
gosu app python -m app.cli bootstrap

if [ -f "${FIRST_START_MARKER_FILE:-/data/.first_start_pending}" ]; then
  echo ""
  echo "============================================================"
  echo " REMOTE SERVER SIAP DIGUNAKAN"
  echo "============================================================"
  cat "${INITIAL_CREDENTIALS_FILE:-/data/INITIAL_ADMIN_CREDENTIALS.txt}"
  echo "Dari komputer Anda, gunakan SSH tunnel lalu buka:"
  echo "  http://localhost:${SERVER_PUBLIC_PORT:-8800}/login"
  echo "============================================================"
  echo ""
  rm -f "${FIRST_START_MARKER_FILE:-/data/.first_start_pending}"
fi

exec gosu app "$@"
