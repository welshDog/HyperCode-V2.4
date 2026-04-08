# ================================================================
# HyperHealth Agent — Multi-stage build
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

# Copy source code
COPY --chown=hyperhealth:hyperhealth . .

USER hyperhealth

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8090/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090", "--workers", "2"]
