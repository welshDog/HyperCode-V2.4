# Backup Postgres Database (custom-format dump + sha256)
# Usage: ./scripts/backup_postgres.ps1
#
# - Role/DB come from the container's own POSTGRES_USER/POSTGRES_DB (no hardcoded role).
# - Dump is written INSIDE the container and copied out with `docker cp`, so PowerShell
#   never re-encodes the bytes (the old `docker exec ... > file` redirect could corrupt them).
# - A failed/empty dump is deleted and never counts toward retention; old backups are only
#   pruned after a verified-good new one exists.
# Restore:  docker cp <file> postgres:/tmp/r.dump ; docker exec postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d <db> /tmp/r.dump'

$ErrorActionPreference = 'Stop'
$timestamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir  = Join-Path $PSScriptRoot "..\backups\postgres"
$backupFile = Join-Path $backupDir "backup_$timestamp.dump"
$inContainer = "/tmp/backup_$timestamp.dump"

New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

function Fail($msg) {
    Write-Host "Backup failed: $msg" -ForegroundColor Red
    if (Test-Path $backupFile) { Remove-Item $backupFile -Force }
    docker exec postgres rm -f $inContainer 2>$null | Out-Null
    exit 1
}

Write-Host "Starting backup (custom format)..."
docker exec postgres sh -c "pg_dump -U `"`$POSTGRES_USER`" -d `"`$POSTGRES_DB`" -Fc -f $inContainer"
if ($LASTEXITCODE -ne 0) { Fail "pg_dump exited $LASTEXITCODE" }

docker cp "postgres:$inContainer" $backupFile
if ($LASTEXITCODE -ne 0) { Fail "docker cp exited $LASTEXITCODE" }
docker exec postgres rm -f $inContainer | Out-Null

if (-not (Test-Path $backupFile) -or (Get-Item $backupFile).Length -lt 1024) { Fail "dump missing or suspiciously small" }

# Prove the archive is readable (catalog listing) before trusting it.
docker cp $backupFile "postgres:$inContainer" | Out-Null
docker exec postgres sh -c "pg_restore -l $inContainer > /dev/null"
$listRc = $LASTEXITCODE
docker exec postgres rm -f $inContainer | Out-Null
if ($listRc -ne 0) { Fail "pg_restore cannot read the archive" }

$hash = (Get-FileHash $backupFile -Algorithm SHA256).Hash
"$hash  $(Split-Path $backupFile -Leaf)" | Set-Content "$backupFile.sha256"
Write-Host ("Backup OK: {0} ({1:N1} MB) sha256={2}" -f $backupFile, ((Get-Item $backupFile).Length/1MB), $hash.Substring(0,16)) -ForegroundColor Green

# Retention: keep the newest 7 verified dumps.
Get-ChildItem $backupDir -Filter "backup_*.dump" | Sort-Object CreationTime -Descending | Select-Object -Skip 7 | ForEach-Object {
    Remove-Item $_.FullName -Force
    Remove-Item "$($_.FullName).sha256" -Force -ErrorAction SilentlyContinue
}
