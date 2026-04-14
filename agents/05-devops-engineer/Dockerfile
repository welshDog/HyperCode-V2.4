# DevOps Engineer Agent - Optimized
# Multi-stage build with improved caching

# ========================================
# Stage 1: Builder
# ========================================
FROM python:3.11-slim AS builder

WORKDIR /build

# OS package hardening in builder stage
RUN apt-get update --allow-releaseinfo-change && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Python dependencies (leverage cache)
COPY agents/05-devops-engineer/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# ========================================
# Stage 2: Runtime
# ========================================
FROM python:3.11-slim

WORKDIR /app

# OS package hardening — upgrade all + docker-ce-cli (official) + kubectl
# Using docker-ce-cli (not docker.io) avoids Debian-packaged moby HIGH CVEs
RUN apt-get update --allow-releaseinfo-change && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        libexpat1 \
        openssl && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install kubectl (pinned version for reproducibility)
RUN curl -LO "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm kubectl

# Pip tool hardening — pin safe versions
RUN pip install --upgrade --no-cache-dir \
    "pip==26.0.1" \
    "setuptools>=80.0.0" \
    "wheel==0.46.2" \
    "jaraco.context>=6.0.0" \
    "jaraco.functools>=4.1.0" \
    "jaraco.text>=4.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AGENT_NAME=devops-engineer \
    AGENT_ROLE="DevOps Engineer" \
    AGENT_MODEL=claude-3-5-sonnet-20241022 \
    AGENT_PORT=8006

# Install wheels from builder
COPY --from=builder /wheels /wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels

# Copy application code
COPY agents/05-devops-engineer/agent.py .
COPY agents/05-devops-engineer/base_agent.py .
COPY agents/05-devops-engineer/config.json .

# Copy Shared Modules (Evolution Protocol)
COPY agents/shared /app/agents/shared

# Mount point for Hive Mind
VOLUME ["/app/hive_mind"]

# Non-root user with docker/kubectl access — security hardening
# docker group GID 999 is the default on most Linux distros
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && (getent group docker || groupadd -g 999 docker) \
    && usermod -aG docker appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8006

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \
    CMD curl -f http://localhost:${AGENT_PORT}/health || exit 1

CMD ["python", "agent.py"]
