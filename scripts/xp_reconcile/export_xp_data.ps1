# export_xp_data.ps1 - READ-ONLY snapshot of the datasets the XP reconcile tools compare.
#   Redis db1: every "seen" marker (with its remaining TTL and the exact time it was read) and the award stream;
#   Postgres: the dev-action ledger rows.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\xp_reconcile\export_xp_data.ps1 -OutDir <folder>
# Then:  python -X utf8 scripts\xp_reconcile\analyse_missing.py <folder>      (see docs\BROSKI_XP_RECONCILE.md)
param([Parameter(Mandatory = $true)][string]$OutDir)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# Windows PowerShell 5.1's Set-Content -Encoding utf8 writes a BOM, which shifted the first marker key by one character and
# produced a false "missing" award during testing. Always write BOM-free, whichever PowerShell runs this.
function Save-Utf8([string]$Path, [object]$Lines) {
    [IO.File]::WriteAllLines($Path, [string[]]@($Lines), (New-Object Text.UTF8Encoding $false))
}

# Run a snippet inside a container as base64 so Windows PowerShell 5.1 cannot mangle quoting.
function Invoke-InContainer([string]$Container, [string]$Snippet) {
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($Snippet -replace "`r", '')))
    $out = docker exec $Container sh -c "echo $b64 | base64 -d | sh"
    if ($LASTEXITCODE -ne 0) { throw "docker exec $Container failed (exit $LASTEXITCODE)" }
    return $out
}

# ORDER MATTERS: markers first, then the stream (a superset of them). If an award lands mid-export its marker (if read) always has
# its stream entry. Each marker line is "<key> <remaining ttl> <epoch seconds when that ttl was read>".
$markers = Invoke-InContainer 'redis' 'redis-cli -n 1 --scan --pattern "broski:xp:seen:*" | while read k; do echo "$k $(redis-cli -n 1 ttl "$k") $(date +%s)"; done'
Save-Utf8 (Join-Path $OutDir 'markers.txt') $markers
Save-Utf8 (Join-Path $OutDir 'snapshot.txt') @("snapshot time (UTC epoch): " + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds())

# The whole award stream: raw redis-cli output (an id line, then field/value lines).
$stream = docker exec redis redis-cli -n 1 xrange broski:xp:log - +
if ($LASTEXITCODE -ne 0) { throw 'could not read the Redis stream' }
Save-Utf8 (Join-Path $OutDir 'stream.txt') $stream

# The ledger's dev-action rows as CSV (quoted, so commit messages with punctuation are safe).
$sql = "COPY (select id, wallet_id, amount, reason, meta->>'source' as source, meta->>'source_id' as source_id, to_char(created_at at time zone 'UTC','YYYY-MM-DD HH24:MI:SS.MS') as created_utc from broski_transactions where meta->>'stream'='dev-action' order by id) TO STDOUT WITH CSV HEADER"
$ledger = Invoke-InContainer 'postgres' ('psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q -c "' + $sql.Replace('"', '\"') + '"')
Save-Utf8 (Join-Path $OutDir 'ledger.csv') $ledger

Get-ChildItem $OutDir | ForEach-Object { "{0,-14} {1,9:N0} bytes" -f $_.Name, $_.Length }
