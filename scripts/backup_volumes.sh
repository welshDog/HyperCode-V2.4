#!/bin/bash
set -e

BACKUP_DIR="/backups/hypercode"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL (most critical)
echo "Backing up PostgreSQL..."
docker exec postgres pg_dump -U postgres hypercode | \
  gzip > "$BACKUP_DIR/postgres_$TIMESTAMP.sql.gz"

# Backup Redis (session state)
echo "Backing up Redis..."
docker exec redis redis-cli BGSAVE
docker cp redis:/data/dump.rdb "$BACKUP_DIR/redis_$TIMESTAMP.rdb"

# Backup Grafana dashboards (easy to recreate, but save anyway)
echo "Backing up Grafana..."
docker run --rm -v hypercode_grafana-data:/data -v "$BACKUP_DIR":/backup \
  alpine tar czf /backup/grafana_$TIMESTAMP.tar.gz /data

# Retention: keep 30 days
find "$BACKUP_DIR" -type f -mtime +30 -delete

echo "Backup complete: $BACKUP_DIR"
