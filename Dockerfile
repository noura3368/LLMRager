# STAGE 1: Common Base (Installed ONCE)
FROM python:3.12-slim AS base
RUN apt-get update && apt-get install -y gcc curl  
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt  
WORKDIR /app
COPY haiku.rag.yaml /app/haiku.rag.yaml  
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY ./scripts /app/scripts
RUN chmod +x /app/scripts/*.sh

# STAGE 2: Watcher specific
FROM base AS watcher_build
COPY ./watcher /app/watcher
COPY ./llm_pipeline /app/llm_pipeline
RUN chmod +x /app/watcher/entrypoint.sh
ENTRYPOINT ["/app/watcher/entrypoint.sh"]

# STAGE 3: Orchestrator specific
FROM base AS orchestrator_build
COPY ./llm_pipeline /app/llm_pipeline

CMD ["/app/scripts/load_config_env.sh", "uvicorn", "llm_pipeline.main:app", "--host", "0.0.0.0", "--port", "8002"]