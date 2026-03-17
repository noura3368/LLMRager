FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

COPY watcher/requirements.txt /app/watcher/requirements.txt
RUN pip install --no-cache-dir -r /app/watcher/requirements.txt

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

COPY watcher /app/watcher
COPY llm_pipeline/ /app/llm_pipeline/

RUN chmod +x /app/watcher/entrypoint.sh

ENTRYPOINT ["/app/watcher/entrypoint.sh"]