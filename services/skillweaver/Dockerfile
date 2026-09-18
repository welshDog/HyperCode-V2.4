FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (pinned to match backend/requirements.txt baseline)
# NOTE: No python-multipart — SkillWeaver only speaks JSON, no multipart endpoints.
RUN pip install --no-cache-dir \
    redis==5.3.1 \
    "pydantic>=2.10.0,<2.12" \
    fastapi==0.135.3 \
    uvicorn==0.35.0 \
    httpx==0.28.1

# Copy SkillWeaver code + services namespace init
COPY services/__init__.py /app/services/__init__.py
COPY services/skillweaver/ /app/services/skillweaver/

# Create necessary directories
RUN mkdir -p /app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8051/health || exit 1

# Default environment
ENV LOG_LEVEL=INFO
ENV REDIS_URL=redis://redis:6379
ENV PORT=8051

# Run SkillWeaver
CMD ["python", "-m", "uvicorn", "services.skillweaver.server:app", "--host", "0.0.0.0", "--port", "8051"]
