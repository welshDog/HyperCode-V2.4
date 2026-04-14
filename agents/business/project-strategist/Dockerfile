FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    REDIS_HOST=redis \
    REDIS_PORT=6379

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/

# Non-root user — security hardening
RUN addgroup --system appuser && adduser --system --group appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8019

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8019/health || exit 1

CMD ["python", "src/main.py"]
