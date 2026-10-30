# docker-stats-exporter: per-container metrics for Docker Desktop (containerd
# image store), where cAdvisor cannot enumerate containers. Stdlib only.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY exporter.py .

RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

EXPOSE 9417
HEALTHCHECK --interval=30s --timeout=20s --retries=3 --start-period=30s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9417/health', timeout=10)"

CMD ["python", "exporter.py"]
