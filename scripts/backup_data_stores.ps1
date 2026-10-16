# Backup Redis + MinIO + Chroma into backups\stores\<timestamp>\ (checksums + manifest.json).
# Usage: ./scripts/backup_data_stores.ps1 [-SkipChroma]
#
# - Redis : BGSAVE (consistent point-in-time RDB), copy dump.rdb out. AOF is not needed for a restore.
# - MinIO : tar of the data volume via a throwaway helper container (read-only mount).
# - Chroma: COLD copy - the container is stopped for a few seconds so SQLite/HNSW files are consistent,
#           and ALWAYS restarted in a finally block. Use -SkipChroma to avoid even that blip.
# Restore proof: ./scripts/restore_drill_stores.ps1
param([switch]$SkipChroma)
$ErrorActionPreference = 'Stop'

$Helper = 'redis:8-alpine'   # already present locally; only used for tar (--pull never)
$ts   = Get-Date -Format 'yyyyMMdd_HHmmss'
$root = Join-Path $PSScriptRoot '..\backups\stores'
$dest = Join-Path $root $ts
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$dest = (Resolve-Path $dest).Path
$manifest = [ordered]@{ created = (Get-Date).ToString('s'); redis = $null; minio = $null; chroma = $null }
$failed = $false

function Fail($m) { Write-Host "FAIL: $m" -ForegroundColor Red; $script:failed = $true }

# Resolve the volume mounted at /data from the RUNNING container, so a different Compose project name
# (not "hypercode-v24") can never make us archive a freshly auto-created empty volume.
function Get-DataVolume($container) {
    $out = docker inspect $container --format '{{range .Mounts}}{{.Destination}}={{.Name}};{{end}}'
    if ($LASTEXITCODE -ne 0) { throw "cannot inspect container '$container'" }
    $m = ($out -split ';' | Where-Object { $_ -like '/data=*' } | Select-Object -First 1)
    $name = if ($m) { ($m -split '=', 2)[1] } else { '' }
    if ([string]::IsNullOrWhiteSpace($name)) { throw "no named volume mounted at /data on '$container'" }
    $name
}

# Minimal HTTP GET against a container's localhost:8000 using bash /dev/tcp (the chroma image has no curl/wget/python).
function Invoke-ChromaGet($container, $path) {
    # Windows PowerShell 5.1 prepends a UTF-8 BOM to text piped to a native exe, which makes bash choke.
    # Ship the command as base64 instead: no BOM, no quoting layers.
    $sh = 'exec 3<>/dev/tcp/127.0.0.1/8000; printf "GET ' + $path + ' HTTP/1.0\r\nHost: x\r\n\r\n" >&3; cat <&3 | tr -d "\r" | sed "1,/^$/d"'
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($sh))
    $out = (docker exec $container bash -c "echo $b64 | base64 -d | bash") -join ''
    if ([string]::IsNullOrWhiteSpace($out)) { throw "empty response from chroma for $path" }
    $out
}

# ---------------- Redis ----------------
try {
    Write-Host '[redis] BGSAVE...'
    $before = [int64](docker exec redis redis-cli lastsave)
    docker exec redis redis-cli bgsave | Out-Null
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ([int64](docker exec redis redis-cli lastsave) -le $before) {
        if ($sw.Elapsed.TotalSeconds -gt 120) { throw 'BGSAVE did not finish in 120 s' }
        Start-Sleep -Seconds 1
    }
    docker cp redis:/data/dump.rdb (Join-Path $dest 'redis-dump.rdb') | Out-Null
    $ks = @{}
    foreach ($l in (docker exec redis redis-cli info keyspace)) {
        if ($l -match '^(db\d+):keys=(\d+)') { $ks[$Matches[1]] = [int]$Matches[2] }
    }
    $manifest.redis = $ks
    Write-Host ("[redis] OK  {0:N1} KB  keyspace {1}" -f ((Get-Item (Join-Path $dest 'redis-dump.rdb')).Length/1KB), (($ks.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join ' '))
} catch { Fail "redis: $_" }

# ---------------- MinIO ----------------
try {
    Write-Host '[minio] tar volume...'
    $minioVol = Get-DataVolume minio
    docker run --rm --pull never -v "${minioVol}:/src:ro" -v "${dest}:/out" $Helper tar czf /out/minio-data.tgz -C /src .
    if ($LASTEXITCODE -ne 0) { throw "tar exit $LASTEXITCODE" }
    $manifest.minio = [int](docker run --rm --pull never -v "${minioVol}:/src:ro" $Helper sh -c 'find /src -type f | wc -l')
    Write-Host ("[minio] OK  {0:N1} KB  {1} files" -f ((Get-Item (Join-Path $dest 'minio-data.tgz')).Length/1KB), $manifest.minio)
} catch { Fail "minio: $_" }

# ---------------- Chroma ----------------
if (-not $SkipChroma) {
    $stopped = $false
    try {
        $base = '/api/v2/tenants/default_tenant/databases/default_database/collections'
        $raw = Invoke-ChromaGet chroma $base
        if ($raw.Trim()[0] -ne '[') { throw "unexpected collections response: $($raw.Substring(0,[Math]::Min(80,$raw.Length)))" }
        $cols = $raw | ConvertFrom-Json
        $info = @()
        foreach ($c in @($cols | Where-Object { $_ })) {
            $n = [int](Invoke-ChromaGet chroma "$base/$($c.id)/count")
            $info += [ordered]@{ id = $c.id; name = $c.name; count = $n }
        }
        $manifest.chroma = $info
        Write-Host "[chroma] stopping briefly for a consistent copy ($(@($info).Count) collections)..."
        $chromaVol = Get-DataVolume chroma
        docker stop chroma | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "docker stop chroma failed (exit $LASTEXITCODE) - not copying live files" }
        $stopped = $true
        docker run --rm --pull never -v "${chromaVol}:/src:ro" -v "${dest}:/out" $Helper tar czf /out/chroma-data.tgz -C /src .
        if ($LASTEXITCODE -ne 0) { throw "tar exit $LASTEXITCODE" }
        Write-Host ("[chroma] OK  {0:N1} KB" -f ((Get-Item (Join-Path $dest 'chroma-data.tgz')).Length/1KB))
    } catch { Fail "chroma: $_" }
    finally {
        if ($stopped) {
            docker start chroma | Out-Null
            if ($LASTEXITCODE -ne 0) { Fail 'chroma did NOT restart - start it manually: docker start chroma' } else { Write-Host '[chroma] restarted' }
        }
    }
}

# ---------------- checksums + manifest + retention ----------------
Get-ChildItem $dest -File | Where-Object { $_.Name -notin 'manifest.json','SHA256SUMS' } | ForEach-Object {
    "$((Get-FileHash $_.FullName -Algorithm SHA256).Hash)  $($_.Name)"
} | Set-Content (Join-Path $dest 'SHA256SUMS')
$manifest | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $dest 'manifest.json') -Encoding utf8

if ($failed) { Write-Host "Backup INCOMPLETE: $dest" -ForegroundColor Red; exit 1 }
Write-Host "Backup OK: $dest" -ForegroundColor Green
Get-ChildItem $root -Directory | Sort-Object Name -Descending | Select-Object -Skip 7 | Remove-Item -Recurse -Force
