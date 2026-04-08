FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd -m -u 1000 broski && chown -R broski:broski /app
COPY --chown=broski:broski main.py .
USER broski
EXPOSE 8016
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:8016/health || exit 1
CMD ["python", "main.py"]
