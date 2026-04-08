# Restore Postgres Database
# Usage: ./scripts/restore_postgres.ps1 [-BackupFile "path\to\file.sql"] [-Force]

param (
    [string]$BackupFile = "",
    [switch]$Force
)

$backupDir = ".\backups\postgres"

# 1. Determine Backup File
if ([string]::IsNullOrEmpty($BackupFile)) {
    if (Test-Path -Path $backupDir) {
        $latestBackup = Get-ChildItem -Path $backupDir -Filter "backup_*.sql" | Sort-Object CreationTime -Descending | Select-Object -First 1
        if ($latestBackup) {
            $BackupFile = $latestBackup.FullName
            Write-Host "No backup file specified. Using latest: $BackupFile" -ForegroundColor Yellow
        } else {
            Write-Host "❌ No backup files found in $backupDir" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "❌ Backup directory $backupDir does not exist." -ForegroundColor Red
        exit 1
    }
}

if (-not (Test-Path -Path $BackupFile)) {
    Write-Host "❌ Backup file not found: $BackupFile" -ForegroundColor Red
    exit 1
}

# 2. Confirmation
if (-not $Force) {
    Write-Host "⚠️  WARNING: This will OVERWRITE the current 'hypercode' database." -ForegroundColor Red
    Write-Host "   Backup to be restored: $BackupFile"
    $confirmation = Read-Host "Are you sure you want to proceed? (y/N)"
    if ($confirmation -ne "y") {
        Write-Host "Restore cancelled."
        exit 0
    }
}

Write-Host "Starting restore process..."

# 3. Stop dependent services to release DB locks
Write-Host "Stopping dependent services (hypercode-core, celery-worker)..."
docker compose -f docker-compose.production.yml stop hypercode-core celery-worker

# 4. Drop and Recreate Database
Write-Host "Recreating database 'hypercode'..."
# We use 'postgres' user (superuser) to drop/create if 'hyper' doesn't have permissions, 
# but 'hyper' is likely the owner. Let's try with 'hyper' first.
# If 'hyper' is the user, we need to connect to 'template1' or 'postgres' db to drop 'hypercode'.
docker exec postgres dropdb -U hyper --if-exists hypercode
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to drop database. Check active connections." -ForegroundColor Red
    # Try to restart services before exiting?
    docker compose -f docker-compose.production.yml start hypercode-core celery-worker
    exit 1
}

docker exec postgres createdb -U hyper hypercode
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to create database." -ForegroundColor Red
    docker compose -f docker-compose.production.yml start hypercode-core celery-worker
    exit 1
}

# 5. Restore Data
Write-Host "Restoring data from $BackupFile..."
# Use Get-Content piped to docker exec
# Note: PowerShell piping of binary/large text might have encoding issues. 
# 'cat' (Get-Content) is safer if we ensure encoding. 
# Alternatively, use input redirection < inside a shell, but we are in PS.
# Best generic way in PS to pipe file to command:
cmd /c "type `"$BackupFile`" | docker exec -i postgres psql -U hyper -d hypercode"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Database restored successfully." -ForegroundColor Green
} else {
    Write-Host "❌ Restore failed during SQL execution." -ForegroundColor Red
}

# 6. Restart Services
Write-Host "Restarting services..."
docker compose -f docker-compose.production.yml start hypercode-core celery-worker

Write-Host "Restore operation complete."
