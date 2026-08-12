#!/bin/sh
set -eu
if [ "$#" -gt 0 ] && [ -n "${1:-}" ]; then
  exec python -m app.maintenance backup "$1"
fi
exec python -m app.maintenance backup
