FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

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
