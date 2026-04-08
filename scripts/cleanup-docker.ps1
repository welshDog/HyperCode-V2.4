#!/usr/bin/env pwsh
# Docker Cleanup Script for HyperCode V2.0
# Removes exited containers, unused images, and frees up disk space

Write-Host "🧹 HyperCode Docker Cleanup Script" -ForegroundColor Cyan
Write-Host "==================================`n" -ForegroundColor Cyan

# Check if Docker is running
try {
    docker ps > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Docker is not installed or not accessible." -ForegroundColor Red
    exit 1
}

# Show current disk usage
Write-Host "📊 Current Docker Disk Usage:" -ForegroundColor Yellow
docker system df
Write-Host ""

# Remove specific exited containers
Write-Host "🗑️  Removing known exited containers..." -ForegroundColor Yellow
$exitedContainers = @(
    "confident_cannon",
    "coder-agent",
    "hyperflow-editor",
    "mcp-server",
    "hyper-mission-system-alertmanager-1"
)

foreach ($container in $exitedContainers) {
    $exists = docker ps -a --filter "name=^/${container}$" --format "{{.Names}}"
    if ($exists) {
        Write-Host "  Removing: $container" -ForegroundColor Gray
        docker rm $container 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ Removed: $container" -ForegroundColor Green
        }
    }
}

Write-Host ""

# Prune all stopped containers
Write-Host "🗑️  Pruning all stopped containers..." -ForegroundColor Yellow
docker container prune -f
Write-Host ""

# Prune unused images
Write-Host "🗑️  Pruning unused images..." -ForegroundColor Yellow
$response = Read-Host "Remove unused images? This will free up significant space. (y/N)"
if ($response -eq "y" -or $response -eq "Y") {
    docker image prune -a -f
    Write-Host "✅ Unused images removed" -ForegroundColor Green
} else {
    Write-Host "⏭️  Skipped image pruning" -ForegroundColor Gray
}
Write-Host ""

# Prune volumes (careful!)
Write-Host "🗑️  Pruning unused volumes..." -ForegroundColor Yellow
$response = Read-Host "Remove unused volumes? ⚠️  This may delete data! (y/N)"
if ($response -eq "y" -or $response -eq "Y") {
    docker volume prune -f
    Write-Host "✅ Unused volumes removed" -ForegroundColor Green
} else {
    Write-Host "⏭️  Skipped volume pruning" -ForegroundColor Gray
}
Write-Host ""

# Prune networks
Write-Host "🗑️  Pruning unused networks..." -ForegroundColor Yellow
docker network prune -f
Write-Host ""

# Prune build cache
Write-Host "🗑️  Pruning build cache..." -ForegroundColor Yellow
$response = Read-Host "Remove build cache? This will slow down next builds. (y/N)"
if ($response -eq "y" -or $response -eq "Y") {
    docker builder prune -a -f
    Write-Host "✅ Build cache removed" -ForegroundColor Green
} else {
    Write-Host "⏭️  Skipped build cache pruning" -ForegroundColor Gray
}
Write-Host ""

# Show new disk usage
Write-Host "📊 New Docker Disk Usage:" -ForegroundColor Green
docker system df
Write-Host ""

# Summary
Write-Host "✅ Cleanup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Tips:" -ForegroundColor Cyan
Write-Host "  - Run 'docker system prune -a' for aggressive cleanup" -ForegroundColor Gray
Write-Host "  - Use 'docker system df -v' for detailed disk usage" -ForegroundColor Gray
Write-Host "  - Enable BuildKit for better caching: Set DOCKER_BUILDKIT=1" -ForegroundColor Gray
