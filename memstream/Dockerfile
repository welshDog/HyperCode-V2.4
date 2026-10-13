# MemStream Dockerfile - Simple Flask version for testing
FROM python:3.9-slim

# Install curl for healthcheck
# apt-get upgrade picks up the patched Debian packages (openssl, perl, util-linux...)
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Pip tool hardening - setuptools>=80 vendors patched jaraco.context; wheel 0.46.2 fixes CVE-2026-24049
RUN pip install --upgrade --no-cache-dir \
    "pip==26.0.1" \
    "setuptools>=80.0.0" \
    "wheel==0.46.2" \
    "jaraco.context>=6.0.0" \
    "jaraco.functools>=4.1.0" \
    "jaraco.text>=4.0.0"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY app.py .

# Run as non-root (uid 1000), same pattern as agents/*
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose ports
EXPOSE 8009

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8009/health/memstream || exit 1

# Start the server
CMD ["python", "app.py"]