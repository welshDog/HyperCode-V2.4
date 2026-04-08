# Docker Health Monitor for HyperCode (PowerShell)
# Monitors container health and reports issues

param(
    [string]$ComposeFile = "docker-compose.yml",
    [string]$Namespace = "hypercode",
    [switch]$Watch,
    [switch]$Resources
)

Write-Host "🏥 HyperCode Docker Health Monitor" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

function Get-ContainerHealth {
    param([string]$Container)
    
    $health = docker inspect --format='{{.State.Health.Status}}' $Container 2>$null
    if (-not $health) { return "no_healthcheck" }
    return $health
}

function Get-ContainerStatus {
    param([string]$Container)
    
    $status = docker inspect --format='{{.State.Status}}' $Container 2>$null
    if (-not $status) { return "not_found" }
    return $status
}

function Get-RestartCount {
    param([string]$Container)
    
    $count = docker inspect --format='{{.RestartCount}}' $Container 2>$null
    if (-not $count) { return 0 }
    return $count
}

function Get-Uptime {
    param([string]$Container)
    
    $started = docker inspect --format='{{.State.StartedAt}}' $Container 2>$null
    if (-not $started) { return "N/A" }
    
    $startTime = [DateTime]::Parse($started)
    $uptime = (Get-Date) - $startTime
    
    return "{0:N0} seconds" -f $uptime.TotalSeconds
}

function Get-ResourceUsage {
    param([string]$Container)
    
    $stats = docker stats --no-stream --format "CPU: {{.CPUPerc}} | Memory: {{.MemUsage}}" $Container 2>$null
    if (-not $stats) { return "N/A" }
    return $stats
}

function Monitor-Containers {
    $issuesFound = 0
    
    Write-Host "Checking containers..." -ForegroundColor Yellow
    Write-Host ""
    
    $services = docker-compose -f $ComposeFile ps --services
    
    foreach ($service in $services) {
        $container = "${Namespace}_${service}_1"
        
        # Try alternative naming
        if (-not (docker inspect $container 2>$null)) {
            $container = $service
        }
        
        if (-not (docker inspect $container 2>$null)) {
            Write-Host "❌ Container $service : NOT FOUND" -ForegroundColor Red
            $issuesFound++
            continue
        }
        
        $status = Get-ContainerStatus -Container $container
        $health = Get-ContainerHealth -Container $container
        $restarts = Get-RestartCount -Container $container
        $uptime = Get-Uptime -Container $container
        $resources = Get-ResourceUsage -Container $container
        
        # Status check
        if ($status -ne "running") {
            Write-Host "❌ $service : $status" -ForegroundColor Red
            $issuesFound++
            continue
        }
        
        # Health check
        if ($health -eq "unhealthy") {
            Write-Host "❌ $service : UNHEALTHY" -ForegroundColor Red
            Write-Host "   Status: $status | Restarts: $restarts"
            Write-Host "   Uptime: $uptime"
            Write-Host "   Resources: $resources"
            $issuesFound++
            
            # Show recent logs
            Write-Host "   Recent logs:"
            docker logs --tail 5 $container 2>&1 | ForEach-Object { Write-Host "   $_" }
            Write-Host ""
            continue
        }
        
        # Warning for high restart count
        if ([int]$restarts -gt 3) {
            Write-Host "⚠️  $service : $restarts restarts" -ForegroundColor Yellow
            Write-Host "   Status: $status | Health: $health"
            Write-Host "   Uptime: $uptime"
            Write-Host "   Resources: $resources"
            Write-Host ""
            continue
        }
        
        # All good
        if ($health -eq "healthy" -or $health -eq "no_healthcheck") {
            Write-Host "✓ $service : healthy" -ForegroundColor Green
            Write-Host "   Status: $status | Restarts: $restarts"
            Write-Host "   Uptime: $uptime"
            Write-Host "   Resources: $resources"
            Write-Host ""
        }
    }
    
    Write-Host "=====================================" -ForegroundColor Cyan
    if ($issuesFound -eq 0) {
        Write-Host "✅ All containers healthy!" -ForegroundColor Green
        return $true
    } else {
        Write-Host "❌ Found $issuesFound issue(s)" -ForegroundColor Red
        return $false
    }
}

function Show-SystemResources {
    Write-Host ""
    Write-Host "System Resources:" -ForegroundColor Cyan
    Write-Host "-----------------"
    docker system df
    Write-Host ""
}

# Main execution
if ($Resources) {
    Show-SystemResources
    exit
}

if ($Watch) {
    while ($true) {
        Clear-Host
        Monitor-Containers
        Write-Host ""
        Write-Host "Refreshing in 10 seconds... (Ctrl+C to stop)" -ForegroundColor Yellow
        Start-Sleep -Seconds 10
    }
} else {
    Monitor-Containers
}
