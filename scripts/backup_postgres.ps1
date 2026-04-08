# Backup Postgres Database
# Usage: ./scripts/backup_postgres.ps1

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = ".\backups\postgres"
$backupFile = "$backupDir\backup_$timestamp.sql"

if (-not (Test-Path -Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}

Write-Host "Starting backup for database: hypercode..."

# Execute docker command
docker exec postgres pg_dump -U hyper hypercode > $backupFile

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Backup successful: $backupFile" -ForegroundColor Green
    
    # Cleanup old backups (keep last 7)
    $files = Get-ChildItem -Path $backupDir -Filter "backup_*.sql" | Sort-Object CreationTime -Descending
    if ($files.Count -gt 7) {
        $files | Select-Object -Skip 7 | Remove-Item
    }
} else {
    Write-Host "❌ Backup failed!" -ForegroundColor Red
    exit 1
}
