#!/bin/sh
set -eu

eval "$(python /app/scripts/load_config_env.py)"
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
exec haiku-rag --config /app/haiku.rag.yaml serve --monitor --db /data/haiku.rag.lancedb