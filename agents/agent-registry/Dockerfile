FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd -m -u 1000 broski && chown -R broski:broski /app
COPY --chown=broski:broski agent_registry.py .
USER broski
EXPOSE 8077
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:8077/health || exit 1
CMD ["python", "agent_registry.py"]
