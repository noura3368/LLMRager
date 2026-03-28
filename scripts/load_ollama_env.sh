#!/bin/sh
set -eu

DEFAULT_MODEL="qwen2.5:32b"
DEFAULT_PREPROCESSING_MODEL="qwen2.5:7b"
ENV_FILE="${ENV_FILE:-/app/.env}"

get_dotenv_value() {
    key="$1"
    file="$2"

    [ -f "$file" ] || return 0

    line=$(grep -E "^${key}=" "$file" | tail -n 1 || true)
    [ -n "$line" ] || return 0

    value=${line#*=}

    case "$value" in
        \"*\") value=${value#\"}; value=${value%\"} ;;
        \'*\') value=${value#\'}; value=${value%\'} ;;
    esac

    printf '%s\n' "$value"
}

USE_ENV_FILE_VALUE=$(get_dotenv_value "USE_ENV_FILE" "$ENV_FILE" || true)
USE_ENV_FILE=$(printf '%s' "${USE_ENV_FILE_VALUE:-false}" | tr '[:upper:]' '[:lower:]')

DOTENV_MODELS=$(get_dotenv_value "MODELS" "$ENV_FILE" || true)
DOTENV_PRE_PROCESSING_MODEL=$(get_dotenv_value "PRE_PROCESSING_MODEL" "$ENV_FILE" || true)

if [ "$USE_ENV_FILE" = "true" ]; then
    MODELS="${DOTENV_MODELS:-${MODELS:-$DEFAULT_MODEL}}"
    PRE_PROCESSING_MODEL="${DOTENV_PRE_PROCESSING_MODEL:-${PRE_PROCESSING_MODEL:-$DEFAULT_PREPROCESSING_MODEL}}"
else
    MODELS="${MODELS:-${DOTENV_MODELS:-$DEFAULT_MODEL}}"
    PRE_PROCESSING_MODEL="${PRE_PROCESSING_MODEL:-${DOTENV_PRE_PROCESSING_MODEL:-$DEFAULT_PREPROCESSING_MODEL}}"
fi

if [ -z "${MODELS:-}" ]; then
    echo "Warning: MODELS is empty. Setting default $DEFAULT_MODEL." >&2
    MODELS="$DEFAULT_MODEL"
fi

if [ -z "${PRE_PROCESSING_MODEL:-}" ]; then
    echo "Warning: PRE_PROCESSING_MODEL is empty. Setting default $DEFAULT_PREPROCESSING_MODEL." >&2
    PRE_PROCESSING_MODEL="$DEFAULT_PREPROCESSING_MODEL"
fi

export MODELS
export PRE_PROCESSING_MODEL

echo "MODELS=$MODELS" >&2
echo "PRE_PROCESSING_MODEL=$PRE_PROCESSING_MODEL" >&2