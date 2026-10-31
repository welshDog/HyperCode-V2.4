# Docker's published docker-compose-plugin 5.6.0 (latest) is built with Go 1.26.8 and
# golang.org/x/net v0.58.0, which carry HIGH CVEs (fixed in Go 1.26.9 / x/net 0.60.0). Go 1.26.9 itself has a HIGH
# crypto/x509 CVE-2026-111943 (fixed in 1.26.10), and the compiled binary embeds the toolchain's stdlib, so Trivy flags it.
# Build the same Compose release ourselves on a patched toolchain until upstream ships one.
FROM golang:1.26.10-bookworm AS compose
ARG COMPOSE_VERSION=v5.6.0
RUN git clone --depth 1 --branch "${COMPOSE_VERSION}" https://github.com/docker/compose.git /src
WORKDIR /src
RUN go get golang.org/x/net@v0.60.0 && \
    CGO_ENABLED=0 go build -trimpath \
        -ldflags "-w -X github.com/docker/compose/v5/internal.Version=${COMPOSE_VERSION}" \
        -o /out/docker-compose ./cmd

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install docker CLI + compose plugin + redis + docker SDK
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        git && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=compose /out/docker-compose /usr/libexec/docker/cli-plugins/docker-compose

# Install Python dependencies
RUN pip install --no-cache-dir \
    redis==5.0.1 \
    aioredis==2.0.1 \
    docker==7.1.0

# Run as root (has docker socket access)
COPY spawner.py .

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import redis.asyncio; import asyncio; asyncio.run(redis.asyncio.from_url('${REDIS_URL:-redis://redis:6379/0}').ping())" || exit 1

CMD ["python", "-u", "spawner.py"]
