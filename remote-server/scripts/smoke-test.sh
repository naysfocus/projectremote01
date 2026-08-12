#!/bin/sh
set -eu
BASE_URL="${1:-http://127.0.0.1:8800}"
python - "$BASE_URL" <<'PY'
import json
import sys
import urllib.request
base = sys.argv[1].rstrip('/')
with urllib.request.urlopen(base + '/health', timeout=5) as response:
    body = json.load(response)
assert body['ok'] is True, body
with urllib.request.urlopen(base + '/ready', timeout=5) as response:
    ready = json.load(response)
assert ready['ok'] is True, ready
print(body)
print(ready)
PY
