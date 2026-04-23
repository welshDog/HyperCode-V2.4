FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY agents/goal_keeper/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agents/goal_keeper/ .
COPY agents/shared/ /app/shared/
COPY agents/HYPER-AGENT-BIBLE.md .

# Non-root user
RUN useradd -m -u 1000 goalkeeper
USER goalkeeper

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8050/health || exit 1

# Run
CMD ["python", "main.py"]
