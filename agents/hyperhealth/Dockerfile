# ================================================================
# HyperHealth Agent — DHI multi-stage build with Alembic migrations
# ================================================================
FROM dhi.io/python:3.11.18-debian12-dev AS builder

ENV PATH="/app/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install requirements separately to retain dependency-layer caching.
RUN python -m venv /app/venv
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ────────────────────────────────────────────────
FROM dhi.io/python:3.11.18-debian12 AS runtime

ENV PATH="/app/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# DHI runtime runs nonroot (UID/GID 65532); own the app artifacts so imports,
# Alembic, and both runtime modes can read them without elevated privileges.
COPY --from=builder --chown=65532:65532 /app/venv /app/venv
COPY --chown=65532:65532 . /app/

USER 65532:65532

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8090/health', timeout=5)"]

# The wrapper runs migrations before API workers and execs Compose's worker
# command unchanged; DHI runtime images do not include a shell.
ENTRYPOINT ["python", "/app/entrypoint.py"]
CMD ["api"]
