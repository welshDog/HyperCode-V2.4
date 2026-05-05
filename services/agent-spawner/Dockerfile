FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install docker CLI + redis + docker SDK
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    redis==5.0.1 \
    aioredis==2.0.1 \
    docker==7.1.0

# Run as root (has docker socket access)
# In production, use docker:dind or proper socket proxy
COPY spawner.py .

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import redis.asyncio; import asyncio; asyncio.run(redis.asyncio.from_url('${REDIS_URL:-redis://redis:6379/0}').ping())" || exit 1

CMD ["python", "spawner.py"]
