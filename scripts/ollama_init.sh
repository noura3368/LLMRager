#!/bin/sh
set -eu

ollama serve &
SERVER_PID=$!

until ollama list >/dev/null 2>&1; do
    sleep 1
done

echo "Ollama is ready. Attempting to pull nomic-embed-text:latest..."
ollama pull nomic-embed-text:latest
echo "Ollama is ready and pulled nomic-embed-text:latest"

if [ -n "${MODELS:-}" ]; then
    echo "Attempting to pull models from MODELS=$MODELS ..."
    OLD_IFS=$IFS
    IFS=','

    for model in $MODELS; do
        model=$(printf '%s' "$model" | xargs)
        [ -z "$model" ] && continue

        echo "Pulling model: $model"
        ollama pull "$model" #|| echo "Failed to pull $model" >&2
    done

    IFS=$OLD_IFS
else
    echo "MODELS is empty; skipping main model pulls."
fi

if [ -n "${PRE_PROCESSING_MODEL:-}" ]; then
    echo "Attempting to pull preprocessing model ${PRE_PROCESSING_MODEL}..."
    ollama pull "$PRE_PROCESSING_MODEL" || echo "Failed to pull preprocessing model ${PRE_PROCESSING_MODEL}" >&2
else
    echo "PRE_PROCESSING_MODEL is empty; skipping preprocessing model pull."
fi

wait "$SERVER_PID"