FROM python:3.11-slim

# OS package hardening — upgrade all + install docker-ce-cli (official Docker repo)
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
    apt-get install -y --no-install-recommends docker-ce-cli && \
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

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install python dependencies
COPY healer/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy full agents tree so `agents.shared.*` imports resolve
COPY . /app/agents

# Non-root user with docker group access — security hardening
# -o on docker groupadd: appuser's system GID may already claim 999 on Debian Trixie;
# -o lets the docker group share/reuse that GID without failing the build.
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && (getent group docker || groupadd -o -g 999 docker) \
    && usermod -aG docker appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8008

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8008/health || exit 1

CMD ["uvicorn", "agents.healer.main:app", "--host", "0.0.0.0", "--port", "8008"]
