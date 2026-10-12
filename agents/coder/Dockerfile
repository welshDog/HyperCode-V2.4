# Coder Agent — inherits from shared agent-base (FastAPI + docker-cli)
FROM agent-base:latest

WORKDIR /app

# Install agent-specific dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install docker-mcp via pipx
RUN pipx install git+https://github.com/QuantGeekDev/docker-mcp.git
# pipx keeps a shared pip under /opt/pipx/shared that it used only to install docker-mcp.
# pip 26.2.1 (newest release) vendors msgpack 1.1.2, urllib3 2.7.0 and setuptools 70.3.0, which
# carry HIGH CVEs with no pip release that updates them yet. Nothing at runtime needs that pip
# (the docker-mcp venv only references the shared dir through a .pth), so remove it from the image.
RUN rm -rf /opt/pipx/shared/lib/python3.12/site-packages/pip \
           /opt/pipx/shared/lib/python3.12/site-packages/pip-*.dist-info

# Copy application code LAST (most frequently changed)
COPY . .

ENV PYTHONPATH=/app \
    AGENT_PORT=8080

# Non-root user already set in agent-base
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -fsS "http://localhost:${AGENT_PORT:-8000}/health" >/dev/null || exit 1

CMD ["python", "main.py"]
