FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

COPY llm_pipeline/requirements.txt /app/llm_pipeline/requirements.txt
RUN pip install --no-cache-dir -r /app/llm_pipeline/requirements.txt

COPY llm_pipeline /app/llm_pipeline

CMD ["uvicorn", "llm_pipeline.main:app", "--host", "0.0.0.0", "--port", "8001"]