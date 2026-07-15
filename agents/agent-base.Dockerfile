# ========================================
# AGENT BASE TEMPLATE — Shared foundation for all HyperCode agents
# Usage: Each agent Dockerfile extends this with COPY + CMD
# Benefits: DRY principle, consistent security, optimized layers
# Target image size: 180-220MB (vs 500-800MB unoptimized)
# ========================================

# ── STAGE 1: Builder (Dependencies) ─────────────────────────────────────────
FROM python:3.11-alpine:3.19 AS builder

WORKDIR /build

# Install build dependencies (minimal set)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    postgresql-dev \
    && rm -rf /var/cache/apk/*

# Upgrade pip + pinned tools for security
RUN pip install --no-cache-dir --upgrade \
    "pip==26.0.1" \
    "setuptools>=80.0.0" \
    "wheel==0.46.2"

# Copy requirements first (better cache layer)
COPY requirements.txt .

# Install Python dependencies (no cache)
RUN pip install --no-cache-dir -r requirements.txt


# ── STAGE 2: Runtime (Minimal) ──────────────────────────────────────────────
FROM python:3.11-alpine:3.19

WORKDIR /app

# Environment variables for stability
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Install only runtime dependencies
RUN apk add --no-cache \
    curl \
    ca-certificates \
    libpq \
    postgresql-client \
    && rm -rf /var/cache/apk/*

# Create non-root user for security
RUN addgroup -g 1000 -S agent && \
    adduser -u 1000 -S agent -G agent && \
    mkdir -p /app && \
    chown -R agent:agent /app

# Copy built Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (LAST — most frequently changed)
COPY --chown=agent:agent . /app

# Drop all capabilities, no new privileges
RUN chmod 755 /app

# Switch to non-root user
USER agent

# Expose port (override in specific agent)
EXPOSE 8000

# Health check (template — override in compose or agent CMD)
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:${AGENT_PORT:-8000}/health || exit 1

# Default command (override in specific agent Dockerfile)
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${AGENT_PORT:-8000}"]
