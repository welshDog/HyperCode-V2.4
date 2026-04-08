# agents/base-agent/Dockerfile
# Every Hyper Agent extends FROM this

FROM python:3.12-slim

# Non-root user — security hardening ✅
RUN groupadd -r hyper && useradd -r -g hyper hyper

WORKDIR /app

# Deps first (layer cache wins)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R hyper:hyper /app

USER hyper

# Health endpoint MUST exist — non-negotiable
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
