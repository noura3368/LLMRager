#!/bin/sh
set -eu

eval "$(python /app/scripts/load_config_env.py)"
exec uvicorn llm_pipeline.main:app --host 0.0.0.0 --port 8002