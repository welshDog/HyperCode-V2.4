$ErrorActionPreference = "Stop"
$BACKUP_DIR = Join-Path $PWD "backups\hypercode"
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
New-Item -ItemType Directory -Force -Path $BACKUP_DIR | Out-Null

Write-Host "Backing up PostgreSQL..."
# Dump to a file inside container first to avoid PowerShell encoding issues
docker exec postgres pg_dump -U postgres hypercode -f /tmp/db_backup.sql
docker cp "postgres:/tmp/db_backup.sql" "$BACKUP_DIR\postgres_$TIMESTAMP.sql"
docker exec postgres rm /tmp/db_backup.sql

Write-Host "Backing up Redis..."
docker exec redis redis-cli BGSAVE
docker cp "redis:/data/dump.rdb" "$BACKUP_DIR\redis_$TIMESTAMP.rdb"

Write-Host "Backing up Grafana..."
# Mount the volume and the local backup dir to tar the data
docker run --rm -v "hypercode_grafana-data:/data" -v "$BACKUP_DIR`:/backup" alpine tar czf "/backup/grafana_$TIMESTAMP.tar.gz" /data

# Retention: keep 30 days
Get-ChildItem $BACKUP_DIR | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item

Write-Host "Backup complete: $BACKUP_DIR"
