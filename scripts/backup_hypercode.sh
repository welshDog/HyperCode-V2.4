#!/bin/bash
# backup_hypercode.sh - Daily backup for HyperCode
# Usage: ./scripts/backup_hypercode.sh

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

echo "🔄 Starting HyperCode backup: $TIMESTAMP"

# PostgreSQL backup
echo "📦 Backing up PostgreSQL..."
docker exec postgres pg_dump -U postgres hypercode | gzip > "$BACKUP_DIR/postgres_$TIMESTAMP.sql.gz"

# Redis backup
echo "💾 Backing up Redis..."
docker exec redis redis-cli BGSAVE
# Wait briefly for BGSAVE to complete (simple heuristic)
sleep 5
docker cp redis:/data/dump.rdb "$BACKUP_DIR/redis_$TIMESTAMP.rdb"

# Verify backups
POSTGRES_SIZE=$(stat -c%s "$BACKUP_DIR/postgres_$TIMESTAMP.sql.gz" 2>/dev/null || echo "0")
REDIS_SIZE=$(stat -c%s "$BACKUP_DIR/redis_$TIMESTAMP.rdb" 2>/dev/null || echo "0")

if [ "$POSTGRES_SIZE" -gt 0 ] && [ "$REDIS_SIZE" -gt 0 ]; then
    echo "✅ Backup complete!"
    echo "   PostgreSQL: $POSTGRES_SIZE bytes"
    echo "   Redis: $REDIS_SIZE bytes"
    exit 0
else
    echo "❌ Backup failed! Check container status."
    exit 1
fi
