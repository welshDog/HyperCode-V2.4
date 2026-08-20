FROM python:3.11-slim

WORKDIR /app

ENV AGENT_PORT=8080

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY . .

# Non-root user
RUN useradd -m -u 1000 goalkeeper
USER goalkeeper

# Health check
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run
CMD ["python", "main.py"]
