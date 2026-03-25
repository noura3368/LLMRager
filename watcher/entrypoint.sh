#!/bin/sh
set -eu
eval "$(python /app/scripts/load_config_env.py)"

CONFIG="${CONFIG:-/app/haiku.rag.yaml}"
DB_PATH="${DB_PATH:-/data/haiku.rag.lance}"

if [ ! -d "$DB_PATH" ]; then
  echo "Initializing DB_PATH at $DB_PATH..."
  haiku-rag --config "$CONFIG" init --db "$DB_PATH"
else
  echo "DB_PATH already exists at $DB_PATH"
fi

python - <<'PY'
import os, time, urllib.request
url = os.environ["DOCLING_SERVE_URL"] + "/health"
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
if [ "$#" -gt 0 ]; then
  exec "$@"
else
  /app/scripts/ollama_init.sh
  exec python -u /app/watcher/watcher.py
fi
