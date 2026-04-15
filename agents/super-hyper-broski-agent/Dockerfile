FROM python:3.11-slim

WORKDIR /app

# OS package hardening — upgrade all + force-install patched packages
RUN apt-get update --allow-releaseinfo-change && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libexpat1 \
        openssl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Pip tool hardening — pin safe versions (eliminates pip/setuptools/jaraco CVEs)
RUN pip install --upgrade --no-cache-dir \
    "pip==26.0.1" \
    "setuptools>=80.0.0" \
    "wheel==0.46.2" \
    "jaraco.context>=6.0.0" \
    "jaraco.functools>=4.1.0" \
    "jaraco.text>=4.0.0"

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m -u 1000 broski && chown -R broski:broski /app
USER broski

# Copy application
COPY --chown=broski:broski main.py .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
    CMD curl -f http://localhost:8015/health || exit 1

# Expose port
EXPOSE 8015

# Run
CMD ["python", "main.py"]
