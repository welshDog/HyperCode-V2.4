# ============================================================
# HyperCode V2.4 — Lean Mode STOP
# Safe REVERSE-order shutdown. Agents first, data last.
# Data volumes are NEVER touched. Safe to re-run anytime.
# ============================================================

Write-Host "`n🔴 LEAN MODE STOP — HyperCode V2.4" -ForegroundColor Red
Write-Host "============================================================"
Write-Host "Stopping in safe order (agents first, data last)...`n"

# --- LAYER 5: DASHBOARD first ---
Write-Host "🖥️  Stopping dashboard..." -ForegroundColor Yellow
docker stop hypercode-dashboard 2>$null
Start-Sleep -Seconds 3

# --- LAYER 4: OBSERVABILITY ---
Write-Host "📊 Stopping observability..." -ForegroundColor Yellow
docker stop grafana prometheus promtail loki tempo alertmanager 2>$null
Start-Sleep -Seconds 5

# --- LAYER 3: AGENTS ---
Write-Host "🤖 Stopping agents (crew, healer, proxies)..." -ForegroundColor Yellow
docker stop crew-orchestrator healer-agent docker-socket-proxy docker-socket-proxy-healer docker-socket-proxy-build 2>$null
Start-Sleep -Seconds 5

# --- LAYER 2: CORE ---
Write-Host "⚡ Stopping core layer (celery, hypercode-core, ollama)..." -ForegroundColor Yellow
docker stop celery-worker hypercode-core hypercode-ollama 2>$null
Start-Sleep -Seconds 5

# --- LAYER 1: DATA (last — protect postgres + redis) ---
Write-Host "📦 Stopping data layer (redis, postgres)..." -ForegroundColor Yellow
docker stop redis postgres 2>$null
Start-Sleep -Seconds 3

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "✅ All lean-mode containers stopped. Data is SAFE." -ForegroundColor Green
Write-Host "   Volumes (postgres-data, redis-data) untouched."
Write-Host "   To restart: .\scripts\lean-start.ps1"
Write-Host ""

# Show anything still running (should be BROskiPets / Supabase if those are up)
$stillRunning = docker ps --format "table {{.Names}}`t{{.Status}}" 2>$null
if ($stillRunning -match "\w") {
    Write-Host "Still running (other projects):"
    Write-Host $stillRunning
}
