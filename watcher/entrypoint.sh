#!/bin/sh
set -eu

CONFIG="${CONFIG:-/app/haiku.rag.yaml}"
DB="${DB:-/data/haiku.rag.lancedb}"

if [ ! -d "$DB" ]; then
  echo "Initializing DB at $DB..."
  haiku-rag --config "$CONFIG" init --db "$DB"
else
  echo "DB already exists at $DB"
fi

python - <<'PY'
import time, urllib.request
url="http://docling-serve:5001/health"
for _ in range(180):
    try:
        urllib.request.urlopen(url, timeout=2).read()
        print("docling-serve ready")
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("docling-serve not ready")
PY
exec haiku-rag --config "$CONFIG" serve --monitor --db "$DB"