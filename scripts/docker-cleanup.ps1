# Docker Cleanup for HyperCode (PowerShell)
# Safely removes unused Docker resources

param(
    [switch]$All,
    [switch]$Containers,
    [switch]$Images,
    [switch]$Volumes,
    [switch]$Cache,
    [switch]$Networks,
    [switch]$Deep,
    [switch]$HyperCode,
    [switch]$Help
)

Write-Host "🧹 HyperCode Docker Cleanup Utility" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

function Show-DiskUsage {
    Write-Host "Current Docker disk usage:" -ForegroundColor Yellow
    docker system df
    Write-Host ""
}

function Clean-StoppedContainers {
    Write-Host "Removing stopped containers..." -ForegroundColor Yellow
    $count = (docker ps -a -q -f status=exited).Count
    if ($count -gt 0) {
        docker container prune -f | Out-Null
        Write-Host "✓ Removed $count stopped container(s)" -ForegroundColor Green
    } else {
        Write-Host "No stopped containers to remove"
    }
    Write-Host ""
}

function Clean-DanglingImages {
    Write-Host "Removing dangling images..." -ForegroundColor Yellow
    $count = (docker images -f "dangling=true" -q).Count
    if ($count -gt 0) {
        docker image prune -f | Out-Null
        Write-Host "✓ Removed $count dangling image(s)" -ForegroundColor Green
    } else {
        Write-Host "No dangling images to remove"
    }
    Write-Host ""
}

function Clean-UnusedVolumes {
    Write-Host "Removing unused volumes..." -ForegroundColor Yellow
    $count = (docker volume ls -qf dangling=true).Count
    if ($count -gt 0) {
        docker volume prune -f | Out-Null
        Write-Host "✓ Removed $count unused volume(s)" -ForegroundColor Green
    } else {
        Write-Host "No unused volumes to remove"
    }
    Write-Host ""
}

function Clean-BuildCache {
    Write-Host "Removing build cache..." -ForegroundColor Yellow
    docker builder prune -f | Out-Null
    Write-Host "✓ Build cache cleaned" -ForegroundColor Green
    Write-Host ""
}

function Clean-UnusedNetworks {
    Write-Host "Removing unused networks..." -ForegroundColor Yellow
    docker network prune -f | Out-Null
    Write-Host "✓ Unused networks removed" -ForegroundColor Green
    Write-Host ""
}

function Clean-OldImages {
    Write-Host "Removing old image versions (keeping last 3)..." -ForegroundColor Yellow
    
    $repos = @(
        "hypercode-core", "crew-orchestrator", 
        "frontend-specialist", "backend-specialist",
        "database-architect", "qa-engineer",
        "devops-engineer", "security-engineer",
        "system-architect", "project-strategist"
    )
    
    foreach ($repo in $repos) {
        $images = docker images --format "{{.ID}}" $repo 2>$null | Select-Object -Skip 3
        if ($images) {
            Write-Host "Cleaning old versions of $repo..."
            $images | ForEach-Object { docker rmi -f $_ 2>$null }
        }
    }
    Write-Host ""
}

function Deep-Clean {
    Write-Host "⚠️  WARNING: This will remove ALL unused Docker resources" -ForegroundColor Yellow
    Write-Host "This includes:"
    Write-Host "  - All stopped containers"
    Write-Host "  - All networks not used by at least one container"
    Write-Host "  - All dangling images"
    Write-Host "  - All dangling build cache"
    Write-Host ""
    
    $confirm = Read-Host "Are you sure? (yes/no)"
    
    if ($confirm -eq "yes") {
        docker system prune -a -f --volumes
        Write-Host "✓ Deep clean complete" -ForegroundColor Green
    } else {
        Write-Host "Deep clean cancelled"
    }
    Write-Host ""
}

function Clean-HyperCodeResources {
    Write-Host "⚠️  WARNING: This will remove all HyperCode containers and volumes" -ForegroundColor Yellow
    Write-Host ""
    
    $confirm = Read-Host "Are you sure? (yes/no)"
    
    if ($confirm -eq "yes") {
        Write-Host "Stopping and removing HyperCode containers..."
        
        docker-compose -f docker-compose.yml down -v 2>$null
        docker-compose -f docker-compose.prod.yml down -v 2>$null
        docker-compose -f docker-compose.agents.yml down -v 2>$null
        docker-compose -f docker-compose.monitoring.yml down -v 2>$null
        
        Write-Host "Removing HyperCode images..."
        docker images | Select-String "hypercode" | ForEach-Object {
            $imageId = ($_ -split '\s+')[2]
            docker rmi -f $imageId 2>$null
        }
        
        Write-Host "✓ HyperCode resources cleaned" -ForegroundColor Green
    } else {
        Write-Host "Cleanup cancelled"
    }
    Write-Host ""
}

function Show-Help {
    Write-Host "Usage: .\docker-cleanup.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -All              Clean all unused resources (default)"
    Write-Host "  -Containers       Clean stopped containers only"
    Write-Host "  -Images           Clean dangling images only"
    Write-Host "  -Volumes          Clean unused volumes only"
    Write-Host "  -Cache            Clean build cache only"
    Write-Host "  -Networks         Clean unused networks only"
    Write-Host "  -Deep             Deep clean (removes ALL unused resources)"
    Write-Host "  -HyperCode        Remove all HyperCode specific resources"
    Write-Host "  -Help             Show this help message"
    Write-Host ""
}

# Main execution
Show-DiskUsage

if ($Help) {
    Show-Help
    exit
}

if ($Containers) {
    Clean-StoppedContainers
}
elseif ($Images) {
    Clean-DanglingImages
}
elseif ($Volumes) {
    Clean-UnusedVolumes
}
elseif ($Cache) {
    Clean-BuildCache
}
elseif ($Networks) {
    Clean-UnusedNetworks
}
elseif ($Deep) {
    Deep-Clean
}
elseif ($HyperCode) {
    Clean-HyperCodeResources
}
else {
    # Default: clean all
    Clean-StoppedContainers
    Clean-DanglingImages
    Clean-UnusedVolumes
    Clean-BuildCache
    Clean-UnusedNetworks
    Clean-OldImages
}

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "After cleanup:" -ForegroundColor Yellow
Show-DiskUsage
Write-Host "✅ Cleanup complete!" -ForegroundColor Green
