FROM python:3.11-slim

WORKDIR /app

# Security: non-root user
RUN groupadd -r broski && useradd -r -g broski broski

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure data dirs exist
RUN mkdir -p /opt/hypercode/data/broski-bot/db \
             /opt/hypercode/data/broski-bot/logs \
             /opt/hypercode/data/broski-bot/backups \
  && chown -R broski:broski /app /opt/hypercode

USER broski

CMD ["python", "main.py"]
