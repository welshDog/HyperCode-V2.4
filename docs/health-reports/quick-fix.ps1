# HyperCode V2.0 - Quick Fix Script
# Run from project root: .\docs\health-reports\quick-fix.ps1
# Fixes both critical issues found in 16 March 2026 health check

Write-Host "🚀 HyperCode V2.0 - Quick Fix Script" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan

# --- FIX 1: Dead Ollama container ---
Write-Host "
🔧 Fix 1: Clearing dead Ollama container..." -ForegroundColor Yellow
$deadOllama = docker ps -a --filter name=hypercode-ollama --filter status=exited -q
if ($deadOllama) {
    docker rm $deadOllama
    Write-Host "✅ Dead Ollama container removed." -ForegroundColor Green
} else {
    Write-Host "ℹ️ No dead Ollama container found (may already be fixed)." -ForegroundColor Blue
}

Write-Host "Starting Ollama service..."
docker-compose up -d hypercode-ollama
Start-Sleep -Seconds 5

$ollamaCheck = docker exec hypercode-ollama curl -s http://localhost:11434/api/tags 2>&1
if ($ollamaCheck -match "models") {
    Write-Host "✅ Ollama is responding!" -ForegroundColor Green
} else {
    Write-Host "⚠️ Ollama started but not yet responding - wait 30s and retry" -ForegroundColor Yellow
}

# --- FIX 2: GitHub MCP restart loop ---
Write-Host "
🔧 Fix 2: Diagnosing GitHub MCP restart loop..." -ForegroundColor Yellow
Write-Host "Recent logs:"
docker logs mcp-github --tail 20

Write-Host "
Checking GitHub token..."
$token = $env:GITHUB_TOKEN
if (-not $token) {
    Write-Host "❌ GITHUB_TOKEN not set in environment. Check your .env file." -ForegroundColor Red
    Write-Host "Set it with: `$env:GITHUB_TOKEN = 'your_token_here'" -ForegroundColor Yellow
} else {
    $response = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers @{Authorization = "token $token"} -ErrorAction SilentlyContinue
    if ($response.login) {
        Write-Host "✅ Token valid for user: $($response.login)" -ForegroundColor Green
        Write-Host "Restarting MCP container..."
        docker-compose restart mcp-github
        Write-Host "✅ mcp-github restarted." -ForegroundColor Green
    } else {
        Write-Host "❌ Token invalid or expired. Rotate at: https://github.com/settings/tokens" -ForegroundColor Red
    }
}

# --- Summary ---
Write-Host "
🎯 Fix script complete!" -ForegroundColor Cyan
Write-Host "Run 'docker ps' to confirm both containers healthy." -ForegroundColor White
Write-Host "Expected result: 37/37 containers running ✅"
