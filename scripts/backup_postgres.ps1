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

# Full-content check on the in-container file BEFORE trusting it: `pg_restore -f /dev/null` decompresses and
# replays every data block (a catalogue-only `-l` would pass a truncated data section). No scratch DB needed.
docker exec postgres sh -c "pg_restore -f /dev/null $inContainer"
if ($LASTEXITCODE -ne 0) { Fail "pg_restore cannot read the full archive (truncated or corrupt dump)" }
$srcHash = ((docker exec postgres sh -c "sha256sum $inContainer") -split '\s+')[0].ToUpper()
if ($srcHash.Length -ne 64) { Fail "could not checksum the dump inside the container" }

docker cp "postgres:$inContainer" $backupFile
if ($LASTEXITCODE -ne 0) { Fail "docker cp exited $LASTEXITCODE" }
docker exec postgres rm -f $inContainer | Out-Null

if (-not (Test-Path $backupFile) -or (Get-Item $backupFile).Length -lt 1024) { Fail "dump missing or suspiciously small" }

$hash = (Get-FileHash $backupFile -Algorithm SHA256).Hash
if ($hash -ne $srcHash) { Fail "copy to host does not match the dump made in the container (checksum mismatch)" }
"$hash  $(Split-Path $backupFile -Leaf)" | Set-Content "$backupFile.sha256"
Write-Host ("Backup OK: {0} ({1:N1} MB) sha256={2}" -f $backupFile, ((Get-Item $backupFile).Length/1MB), $hash.Substring(0,16)) -ForegroundColor Green

# Retention: keep the newest 7 verified dumps.
Get-ChildItem $backupDir -Filter "backup_*.dump" | Sort-Object CreationTime -Descending | Select-Object -Skip 7 | ForEach-Object {
    Remove-Item $_.FullName -Force
    Remove-Item "$($_.FullName).sha256" -Force -ErrorAction SilentlyContinue
}
