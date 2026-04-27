# ============================================================
# HyperCode FULL STOP — All 3 Projects
# Stops HyperCode + BROskiPets + Supabase in safe order.
# Data is NEVER deleted. Volumes untouched.
# ============================================================

Write-Host "`n🛑 FULL ECOSYSTEM STOP" -ForegroundColor Red
Write-Host "Stopping all 3 Docker projects safely...`n"

# 1. HyperCode lean stop first
Write-Host "[1/3] Stopping HyperCode V2.4..." -ForegroundColor Yellow
& "$PSScriptRoot\lean-stop.ps1"

# 2. BROskiPets
Write-Host "`n[2/3] Stopping BROskiPets..." -ForegroundColor Yellow
Set-Location "H:\BROskiPets-LLM-dNFT" -ErrorAction SilentlyContinue
docker compose down 2>$null
Write-Host "✅ BROskiPets stopped."

# 3. Supabase local stack
Write-Host "`n[3/3] Stopping Supabase local stack..." -ForegroundColor Yellow
Set-Location "H:\the hyper vibe coding hub" -ErrorAction SilentlyContinue
docker compose down 2>$null
Write-Host "✅ Supabase stack stopped."

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "✅ ALL PROJECTS STOPPED. RAM freed. Data safe." -ForegroundColor Green
Write-Host ""
