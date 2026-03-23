# --- STAGE 1: Shared Base ---
FROM python:3.12-slim AS base
RUN apt-get update && apt-get install -y gcc curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY haiku.rag.yaml /app/
COPY ./scripts /app/scripts
RUN chmod +x /app/scripts/*.sh

# --- STAGE 2: Watcher (The "Heavy" Ingestor) ---
FROM base AS watcher
# Install heavy libs only needed for PDF/Doc processing (Docling)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libxcb1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements-watcher.txt .
RUN pip install --no-cache-dir -r requirements-watcher.txt  
COPY ./watcher /app/watcher
COPY ./llm_pipeline /app/llm_pipeline
RUN chmod +x /app/watcher/entrypoint.sh
ENTRYPOINT ["/app/watcher/entrypoint.sh"]

# --- STAGE 3: Orchestrator (The "Slim" Querier) ---
FROM base AS orchestrator
# Only install the slim requirements here
COPY requirements-orchestrator.txt . 
RUN pip install --no-cache-dir -r requirements-orchestrator.txt  
COPY ./llm_pipeline /app/llm_pipeline
# Use the script to launch the API
CMD ["python", "-u", "/app/scripts/load_config_env.py", "uvicorn", "llm_pipeline.main:app", "--host", "0.0.0.0", "--port", "8002"]