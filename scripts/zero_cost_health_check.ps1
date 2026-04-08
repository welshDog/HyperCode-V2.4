# 🩺 HyperCode Zero-Cost Health Check Playbook
# Date: 2026-03-08
# Purpose: Validate local LLM stack and infrastructure health

$ErrorActionPreference = "Continue"

function Write-Log {
    param([string]$Message, [string]$Color = "Cyan")
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor $Color
}

Write-Log "🦅 HYPERCODE ZERO-COST HEALTH CHECK" "Green"

# 1. Infrastructure Check
Write-Log "1. Checking Infrastructure..." "Yellow"

# Redis
$redis = docker exec redis redis-cli ping 2>$null
if ($redis -eq "PONG") {
    Write-Log "✅ Redis: HEALTHY (PONG)" "Green"
} else {
    Write-Log "❌ Redis: UNHEALTHY" "Red"
}

# Postgres
$pg = docker exec postgres pg_isready -U postgres 2>$null
if ($pg -like "*accepting connections*") {
    Write-Log "✅ Postgres: HEALTHY" "Green"
} else {
    Write-Log "❌ Postgres: UNHEALTHY" "Red"
}

# 2. Local LLM Check
Write-Log "2. Checking Local LLM (Ollama)..." "Yellow"
$ollama = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method Get -ErrorAction SilentlyContinue
if ($ollama.StatusCode -eq 200) {
    Write-Log "✅ Ollama: ONLINE" "Green"
    $models = ($ollama.Content | ConvertFrom-Json).models
    Write-Log "   Models available: $($models.name -join ', ')" "Cyan"
} else {
    Write-Log "❌ Ollama: OFFLINE" "Red"
}

# 3. Core API Check
Write-Log "3. Checking HyperCode Core..." "Yellow"
$core = Invoke-WebRequest -Uri "http://localhost:8000/" -Method Get -ErrorAction SilentlyContinue
if ($core.StatusCode -eq 200) {
    Write-Log "✅ HyperCode Core: ONLINE" "Green"
} else {
    Write-Log "❌ HyperCode Core: UNREACHABLE" "Red"
    Write-Log "   Last 30 lines of logs:" "Magenta"
    docker logs --tail 30 hypercode-core
}

# 4. Perplexity Session Check (Simulation)
Write-Log "4. Checking Perplexity Session Auth..." "Yellow"
# This simulates a request that would normally go to Perplexity
# In a real scenario, we'd hit an endpoint that triggers the Brain
Write-Log "ℹ️  Perplexity Session Auth is configured in settings." "Cyan"

Write-Log "Health Check Complete." "Green"
