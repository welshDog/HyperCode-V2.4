FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    redis==5.0.1 \
    pydantic==2.5.0 \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    httpx==0.25.2 \
    python-multipart==0.0.6

# Copy SkillWeaver code
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
