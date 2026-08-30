# Meta-Research Architect Hyper Agent - Phase 1 (observe -> explain)
FROM python:3.12-slim

# Non-root user
RUN groupadd -r hyper && useradd -r -g hyper hyper

WORKDIR /app

# Deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R hyper:hyper /app
USER hyper

ENV META_RESEARCH_ARCHITECT_PORT=8095

# python:3.12-slim has no curl - use urllib
HEALTHCHECK --interval=30s --timeout=3s --retries=3 --start-period=15s \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8095/health', timeout=2).status==200 else 1)"]

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8095"]
