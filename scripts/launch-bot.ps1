<#
  launch-bot.ps1 — broski-bot one-shot launch
  preflight (env_check) -> migrate -> up -d
  Fail-fast on any non-zero exit. No secrets printed.

  Usage:
    .\scripts\launch-bot.ps1
    .\scripts\launch-bot.ps1 -SkipMigrate
    .\scripts\launch-bot.ps1 -NoPreflight     # not recommended
#>

[CmdletBinding()]
param(
  [switch]$SkipMigrate,
  [switch]$NoPreflight
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $RepoRoot

$ComposeArgs = @(
  '-f', 'docker-compose.yml',
  '-f', 'docker-compose.secrets.yml',
  '--profile', 'discord'
)

function Step($emoji, $msg) {
  Write-Host ""
  Write-Host "$emoji  $msg" -ForegroundColor Cyan
}

function Fail($msg, $code) {
  Write-Host ""
  Write-Host "💀  $msg (exit $code)" -ForegroundColor Red
  exit $code
}

# 1. Preflight
if (-not $NoPreflight) {
  Step '🛡️' 'Preflight — env_check (core + secrets + discord profile)'
  python scripts/env_check.py --core --secrets --profile discord
  if ($LASTEXITCODE -ne 0) { Fail 'env_check failed — fix .env / secrets before retry' $LASTEXITCODE }
} else {
  Write-Host "⚠️  Skipping preflight (NoPreflight set)" -ForegroundColor Yellow
}

# 2. Migrate
if (-not $SkipMigrate) {
  Step '🧱' 'Migrate — broski-bot Alembic upgrade head'
  docker compose @ComposeArgs run --rm broski-bot migrate
  if ($LASTEXITCODE -ne 0) { Fail 'migrate failed — check broski-bot logs' $LASTEXITCODE }
} else {
  Write-Host "⚠️  Skipping migrate (SkipMigrate set)" -ForegroundColor Yellow
}

# 3. Up
Step '🚀' 'Launch — docker compose up -d (discord profile)'
docker compose @ComposeArgs up -d
if ($LASTEXITCODE -ne 0) { Fail 'compose up failed — check docker logs' $LASTEXITCODE }

Step '✅' 'broski-bot is up. Tail logs:'
Write-Host "   docker compose $($ComposeArgs -join ' ') logs -f broski-bot" -ForegroundColor Gray
Write-Host ""
Write-Host "🐶♾️🔥  Nice one BROski♾️!" -ForegroundColor Green
