# ============================================
# 🚀 HYPER STARTUP v1.0 — by BROski♾️
# ============================================

$dockerDir = "H:\HyperStation zone\HyperCode\HyperCode-V2.4"
$frontendDir = "H:\Hyper-Vibe-Coding-Course\frontend"
$stripePort = "localhost:8000/api/webhooks/stripe"

Clear-Host
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "  🚀 HYPER STARTUP — BROski Stack v1.0" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Magenta

# ── STEP 1: Docker Stack ──────────────────
Write-Host "`n[1/4] 🐳 Firing up Docker containers..." -ForegroundColor Yellow
Set-Location $dockerDir
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
Write-Host "      Docker stack launched!" -ForegroundColor Green

# ── STEP 2: Wait for hypercode-core ──────
Write-Host "`n[2/4] ⏳ Waiting for hypercode-core to be healthy..." -ForegroundColor Yellow
$maxWait = 60
$waited = 0
do {
    Start-Sleep -Seconds 3
    $waited += 3
    $status = docker inspect --format="{{.State.Health.Status}}" hypercode-core 2>$null
    Write-Host "      → Status: $status ($waited s)" -ForegroundColor Gray
} while ($status -ne "healthy" -and $waited -lt $maxWait)

if ($status -eq "healthy") {
    Write-Host "      ✅ hypercode-core is healthy!" -ForegroundColor Green
} else {
    Write-Host "      ⚠️  Timed out — check docker logs hypercode-core" -ForegroundColor Red
}

# ── STEP 3: Stripe Webhook Listener ──────
Write-Host "`n[3/4] 💳 Starting Stripe webhook listener..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "stripe listen --forward-to $stripePort"
Write-Host "      Stripe listener open in new window!" -ForegroundColor Green

# ── STEP 4: Frontend Dev Server ──────────
Write-Host "`n[4/4] ⚡ Launching frontend dev server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$frontendDir'; npm run dev"
Write-Host "      Frontend launching in new window!" -ForegroundColor Green

# ── DONE ─────────────────────────────────
Write-Host "`n============================================" -ForegroundColor Magenta
Write-Host "  ✅ ALL SYSTEMS GO, BROski♾️!" -ForegroundColor Cyan
Write-Host "  🌐 Frontend  → http://localhost:5173" -ForegroundColor White
Write-Host "  🔧 API Core  → http://localhost:8000" -ForegroundColor White
Write-Host "  📊 Grafana   → http://localhost:8088" -ForegroundColor White
Write-Host "  🤖 Dashboard → http://localhost:8088" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "`nPress any key to close this window..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")