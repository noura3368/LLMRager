#!/bin/sh
set -eu

ollama serve &
SERVER_PID=$!

until ollama list >/dev/null 2>&1; do
    sleep 1
done
echo "Ollama is ready. Attempting to pull nomic-embed-model..."
ollama pull nomic-embed-text:latest
echo "Ollama is ready and model pull attempted."
echo "Attempting to pull model ${MODELS_CSV}..."
ollama pull "${MODELS_CSV}" || true
echo "Model pull attempted. Starting server..."
echo "Attempting to pull preprocessing model ${PRE_PROCESSING_MODEL}..."
ollama pull "${PRE_PROCESSING_MODEL}" || true
echo "Preprocessing model pull attempted. Starting server..."

wait "$SERVER_PID"