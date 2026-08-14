# Stripe MCP Server Dockerfile
# Follows Phase 9 security patterns from HyperCode.

FROM python:3.11-slim AS base

# ---------- Part A: OS hardening ----------
RUN apt-get update --allow-releaseinfo-change && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates curl libexpat1 openssl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# ---------- Part B: pip pinning ----------
RUN pip install --upgrade --no-cache-dir \
    "pip==26.0.1" "setuptools>=80.0.0" "wheel==0.46.2" \
    "jaraco.context>=6.0.0" "jaraco.functools>=4.1.0" "jaraco.text>=4.0.0"

# ---------- Runtime stage ----------
FROM base AS runtime

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .

# Non-root user (Phase 9 pattern)
RUN groupadd -o -g 999 docker && \
    useradd --create-home --shell /bin/bash --gid 999 --uid 1000 appuser || true
USER appuser

EXPOSE 8100

CMD ["python", "server.py"]
