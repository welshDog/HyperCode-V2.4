# Coder Agent - Standardized
# Based on BaseAgent pattern (FastAPI)

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install docker-mcp via pipx to avoid dependency conflicts (httpx version)
ENV PIPX_HOME=/opt/pipx
ENV PIPX_BIN_DIR=/usr/local/bin
RUN pip install pipx && \
    pipx install git+https://github.com/QuantGeekDev/docker-mcp.git

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

ENV PYTHONPATH=/app

# Non-root user with docker group access — security hardening
# docker group GID 999 is the default on most Linux distros
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && (getent group docker || groupadd -g 999 docker) \
    && usermod -aG docker appuser \
    && chown -R appuser:appuser /app
USER appuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -fsS "http://localhost:${AGENT_PORT:-8000}/health" >/dev/null || exit 1

CMD ["python", "main.py"]
