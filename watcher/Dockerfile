FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*
COPY watcher.py /app/watcher.py
COPY entrypoint.sh /entrypoint.sh
COPY ./services/ /app/services/
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]