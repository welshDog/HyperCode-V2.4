<#
.SYNOPSIS
  Helper for a CONTROLLED WSL / Docker Desktop restart. See docs\WSL_RESTART_RUNBOOK.md (read it first).

.DESCRIPTION
  preflight    READ-ONLY. Checks the machine is ready, snapshots every container (name/image/status/health/restart
               policy) to backups\wsl-restart\<time>\inventory.csv, and tells you READY / NOT READY.
  plan         READ-ONLY. Prints the exact, ordered commands for the pre-shutdown steps and the stop sequence.
               It never runs them: the stop side is deliberately manual.
  start-stack  Staged bring-up AFTER Docker is back: starts containers tier by tier with `docker start` (NEVER
               `compose up`, so each container keeps its exact environment), waits for each tier to be healthy and
               checks the RAM guard between tiers. Idempotent: containers already running are left alone.
               -DryRun prints what it would do.
  verify       READ-ONLY. WSL channel, swap, RAM guard, containers vs the preflight snapshot, smoke test, watchdog.

  Why staged: every container has a restart policy, so Docker would start all ~37 at once on an 8 GB box, the
  storm that caused the old exit-137 deaths. Tiers are ordered by dependency (data -> core -> guards ->
  orchestrator -> agents -> watchers LAST so the healer/registry do not "heal" things that are simply not up yet).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wsl-restart.ps1 -Action preflight
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wsl-restart.ps1 -Action plan
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wsl-restart.ps1 -Action start-stack
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wsl-restart.ps1 -Action verify
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet('preflight', 'plan', 'start-stack', 'verify')][string]$Action,
    [switch]$DryRun,
    [switch]$SkipRamGuard,           # EMERGENCY ONLY: do not consult ram_guard between tiers (e.g. while WSL itself is broken)
    [int]$TierTimeoutSec = 300,
    [int]$CoreTimeoutSec = 720,     # hypercode-core spends ~90 s importing, then runs migrations
    [string]$FromTier = ''           # e.g. -FromTier 3 to resume after a stopped bring-up
)
$ErrorActionPreference = 'Continue'
$Repo = Split-Path -Parent $PSScriptRoot
Set-Location $Repo

# Ordered by dependency. Names must match `docker ps` exactly. The Docker Desktop extension container
# (kubetoolsca_...) is managed by Docker Desktop itself and is intentionally not listed.
$Tiers = @(
    @{ Id = '0'; Name = 'docker proxies + data';  Timeout = 180; Items = @('docker-socket-proxy', 'docker-socket-proxy-build', 'docker-socket-proxy-healer', 'postgres', 'redis', 'minio', 'chroma', 'memstream', 'hypercode-ollama') },
    @{ Id = '1'; Name = 'core API';               Timeout = $CoreTimeoutSec; Items = @('hypercode-core') },
    @{ Id = '2'; Name = 'core workers';           Timeout = 240; Items = @('celery-worker') },
    @{ Id = '3'; Name = 'guards + gateway';       Timeout = 180; Items = @('fcc-proxy', 'safety-shepherd', 'governor') },
    @{ Id = '4'; Name = 'orchestrator (SPOF)';    Timeout = 240; Items = @('crew-orchestrator') },
    @{ Id = '5'; Name = 'platform agents';        Timeout = 300; Items = @('coder-agent', 'qa-engineer', 'coder-studio', 'evolve-relay', 'skillweaver', 'hyper-brain', 'hyperhealth-worker', 'hypercode-mcp-server', 'hypercode-dashboard', 'broski-bot', 'broski-economy-consumer', 'github-sync', 'github-sync-brain', 'obsidian-watcher') },
    @{ Id = '6'; Name = 'small agents';           Timeout = 180; Items = @('agent-focus-tracker', 'agent-hyper-brain-core', 'agent-mcp-bridge', 'agent-morning-briefing') },
    @{ Id = '7'; Name = 'watchers (LAST)';        Timeout = 180; Items = @('throttle-agent', 'agent-registry', 'healer-agent') }
)
$AllTierNames = @($Tiers | ForEach-Object { $_.Items } | ForEach-Object { $_ })
$ExtensionContainer = 'kubetoolsca_krs-docker-extension-desktop-extension-service'

$script:bad = 0; $script:warn = 0
function Ok($m)   { Write-Host "  OK    $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  WARN  $m" -ForegroundColor Yellow; $script:warn++ }
function Bad($m)  { Write-Host "  BAD   $m" -ForegroundColor Red; $script:bad++ }
function Head($m) { Write-Host ""; Write-Host "== $m" -ForegroundColor Cyan }

function Get-CState($name) {
    $raw = docker inspect $name --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $raw) { return @{ Exists = $false; Running = $false; Health = ''; Ready = $false } }
    $p = $raw -split '\|'
    $running = ($p[0] -eq 'running')
    return @{ Exists = $true; Running = $running; Health = $p[1]; Ready = ($running -and ($p[1] -eq 'healthy' -or $p[1] -eq 'none')) }
}
function Test-DockerUp { docker info --format '{{.ServerVersion}}' 2>$null | Out-Null; return ($LASTEXITCODE -eq 0) }
function Test-RamOk {
    # ram_guard.py calls `wsl -e`; with the WSL channel wedged that call can hang, so bound it with a timeout and
    # treat "no answer" as NOT OK (the safe side) rather than blocking the whole bring-up.
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) { return $true }
    $job = Start-Job -ScriptBlock { param($r) Set-Location $r; python scripts\ram_guard.py --for start 2>&1 | Out-Null; $LASTEXITCODE } -ArgumentList $Repo
    if (-not (Wait-Job $job -Timeout 45)) { Stop-Job $job; Remove-Job $job -Force; return $false }
    $code = Receive-Job $job; Remove-Job $job -Force
    return ([int]($code | Select-Object -Last 1) -eq 0)
}
# Run a command in a child job with a hard timeout (a wedged `wsl` call can otherwise block for minutes).
function Invoke-Bounded([scriptblock]$Block, [object[]]$ArgList = @(), [int]$TimeoutSec = 25) {
    $job = Start-Job -ScriptBlock $Block -ArgumentList $ArgList
    if (-not (Wait-Job $job -Timeout $TimeoutSec)) { Stop-Job $job; Remove-Job $job -Force; return @{ Code = -2; Out = "timed out after ${TimeoutSec}s" } }
    $r = Receive-Job $job; Remove-Job $job -Force
    return $r
}
function Get-NewestAge($items) {
    $n = $items | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $n) { return $null }
    return [math]::Round(((Get-Date) - $n.LastWriteTime).TotalHours, 1)
}

# ------------------------------------------------------------------ preflight
if ($Action -eq 'preflight') {
    Head 'Docker'
    if (Test-DockerUp) { Ok 'Docker engine answers' } else { Bad 'Docker engine is not answering - preflight needs it up'; exit 1 }

    Head 'Container inventory vs tiers'
    $running = @(docker ps --format '{{.Names}}')
    $unknown = @($running | Where-Object { $AllTierNames -notcontains $_ -and $_ -ne $ExtensionContainer })
    $absent = @($AllTierNames | Where-Object { $running -notcontains $_ })
    Ok ("{0} running container(s); {1} in tiers" -f $running.Count, @($running | Where-Object { $AllTierNames -contains $_ }).Count)
    if ($unknown.Count) { Bad ("running but NOT in any tier (add to `$Tiers or stop them deliberately): " + ($unknown -join ', ')) }
    if ($absent.Count)  { Warn ("in a tier but not running now (start-stack will start them): " + ($absent -join ', ')) }

    $snapDir = Join-Path $Repo ('backups\wsl-restart\' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
    New-Item -ItemType Directory -Force -Path $snapDir | Out-Null
    # NOTE: no embedded double quotes in the --format template: Windows PowerShell 5.1 mangles them and docker then
    # returns nothing (the label is read from {{json .Config.Labels}} instead).
    $rows = foreach ($n in @(docker ps -a --format '{{.Names}}')) {
        $i = docker inspect $n --format '{{.Config.Image}}|{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}|{{.HostConfig.RestartPolicy.Name}}|{{json .Config.Labels}}' 2>$null
        $p = @($i -split '\|', 5)
        $proj = ''
        if ($p.Count -ge 5) { try { $proj = [string](($p[4] | ConvertFrom-Json).'com.docker.compose.project') } catch { } }
        [pscustomobject]@{ Name = $n; Image = $p[0]; Status = $p[1]; Health = $p[2]; RestartPolicy = $(if ($p.Count -ge 4 -and $p[3]) { $p[3] } else { 'no' }); ComposeProject = $proj }
    }
    $rows | Export-Csv -NoTypeInformation -Encoding utf8 (Join-Path $snapDir 'inventory.csv')
    $empty = @($rows | Where-Object { -not $_.Image -or -not $_.Status })
    if ($empty.Count) { Bad ("snapshot is INCOMPLETE for {0} container(s) (docker inspect returned nothing): {1}" -f $empty.Count, (($empty | Select-Object -First 5 | ForEach-Object { $_.Name }) -join ', ')) }
    else { Ok ("snapshot of {0} containers saved and complete: {1}" -f @($rows).Count, $snapDir.Replace($Repo + '\', '')) }

    Head 'What Docker would auto-start on its own (restart policies)'
    $always = @($rows | Where-Object { $_.RestartPolicy -eq 'always' } | ForEach-Object { $_.Name })
    $exitedAuto = @($rows | Where-Object { $_.Status -ne 'running' -and $_.RestartPolicy -in 'always', 'unless-stopped' } | ForEach-Object { $_.Name })
    if ($always.Count)     { Warn ("restart=always (cannot be stopped for good; neutralise first): " + ($always -join ', ')) }
    if ($exitedAuto.Count) { Warn ("STOPPED but have a restart policy, so Docker may start them again (OOM-killed ones count): " + ($exitedAuto -join ', ')) }
    Ok "the 'plan' action prints the exact docker update commands that neutralise these"

    Head 'Backups (a restart can corrupt data if it goes wrong - be able to restore)'
    $pg = Get-ChildItem (Join-Path $Repo 'backups\postgres') -Filter 'backup_*.dump' -ErrorAction SilentlyContinue
    $age = Get-NewestAge $pg
    if ($null -eq $age) { Bad 'no Postgres dump found' } elseif ($age -gt 3) { Bad ("newest Postgres dump is $age h old - run the backup tasks first (limit 3 h)") } else { Ok "newest Postgres dump $age h old" }
    $st = Get-ChildItem (Join-Path $Repo 'backups\stores') -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path (Join-Path $_.FullName 'SHA256SUMS') }
    $age = Get-NewestAge $st
    if ($null -eq $age) { Bad 'no completed Redis/MinIO/Chroma backup found' } elseif ($age -gt 3) { Bad ("newest stores backup is $age h old - run the backup tasks first (limit 3 h)") } else { Ok "newest stores backup $age h old" }
    $drive = Get-ChildItem 'G:\My Drive\HyperCode-Backups' -Filter 'hypercode_*.7z' -ErrorAction SilentlyContinue
    $age = Get-NewestAge $drive
    if ($null -eq $age) { Warn 'no encrypted archive visible in Google Drive' } elseif ($age -gt 6) { Warn "newest encrypted Drive archive is $age h old" } else { Ok "newest encrypted Drive archive $age h old" }

    Head 'Disk space and WSL settings'
    $hFree = [math]::Round((Get-PSDrive H).Free / 1GB); $cFree = [math]::Round((Get-PSDrive C).Free / 1GB)
    if ($hFree -lt 40) { Bad "H: only $hFree GB free" } else { Ok "H: $hFree GB free (a full copy of the 213 GB Docker data disk needs ~230 GB: optional)" }
    if ($cFree -lt 15) { Bad "C: only $cFree GB free" } else { Ok "C: $cFree GB free" }
    $cfg = Join-Path $env:USERPROFILE '.wslconfig'
    if (Test-Path $cfg) {
        $swap = (Get-Content $cfg | Where-Object { $_ -match '^\s*swapFile\s*=' } | Select-Object -First 1)
        if ($swap) { $p = ($swap -split '=', 2)[1].Trim() -replace '\\\\', '\'; $par = Split-Path $p -Parent; if (Test-Path $par) { Ok "swap parent folder exists ($par)" } else { Bad "swap parent folder MISSING ($par): WSL would silently run with ZERO swap" } }
        else { Warn '.wslconfig has no swapFile line' }
    } else { Warn 'no .wslconfig found' }
    $dd = Get-ChildItem 'H:\HyperStation zone\HyperCode\DockerData' -Recurse -Filter docker_data.vhdx -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($dd) { Ok ("Docker data disk: {0} ({1:N0} GB). NEVER use Docker Desktop 'Clean / Purge data' or 'Reset to factory defaults'." -f $dd.FullName, ($dd.Length / 1GB)) } else { Warn 'Docker data disk not found at the expected path' }

    Head 'Scheduled jobs that will misfire during the window'
    Get-ScheduledTask -TaskPath '\HyperCode\' -ErrorAction SilentlyContinue | ForEach-Object {
        $t = @($_.Triggers | ForEach-Object { if ($_.StartBoundary) { ([datetime]$_.StartBoundary).ToString('HH:mm') } else { 'at logon' } }) -join ', '
        Write-Host ("        {0,-30} {1,-8} {2}" -f $_.TaskName, $_.State, $t)
    }
    Warn 'avoid 12:00-12:30 (backups) and 13:00 / 18:00 (watchdog), or Disable-ScheduledTask the watchdog for the window (the runbook has the commands)'

    Head 'Shell environment (compose reads these silently)'
    foreach ($n in 'API_KEY', 'HYPERCODE_API_KEY', 'CREW_LLM_BASE_URL', 'COMPOSE_PROJECT_NAME') {
        if ([Environment]::GetEnvironmentVariable($n)) { Warn "$n is set in this shell" } else { Ok "$n unset (fine: the bring-up uses docker start, never compose up)" }
    }

    Write-Host ""
    if ($script:bad -eq 0) { Write-Host "PREFLIGHT: READY ($($script:warn) warning(s))" -ForegroundColor Green; exit 0 }
    Write-Host "PREFLIGHT: NOT READY ($($script:bad) blocker(s), $($script:warn) warning(s))" -ForegroundColor Red; exit 1
}

# ------------------------------------------------------------------ plan
if ($Action -eq 'plan') {
    $stopped = @(docker ps -a --filter status=exited --filter status=created --format '{{.Names}}')
    Write-Host "`nPRINT-ONLY. Nothing below is executed by this script.`n" -ForegroundColor Yellow
    Write-Host '# A. Neutralise auto-start (so a manual stop sticks and nothing starts itself):' -ForegroundColor Cyan
    Write-Host 'docker update --restart=unless-stopped healer-agent      # it is "always": make a manual stop stick (restore to always at the end)'
    if ($stopped.Count) { Write-Host ('docker update --restart=no ' + ($stopped -join ' ') + '   # exited containers Docker might otherwise start again') }
    Write-Host "`n# B. Flush the databases to disk:" -ForegroundColor Cyan
    Write-Host 'docker exec redis redis-cli bgsave        # then re-run `docker exec redis redis-cli info persistence` until rdb_bgsave_in_progress:0'
    Write-Host 'docker exec postgres sh -c ''psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c CHECKPOINT'''
    Write-Host "`n# C. Stop in REVERSE dependency order (watchers first so they do not fight the shutdown):" -ForegroundColor Cyan
    $rev = @($Tiers); [array]::Reverse($rev)
    foreach ($t in $rev) {
        $names = @($t.Items); [array]::Reverse($names)   # reverse inside the tier too: healer + registry before throttle
        $to = if ($t.Id -eq '0') { 60 } else { 30 }
        Write-Host ("docker stop -t {0} {1}      # tier {2}: {3}" -f $to, ($names -join ' '), $t.Id, $t.Name)
    }
    Write-Host "`n# D. Stop Docker Desktop, then the WSL VM:" -ForegroundColor Cyan
    Write-Host 'docker desktop stop'
    Write-Host 'wsl --shutdown'
    Write-Host 'wsl -l -v          # every distro must say Stopped'
    Write-Host "`n# E. Start again:" -ForegroundColor Cyan
    Write-Host 'docker desktop start'
    Write-Host 'wsl -e true; wsl -e free -m      # channel answers and Swap total is NOT 0'
    Write-Host 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wsl-restart.ps1 -Action start-stack'
    Write-Host 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wsl-restart.ps1 -Action verify'
    exit 0
}

# ------------------------------------------------------------------ start-stack
if ($Action -eq 'start-stack') {
    if (-not (Test-DockerUp)) { Write-Host 'Docker is not answering yet. Wait for Docker Desktop, then re-run.' -ForegroundColor Red; exit 1 }
    foreach ($t in $Tiers) {
        if ($FromTier -and ([int]$t.Id -lt [int]$FromTier)) { continue }
        Head ("Tier {0}: {1}" -f $t.Id, $t.Name)
        if ($SkipRamGuard -and $t.Id -eq '0') { Write-Host '  NOTE: -SkipRamGuard is set: memory is NOT being checked between tiers' -ForegroundColor Yellow }
        if (-not $DryRun -and -not $SkipRamGuard -and -not (Test-RamOk)) {
            Write-Host '  RAM guard says NOT OK; waiting up to 90 s for it to recover...' -ForegroundColor Yellow
            $sw = [Diagnostics.Stopwatch]::StartNew(); while (-not (Test-RamOk) -and $sw.Elapsed.TotalSeconds -lt 90) { Start-Sleep -Seconds 5 }
            if (-not (Test-RamOk)) { Write-Host "  STOP: RAM guard still not OK. Free memory, then re-run with -FromTier $($t.Id)" -ForegroundColor Red; exit 2 }
        }
        $toStart = @()
        foreach ($n in $t.Items) {
            $s = Get-CState $n
            if (-not $s.Exists) { Write-Host "  skip  $n (container does not exist)" -ForegroundColor Yellow }
            elseif ($s.Running) { Write-Host "  up    $n (already running, health=$($s.Health))" }
            else { $toStart += $n }
        }
        if ($toStart.Count) {
            if ($DryRun) { Write-Host ("  DRY RUN: would run: docker start " + ($toStart -join ' ')) -ForegroundColor Yellow }
            else { docker start @toStart 2>&1 | ForEach-Object { Write-Host "  start $_" } }
        }
        if ($DryRun) { continue }
        $sw = [Diagnostics.Stopwatch]::StartNew(); $pending = @()
        do {
            $pending = @($t.Items | Where-Object { $s = Get-CState $_; $s.Exists -and -not $s.Ready })
            if ($pending.Count -eq 0) { break }
            Start-Sleep -Seconds 5
        } while ($sw.Elapsed.TotalSeconds -lt $t.Timeout)
        if ($pending.Count) {
            Write-Host ("  STOP: not ready after {0}s: {1}" -f $t.Timeout, ($pending -join ', ')) -ForegroundColor Red
            Write-Host "  Inspect with: docker logs <name>; fix; then re-run with -FromTier $($t.Id)" -ForegroundColor Red
            exit 3
        }
        Write-Host ("  tier {0} ready in ~{1}s" -f $t.Id, [int]$sw.Elapsed.TotalSeconds) -ForegroundColor Green
    }
    Write-Host ""
    if ($DryRun) { Write-Host 'DRY RUN complete: nothing was started.' -ForegroundColor Yellow; exit 0 }
    Write-Host 'START-STACK: all tiers ready.' -ForegroundColor Green
    Write-Host 'Now: docker update --restart=always healer-agent   (restore its policy), then run -Action verify.'
    exit 0
}

# ------------------------------------------------------------------ verify
if ($Action -eq 'verify') {
    Head 'WSL channel (the original fault: `wsl -e` timed out with 0x8007274c)'
    $t = Invoke-Bounded { $o = & wsl -e true 2>&1; @{ Code = $LASTEXITCODE; Out = ($o -join ' ') } } @() 25
    if ($t.Code -eq 0) { Ok 'wsl -e true answers' } else { Bad "wsl -e true FAILED (exit $($t.Code), $($t.Out)): the WSL channel is still broken" }
    $f = Invoke-Bounded { $o = & wsl -e free -m 2>&1; @{ Code = $LASTEXITCODE; Out = ($o -join "`n") } } @() 25
    if ($f.Out -match '(?m)^Swap:\s+(\d+)') { if ([int]$Matches[1] -gt 0) { Ok "swap is live ($($Matches[1]) MB)" } else { Bad 'Swap total is 0: check the swapFile parent folder in .wslconfig' } } else { Warn 'could not read free -m' }

    Head 'Docker + RAM guard'
    if (Test-DockerUp) { Ok 'Docker engine answers' } else { Bad 'Docker engine is not answering' }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $g = Invoke-Bounded { param($r) Set-Location $r; $o = python scripts\ram_guard.py --for build 2>&1; @{ Code = $LASTEXITCODE; Out = ($o -join "`n") } } @($Repo) 80
        $v = [regex]::Match([string]$g.Out, '(?m)^\s*VERDICT:.*$').Value.Trim()
        # Match the verdict WORD, not any "GREEN" in the sentence ("... a build needs GREEN" must stay a warning).
        if ($v -match '^VERDICT:\s*GREEN\b') { Ok $v } elseif ($v) { Warn $v } else { Warn "ram_guard gave no verdict ($($g.Out))" }
    }

    Head 'Containers vs the preflight snapshot'
    $snap = Get-ChildItem (Join-Path $Repo 'backups\wsl-restart') -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
    if (-not $snap) { Warn 'no preflight snapshot found to compare against' }
    else {
        $before = Import-Csv (Join-Path $snap.FullName 'inventory.csv')
        $wasUp = @($before | Where-Object { $_.Status -eq 'running' })
        $problems = @()
        foreach ($b in $wasUp) { $s = Get-CState $b.Name; if (-not $s.Ready) { $problems += ("{0} (now: {1})" -f $b.Name, $(if ($s.Exists) { "running=$($s.Running) health=$($s.Health)" } else { 'missing' })) } }
        if ($problems.Count) { Bad ("were running before, NOT ready now: " + ($problems -join '; ')) } else { Ok ("all {0} containers that were running before are ready (snapshot {1})" -f $wasUp.Count, $snap.Name) }
        $wasOff = @($before | Where-Object { $_.Status -ne 'running' } | ForEach-Object { $_.Name })
        $nowOn = @($wasOff | Where-Object { (Get-CState $_).Running })
        if ($nowOn.Count) { Warn ("were STOPPED before but are running now: " + ($nowOn -join ', ')) } else { Ok 'nothing that was stopped before has started by itself' }
        $h = $before | Where-Object { $_.Name -eq 'healer-agent' }
        $pol = docker inspect healer-agent --format '{{.HostConfig.RestartPolicy.Name}}' 2>$null
        if ($h -and $pol -ne $h.RestartPolicy) { Warn ("healer-agent restart policy is '$pol' but was '$($h.RestartPolicy)': docker update --restart=$($h.RestartPolicy) healer-agent") } else { Ok 'healer-agent restart policy restored' }
    }

    Head 'Stack health'
    $o = powershell -NoProfile -ExecutionPolicy Bypass -File scripts\stack-smoke.ps1 -Quiet 2>&1 | Select-Object -Last 1
    if ($o -match 'PASS') { Ok $o } else { Bad "stack smoke: $o" }
    $w = powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup_watchdog.ps1 -DryRun 2>&1 | Where-Object { $_.Trim() } | Select-Object -First 2
    if ($w -match 'healthy') { Ok ($w | Select-Object -First 1) } else { Warn ("watchdog: " + (($w -join ' ') -replace '\s+', ' ')) }

    Write-Host ""
    if ($script:bad -eq 0) { Write-Host "VERIFY: PASS ($($script:warn) warning(s))" -ForegroundColor Green; exit 0 }
    Write-Host "VERIFY: FAIL ($($script:bad) problem(s))" -ForegroundColor Red; exit 1
}
