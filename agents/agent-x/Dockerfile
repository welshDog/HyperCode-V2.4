# ── Stage 1: Build wheels ─────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# OS package hardening — upgrade all packages to get latest security patches
RUN apt-get update --allow-releaseinfo-change && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        gcc \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY agents/agent-x/requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# OS package hardening — upgrade all + force-install patched libexpat1 + openssl
# docker.io: needed for build/deploy ops; upgraded to latest available in Debian
RUN apt-get update --allow-releaseinfo-change && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libexpat1 \
        openssl \
        docker.io && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Pip tool hardening — pin safe versions (eliminates pip/setuptools/jaraco CVEs)
RUN pip install --upgrade --no-cache-dir \
    "pip==26.0.1" \
    "setuptools>=80.0.0" \
    "wheel==0.46.2" \
    "jaraco.context>=6.0.0" \
    "jaraco.functools>=4.1.0" \
    "jaraco.text>=4.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    AGENT_NAME=agent-x-01 \
    AGENT_PORT=8000 \
    OLLAMA_HOST=http://hypercode-ollama:11434 \
    OLLAMA_MODEL=tinyllama:latest \
    WORKSPACE_PATH=/workspace \
    HYPER_AGENTS_COMPOSE=/workspace/docker-compose.hyper-agents.yml \
    AGENTS_COMPOSE=/workspace/docker-compose.agents.yml

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy Agent X package — named 'agentx' (no hyphen) for valid Python import
COPY agents/agent-x/ /app/agentx/

# Expose workspace mount point (repo root mounted at runtime via compose volume)
VOLUME ["/workspace"]

# Non-root user with docker group access — security hardening
# docker group GID 999 is the default on most Linux distros
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && (getent group docker || groupadd -g 999 docker) \
    && usermod -aG docker appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \
    CMD curl -f http://localhost:${AGENT_PORT}/health || exit 1

CMD ["python", "-m", "agentx.main"]
