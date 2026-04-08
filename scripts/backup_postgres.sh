#!/bin/sh
# Backup Postgres Database
# Usage: ./backup_postgres.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups/postgres"
mkdir -p $BACKUP_DIR

echo "Starting backup for database: ${POSTGRES_DB:-hypercode}..."

docker exec postgres pg_dump -U ${POSTGRES_USER:-hyper} ${POSTGRES_DB:-hypercode} > $BACKUP_DIR/backup_$TIMESTAMP.sql

if [ $? -eq 0 ]; then
  echo "✅ Backup successful: $BACKUP_DIR/backup_$TIMESTAMP.sql"
  # Keep only last 7 backups
  ls -tp $BACKUP_DIR/backup_*.sql | tail -n +8 | xargs -I {} rm -- {}
else
  echo "❌ Backup failed!"
  exit 1
fi
