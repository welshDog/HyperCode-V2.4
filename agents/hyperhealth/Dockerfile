# ================================================================
# HyperHealth Agent — Multi-stage build with Alembic migrations
# Matches healer agent pattern for consistency
# ================================================================
FROM python:3.11-slim AS base

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Builder stage ────────────────────────────────────────────────
FROM base AS builder

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ────────────────────────────────────────────────
FROM base AS runtime

# Create non-root user (security best practice)
RUN groupadd --gid 1001 hyperhealth \
    && useradd --uid 1001 --gid hyperhealth --shell /bin/bash --create-home hyperhealth

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Clean up __pycache__ and .pyc files from builder
RUN find /usr/local/lib/python3.11/site-packages -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.11/site-packages -type f -name "*.pyc" -delete 2>/dev/null || true

# Copy migrations and source code
COPY --chown=hyperhealth:hyperhealth migrations /app/migrations
COPY --chown=hyperhealth:hyperhealth . .

USER hyperhealth

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8090/health || exit 1

# Run migrations on container start: upgrade head, fallback to stamp if needed
CMD ["sh", "-c", "alembic upgrade head || alembic stamp 001 && exec uvicorn main:app --host 0.0.0.0 --port 8090 --workers 2"]
