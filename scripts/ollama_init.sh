#!/bin/sh
set -eu

CONFIG_FILE="/app/llm_pipeline/services/config.txt"

get_config_value() {
    key="$1"
    if [ -f "$CONFIG_FILE" ]; then
        grep -E "^${key}=" "$CONFIG_FILE" | tail -n 1 | cut -d '=' -f2-
    fi
}

USE_DOCKER_ENV_FILE="$(get_config_value USE_DOCKER_ENV_FILE || true)"

if [ "$USE_DOCKER_ENV_FILE" = "true" ]; then
    OLLAMA_URL="$(get_config_value OLLAMA_URL)"
else
    OLLAMA_URL="${OLLAMA_URL:-http://ollama:11434}"
fi

echo "Using OLLAMA_URL=$OLLAMA_URL"

# Wait for Ollama to be ready
until curl -s "$OLLAMA_URL/api/tags" >/dev/null; do
    sleep 1
done

# Pull required models
curl -s "$OLLAMA_URL/api/pull" -d '{"name":"nomic-embed-text:latest"}' >/dev/null