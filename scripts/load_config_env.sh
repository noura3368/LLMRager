#!/bin/sh
set -eu

CONFIG_FILE="${CONFIG_FILE:-/app/llm_pipeline/services/config.txt}"

get_config_value() {
    key="$1"
    if [ -f "$CONFIG_FILE" ]; then
        awk -F= -v k="$key" '
            $1 ~ "^[[:space:]]*" k "[[:space:]]*$" {
                val=$0
                sub(/^[^=]*=/, "", val)
                sub(/^[[:space:]]+/, "", val)
                sub(/[[:space:]]+$/, "", val)
                print val
            }
        ' "$CONFIG_FILE" | tail -n 1
    fi
}

resolve_value() {
    key="$1"
    default="${2:-}"

    cfg="$(get_config_value "$key" || true)"
    eval "env_val=\${$key-}"

    if [ "${USE_DOCKER_ENV_FILE_RESOLVED:-false}" = "true" ]; then
        if [ -n "$cfg" ]; then
            printf '%s\n' "$cfg"
        elif [ -n "${env_val:-}" ]; then
            printf '%s\n' "$env_val"
        else
            printf '%s\n' "$default"
        fi
    else
        if [ -n "${env_val:-}" ]; then
            printf '%s\n' "$env_val"
        elif [ -n "$cfg" ]; then
            printf '%s\n' "$cfg"
        else
            printf '%s\n' "$default"
        fi
    fi
}

USE_DOCKER_ENV_FILE_RESOLVED="$(get_config_value USE_DOCKER_ENV_FILE || true)"
USE_DOCKER_ENV_FILE_RESOLVED="$(printf '%s' "${USE_DOCKER_ENV_FILE_RESOLVED:-false}" | tr '[:upper:]' '[:lower:]')"

export OLLAMA_URL="$(resolve_value OLLAMA_URL http://localhost:11434)"
export MODELS_CSV="$(resolve_value MODELS_CSV /app/llm_pipeline/services/file.csv)"
export PROMPTS="$(resolve_value PROMPTS /app/llm_pipeline/prompts/original)"
export PRE_PROCESSING_MODEL="$(resolve_value PRE_PROCESSING_MODEL qwen2.5:7b)"

# Optional, if Haiku should follow the same Ollama URL
export OLLAMA_BASE_URL="$OLLAMA_URL"

echo "USE_DOCKER_ENV_FILE_RESOLVED=$USE_DOCKER_ENV_FILE_RESOLVED"
echo "OLLAMA_URL=$OLLAMA_URL"
echo "MODELS_CSV=$MODELS_CSV"
echo "PROMPTS=$PROMPTS"
echo "PRE_PROCESSING_MODEL=$PRE_PROCESSING_MODEL"

[ "$#" -gt 0 ] || { echo "No command provided"; exit 1; }
exec "$@"