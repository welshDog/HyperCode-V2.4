# ============================================================
# HyperCode V2.4 — Lean Mode START
# Safe ordered startup. Waits for each layer to be healthy.
# Run from: H:\HyperStation zone\HyperCode\HyperCode-V2.4
# ============================================================

Write-Host "`n🟢 LEAN MODE START — HyperCode V2.4" -ForegroundColor Green
Write-Host "============================================================"

$compose = "docker compose -f docker-compose.yml -f docker-compose.lean.yml -f docker-compose.secrets.yml"

# --- LAYER 1: DATA (redis + postgres must be healthy first) ---
Write-Host "`n📦 Layer 1: Starting data layer (redis, postgres)..." -ForegroundColor Cyan
Invoke-Expression "$compose up -d --no-build redis postgres"
Write-Host "⏳ Waiting for redis + postgres to be healthy..."
Start-Sleep -Seconds 10

# Health gate — keep waiting until both are healthy
$retries = 0
do {
    $unhealthy = docker ps --filter "name=redis" --filter "name=postgres" --format "{{.Names}}\t{{.Status}}" | Select-String "starting|unhealthy"
    if ($unhealthy) {
        Write-Host "   Still waiting... ($retries/10)" -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        $retries++
    }
} while ($unhealthy -and $retries -lt 10)
Write-Host "✅ Data layer ready!" -ForegroundColor Green

# --- LAYER 2: CORE (ollama first, then core + celery) ---
Write-Host "`n⚡ Layer 2: Starting core layer (ollama, hypercode-core, celery-worker)..." -ForegroundColor Cyan
Invoke-Expression "$compose up -d --no-build hypercode-ollama"
Write-Host "⏳ Waiting 15s for Ollama to warm up..."
Start-Sleep -Seconds 15

Invoke-Expression "$compose up -d --no-build hypercode-core celery-worker"
Write-Host "⏳ Waiting for hypercode-core to be healthy (up to 60s)..."
Start-Sleep -Seconds 30

$retries = 0
do {
    $coreStatus = docker inspect hypercode-core --format "{{.State.Health.Status}}" 2>$null
    if ($coreStatus -ne "healthy") {
        Write-Host "   hypercode-core status: $coreStatus ($retries/12)" -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        $retries++
    }
} while ($coreStatus -ne "healthy" -and $retries -lt 12)
Write-Host "✅ Core layer ready!" -ForegroundColor Green

# --- LAYER 3: AGENTS (healer + crew need core to be healthy) ---
Write-Host "`n🤖 Layer 3: Starting agents (healer, crew-orchestrator, socket proxies)..." -ForegroundColor Cyan
Invoke-Expression "$compose up -d --no-build docker-socket-proxy docker-socket-proxy-healer healer-agent crew-orchestrator"
Start-Sleep -Seconds 10
Write-Host "✅ Agent layer ready!" -ForegroundColor Green

# --- LAYER 4: OBSERVABILITY ---
Write-Host "`n📊 Layer 4: Starting observability (prometheus, grafana, loki, tempo, promtail)..." -ForegroundColor Cyan
Invoke-Expression "$compose up -d --no-build prometheus grafana loki tempo promtail"
Start-Sleep -Seconds 10
Write-Host "✅ Observability layer ready!" -ForegroundColor Green

# --- LAYER 5: DASHBOARD ---
Write-Host "`n🖥️  Layer 5: Starting dashboard..." -ForegroundColor Cyan
Invoke-Expression "$compose up -d --no-build dashboard"
Start-Sleep -Seconds 15
Write-Host "✅ Dashboard ready!" -ForegroundColor Green

# --- FINAL STATUS ---
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "🏆 LEAN MODE RUNNING! Here's your stack:" -ForegroundColor Green
Write-Host "============================================================"
docker ps --format "table {{.Names}}`t{{.Status}}" | Select-String -NotMatch "NAMES" | Sort-Object

Write-Host "`n🔗 Quick links:"
Write-Host "   API:       http://localhost:8000/health"
Write-Host "   Dashboard: http://localhost:8088"
Write-Host "   Grafana:   http://localhost:3001"
Write-Host "   Prometheus:http://localhost:9090"
Write-Host "`n💡 Add more layers:"
Write-Host "   Agents:    docker compose ... --profile agents up -d"
Write-Host "   Discord:   docker compose ... --profile discord up -d"
Write-Host "   Pets:      docker compose ... --profile pets up -d"
Write-Host ""
