# Resource Verification Script
Write-Host "📊 Verifying Resource Limits & Usage..." -ForegroundColor Cyan

# 1. Check if containers are running
$running = docker ps -q
if (-not $running) {
    Write-Host "⚠️ No containers running. Please start the stack first." -ForegroundColor Yellow
} else {
    Write-Host "running containers detected. Fetching stats..."
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
}

# 2. Verify Config Limits (Static Check)
Write-Host "`n🔍 Verifying docker-compose.yml limits..."
$content = Get-Content "docker-compose.yml" -Raw
if ($content -match "cpus: \"1\"" -and $content -match "memory: 1G") {
    Write-Host "✅ Resource limits detected in configuration." -ForegroundColor Green
} else {
    Write-Host "❌ Resource limits might be missing in docker-compose.yml." -ForegroundColor Red
}
