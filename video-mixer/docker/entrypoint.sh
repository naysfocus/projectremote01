#!/bin/sh
set -eu
mkdir -p /config
chown -R app:app /config
exec gosu app "$@"
