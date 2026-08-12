#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export REMOTE_HP_BIND=0.0.0.0
export REMOTE_HP_PORT=5001
exec ./jalankan-ubuntu.sh
