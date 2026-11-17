FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_ARTIFACTS_DIR=/app/model_artifacts \
    AUDIT_LOG_PATH=/app/audit_logs/audit.jsonl

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY model_artifacts ./model_artifacts

RUN useradd --uid 1000 --create-home appuser \
    && mkdir -p /app/audit_logs \
    && chown -R appuser /app/audit_logs
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/readyz').status==200 else 1)"

# One worker + threads: metrics and the loaded model live in process memory,
# so a single process keeps /metrics and /model/reload consistent.
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--bind", "0.0.0.0:8000", "app.main:create_app()"]
