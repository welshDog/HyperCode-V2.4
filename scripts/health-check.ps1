#!/usr/bin/env pwsh
# Docker Health Check Script for HyperCode V2.0
# Checks status of all containers and reports issues

Write-Host "🏥 HyperCode Docker Health Check" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

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

# Get all containers
$containers = docker ps -a --format "json" | ConvertFrom-Json

Write-Host "📊 Container Status Summary:" -ForegroundColor Yellow
Write-Host ""

$running = 0
$healthy = 0
$unhealthy = 0
$exited = 0

foreach ($container in $containers) {
    $name = $container.Names
    $status = $container.Status
    $state = $container.State
    
    # Determine icon and color
    if ($state -eq "running") {
        $running++
        if ($status -match "healthy") {
            $healthy++
            $icon = "✅"
            $color = "Green"
        } elseif ($status -match "unhealthy") {
            $unhealthy++
            $icon = "❌"
            $color = "Red"
        } else {
            $icon = "🟢"
            $color = "Green"
        }
    } elseif ($state -eq "exited") {
        $exited++
        $icon = "🔴"
        $color = "Red"
    } else {
        $icon = "⚠️ "
        $color = "Yellow"
    }
    
    Write-Host "$icon $name" -ForegroundColor $color -NoNewline
    Write-Host " - $status" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  🟢 Running: $running" -ForegroundColor Green
Write-Host "  ✅ Healthy: $healthy" -ForegroundColor Green
if ($unhealthy -gt 0) {
    Write-Host "  ❌ Unhealthy: $unhealthy" -ForegroundColor Red
}
if ($exited -gt 0) {
    Write-Host "  🔴 Exited: $exited" -ForegroundColor Red
}

Write-Host ""

# Check disk usage
Write-Host "💾 Docker Disk Usage:" -ForegroundColor Yellow
docker system df

Write-Host ""

# Check unhealthy containers in detail
if ($unhealthy -gt 0) {
    Write-Host "🔍 Investigating Unhealthy Containers:" -ForegroundColor Yellow
    Write-Host ""
    
    foreach ($container in $containers) {
        if ($container.Status -match "unhealthy") {
            $name = $container.Names
            Write-Host "📋 Logs for $name (last 20 lines):" -ForegroundColor Red
            docker logs --tail 20 $name
            Write-Host ""
        }
    }
}

# Check exited containers
if ($exited -gt 0) {
    Write-Host "🔍 Exited Containers:" -ForegroundColor Yellow
    Write-Host ""
    
    foreach ($container in $containers) {
        if ($container.State -eq "exited") {
            $name = $container.Names
            Write-Host "📋 Last logs for $name:" -ForegroundColor Gray
            docker logs --tail 10 $name
            Write-Host ""
        }
    }
    
    Write-Host "💡 Tip: Run './scripts/cleanup-docker.ps1' to remove exited containers" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "✅ Health Check Complete!" -ForegroundColor Green
