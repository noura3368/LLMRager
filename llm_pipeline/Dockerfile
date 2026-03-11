FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py /app/main.py
COPY ./services/ /app/services/
COPY test.py /app/test.py
COPY commands_extracted.json /app/commands_extracted.json
COPY haiku.rag.yaml /app/haiku.rag.yaml

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]