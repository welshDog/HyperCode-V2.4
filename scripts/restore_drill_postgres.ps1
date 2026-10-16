# Postgres restore drill: restore the newest backup into a THROWAWAY database and
# compare exact per-table row counts + alembic version against the live database.
# Usage: ./scripts/restore_drill_postgres.ps1 [-BackupFile path\to\backup.dump] [-KeepScratch]
#
# Safe by design: only ever creates/drops the scratch DB "restore_drill"; the live DB is read-only here.
# Exit 0 = restore verified, 1 = failed or mismatch.
param([string]$BackupFile, [switch]$KeepScratch)

$ErrorActionPreference = 'Stop'
$scratch = 'restore_drill'
$backupDir = Join-Path $PSScriptRoot "..\backups\postgres"
if (-not $BackupFile) {
    $BackupFile = (Get-ChildItem $backupDir -Filter "backup_*.dump" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
}
if (-not $BackupFile -or -not (Test-Path $BackupFile)) { Write-Host "No backup file found" -ForegroundColor Red; exit 1 }
$item = Get-Item $BackupFile
$age = [int]((Get-Date) - $item.LastWriteTime).TotalMinutes
Write-Host ("Backup: {0}  {1:N1} MB  age {2} min" -f $item.Name, ($item.Length/1MB), $age)

# 1. checksum must match what the backup wrote
$shaFile = "$BackupFile.sha256"
if (Test-Path $shaFile) {
    $want = ((Get-Content $shaFile) -split '\s+')[0]
    $got  = (Get-FileHash $BackupFile -Algorithm SHA256).Hash
    if ($want -ne $got) { Write-Host "CHECKSUM MISMATCH" -ForegroundColor Red; exit 1 }
    Write-Host "checksum OK"
} else { Write-Host "warning: no .sha256 alongside backup" -ForegroundColor Yellow }

# SQL goes over stdin: embedded quotes in `-c "..."` get mangled by PowerShell's native-arg passing.
function PsqlLive($db, $sql) { $sql | docker exec -i postgres sh -c ('psql -U "$POSTGRES_USER" -d {0} -At -v ON_ERROR_STOP=1' -f $db) }
$liveDb = (docker exec postgres sh -c 'echo $POSTGRES_DB').Trim()

$countSql = "select table_name||'='||((xpath('/row/c/text()', query_to_xml(format('select count(*) as c from %I.%I', table_schema, table_name), false, true, '')))[1])::text from information_schema.tables where table_schema='public' and table_type='BASE TABLE' order by 1"

$ok = $true
try {
    PsqlLive postgres "drop database if exists $scratch" | Out-Null
    PsqlLive postgres "create database $scratch" | Out-Null

    docker cp $BackupFile "postgres:/tmp/drill.dump" | Out-Null
    $sw = [Diagnostics.Stopwatch]::StartNew()
    docker exec postgres sh -c "pg_restore -U `"`$POSTGRES_USER`" -d $scratch --no-owner /tmp/drill.dump" 2>&1 | Select-Object -Last 5
    $rc = $LASTEXITCODE
    $sw.Stop()
    Write-Host ("pg_restore exit {0} in {1:N1}s" -f $rc, $sw.Elapsed.TotalSeconds)
    if ($rc -ne 0) { $ok = $false }

    $live = PsqlLive $liveDb $countSql
    $rest = PsqlLive $scratch $countSql
    $diff = Compare-Object $live $rest
    Write-Host ("tables: live={0} restored={1}" -f @($live).Count, @($rest).Count)
    if ($diff) {
        Write-Host "ROW-COUNT DIFFERENCES (live '<=' vs restored '=>'; hot tables may drift since the dump):" -ForegroundColor Yellow
        $diff | ForEach-Object { "  $($_.SideIndicator) $($_.InputObject)" }
        if (@($live).Count -ne @($rest).Count) { $ok = $false }
    } else { Write-Host "row counts identical across all tables" -ForegroundColor Green }

    $lv = PsqlLive $liveDb "select version_num from alembic_version"
    $rv = PsqlLive $scratch "select version_num from alembic_version"
    Write-Host "alembic live=$lv restored=$rv"
    if ($lv -ne $rv) { $ok = $false }
}
finally {
    docker exec postgres rm -f /tmp/drill.dump | Out-Null
    if (-not $KeepScratch) { PsqlLive postgres "drop database if exists $scratch" | Out-Null; Write-Host "scratch DB dropped" }
}
if ($ok) { Write-Host "RESTORE DRILL: PASS" -ForegroundColor Green; exit 0 }
Write-Host "RESTORE DRILL: FAIL" -ForegroundColor Red; exit 1
