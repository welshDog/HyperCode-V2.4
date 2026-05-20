#!/usr/bin/env pwsh
# ════════════════════════════════════════════════════════════════════════════════
# launch-all-agents.ps1 — 25-AGENT FULL SQUAD LAUNCHER
# Usage: .\scripts\launch-all-agents.ps1
# Updated: May 21, 2026
# ════════════════════════════════════════════════════════════════════════════════

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Colors
$colors = @{
    success = "Green"
    error = "Red"
    warning = "Yellow"
    info = "Cyan"
    phase = "Magenta"
}

function Write-Status {
    param([string]$msg, [string]$type = "info")
    $color = $colors[$type] ?? "White"
    Write-Host "[$([datetime]::Now.ToString('HH:mm:ss'))] $msg" -ForegroundColor $color
}

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1: PREFLIGHT CHECKS
# ══════════════════════════════════════════════════════════════════════════════

Write-Status "🚀 PHASE 1: PREFLIGHT CHECKS" -type phase
Write-Status ""

# Check Docker
try {
    $docker_version = docker --version
    Write-Status "✅ Docker: $docker_version" -type success
} catch {
    Write-Status "❌ Docker not found. Install Docker Desktop." -type error
    exit 1
}

# Check Docker daemon
try {
    docker ps > $null
    Write-Status "✅ Docker daemon running" -type success
} catch {
    Write-Status "❌ Docker daemon not running. Start Docker Desktop." -type error
    exit 1
}

# Check .env file
if (-not (Test-Path ".env")) {
    Write-Status "⚠️  .env file missing. Creating template..." -type warning
    Copy-Item ".env.example" ".env"
    Write-Status "📝 Created .env — fill in secrets before proceeding" -type info
    exit 0
}

Write-Status "✅ .env file exists" -type success

# Check disk space
$disk = Get-Volume -DriveLetter H
$free_gb = [math]::Round($disk.SizeRemaining / 1GB, 1)
if ($free_gb -lt 15) {
    Write-Status "❌ Insufficient disk space: ${free_gb}GB free (need 15GB+)" -type error
    exit 1
}
Write-Status "✅ Disk space: ${free_gb}GB free" -type success

# Check memory (WSL2 default is 8GB, we need ~30GB allocated across 25 agents)
Write-Status "⚠️  Ensure WSL2 has ≥32GB allocated. Check %USERPROFILE%\.wslconfig" -type warning

Write-Status ""
Write-Status "✅ Preflight checks passed" -type success
Write-Status ""

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2: BUILD AGENT IMAGES
# ══════════════════════════════════════════════════════════════════════════════

Write-Status "🏗️  PHASE 2: BUILD AGENT IMAGES (this may take 10-15 mins)" -type phase

$agents = @(
    # Tier 1: Core
    "crew-orchestrator",
    "agent-x",
    "brain-agent",
    "coder-agent",
    "tips-tricks-writer",
    # Tier 2: Specialists
    "frontend-specialist",
    "backend-specialist",
    "database-architect",
    "qa-engineer",
    "devops-engineer",
    "security-engineer",
    "system-architect",
    "project-strategist",
    # Tier 3: Infrastructure
    "hyper-architect",
    "hyper-observer",
    "hyper-worker",
    "goal-keeper",
    "throttle-agent",
    "super-hyper-broski-agent",
    "test-agent",
    "hypercode-mcp-server",
    # Tier 4: Utility
    "session-snapshot",
    "hyper-split-agent",
    "coderabbit-webhook",
    "business-agent"
)

$failed_builds = @()

foreach ($agent in $agents) {
    Write-Status ""
    Write-Status "Building: $agent..." -type info
    
    try {
        # Use docker compose build if dockerfile in compose, else docker build
        $build_cmd = "docker compose -f docker-compose.yml -f docker-compose.agents-full.yml build $agent"
        Invoke-Expression $build_cmd -ErrorAction Stop
        Write-Status "✅ Built: $agent" -type success
    } catch {
        Write-Status "❌ Build failed: $agent" -type error
        $failed_builds += $agent
    }
}

if ($failed_builds.Count -gt 0) {
    Write-Status ""
    Write-Status "⚠️  Failed builds: $($failed_builds -join ', ')" -type warning
    Write-Status "Review Dockerfiles and retry: docker compose build <agent>" -type info
}

Write-Status ""
Write-Status "✅ Build phase complete" -type success
Write-Status ""

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3: LAUNCH AGENTS
# ══════════════════════════════════════════════════════════════════════════════

Write-Status "🚀 PHASE 3: LAUNCHING 25-AGENT SQUAD" -type phase
Write-Status ""

# Start full stack
Write-Status "Starting all services with: docker compose -f docker-compose.yml -f docker-compose.agents-full.yml up -d"
docker compose -f docker-compose.yml -f docker-compose.agents-full.yml up -d

if ($LASTEXITCODE -ne 0) {
    Write-Status "❌ Launch failed" -type error
    exit 1
}

Write-Status "✅ All agents launched" -type success
Write-Status ""

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 4: HEALTH CHECKS
# ══════════════════════════════════════════════════════════════════════════════

Write-Status "🏥 PHASE 4: HEALTH CHECKS (waiting 30s for startup)" -type phase
Start-Sleep -Seconds 30

Write-Status ""

$health_checks = @(
    @{ name = "crew-orchestrator"; port = 8081; tier = "CORE" },
    @{ name = "agent-x"; port = 8083; tier = "CORE" },
    @{ name = "brain-agent"; port = 8082; tier = "CORE" },
    @{ name = "coder-agent"; port = 8002; tier = "CORE" },
    @{ name = "tips-tricks-writer"; port = 8011; tier = "CORE" },
    @{ name = "frontend-specialist"; port = 8012; tier = "SPECIALIST" },
    @{ name = "backend-specialist"; port = 8003; tier = "SPECIALIST" },
    @{ name = "database-architect"; port = 8004; tier = "SPECIALIST" },
    @{ name = "qa-engineer"; port = 8005; tier = "SPECIALIST" },
    @{ name = "devops-engineer"; port = 8006; tier = "SPECIALIST" },
    @{ name = "security-engineer"; port = 8007; tier = "SPECIALIST" },
    @{ name = "system-architect"; port = 8009; tier = "SPECIALIST" },
    @{ name = "project-strategist"; port = 8001; tier = "SPECIALIST" },
    @{ name = "hyper-architect"; port = 8091; tier = "INFRA" },
    @{ name = "hyper-observer"; port = 8092; tier = "INFRA" },
    @{ name = "hyper-worker"; port = 8093; tier = "INFRA" },
    @{ name = "goal-keeper"; port = 8050; tier = "INFRA" },
    @{ name = "throttle-agent"; port = 8014; tier = "INFRA" },
    @{ name = "super-hyper-broski-agent"; port = 8015; tier = "INFRA" },
    @{ name = "test-agent"; port = 8100; tier = "INFRA" },
    @{ name = "hypercode-mcp-server"; port = 8823; tier = "INFRA" },
    @{ name = "session-snapshot"; port = 8097; tier = "UTILITY" },
    @{ name = "hyper-split-agent"; port = 8096; tier = "UTILITY" },
    @{ name = "coderabbit-webhook"; port = 8024; tier = "UTILITY" },
    @{ name = "business-agent"; port = 8020; tier = "UTILITY" }
)

$healthy = 0
$unhealthy = 0

foreach ($check in $health_checks) {
    try {
        $response = curl.exe -s -f "http://localhost:$($check.port)/health" -m 2 2>$null
        if ($?) {
            Write-Status "✅ $($check.tier): $($check.name) — HEALTHY" -type success
            $healthy++
        } else {
            Write-Status "⚠️  $($check.tier): $($check.name) — Starting" -type warning
            $unhealthy++
        }
    } catch {
        Write-Status "⚠️  $($check.tier): $($check.name) — Pending" -type warning
        $unhealthy++
    }
}

Write-Status ""
Write-Status "📊 HEALTH SUMMARY" -type info
Write-Status "   Healthy: $healthy / $($health_checks.Count)" -type success
Write-Status "   Pending: $unhealthy / $($health_checks.Count)" -type warning
Write-Status ""

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 5: FINAL REPORT
# ══════════════════════════════════════════════════════════════════════════════

Write-Status "📋 FINAL REPORT" -type phase
Write-Status ""

Write-Status "Running containers:" -type info
docker ps --filter "label=com.hypercode.tier" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | Select-Object -First 10

Write-Status ""
Write-Status "Next steps:" -type info
Write-Status "  1. Monitor logs: docker compose logs -f crew-orchestrator" -type info
Write-Status "  2. Visit dashboard: http://localhost:3001 (Grafana)" -type info
Write-Status "  3. API docs: http://localhost:8000/docs" -type info
Write-Status ""

Write-Status "🚀 25-AGENT SQUAD ACTIVATION COMPLETE!" -type phase

Write-Status ""
Write-Status "BROski Power Level: 🔥 MAXIMUM OVERDRIVE ♾️" -type success
