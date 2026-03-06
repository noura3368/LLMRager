#!/bin/sh
set -eu

OLLAMA_URL="${OLLAMA_URL:-http://ollama:11434}"

# Wait for Ollama to be ready
until curl -s "$OLLAMA_URL/api/tags" >/dev/null; do
  sleep 1
done

# Pull required models (add/remove as needed)
curl -s "$OLLAMA_URL/api/pull" -d '{"name":"gpt-oss"}' >/dev/null
curl -s "$OLLAMA_URL/api/pull" -d '{"name":"qwen3-embedding:4b"}' >/dev/null

echo "Pulled llama3.1:8b"