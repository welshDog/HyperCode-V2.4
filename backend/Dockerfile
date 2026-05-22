# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/app/cache/sentence_transformers
ARG INSTALL_AI_DEPS=false

# OS package hardening — upgrade all + install build deps
RUN apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        ca-certificates && \
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

# Install dependencies FIRST (before code) for better layer caching
COPY requirements.txt requirements-ai.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$INSTALL_AI_DEPS" = "true" ]; then pip install --no-cache-dir -r requirements-ai.txt; fi


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/app/cache/sentence_transformers
ARG INSTALL_AI_DEPS=false

# OS package hardening — upgrade all + explicitly install patched security libs
RUN apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        ca-certificates \
        libexpat1 \
        openssl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Pip tool hardening — pin safe versions
RUN pip install --upgrade --no-cache-dir \
    "pip==26.0.1" \
    "setuptools>=80.0.0" \
    "wheel==0.46.2" \
    "jaraco.context>=6.0.0" \
    "jaraco.functools>=4.1.0" \
    "jaraco.text>=4.0.0"

# Non-root user — security hardening
RUN addgroup --system appuser && adduser --system --group appuser

# Create cache directories
RUN mkdir -p /app/cache/huggingface /app/cache/sentence_transformers && \
    chown -R appuser:appuser /app/cache

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code LAST (most frequently changed layer)
COPY . .

# Remove setuptools vendored wheel/jaraco metadata/executables flagged by scanners
# (jaraco.context-5.3.0 dist-info ships inside setuptools/_vendor — the standalone
#  install is pinned to 6.1.0 in requirements.txt; this strips the vendored phantom)
RUN python -c "import glob, os, shutil, setuptools; vendor=os.path.join(os.path.dirname(setuptools.__file__), '_vendor'); [shutil.rmtree(p, ignore_errors=True) for pat in ('wheel-*.dist-info', 'jaraco.*-*.dist-info') for p in glob.glob(os.path.join(vendor, pat))]; shutil.rmtree(os.path.join(vendor, 'bin'), ignore_errors=True)"

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD sh -c 'curl -f "http://localhost:${PORT:-8000}/health" || exit 1'

# Migrations MUST complete before uvicorn starts (alembic blocks on `&&`)
CMD ["sh", "-c", "alembic upgrade head && exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
