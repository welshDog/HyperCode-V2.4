FROM python:3.11-slim

# Install Docker CLI (client only — not the daemon) + curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

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
# docker group GID 999 is the default on most Linux distros;
# compose can override with group_add if the host GID differs
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && (getent group docker || groupadd -g 999 docker) \
    && usermod -aG docker appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8008

# Health check
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8008/health || exit 1

# Run the application
CMD ["uvicorn", "agents.healer.main:app", "--host", "0.0.0.0", "--port", "8008"]
