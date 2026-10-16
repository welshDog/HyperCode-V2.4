# Restore drill for Redis + MinIO + Chroma: restore the newest backups\stores\<ts> into THROWAWAY
# containers (no network, scratch volumes) and verify against the backup's manifest.json.
# Usage: ./scripts/restore_drill_stores.ps1 [-BackupDir backups\stores\<ts>]
# Never touches the live containers or volumes. Exit 0 = all three verified, 1 = anything failed.
param([string]$BackupDir)
$ErrorActionPreference = 'Stop'

$Helper = 'redis:8-alpine'
if (-not $BackupDir) {
    $BackupDir = (Get-ChildItem (Join-Path $PSScriptRoot '..\backups\stores') -Directory | Sort-Object Name -Descending | Select-Object -First 1).FullName
}
$BackupDir = (Resolve-Path $BackupDir).Path
$m = Get-Content (Join-Path $BackupDir 'manifest.json') -Raw | ConvertFrom-Json
Write-Host "Backup: $BackupDir  (taken $($m.created))"

$results = [ordered]@{}
function Result($name, $ok, $detail) {
    $script:results[$name] = $ok
    $c = if ($ok) { 'Green' } else { 'Red' }
    Write-Host ("  {0,-7} {1}  {2}" -f $name, $(if ($ok) { 'PASS' } else { 'FAIL' }), $detail) -ForegroundColor $c
}
# Run a shell snippet inside a container without stdin/BOM/quoting problems (base64 transport).
function Invoke-Sh($container, $snippet, $shell = 'bash') {
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($snippet))
    (docker exec $container $shell -c "echo $b64 | base64 -d | $shell") -join "`n"
}
# `docker logs 2>&1` raises under $ErrorActionPreference='Stop' in Windows PowerShell 5.1 - read it with Continue.
function Get-Log($container) { & { $ErrorActionPreference = 'Continue'; docker logs $container 2>&1 } | Out-String }
function Wait-Until($sb, $secs, $what) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $secs) { try { if (& $sb) { return } } catch {} ; Start-Sleep 2 }
    throw "timeout waiting for $what"
}

$scratch = 'drill_redis','drill_minio','drill_chroma'
$boxes   = 'redis-drill','minio-drill','chroma-drill'

try {
    # 0. checksums
    Write-Host '[0] verify checksums'
    $bad = 0
    Get-Content (Join-Path $BackupDir 'SHA256SUMS') | ForEach-Object {
        $h, $f = $_ -split '\s+', 2
        if ((Get-FileHash (Join-Path $BackupDir $f) -Algorithm SHA256).Hash -ne $h) { Write-Host "  checksum mismatch: $f" -ForegroundColor Red; $bad++ }
    }
    Result 'sha256' ($bad -eq 0) "$bad mismatches"

    # 1. Redis
    Write-Host '[1] redis'
    try {
        docker volume create drill_redis | Out-Null
        docker run --rm --pull never -v drill_redis:/data -v "${BackupDir}:/in:ro" $Helper sh -c 'cp /in/redis-dump.rdb /data/dump.rdb' | Out-Null
        docker run -d --pull never --name redis-drill --network none --memory 128m -v drill_redis:/data $Helper redis-server --appendonly no --save '""' | Out-Null
        Wait-Until { (docker exec redis-drill redis-cli ping) -eq 'PONG' -and (docker exec redis-drill redis-cli info persistence) -match 'loading:0' } 60 'redis load'
        $got = @{}
        foreach ($l in (docker exec redis-drill redis-cli info keyspace)) { if ($l -match '^(db\d+):keys=(\d+)') { $got[$Matches[1]] = [int]$Matches[2] } }
        $okR = $true; $detail = @()
        foreach ($p in $m.redis.PSObject.Properties) {
            $want = [int]$p.Value; $have = [int]($got[$p.Name]); $tol = [Math]::Max(5, [int]($want * 0.05))
            if ([Math]::Abs($want - $have) -gt $tol) { $okR = $false }
            $detail += "$($p.Name):$have/$want"
        }
        Result 'redis' $okR ("restored/manifest keys  " + ($detail -join ' '))
    } catch { Result 'redis' $false "$_" }

    # 2. MinIO
    Write-Host '[2] minio'
    try {
        docker volume create drill_minio | Out-Null
        docker run --rm --pull never -v drill_minio:/data -v "${BackupDir}:/in:ro" $Helper tar xzf /in/minio-data.tgz -C /data
        if ($LASTEXITCODE -ne 0) { throw 'tar extract failed' }
        $files = [int](docker run --rm --pull never -v drill_minio:/data:ro $Helper sh -c 'find /data -type f | wc -l')
        $secrets = (Resolve-Path (Join-Path $PSScriptRoot '..\secrets')).Path
        docker run -d --pull never --name minio-drill --network none --memory 256m `
            -v drill_minio:/data `
            -v "$secrets\minio_root_user.txt:/run/secrets/minio_root_user:ro" `
            -v "$secrets\minio_root_password.txt:/run/secrets/minio_root_password:ro" `
            -e MINIO_ROOT_USER_FILE=/run/secrets/minio_root_user -e MINIO_ROOT_PASSWORD_FILE=/run/secrets/minio_root_password `
            minio/minio:latest server /data | Out-Null
        Wait-Until { (docker ps --filter name=minio-drill --filter status=running -q) -and ((Get-Log minio-drill) -match 'API:') } 90 'minio boot'
        $log = Get-Log minio-drill
        $fatal = $log -match '(?i)fatal|unable to initialize|decrypt|checksum'
        Result 'minio' (($files -ge [int]$m.minio - 2) -and -not $fatal) "files restored=$files manifest=$($m.minio); boots with original root creds; fatal-in-log=$fatal"
    } catch { Result 'minio' $false "$_" }

    # 3. Chroma
    Write-Host '[3] chroma'
    $chromaTgz = Join-Path $BackupDir 'chroma-data.tgz'
    if (-not (Test-Path $chromaTgz) -and $null -eq $m.chroma) {
        # backup_data_stores.ps1 -SkipChroma writes no archive and a null chroma manifest: not a failure.
        Write-Host '  chroma  SKIPPED  (this backup was taken with -SkipChroma)' -ForegroundColor Yellow
    } else {
    try {
        docker volume create drill_chroma | Out-Null
        docker run --rm --pull never -v drill_chroma:/data -v "${BackupDir}:/in:ro" $Helper tar xzf /in/chroma-data.tgz -C /data
        if ($LASTEXITCODE -ne 0) { throw 'tar extract failed' }
        docker run -d --pull never --name chroma-drill --network none --memory 384m -v drill_chroma:/data chromadb/chroma:latest | Out-Null
        $base = '/api/v2/tenants/default_tenant/databases/default_database/collections'
        $get = { param($p) Invoke-Sh chroma-drill ('exec 3<>/dev/tcp/127.0.0.1/8000; printf "GET ' + $p + ' HTTP/1.0\r\nHost: x\r\n\r\n" >&3; cat <&3 | tr -d "\r" | sed "1,/^$/d"') }
        Wait-Until { (& $get '/api/v2/heartbeat') -match 'heartbeat' } 90 'chroma boot'
        $cols = @((& $get $base) | ConvertFrom-Json | Where-Object { $_ })
        $okC = ($cols.Count -eq @($m.chroma).Count); $detail = @()
        foreach ($w in @($m.chroma)) {
            $hit = $cols | Where-Object { $_.id -eq $w.id -and $_.name -eq $w.name }
            $n = if ($hit) { [int](& $get "$base/$($w.id)/count") } else { -1 }
            if ($n -ne [int]$w.count) { $okC = $false }
            $detail += "$($w.name):$n/$($w.count)"
        }
        Result 'chroma' $okC ("collections=$($cols.Count)  vectors restored/manifest " + ($detail -join ' '))
    } catch { Result 'chroma' $false "$_" }
    }
}
finally {
    foreach ($b in $boxes)   { docker rm -f $b 2>$null | Out-Null }
    foreach ($v in $scratch) { docker volume rm $v 2>$null | Out-Null }
    Write-Host 'scratch containers + volumes removed'
}

if ($results.Values -contains $false) { Write-Host 'STORES RESTORE DRILL: FAIL' -ForegroundColor Red; exit 1 }
Write-Host 'STORES RESTORE DRILL: PASS' -ForegroundColor Green; exit 0
