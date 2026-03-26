echo "Waiting for Ollama at $OLLAMA_BASE_URL..."
until curl -fsS "$OLLAMA_BASE_URL/api/tags" >/dev/null; do
    sleep 1
done

curl -fsS "$OLLAMA_BASE_URL/api/pull" \
  -H "Content-Type: application/json" \
  -d '{"name":"nomic-embed-text:latest"}' >/dev/null || true
echo "Ollama is ready and model pull attempted."