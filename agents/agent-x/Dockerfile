# ── Stage 1: Build wheels ─────────────────────────────────────────────────────
FROM python:3.11.8-slim AS builder

WORKDIR /build

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY agents/agent-x/requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11.8-slim

WORKDIR /app

# curl for healthcheck; docker CLI for build/deploy operations
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends curl docker.io && \
    rm -rf /var/lib/apt/lists/*

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

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \
    CMD curl -f http://localhost:${AGENT_PORT}/health || exit 1

CMD ["python", "-m", "agentx.main"]
