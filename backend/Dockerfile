# syntax=docker/dockerfile:1.7

# Dependency set baked into the runtime image (selects the `deps-*` stage below):
#   full (default) -> requirements.txt            (current broad image, unchanged behaviour)
#   core           -> requirements.core.txt       (slim API runtime; see requirements.core.in)
# Slim build:  docker build -f backend/Dockerfile --build-arg DEPS_VARIANT=core \
#                -t hypercode-core:slim-check ./backend
ARG DEPS_VARIANT=full

# ── Stage 1a: Shared build base (OS + pip tooling hardening) ──────────────────
FROM python:3.12-slim AS build-base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/app/cache/sentence_transformers

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


# ── Stage 1b: Full dependency set (default) ───────────────────────────────────
FROM build-base AS builder
ARG INSTALL_AI_DEPS=false

# Install dependencies FIRST (before code) for better layer caching
COPY requirements.txt requirements-ai.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt && \
    if [ "$INSTALL_AI_DEPS" = "true" ]; then pip install -r requirements-ai.txt; fi

FROM builder AS deps-full


# ── Stage 1c: Slim core dependency set (opt-in: DEPS_VARIANT=core) ────────────
# No scientific stack, agent frameworks, dev/security tooling or model-serving
# libs. INSTALL_AI_DEPS is intentionally ignored here.
FROM build-base AS deps-core

COPY requirements.core.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.core.txt

# Precompile bytecode. PYTHONDONTWRITEBYTECODE=1 is set (the runtime user cannot
# write site-packages anyway), so without this every container start recompiles all
# of site-packages from source: measured `import app.main` 101 s -> 55 s with .pyc
# (about +180 MB). unchecked-hash: the image is immutable, so Python skips the
# source mtime check. Files that fail to compile are harmless and just compile at
# import, hence the fallback instead of failing the build.
RUN python -m compileall -q -j 0 --invalidation-mode unchecked-hash \
        /usr/local/lib/python3.12/site-packages \
    || echo "note: some site-packages files could not be byte-compiled (harmless)"


# ── Stage 1d: Selected dependency set ─────────────────────────────────────────
FROM deps-${DEPS_VARIANT} AS deps


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim

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

# The builder owns dependency installation; copying its site-packages keeps the
# runtime image free of compilers and avoids reinstalling the full dependency set.

RUN addgroup --system appuser && adduser --system --group appuser

# Create cache directories
RUN mkdir -p /app/cache/huggingface /app/cache/sentence_transformers && \
    chown -R appuser:appuser /app/cache

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code LAST (most frequently changed layer)
COPY . .

# Slim (core) variant only: precompile the app's own bytecode too, in the default
# timestamp mode so a bind-mounted newer source is still picked up. The `full`
# variant is deliberately unchanged.
ARG DEPS_VARIANT
RUN if [ "$DEPS_VARIANT" = "core" ]; then \
        python -m compileall -q -j 0 app alembic \
        || echo "note: some app files could not be byte-compiled (harmless)"; \
    fi

# Remove setuptools vendored wheel/jaraco metadata/executables flagged by scanners
# (jaraco.context-5.3.0 dist-info ships inside setuptools/_vendor — the standalone
#  install is pinned to 6.1.0 in requirements.txt; this strips the vendored phantom)
RUN python -c "import glob, os, shutil, setuptools; vendor=os.path.join(os.path.dirname(setuptools.__file__), '_vendor'); [shutil.rmtree(p, ignore_errors=True) for pat in ('wheel-*.dist-info', 'jaraco.*-*.dist-info') for p in glob.glob(os.path.join(vendor, pat))]; shutil.rmtree(os.path.join(vendor, 'bin'), ignore_errors=True)"

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# `adduser --system` gives appuser HOME=/nonexistent. chromadb's default embedding
# function (the fallback in app/core/rag.py when sentence-transformers is not
# installed, which is the case unless INSTALL_AI_DEPS=true) caches its ONNX model
# under $HOME/.cache/chroma and crashed with `PermissionError: /nonexistent`.
# /app/cache is created above and owned by appuser, so use it as HOME.
ENV HOME=/app/cache

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD sh -c 'curl -f "http://localhost:${PORT:-8000}/health" || exit 1'

# Migrations MUST complete before uvicorn starts (alembic blocks on `&&`)
CMD ["sh", "-c", "alembic upgrade head && exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
