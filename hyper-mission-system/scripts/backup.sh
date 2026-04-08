#!/bin/bash
# Backup script for PostgreSQL

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backup_$TIMESTAMP.sql"

echo "Starting backup for $TIMESTAMP..."
docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U user hypermission > backups/$BACKUP_FILE

if [ $? -eq 0 ]; then
  echo "Backup successful: backups/$BACKUP_FILE"
  # aws s3 cp backups/$BACKUP_FILE s3://my-bucket/backups/
else
  echo "Backup failed!"
  exit 1
fi
