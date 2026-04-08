# DevOps Engineer Agent - Optimized
# Multi-stage build with improved caching

# ========================================
# Stage 1: Builder
# ========================================
FROM python:3.11.8-slim AS builder

WORKDIR /build

# Install build dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (leverage cache)
COPY agents/05-devops-engineer/requirements.txt .
# Install dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# ========================================
# Stage 2: Runtime
# ========================================
FROM python:3.11.8-slim

WORKDIR /app

# Install runtime dependencies (curl for healthcheck, docker for deployment, kubectl)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    docker.io \
    && mkdir -p /usr/lib/docker/cli-plugins \
    && curl -L "https://github.com/docker/compose/releases/download/v2.24.6/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose \
    && ln -s /usr/local/bin/docker-compose /usr/lib/docker/cli-plugins/docker-compose \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AGENT_NAME=devops-engineer \
    AGENT_ROLE="DevOps Engineer" \
    AGENT_MODEL=claude-3-5-sonnet-20241022 \
    AGENT_PORT=8006

# Install wheels from builder
COPY --from=builder /wheels /wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels

# Copy application code
COPY agents/05-devops-engineer/agent.py .
COPY agents/base-agent/agent.py ./base_agent.py
COPY agents/05-devops-engineer/config.json .

# Copy Shared Modules (Evolution Protocol)
COPY agents/shared /app/agents/shared

# Mount point for Hive Mind
VOLUME ["/app/hive_mind"]

EXPOSE 8006

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \
    CMD curl -f http://localhost:${AGENT_PORT}/health || exit 1

CMD ["python", "agent.py"]
