# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

COPY agents/hypervisor-agent/requirements.txt .

RUN python -m pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install dumb-init for signal handling
RUN apt-get update && apt-get install -y --no-install-recommends dumb-init && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 10001 appuser

# Copy wheels and install
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy source
COPY agents/hypervisor-agent/ .

# Switch user
USER appuser

EXPOSE 8094

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8094/health')"

ENTRYPOINT ["dumb-init", "--"]
CMD ["python", "hypervisor_agent.py"]
