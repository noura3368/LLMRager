#!/bin/sh
set -eu

OLLAMA_URL="${OLLAMA_URL:-http://ollama:11434}"

# Wait for Ollama to be ready
until curl -s "$OLLAMA_URL/api/tags" >/dev/null; do
  sleep 1
done

# Pull required models (add/remove as needed)
#curl -s "$OLLAMA_URL/api/pull" -d '{"name":"qwen2.5:7b"}' >/dev/null
curl -s "$OLLAMA_URL/api/pull" -d '{"name":"nomic-embed-text:latest"}' >/dev/null
