<#
  stack-smoke.ps1 - fast "is the default stack really up?" gate. Exit 0 = pass, 1 = fail.

  Catches what `docker ps` + a 200 on /health silently miss:
    * required containers left in Created / Restarting / Exited (never started)
    * required containers running but not healthy
    * core answering 200 with status "degraded" (boot_error) - the 2026-10-16 JWT/MinIO case
    * dashboard / MCP / FCC endpoints and the Celery worker not answering

  Read-only: never starts, stops, or prints secrets.
  Usage: powershell -NoProfile -File scripts\stack-smoke.ps1 [-Quiet]
#>
param([switch]$Quiet)

$ErrorActionPreference = 'Continue'
$fail = 0
function Pass($m) { if (-not $Quiet) { Write-Host "  PASS  $m" -ForegroundColor Green } }
function Fail($m) { Write-Host "  FAIL  $m" -ForegroundColor Red; $script:fail++ }

# Required = the default product path (docs/HYPERCODE_PROJECT_UPGRADE_REPORT.md section 13).
$required = 'hypercode-core','postgres','redis','celery-worker','hypercode-dashboard',
            'hypercode-mcp-server','fcc-proxy','throttle-agent','healer-agent','safety-shepherd'

Write-Host "== containers"
foreach ($n in $required) {
  $raw = docker inspect $n --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' 2>$null
  if ($LASTEXITCODE -ne 0 -or -not $raw) { Fail "$n missing (container does not exist)"; continue }
  $state, $health = $raw -split '\|'
  if ($state -ne 'running')                     { Fail "$n is '$state' (not running)" }
  elseif ($health -notin 'healthy','none')      { Fail "$n running but health='$health'" }
  else                                          { Pass "$n $state/$health" }
}

Write-Host "== any Created/Restarting container in the project"
$stuck = docker ps -a --filter 'status=created' --filter 'status=restarting' --format '{{.Names}} ({{.Status}})'
if ($stuck) { $stuck | ForEach-Object { Fail "stuck: $_" } } else { Pass 'none stuck' }

Write-Host "== core readiness (status must be 'ok', not just HTTP 200)"
$h = curl.exe -s -m 8 http://127.0.0.1:8000/health
try {
  $j = $h | ConvertFrom-Json
  if ($j.status -eq 'ok') { Pass 'core status=ok' }
  else { Fail "core status='$($j.status)' boot_error='$($j.boot_error)'" }
} catch { Fail "core /health unreadable: '$h'" }

Write-Host "== endpoints"
foreach ($e in @{ dashboard='http://127.0.0.1:8088/'; mcp='http://127.0.0.1:8823/health'; fcc='http://127.0.0.1:8083/health' }.GetEnumerator()) {
  $code = curl.exe -s -o NUL -w '%{http_code}' -m 8 $e.Value
  if ($code -eq '200') { Pass "$($e.Key) 200" } else { Fail "$($e.Key) $($e.Value) -> $code" }
}

Write-Host "== celery heartbeat"
$ping = docker exec celery-worker celery -A app.core.celery_app inspect ping -t 5 2>&1 | Out-String
if ($ping -match 'pong') { Pass 'celery pong' } else { Fail 'celery did not answer ping' }

Write-Host ""
if ($fail -eq 0) { Write-Host "SMOKE: PASS" -ForegroundColor Green; exit 0 }
Write-Host "SMOKE: FAIL ($fail problem(s))" -ForegroundColor Red; exit 1
