# ── Stage 1: Build wheels ─────────────────────────────────────────────────────
FROM python:3.11.8-slim AS builder

WORKDIR /build

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY agents/hyper-agents/worker/requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11.8-slim

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    AGENT_NAME=task-worker-01 \
    AGENT_PORT=8093 \
    HYPERFOCUS_MODE=false

# Install pre-built wheels from builder stage
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy the shared hyper_agents package
COPY src/agents/hyper_agents/ /app/src/agents/hyper_agents/

# Create parent __init__.py files that don't exist in the repo
RUN mkdir -p /app/src/agents && \
    touch /app/src/__init__.py /app/src/agents/__init__.py

# Copy agent entrypoint
COPY agents/hyper-agents/worker/main.py /app/main.py

EXPOSE 8093

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \
    CMD curl -f http://localhost:${AGENT_PORT}/health || exit 1

CMD ["python", "main.py"]
