# Backup watchdog: checks that the three backup jobs really ran and their output is fresh, and alerts if not.
#   - each Task Scheduler job's last result (0 = ok; offsite 2 = Google Drive not mounted)
#   - freshness: newest Postgres dump, stores set, C: mirror dump, Google Drive archive
#   - disk space (H:, C:), 7z present, passphrase file present
#   - Redis: memory % of cap (>= -RedisWarnPct, default 70), eviction policy must be volatile-lru, no evicted keys
#   - Core auth: any 401/403 from a container to hypercode-core since the previous run (stale/wrong API keys)
#   - BROski$ XP: awards banked in Redis (seen-markers older than -XpGraceMinutes) with no row in the Postgres ledger
# Alerts go to the Discord health webhook (DISCORD_HEALTH_WEBHOOK in .env, never printed/logged) and a Windows
# toast as fallback. Dedupe: one alert per distinct problem set, repeated at most every 12 h; a "recovered" message
# is sent once when everything is healthy again. Messages contain status text only - no secrets.
# Usage: ./scripts/backup_watchdog.ps1 [-DryRun] [-Test] [-MaxAgeHours 26]
#   -DryRun   print findings, send nothing, don't touch state      -Test  send a one-off test message
param([switch]$DryRun, [switch]$Test, [double]$MaxAgeHours = 26, [double]$RedisWarnPct = 70,
      [double]$AuthWindowHours = 0,   # 0 = since the previous run (clamped 2h..26h)
      [string]$CoreLogPath = '',      # test hook: read core's access log from a file instead of `docker logs`
      [int]$XpGraceMinutes = 10,      # awards younger than this may still be on their way to Postgres
      [string]$XpMarkersFile = '',    # test hooks for the XP reconciliation: lines "<source_id> <ttl>" / one source_id per line
      [string]$XpLedgerFile = '')

. (Join-Path $PSScriptRoot 'lib\xp_reconcile.ps1')
$ErrorActionPreference = 'Stop'
$Repo     = Split-Path -Parent $PSScriptRoot
$Backups  = Join-Path $Repo 'backups'
$LocalCopy = 'C:\HyperCodeBackups'
$State    = Join-Path $Backups 'watchdog-state.json'
$Log      = Join-Path $Backups 'watchdog.log'
$Repeat   = 12   # hours between repeats of the same alert

function Log($m) { $l = "$(Get-Date -Format s) $m"; Write-Host $l; if (-not $DryRun) { Add-Content -Path $Log -Value $l -Encoding utf8 } }

# ---- notification ----
function Get-Webhook {
    $line = Get-Content (Join-Path $Repo '.env') | Where-Object { $_ -match '^\s*DISCORD_HEALTH_WEBHOOK\s*=' } | Select-Object -First 1
    if ($line) { return (($line -split '=', 2)[1]).Trim().Trim('"').Trim("'") }
}
function Send-Alert($title, $lines, $kind) {
    $icon = switch ($kind) { 'ok' { [string][char]0x2705 } 'test' { [char]::ConvertFromUtf32(0x1F514) } default { [string][char]0x26A0 + [char]0xFE0F } }
    $text = "$icon **$title**`n" + (($lines | ForEach-Object { "- $_" }) -join "`n")
    $sent = $false
    $hook = Get-Webhook
    if ($hook) {
        try {
            $body = [Text.Encoding]::UTF8.GetBytes((@{ username = 'HyperCode Backups'; content = $text } | ConvertTo-Json -Compress))
            Invoke-RestMethod -Uri $hook -Method Post -ContentType 'application/json; charset=utf-8' -Body $body | Out-Null
            $sent = $true; Log "alert sent to Discord: $title"
        } catch {
            # never echo the exception text: it can contain the webhook URL
            $code = try { [int]$_.Exception.Response.StatusCode } catch { 'n/a' }
            Log "Discord send FAILED (http $code)"
        }
    } else { Log 'no DISCORD_HEALTH_WEBHOOK in .env' }
    try {   # local toast (works for the logged-in user; harmless if it can't show)
        [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
        $x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $n = $x.GetElementsByTagName('text'); $n.Item(0).AppendChild($x.CreateTextNode($title)) | Out-Null
        $n.Item(1).AppendChild($x.CreateTextNode(($lines | Select-Object -First 3) -join '; ')) | Out-Null
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('HyperCode Backups').Show([Windows.UI.Notifications.ToastNotification]::new($x))
        if (-not $sent) { $sent = $true }
    } catch { }
    return $sent
}

if ($Test) { [void](Send-Alert 'Backup watchdog test' @('If you can read this, backup failure alerts reach you.','No action needed.') 'test'); exit 0 }

# ---- checks ----
$problems = New-Object System.Collections.Generic.List[string]
function Age($item) { [math]::Round(((Get-Date) - $item.LastWriteTime).TotalHours, 1) }

foreach ($t in @(@{n='HyperCode Postgres Backup';ok=@(0)}, @{n='HyperCode Stores Backup';ok=@(0)}, @{n='HyperCode Offsite Copy';ok=@(0)})) {
    $task = Get-ScheduledTask -TaskName $t.n -TaskPath '\HyperCode\' -ErrorAction SilentlyContinue
    if (-not $task) { $problems.Add("Scheduled task '$($t.n)' is missing"); continue }
    $i = Get-ScheduledTaskInfo -TaskName $t.n -TaskPath '\HyperCode\'
    $r = [uint32]$i.LastTaskResult
    if ($r -in 0, 0x41301, 0x41303) { continue }                      # ok / running / never run yet
    if ($t.n -like '*Offsite*' -and $r -eq 2) { $problems.Add('Off-site copy is queued: Google Drive for Desktop is not mounted/signed in'); continue }
    $problems.Add("'$($t.n)' last run failed (result 0x$('{0:X}' -f $r) at $($i.LastRunTime))")
}

function CheckFresh($label, $item) {
    if (-not $item) { $problems.Add("${label}: nothing found"); return }
    $a = Age $item
    if ($a -gt $MaxAgeHours) { $problems.Add("${label} is stale: newest is $a h old (limit $MaxAgeHours h)") }
}
CheckFresh 'Postgres backup' (Get-ChildItem (Join-Path $Backups 'postgres') -Filter 'backup_*.dump' -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1)
CheckFresh 'Stores backup'   (Get-ChildItem (Join-Path $Backups 'stores') -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1)
CheckFresh 'Second-disk copy' (Get-ChildItem (Join-Path $LocalCopy 'postgres') -Filter 'backup_*.dump' -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1)
# Same candidate roots as offsite_copy.ps1, so a delivery there is never reported as "folder not found" here.
$driveRoots = @((Get-PSDrive -PSProvider FileSystem).Name | ForEach-Object { "${_}:\My Drive" }) + "$env:USERPROFILE\My Drive" + "$env:USERPROFILE\Google Drive\My Drive"
$drive = $driveRoots | ForEach-Object { Join-Path $_ 'HyperCode-Backups' } | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($drive) { CheckFresh 'Google Drive archive' (Get-ChildItem $drive -Filter 'hypercode_*.7z' -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1) }
else { $problems.Add('Google Drive folder not found (Drive for Desktop not running/signed in?)') }

foreach ($d in @(@{l='H';min=20}, @{l='C';min=10})) {
    # A disconnected drive must become an alert, not a crash that swallows every other alert.
    $psd = Get-PSDrive -Name $d.l -PSProvider FileSystem -ErrorAction SilentlyContinue
    if (-not $psd -or -not (Test-Path "$($d.l):\")) { $problems.Add("Disk $($d.l): is not available (disconnected?)"); continue }
    $free = [math]::Round($psd.Free / 1GB, 1)
    if ($free -lt $d.min) { $problems.Add("Disk $($d.l): only $free GB free (min $($d.min) GB)") }
}
if (-not (Get-Command 7z -ErrorAction SilentlyContinue)) { $problems.Add('7z not found on PATH (encrypted off-site copy will fail)') }
if (-not (Test-Path (Join-Path $Repo 'secrets\offsite_backup_passphrase.txt'))) { $problems.Add('Off-site passphrase file is missing') }

# ---- Redis health (durable queue/state shares db0 with cache; see volatile-lru change) ----
# Why: with volatile-lru, durable keys (no TTL) are never evicted, so if they fill the cap writes fail loudly.
# Alert early on memory %, a wrong eviction policy (silent data loss risk) and any eviction at all.
try {
    $ri = @{}
    foreach ($l in (docker exec redis redis-cli info memory) + (docker exec redis redis-cli info stats)) {
        if ($l -match '^(used_memory|maxmemory|maxmemory_policy|evicted_keys):(.+)$') { $ri[$Matches[1]] = $Matches[2].Trim() }
    }
    if (-not $ri.ContainsKey('used_memory')) { throw 'no data' }
    $used = [double]$ri['used_memory']; $cap = [double]$ri['maxmemory']
    if ($cap -gt 0) {
        $pct = [math]::Round($used / $cap * 100, 1)
        if ($pct -ge $RedisWarnPct) { $problems.Add("Redis memory at $pct% of its cap ($([math]::Round($used/1MB,0)) MB of $([math]::Round($cap/1MB,0)) MB) - durable queue/state data is at risk") }
    } else { $problems.Add('Redis has no maxmemory cap set') }
    if ($ri['maxmemory_policy'] -ne 'volatile-lru') { $problems.Add("Redis eviction policy is '$($ri['maxmemory_policy'])', expected volatile-lru - durable keys (queues, approvals, task state) can be silently evicted") }
    if ([int64]$ri['evicted_keys'] -gt 0) { $problems.Add("Redis has evicted $($ri['evicted_keys']) key(s) since its last restart - memory pressure") }
} catch { $problems.Add('Redis is not reachable via docker exec (container down or Docker stopped)') }

# ---- Core authentication failures (stale / wrong agent API keys) ----
# Why: after the 2026-10-15 key rotation 8 agents kept the OLD master key and the healer used the literal
# "dev-master-key"; core answered 401/403 and nothing alerted (the XP sink and healer events failed silently).
# Looks only at the period since the previous run, and only at CONTAINER callers (the docker gateway .1 is the
# host/browser, whose expired tokens are normal noise). Message omits counts so the alert de-duplicates.
try {
    $st0 = if (Test-Path $State) { Get-Content $State -Raw | ConvertFrom-Json } else { $null }
    $mins = if ($AuthWindowHours -gt 0) { [int]($AuthWindowHours * 60) }
            elseif ($st0 -and $st0.lastCheck) { [int][math]::Min(1560, [math]::Max(120, ((Get-Date) - [datetime]$st0.lastCheck).TotalMinutes + 2)) }
            else { 1560 }
    if ($CoreLogPath) { $logLines = Get-Content $CoreLogPath }
    else {
        $logLines = & { $ErrorActionPreference = 'Continue'; docker logs hypercode-core --since "${mins}m" 2>&1 }
        if ($LASTEXITCODE -ne 0) { throw 'docker logs failed' }
    }
    $ipmap = @{}
    if (-not $CoreLogPath) {
        foreach ($cid in (docker ps -q)) {
            $l = docker inspect $cid --format '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'
            $p = ($l.Trim() -split '\s+'); for ($i = 1; $i -lt $p.Count; $i++) { if ($p[$i]) { $ipmap[$p[$i]] = $p[0].TrimStart('/') } }
        }
    }
    $seen = New-Object 'System.Collections.Generic.SortedSet[string]'
    foreach ($ln in $logLines) {
        if ($ln -notmatch '^INFO:\s+(\d+\.\d+\.\d+\.\d+):\d+ - "(\w+) (\S+) HTTP/[\d.]+" (401|403)\b') { continue }
        $ip = $Matches[1]; $meth = $Matches[2]; $code = $Matches[4]
        $path = ($Matches[3] -split '\?')[0] -replace '/[0-9a-f]{8}-[0-9a-f-]{27}', '/<id>' -replace '/\d+', '/<n>'
        if ($path -match '^/(api/v1/)?(health|metrics)') { continue }
        if ($ip -match '\.1$') { continue }                       # docker gateway = host / browser
        $who = if ($ipmap.ContainsKey($ip)) { $ipmap[$ip] } else { "unknown($ip)" }
        [void]$seen.Add("$who -> $meth $path ($code)")
    }
    if ($seen.Count -gt 0) {
        $shown = @($seen | Select-Object -First 5); $more = $seen.Count - $shown.Count
        $problems.Add("Core is rejecting calls from services (401/403) - stale or wrong API key? " + ($shown -join '; ') + $(if ($more -gt 0) { "; +$more more" } else { '' }))
    }
} catch { $problems.Add("Could not read hypercode-core's access log to check for auth failures ($($_.Exception.Message))") }

# ---- BROski$ XP: awards banked in Redis but missing from the Postgres wallet ----
# Why: the economy consumer banks every award in Redis first, then posts it to core. When that post failed (stale key
# after a rotation, core down) the award stayed in Redis only and nothing noticed: 63 awards / 660 XP were lost across
# Aug-Oct 2026. End-to-end truth, independent of WHY the post failed. See scripts\lib\xp_reconcile.ps1.
try {
    if ($XpMarkersFile) {
        $xpMarkers = @(Get-Content $XpMarkersFile | Where-Object { $_ -match '^\S+\s+-?\d+\s*$' } | ForEach-Object { $p = $_ -split '\s+'; [pscustomobject]@{ SourceId = $p[0]; Ttl = [int64]$p[1] } })
    } else { $xpMarkers = @(Get-XpMarkers) }
    $xpLedger = if ($XpLedgerFile) { @(Get-Content $XpLedgerFile | Where-Object { $_.Trim() } | ForEach-Object { $_.Trim() }) } else { @(Get-XpLedgerIds) }
    $xpLost = @(Find-MissingXpAwards -Markers $xpMarkers -LedgerIds $xpLedger -GraceSeconds ($XpGraceMinutes * 60))
    if ($xpLost.Count -gt 0) { $problems.Add((Format-XpMissingMessage $xpLost)) }
} catch { $problems.Add("Could not reconcile BROski`$ XP awards (Redis vs Postgres): $($_.Exception.Message)") }

# ---- decide ----
if ($DryRun) {
    if ($problems.Count) { Write-Host "DRY RUN - $($problems.Count) problem(s):" -ForegroundColor Yellow; $problems | ForEach-Object { Write-Host "  - $_" } }
    else { Write-Host 'DRY RUN - all checks healthy' -ForegroundColor Green }
    exit 0
}
$prev = if (Test-Path $State) { Get-Content $State -Raw | ConvertFrom-Json } else { $null }
$sig  = ($problems | Sort-Object) -join '|'
if ($problems.Count -eq 0) {
    Log 'all backup checks healthy'
    if ($prev -and $prev.problems) { [void](Send-Alert 'HyperCode checks healthy again' @('All watchdog checks pass now.') 'ok') }
    @{ problems = ''; lastSent = $null; lastCheck = (Get-Date).ToString('s') } | ConvertTo-Json | Set-Content $State -Encoding utf8
    exit 0
}
Log "$($problems.Count) problem(s): $($problems -join ' ; ')"
$due = (-not $prev) -or ($prev.problems -ne $sig) -or (-not $prev.lastSent) -or (((Get-Date) - [datetime]$prev.lastSent).TotalHours -ge $Repeat)
if ($due) {
    $ok = Send-Alert 'Problem on the HyperCode PC' ($problems.ToArray() + 'Details: scripts\backup_watchdog.ps1 -DryRun   (backup jobs: scripts\backup-*-task.ps1 -Action status)') 'bad'
    @{ problems = $sig; lastSent = $(if ($ok) { (Get-Date).ToString('s') } else { $null }); lastCheck = (Get-Date).ToString('s') } | ConvertTo-Json | Set-Content $State -Encoding utf8
} else {
    Log 'same problem already alerted recently - not repeating'
    @{ problems = $prev.problems; lastSent = $prev.lastSent; lastCheck = (Get-Date).ToString('s') } | ConvertTo-Json | Set-Content $State -Encoding utf8
}
exit 1
