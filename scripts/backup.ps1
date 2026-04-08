# HyperCode Production Backup Script
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "../backups/$timestamp"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

Write-Host "Starting backup for HyperCode at $timestamp..."

# 1. Postgres Backup
Write-Host "Backing up Postgres..."
docker exec postgres pg_dump -U postgres hypercode > "$backupDir/hypercode_db.sql"
if ($?) { Write-Host "Postgres backup success." -ForegroundColor Green } else { Write-Host "Postgres backup failed." -ForegroundColor Red }

# 2. Redis Backup
Write-Host "Backing up Redis..."
# Force save
docker exec redis redis-cli save
# Copy dump.rdb
docker cp redis:/data/dump.rdb "$backupDir/redis_dump.rdb"
if ($?) { Write-Host "Redis backup success." -ForegroundColor Green } else { Write-Host "Redis backup failed." -ForegroundColor Red }

Write-Host "Backup completed in $backupDir"
