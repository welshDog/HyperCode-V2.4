# Coder Agent — inherits from shared agent-base (FastAPI + docker-cli)
FROM agent-base:latest

WORKDIR /app

# Install agent-specific dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install docker-mcp via pipx
RUN pipx install git+https://github.com/QuantGeekDev/docker-mcp.git

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
