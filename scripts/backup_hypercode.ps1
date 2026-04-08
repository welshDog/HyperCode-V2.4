$date = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupDir = "./backups"
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir
}

Write-Host "Backing up Postgres Database..."
docker exec -t postgres pg_dumpall -c -U postgres | Out-File -FilePath "$backupDir/hypercode_db_$date.sql" -Encoding utf8

if ($?) {
    Write-Host "Database backup successful: $backupDir/hypercode_db_$date.sql" -ForegroundColor Green
} else {
    Write-Host "Database backup failed!" -ForegroundColor Red
}
