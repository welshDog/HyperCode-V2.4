FROM python:3.11-slim

WORKDIR /app

# Phase 9 standard: OS hardening
RUN apt-get update --allow-releaseinfo-change && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        gcc \
        postgresql-client \
        ca-certificates \
        curl \
        libexpat1 \
        openssl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY requirements.txt .

# Phase 9 standard: pip pinning
RUN pip install --upgrade --no-cache-dir \
    "pip==26.0.1" \
    "setuptools>=80.0.0" \
    "wheel==0.46.2" \
    "jaraco.context>=6.0.0" \
    "jaraco.functools>=4.1.0" \
    "jaraco.text>=4.0.0" && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import discord; print('ok')" || exit 1

CMD ["python", "bot.py"]
