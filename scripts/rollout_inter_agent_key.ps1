# rollout_inter_agent_key.ps1 - move ALL seven holders of the shared inter-agent key onto secrets/inter_agent_key.txt in ONE pass.
#
# Holders: crew-orchestrator coder-agent qa-engineer safety-shepherd coder-studio evolve-relay governor healer-agent.
# Four of them (crew, coder-agent, shepherd, governor) read the key from the file (overlay *_API_KEY_FILE). The other three have
# no read_secret yet, so the key is passed as the env value the base compose already uses (${API_KEY}) for THIS compose run only:
# it is read from the file in memory, never printed, and cleared from the shell afterwards.
# Each service is recreated with the compose file set it was originally started with (taken from its container label),
# and its other env is preserved (CREW_LLM_BASE_URL is carried over). A before/after env diff (names only) is printed.
#
# DEFAULT IS A DRY RUN. Add -Apply to change anything.   Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\rollout_inter_agent_key.ps1            # dry run
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\rollout_inter_agent_key.ps1 -Apply
# Rollback: put the OLD key (a backup copy you take before -Apply, see -BackupTo) in the file and run -Apply again.
param(
    [switch]$Apply,
    [string]$KeyFile = 'secrets\inter_agent_key.txt',
    [string]$BackupTo = ''      # optional path: the CURRENT key (read from a running peer) is saved here before changing anything
)
$ErrorActionPreference = 'Continue'
Set-Location (Split-Path -Parent $PSScriptRoot)
$root = (Get-Location).Path

# healer-agent: its image predates the vendored read_secret, so it gets the key as an env value like qa-engineer/coder-studio/evolve-relay
$services = 'safety-shepherd', 'governor', 'coder-agent', 'qa-engineer', 'coder-studio', 'evolve-relay', 'crew-orchestrator', 'healer-agent'
# 'fleet' only when the service's own file set includes docker-compose.fleet.yml: the secrets overlay names `governor`, which has
# no image/build of its own, so enabling the profile without fleet.yml makes compose reject the whole project.
function ProfilesFor($f) {
    $p = @('--profile', 'agents', '--profile', 'hyper', '--profile', 'safety', '--profile', 'studio')
    if ($f -contains 'docker-compose.fleet.yml') { $p += @('--profile', 'fleet') }
    $p
}

function EnvMap($c) {
    $m = @{}
    $json = docker inspect $c --format '{{json .Config.Env}}'
    foreach ($e in ($json | ConvertFrom-Json)) { $i = $e.IndexOf('='); $m[$e.Substring(0, $i)] = $e.Substring($i + 1) }
    $m
}
function Health($c) { (docker inspect $c --format '{{.State.Status}} {{.State.Health.Status}}') }

# ---- preflight
if (-not (Test-Path $KeyFile)) { throw "missing $KeyFile - create it first (python: 'hc_' + secrets.token_hex(24))" }
$newKey = ([IO.File]::ReadAllText((Resolve-Path $KeyFile))).Trim()
if ($newKey.Length -lt 40) { throw "$KeyFile looks too short ($($newKey.Length) chars)" }
$ram = python scripts\ram_guard.py 2>&1 | Select-String '^VERDICT'
"RAM guard: $ram"
if ("$ram" -match 'VERDICT: RED') { throw 'RAM guard is RED - not recreating anything now' }

$plan = foreach ($s in $services) {
    # {{json}} not {{index ... "label"}}: embedded double quotes in a --format template return nothing in Windows PowerShell 5.1
    $labels = docker inspect $s --format '{{json .Config.Labels}}' | ConvertFrom-Json
    $files = ($labels.'com.docker.compose.project.config_files') -split ','
    if (-not $files -or -not $files[0]) { throw "no compose config_files label on $s" }
    $f = @(); foreach ($x in $files) { $f += '-f'; $f += ($x.Trim() -replace [regex]::Escape($root + '\'), '') }
    [pscustomobject]@{ Service = $s; F = $f; P = (ProfilesFor $f); Before = (EnvMap $s) }
}
foreach ($p in $plan) {
    docker compose @($p.F) @($p.P) config -q 2>&1 | Out-Null
    $ok = ($LASTEXITCODE -eq 0)
    "{0,-18} files: {1}  config: {2}" -f $p.Service, (($p.F | Where-Object { $_ -ne '-f' }) -join ' + '), $(if ($ok) { 'OK' } else { 'FAILED' })
    if (-not $ok) { throw "compose config fails for $($p.Service) - fix before applying" }
}
'--- BEFORE'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\probe_inter_agent_key.ps1

if (-not $Apply) { 'DRY RUN - nothing changed. Re-run with -Apply to roll out.'; exit 0 }

if ($BackupTo) {
    $old = (EnvMap 'safety-shepherd')['HYPERCODE_API_KEY']
    [IO.File]::WriteAllText($BackupTo, $old, (New-Object Text.UTF8Encoding $false)); $old = $null
    "old key backed up to $BackupTo"
}

# ---- apply: one pass, shepherd first (the receiver), then the rest
foreach ($p in $plan) {
    $s = $p.Service
    [Environment]::SetEnvironmentVariable('API_KEY', $newKey, 'Process')
    $crew = $p.Before['CREW_LLM_BASE_URL']
    if ($crew) { [Environment]::SetEnvironmentVariable('CREW_LLM_BASE_URL', $crew, 'Process') }
    $o = docker compose @($p.F) @($p.P) up -d --no-deps --no-build --force-recreate $s 2>&1
    $rc = $LASTEXITCODE
    [Environment]::SetEnvironmentVariable('API_KEY', $null, 'Process')
    [Environment]::SetEnvironmentVariable('CREW_LLM_BASE_URL', $null, 'Process')
    "{0,-18} recreate rc={1}" -f $s, $rc
    if ($rc -ne 0) { $o | Select-Object -Last 3; throw "recreate of $s failed - STOP, check state, the others are untouched" }
}
$newKey = $null

# ---- wait for health (the registry may start a second copy ~13 s after a recreate)
$deadline = (Get-Date).AddMinutes(6)
do {
    Start-Sleep 10
    $bad = @($services | Where-Object { (Health $_) -notmatch '^running healthy' })
} while ($bad.Count -gt 0 -and (Get-Date) -lt $deadline)
foreach ($s in $services) { "{0,-18} {1}" -f $s, (Health $s) }

'--- env diff (names only)'
foreach ($p in $plan) {
    $a = EnvMap $p.Service
    $d = @(($p.Before.Keys + $a.Keys) | Sort-Object -Unique | Where-Object { $p.Before[$_] -ne $a[$_] })
    "{0,-18} {1}" -f $p.Service, ($d -join ',')
}
'--- AFTER'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\probe_inter_agent_key.ps1
exit $LASTEXITCODE
