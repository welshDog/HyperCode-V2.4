FROM python:3.11-slim

WORKDIR /app

ENV AGENT_PORT=8080

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pip tool hardening - setuptools>=80 vendors patched jaraco.context; wheel 0.46.2 fixes CVE-2026-24049
RUN pip install --upgrade --no-cache-dir \
    "pip==26.0.1" \
    "setuptools>=80.0.0" \
    "wheel==0.46.2" \
    "jaraco.context>=6.0.0" \
    "jaraco.functools>=4.1.0" \
    "jaraco.text>=4.0.0"

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
