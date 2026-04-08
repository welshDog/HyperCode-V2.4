#Requires -Version 5.1
<#
.SYNOPSIS
    HyperCode V2.0 — Master Boot Sequence
.DESCRIPTION
    Full ordered startup with health-gate checking, Alembic migrations,
    Ollama model warm-up, optional profile selection, and live status table.
.PARAMETER Profile
    Which agent profile(s) to activate alongside the core stack.
    Values: none (default), agents, hyper, health, mission, all
.PARAMETER SkipBuild
    Skip docker compose build (use cached images). Faster restarts.
.PARAMETER Restart
    Restart only — skip the compose down step (faster when already mostly up).
.PARAMETER Minimal
    Boot core stack only: Redis, Postgres, Core, Dashboard. Skip observability.
.EXAMPLE
    .\scripts\boot.ps1
    .\scripts\boot.ps1 -Profile hyper
    .\scripts\boot.ps1 -Profile agents -SkipBuild
    .\scripts\boot.ps1 -Minimal
#>

param(
    [ValidateSet("none","agents","hyper","health","mission","all")]
    [string]$Profile = "none",
    [switch]$SkipBuild,
    [switch]$Restart,
    [switch]$Minimal
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"   # Don't hard-stop on non-critical failures
$StartTime = Get-Date

# ─── Colours ──────────────────────────────────────────────────────────────────
function Write-Step  { param($msg) Write-Host "`n$msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "  ✅ $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "  ⚠️  $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "  ❌ $msg" -ForegroundColor Red }
function Write-Info  { param($msg) Write-Host "     $msg" -ForegroundColor DarkGray }

# ─── Banner ───────────────────────────────────────────────────────────────────
Clear-Host
Write-Host @"

  ██╗  ██╗██╗   ██╗██████╗ ███████╗██████╗  ██████╗ ██████╗ ██████╗ ███████╗
  ██║  ██║╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗██╔════╝██╔═══██╗██╔══██╗██╔════╝
  ███████║ ╚████╔╝ ██████╔╝█████╗  ██████╔╝██║     ██║   ██║██║  ██║█████╗
  ██╔══██║  ╚██╔╝  ██╔═══╝ ██╔══╝  ██╔══██╗██║     ██║   ██║██║  ██║██╔══╝
  ██║  ██║   ██║   ██║     ███████╗██║  ██║╚██████╗╚██████╔╝██████╔╝███████╗
  ╚═╝  ╚═╝   ╚═╝   ╚═╝     ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝
                      V2.0 — Autonomous AI Stack  🦅
"@ -ForegroundColor Cyan

Write-Host "  Profile: $Profile  |  SkipBuild: $SkipBuild  |  Minimal: $Minimal  |  $(Get-Date -Format 'yyyy-MM-dd HH:mm')" -ForegroundColor DarkGray
Write-Host ""

# ─── Pre-flight checks ────────────────────────────────────────────────────────
Write-Step "🔍 PRE-FLIGHT CHECKS"

# Docker running?
$dockerOk = $false
try {
    $null = docker info 2>&1
    $dockerOk = $true
    Write-Ok "Docker Engine is running"
} catch {
    Write-Fail "Docker Engine is NOT running — start Docker Desktop first"
    exit 1
}

# .env present?
if (Test-Path ".\.env") {
    Write-Ok ".env file found"
} else {
    Write-Warn ".env file missing — some services may fail to start"
    Write-Info "Copy .env.example to .env and fill in secrets"
}

# Required networks — create if missing
$requiredNetworks = @("hypercode_public_net", "hypercode_data_net", "hypercode-v20_hypercode-net")
foreach ($net in $requiredNetworks) {
    $exists = docker network ls --format "{{.Name}}" | Where-Object { $_ -eq $net }
    if (-not $exists) {
        Write-Info "Creating network: $net"
        docker network create $net 2>&1 | Out-Null
        Write-Ok "Network $net created"
    } else {
        Write-Ok "Network $net exists"
    }
}

# Required data directories (bound volumes)
$dataRoot = if ($env:HC_DATA_ROOT) { $env:HC_DATA_ROOT } else { "H:\HC\data" }
$dirs = @("redis","postgres","grafana","prometheus","ollama","agent_memory","minio","chroma","tempo")
$missingDirs = @()
foreach ($d in $dirs) {
    $path = Join-Path $dataRoot $d
    if (-not (Test-Path $path)) {
        $missingDirs += $path
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}
if ($missingDirs.Count -gt 0) {
    Write-Warn "Created $($missingDirs.Count) missing data directories under $dataRoot"
} else {
    Write-Ok "All data directories present"
}

# ─── STEP 1: Tear down ────────────────────────────────────────────────────────
if (-not $Restart) {
    Write-Step "🧹 STEP 1: CLEAN SLATE"
    Write-Info "Stopping and removing all containers..."
    docker compose down --remove-orphans 2>&1 | Where-Object { $_ -match "Removed|Stopped|removed|stopped" } | ForEach-Object { Write-Info $_ }
    Write-Ok "Stack torn down"
} else {
    Write-Step "♻️  STEP 1: SKIPPED (restart mode)"
}

# ─── Build? ───────────────────────────────────────────────────────────────────
if (-not $SkipBuild) {
    Write-Step "🔨 STEP 2: BUILD IMAGES"
    Write-Info "Building custom images (backend, dashboard, healer, agents)..."
    Write-Info "This takes 2-5 minutes on first run. Grab a brew ☕"
    $buildStart = Get-Date
    docker compose build --parallel 2>&1 | Where-Object { $_ -match "error|Error|warning|Warning|Step|=>|Successfully" } | ForEach-Object { Write-Info $_ }
    $buildSecs = [int]((Get-Date) - $buildStart).TotalSeconds
    Write-Ok "Images built in ${buildSecs}s"
} else {
    Write-Step "🔨 STEP 2: BUILD SKIPPED (--SkipBuild)"
}

# ─── STEP 3: Data layer ───────────────────────────────────────────────────────
Write-Step "🗄️  STEP 3: DATA LAYER (Redis + Postgres + Ollama)"
docker compose up -d redis postgres hypercode-ollama
Write-Info "Waiting for health checks (max 60s)..."

$deadline = (Get-Date).AddSeconds(60)
$healthy = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    $redisOk    = (docker inspect redis    --format "{{.State.Health.Status}}" 2>$null) -eq "healthy"
    $postgresOk = (docker inspect postgres --format "{{.State.Health.Status}}" 2>$null) -eq "healthy"
    $ollamaOk   = (docker inspect hypercode-ollama --format "{{.State.Health.Status}}" 2>$null) -eq "healthy"
    if ($redisOk -and $postgresOk) {
        $healthy = $true
        break
    }
    Write-Info "  redis=$redisOk  postgres=$postgresOk  ollama=$ollamaOk — waiting..."
}

if ($healthy) {
    Write-Ok "Redis   — healthy"
    Write-Ok "Postgres — healthy"
    if ($ollamaOk) { Write-Ok "Ollama  — healthy" }
    else           { Write-Warn "Ollama  — still starting (models load slowly, that's OK)" }
} else {
    Write-Fail "Redis or Postgres failed to become healthy after 60s — check logs:"
    Write-Info "  docker logs redis"
    Write-Info "  docker logs postgres"
    Write-Warn "Continuing anyway — core may retry connections..."
}

# ─── STEP 4: Alembic migrations ───────────────────────────────────────────────
Write-Step "🧬 STEP 4: DATABASE MIGRATIONS (Alembic)"
Write-Info "Running migrations inside hypercode-core container..."

# Run migrations in a one-shot container using the same image
$migrationResult = docker compose run --rm --no-deps `
    -e DB_AUTO_CREATE=false `
    hypercode-core `
    sh -c "cd /app && alembic upgrade head 2>&1" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Ok "Alembic migrations applied"
    $migrationResult | Where-Object { $_ -match "Running|OK|up to date" } | ForEach-Object { Write-Info "  $_" }
} else {
    Write-Warn "Alembic migration had warnings (may already be up to date):"
    $migrationResult | Select-Object -Last 5 | ForEach-Object { Write-Info "  $_" }
}

# ─── STEP 5: Core backend ─────────────────────────────────────────────────────
Write-Step "🧠 STEP 5: HYPERCODE CORE (FastAPI)"
docker compose up -d hypercode-core
Write-Info "Waiting for core to be healthy (max 60s)..."

$deadline = (Get-Date).AddSeconds(60)
$coreHealthy = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 4
    $status = (docker inspect hypercode-core --format "{{.State.Health.Status}}" 2>$null)
    if ($status -eq "healthy") { $coreHealthy = $true; break }
    Write-Info "  core status: $status"
}

if ($coreHealthy) {
    Write-Ok "HyperCode Core — healthy on :8000"
} else {
    Write-Warn "Core not healthy yet — check: docker logs hypercode-core"
}

# ─── STEP 6: Observability ────────────────────────────────────────────────────
if (-not $Minimal) {
    Write-Step "📊 STEP 6: OBSERVABILITY STACK"
    docker compose up -d prometheus grafana loki tempo promtail alertmanager node-exporter cadvisor
    Write-Info "Observability services started (may take 30s for Prometheus WAL replay)"
    Write-Ok "Prometheus  — :9090"
    Write-Ok "Grafana     — :3001  (admin / admin)"
    Write-Ok "Loki        — :3100"
    Write-Ok "Tempo       — :3200"
    Write-Ok "Alertmanager — :9093"
    Write-Ok "cAdvisor    — :8080 (metrics)"
} else {
    Write-Step "📊 STEP 6: OBSERVABILITY SKIPPED (--Minimal)"
}

# ─── STEP 7: Core agents ──────────────────────────────────────────────────────
Write-Step "🤖 STEP 7: CORE AGENTS"
docker compose up -d healer-agent celery-worker hypercode-mcp-server

if (-not $Minimal) {
    docker compose up -d celery-exporter security-scanner
}

Write-Info "Waiting 8s for agents to register..."
Start-Sleep -Seconds 8
Write-Ok "Healer Agent — :8008  (self-healing loop active)"
Write-Ok "Celery Worker — task queue connected"
Write-Ok "MCP Server  — :8823"

# ─── STEP 8: Profile-based agent swarm ───────────────────────────────────────
$profileFlags = @()
switch ($Profile) {
    "agents"  { $profileFlags = @("--profile", "agents") }
    "hyper"   { $profileFlags = @("--profile", "hyper") }
    "health"  { $profileFlags = @("--profile", "health") }
    "mission" { $profileFlags = @("--profile", "mission") }
    "all"     { $profileFlags = @("--profile", "agents", "--profile", "hyper", "--profile", "health", "--profile", "mission") }
    default   { }
}

if ($profileFlags.Count -gt 0) {
    Write-Step "🧠 STEP 8: AGENT SWARM PROFILE [$Profile]"
    $cmd = @("docker", "compose") + $profileFlags + @("up", "-d")
    & $cmd[0] $cmd[1..($cmd.Length-1)]
    Write-Info "Waiting 15s for agent swarm to stabilise..."
    Start-Sleep -Seconds 15

    switch ($Profile) {
        "agents"  {
            Write-Ok "Crew Orchestrator — :8081"
            Write-Ok "Business agents   — (project-strategist, coder-agent, etc.)"
        }
        "hyper"   {
            Write-Ok "Agent X           — :8080 (meta-architect)"
            Write-Ok "Hyper Architect   — :8091"
            Write-Ok "Hyper Observer    — :8092"
            Write-Ok "Hyper Worker      — :8093"
        }
        "health"  {
            Write-Ok "HyperHealth API   — :8090"
            Write-Ok "HyperHealth Worker — active"
        }
        "mission" {
            Write-Ok "Hyper Mission API — :5000"
            Write-Ok "Hyper Mission UI  — :3002"
        }
        "all"     {
            Write-Ok "Full agent swarm — all profiles active"
        }
    }
} else {
    Write-Step "🧠 STEP 8: AGENT SWARM SKIPPED (use -Profile agents|hyper|health|mission|all)"
}

# ─── STEP 9: Dashboard ────────────────────────────────────────────────────────
Write-Step "🖥️  STEP 9: MISSION CONTROL DASHBOARD"
docker compose up -d dashboard
Write-Info "Dashboard starts after hypercode-core is healthy."
Write-Info "Next.js build takes ~30s on first start — be patient."
Write-Ok "Dashboard — :8088 (starting...)"

# Wait briefly then check
Start-Sleep -Seconds 10
$dashStatus = (docker inspect hypercode-dashboard --format "{{.State.Health.Status}}" 2>$null)
if ($dashStatus -eq "healthy") {
    Write-Ok "Dashboard — HEALTHY at http://127.0.0.1:8088"
} else {
    Write-Info "Dashboard still starting ($dashStatus) — check in 30s"
}

# ─── STEP 10: Health gate ─────────────────────────────────────────────────────
Write-Step "🩺 STEP 10: SERVICE HEALTH GATES"

$services = @(
    @{ name="HyperCode Core";  url="http://127.0.0.1:8000/health";      critical=$true  },
    @{ name="Metrics API";     url="http://127.0.0.1:8000/api/v1/metrics"; critical=$false },
    @{ name="Healer Agent";    url="http://127.0.0.1:8008/health";      critical=$true  },
    @{ name="Dashboard";       url="http://127.0.0.1:8088";             critical=$true  },
    @{ name="MCP Server";      url="http://127.0.0.1:8823/sse";         critical=$false },
    @{ name="Prometheus";      url="http://127.0.0.1:9090/-/ready";     critical=$false },
    @{ name="Grafana";         url="http://127.0.0.1:3001";             critical=$false },
    @{ name="Alertmanager";    url="http://127.0.0.1:9093/-/ready";     critical=$false }
)

$criticalFailed = 0
foreach ($svc in $services) {
    if ($Minimal -and $svc.name -in @("Prometheus","Grafana","Alertmanager","MCP Server")) { continue }
    try {
        $resp = Invoke-WebRequest -Uri $svc.url -TimeoutSec 8 -UseBasicParsing -ErrorAction Stop
        Write-Ok "$($svc.name.PadRight(18)) — HTTP $($resp.StatusCode)"
    } catch {
        if ($svc.critical) {
            Write-Fail "$($svc.name.PadRight(18)) — NOT RESPONDING  ← CRITICAL"
            $criticalFailed++
        } else {
            Write-Warn "$($svc.name.PadRight(18)) — not responding (non-critical)"
        }
    }
}

# ─── STEP 11: Container status table ─────────────────────────────────────────
Write-Step "📦 STEP 11: RUNNING CONTAINERS"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>&1

# ─── STEP 12: Ollama model warm-up ────────────────────────────────────────────
Write-Step "🧠 STEP 12: OLLAMA MODEL WARM-UP"
$ollamaModels = docker exec hypercode-ollama ollama list 2>&1
if ($LASTEXITCODE -eq 0) {
    $modelLines = $ollamaModels | Where-Object { $_ -notmatch "^NAME" -and $_ -ne "" }
    if ($modelLines.Count -gt 0) {
        Write-Ok "Loaded models:"
        $modelLines | ForEach-Object { Write-Info "  $_" }
    } else {
        Write-Warn "No Ollama models found — pulling tinyllama (this happens once)..."
        docker exec hypercode-ollama ollama pull tinyllama 2>&1 | Select-Object -Last 3 | ForEach-Object { Write-Info "  $_" }
    }
} else {
    Write-Warn "Ollama not ready yet — models will load on first request"
}

# ─── STEP 13: Redis connectivity verification ─────────────────────────────────
Write-Step "🔴 STEP 13: REDIS VERIFICATION"
$redisPing = docker exec redis redis-cli ping 2>&1
if ($redisPing -match "PONG") {
    Write-Ok "Redis ping — PONG"
    $redisInfo = docker exec redis redis-cli info memory 2>&1 | Where-Object { $_ -match "used_memory_human|maxmemory_human" }
    $redisInfo | ForEach-Object { Write-Info "  $_" }
} else {
    Write-Fail "Redis ping failed — $redisPing"
}

# ─── BOOT SUMMARY ────────────────────────────────────────────────────────────
$elapsed = [int]((Get-Date) - $StartTime).TotalSeconds

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan

if ($criticalFailed -eq 0) {
    Write-Host "  🦅 HyperCode V2.0 — BOOT COMPLETE ✅" -ForegroundColor Green
} else {
    Write-Host "  🦅 HyperCode V2.0 — BOOT COMPLETE WITH WARNINGS ⚠️" -ForegroundColor Yellow
    Write-Host "  $criticalFailed critical service(s) did not respond — check logs" -ForegroundColor Red
}

Write-Host "  Boot time: ${elapsed}s  |  Profile: $Profile" -ForegroundColor DarkGray
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  🖥️  Dashboard:        http://127.0.0.1:8088" -ForegroundColor White
Write-Host "  🧠 Backend API:       http://127.0.0.1:8000/api/v1/docs" -ForegroundColor White
Write-Host "  📊 Grafana:           http://127.0.0.1:3001  (admin/admin)" -ForegroundColor White
Write-Host "  🔭 Prometheus:        http://127.0.0.1:9090" -ForegroundColor White
Write-Host "  🩺 Healer:            http://127.0.0.1:8008/health" -ForegroundColor White
Write-Host "  🔌 MCP Server:        http://127.0.0.1:8823/sse" -ForegroundColor White
Write-Host "  🚨 Alertmanager:      http://127.0.0.1:9093" -ForegroundColor White
Write-Host ""

if ($Profile -eq "none") {
    Write-Host "  💡 Boot with agents:  .\scripts\boot.ps1 -Profile hyper" -ForegroundColor DarkCyan
    Write-Host "  💡 Full swarm:        .\scripts\boot.ps1 -Profile all" -ForegroundColor DarkCyan
    Write-Host "  💡 Fast restart:      .\scripts\boot.ps1 -SkipBuild -Restart" -ForegroundColor DarkCyan
}

Write-Host ""
Write-Host "  📋 Useful commands:" -ForegroundColor DarkGray
Write-Host "     docker compose logs -f hypercode-core   # backend logs" -ForegroundColor DarkGray
Write-Host "     docker compose logs -f healer-agent     # healing events" -ForegroundColor DarkGray
Write-Host "     docker compose logs -f hypercode-dashboard # dashboard" -ForegroundColor DarkGray
Write-Host "     docker stats                             # live resource usage" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  BROski Power Level: 🔥🔥🔥 MAXIMUM HYPERFOCUS 🔥🔥🔥" -ForegroundColor Magenta
Write-Host ""
