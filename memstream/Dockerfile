# MemStream Dockerfile - Simple Flask version for testing
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY app.py .

# Expose ports
EXPOSE 8009

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8009/health/memstream || exit 1

# Start the server
CMD ["python", "app.py"]