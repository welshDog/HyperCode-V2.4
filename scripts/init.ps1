# scripts/init.ps1 — HyperCode V2.0 First-Run Setup (Windows / PowerShell)
# Usage: powershell -File scripts/init.ps1
# Idempotent: safe to re-run at any time.

$ErrorActionPreference = "Stop"
$results = @()

function Pass($msg)  { $script:results += "  [PASS] $msg"; Write-Host "  [PASS] $msg" -ForegroundColor Green }
function Fail($msg)  { $script:results += "  [FAIL] $msg"; Write-Host "  [FAIL] $msg" -ForegroundColor Red }
function Warn($msg)  { $script:results += "  [WARN] $msg"; Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Info($msg)  { Write-Host "  $msg" -ForegroundColor Cyan }

Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  HyperCode V2.0 — First-Run Init" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""

# ── 1. Docker availability ─────────────────────────────────────────────────
Write-Host "[ 1 ] Docker" -ForegroundColor Blue
try {
    $null = docker info 2>&1
    Pass "Docker is running"
} catch {
    Fail "Docker is not running — start Docker Desktop and retry"
    exit 1
}

# ── 2. Create required Docker networks ────────────────────────────────────
Write-Host "[ 2 ] Docker Networks" -ForegroundColor Blue

$networks = @(
    @{ Name = "hypercode_public_net";   Label = "backend-net (external)" },
    @{ Name = "hypercode_frontend_net"; Label = "frontend-net" }
)

foreach ($net in $networks) {
    $existing = docker network ls --format "{{.Name}}" | Where-Object { $_ -eq $net.Name }
    if ($existing) {
        Pass "$($net.Label) already exists ($($net.Name))"
    } else {
        Info "Creating $($net.Name)..."
        docker network create $net.Name | Out-Null
        Pass "$($net.Label) created ($($net.Name))"
    }
}

# ── 3. Validate .env ───────────────────────────────────────────────────────
Write-Host "[ 3 ] Environment File" -ForegroundColor Blue

$envFile = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path $envFile)) {
    $envExample = Join-Path $PSScriptRoot "..\.env.example"
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Warn ".env not found — copied from .env.example. Edit it before starting."
    } else {
        Fail ".env and .env.example both missing — cannot continue"
        exit 1
    }
} else {
    Pass ".env file exists"
}

# Parse .env into a hashtable
$envVars = @{}
Get-Content $envFile | Where-Object { $_ -match "^\s*[^#].*=" } | ForEach-Object {
    $parts = $_ -split "=", 2
    if ($parts.Length -eq 2) {
        $envVars[$parts[0].Trim()] = $parts[1].Trim().Trim('"').Trim("'")
    }
}

# Check HC_DATA_ROOT
if (-not $envVars["HC_DATA_ROOT"] -or $envVars["HC_DATA_ROOT"] -eq "" -or $envVars["HC_DATA_ROOT"] -like "*/absolute/path/*") {
    Fail "HC_DATA_ROOT is not set in .env — edit .env and set a real path (e.g. HC_DATA_ROOT=H:/HyperCode/data)"
} else {
    $dataRoot = $envVars["HC_DATA_ROOT"] -replace "\\", "/"
    Pass "HC_DATA_ROOT = $dataRoot"
}

# Check required secrets
$required = @("POSTGRES_PASSWORD", "API_KEY", "HYPERCODE_JWT_SECRET")
foreach ($key in $required) {
    if (-not $envVars[$key] -or $envVars[$key] -in @("", "changeme", "your_secure_api_key_here", "your_jwt_secret_here")) {
        Warn "$key is not set or still has placeholder value"
    } else {
        Pass "$key is set"
    }
}

# ── 4. Create data directories ─────────────────────────────────────────────
Write-Host "[ 4 ] Data Directories" -ForegroundColor Blue

if ($envVars["HC_DATA_ROOT"] -and $envVars["HC_DATA_ROOT"] -notlike "*/absolute/path/*") {
    $dataRoot = $envVars["HC_DATA_ROOT"] -replace "/", "\"
    $subdirs = @("redis", "postgres", "grafana", "prometheus", "ollama", "agent_memory", "minio", "chroma", "tempo")
    foreach ($sub in $subdirs) {
        $dir = Join-Path $dataRoot $sub
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Pass "Created: $dir"
        } else {
            Pass "Exists:  $dir"
        }
    }
} else {
    Warn "Skipping data directory creation — HC_DATA_ROOT not configured"
}

# ── 5. Summary ─────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  Init Summary" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
$failCount = ($results | Where-Object { $_ -like "*[FAIL]*" }).Count
$warnCount = ($results | Where-Object { $_ -like "*[WARN]*" }).Count

if ($failCount -gt 0) {
    Write-Host "  $failCount issue(s) must be fixed before starting." -ForegroundColor Red
    Write-Host "  Run 'make start' after resolving them." -ForegroundColor Red
} elseif ($warnCount -gt 0) {
    Write-Host "  Init complete with $warnCount warning(s)." -ForegroundColor Yellow
    Write-Host "  Run 'make start' to launch HyperCode V2.0." -ForegroundColor Cyan
} else {
    Write-Host "  All checks passed. Run 'make start' to launch!" -ForegroundColor Green
}
Write-Host ""
exit $failCount
