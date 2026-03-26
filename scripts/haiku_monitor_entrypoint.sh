#!/bin/sh
set -eu

eval "$(python /app/scripts/load_config_env.py)"
exec haiku-rag --config /app/haiku.rag.yaml serve --monitor --db /data/haiku.rag.lancedb