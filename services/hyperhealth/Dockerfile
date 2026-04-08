FROM python:3.12-slim

WORKDIR /app

# Install system deps for asyncpg + ssl
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# API mode (default) or WORKER mode via CMD override
EXPOSE 8090

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090", "--workers", "2"]
