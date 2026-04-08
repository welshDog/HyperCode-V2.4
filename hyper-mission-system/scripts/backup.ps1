Write-Host "Starting backup for $(Get-Date -Format 'yyyyMMdd_HHmmss')..."
$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$BackupFile = "backup_$Timestamp.sql"
docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U user hypermission > "backups/$BackupFile"

if ($?) {
    Write-Host "Backup successful: backups/$BackupFile"
} else {
    Write-Host "Backup failed!"
    exit 1
}
