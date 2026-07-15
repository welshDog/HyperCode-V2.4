FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway injects $PORT; default 8765 for local/docker.
ENV PORT=8765
CMD ["sh", "-c", "uvicorn hyper_mcp_server:app --host 0.0.0.0 --port ${PORT}"]
