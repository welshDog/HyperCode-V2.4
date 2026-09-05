# Docker Cleanup Script for Windows PowerShell
# Schedule via Task Scheduler or run manually
# Usage: powershell -ExecutionPolicy Bypass -File docker-cleanup.ps1 -Action all

param(
    [ValidateSet("build-cache", "images", "containers", "system", "all")]
    [string]$Action = "all",
    
    [string]$LogDir = "C:\logs",
    
    [switch]$Verbose
)

# Configuration
$LogFile = Join-Path $LogDir "docker-cleanup.log"
$ErrorLogFile = Join-Path $LogDir "docker-cleanup-error.log"

# Ensure log directory exists
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Logging function
function Write-Log {
    param(
        [ValidateSet("INFO", "WARN", "ERROR", "DEBUG")]
        [string]$Level = "INFO",
        [string]$Message
    )
    
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] [$Level] $Message"
    
    # Write to console
    switch ($Level) {
        "ERROR" {
            Write-Host $LogEntry -ForegroundColor Red
            Add-Content -Path $ErrorLogFile -Value $LogEntry
        }
        "WARN" {
            Write-Host $LogEntry -ForegroundColor Yellow
            Add-Content -Path $LogFile -Value $LogEntry
        }
        "INFO" {
            Write-Host $LogEntry -ForegroundColor Green
            Add-Content -Path $LogFile -Value $LogEntry
        }
        "DEBUG" {
            if ($Verbose) {
                Write-Host $LogEntry -ForegroundColor Cyan
            }
            Add-Content -Path $LogFile -Value $LogEntry
        }
    }
}

# Check Docker daemon
function Test-DockerDaemon {
    try {
        $null = docker ps 2>$null
        Write-Log -Level INFO "Docker daemon is running"
        return $true
    }
    catch {
        Write-Log -Level ERROR "Docker daemon is not running or not accessible"
        return $false
    }
}

# Get disk usage
function Get-DockerDiskUsage {
    try {
        $output = docker system df --format='table {{.Type}}`t{{.Size}}`t{{.Reclaimable}}'
        return $output
    }
    catch {
        Write-Log -Level ERROR "Failed to get disk usage: $_"
        return $null
    }
}

# Build cache prune
function Invoke-BuildCachePrune {
    Write-Log -Level INFO "=========================================="
    Write-Log -Level INFO "Step 1: Build Cache Prune (Monthly)"
    Write-Log -Level INFO "=========================================="
    
    try {
        $before = docker system df --format='{{.BuildCache.Size}}'
        Write-Log -Level INFO "Before: $before"
        
        docker builder prune -f --verbose 2>&1 | Add-Content -Path $LogFile
        
        $after = docker system df --format='{{.BuildCache.Size}}'
        Write-Log -Level INFO "After: $after"
        Write-Log -Level INFO "✓ Build cache prune completed"
        
        return $true
    }
    catch {
        Write-Log -Level ERROR "Build cache prune failed: $_"
        return $false
    }
}

# Image prune
function Invoke-ImagePrune {
    Write-Log -Level INFO "=========================================="
    Write-Log -Level INFO "Step 2: Image Prune - Unused Images (Weekly)"
    Write-Log -Level INFO "=========================================="
    
    try {
        $before = docker system df --format='{{.Images.Size}}'
        $imageCount = (docker images -q | Measure-Object -Line).Lines
        Write-Log -Level INFO "Before: $before (total images: $imageCount)"
        Write-Log -Level WARN "This will remove images not used by any container"
        
        docker image prune -a -f --verbose 2>&1 | Add-Content -Path $LogFile
        
        $after = docker system df --format='{{.Images.Size}}'
        $imageCountAfter = (docker images -q | Measure-Object -Line).Lines
        Write-Log -Level INFO "After: $after (total images: $imageCountAfter)"
        Write-Log -Level INFO "✓ Image prune completed"
        
        return $true
    }
    catch {
        Write-Log -Level ERROR "Image prune failed: $_"
        return $false
    }
}

# Container prune
function Invoke-ContainerPrune {
    Write-Log -Level INFO "=========================================="
    Write-Log -Level INFO "Step 3: Container Prune - Exited Containers (Weekly)"
    Write-Log -Level INFO "=========================================="
    
    try {
        $exited = (docker ps -a -f status=exited -q | Measure-Object -Line).Lines
        Write-Log -Level INFO "Found $exited exited containers"
        
        if ($exited -gt 0) {
            docker container prune -f --verbose 2>&1 | Add-Content -Path $LogFile
            Write-Log -Level INFO "✓ Container prune completed"
        }
        else {
            Write-Log -Level INFO "No exited containers to prune"
        }
        
        return $true
    }
    catch {
        Write-Log -Level ERROR "Container prune failed: $_"
        return $false
    }
}

# System prune
function Invoke-SystemPrune {
    Write-Log -Level INFO "=========================================="
    Write-Log -Level INFO "Step 4: System Prune - Full Cleanup (Quarterly)"
    Write-Log -Level INFO "=========================================="
    Write-Log -Level WARN "This is a full system prune. Volumes will NOT be touched."
    
    try {
        docker system prune -f --verbose 2>&1 | Add-Content -Path $LogFile
        Write-Log -Level INFO "✓ System prune completed"
        
        return $true
    }
    catch {
        Write-Log -Level ERROR "System prune failed: $_"
        return $false
    }
}

# Report disk usage
function Get-DiskUsageReport {
    Write-Log -Level INFO "=========================================="
    Write-Log -Level INFO "Final Disk Usage Summary"
    Write-Log -Level INFO "=========================================="
    
    $usage = Get-DockerDiskUsage
    if ($usage) {
        Write-Host ""
        $usage | Tee-Object -FilePath $LogFile -Append
        Write-Host ""
        
        Write-Log -Level INFO "Note: Reclaimable excludes volumes (preserved for data safety)"
    }
}

# Main function
function Main {
    Write-Log -Level INFO "========================================"
    Write-Log -Level INFO "Docker Cleanup Script Started"
    Write-Log -Level INFO "Action: $Action"
    Write-Log -Level INFO "========================================"
    
    # Test Docker daemon
    if (-not (Test-DockerDaemon)) {
        exit 1
    }
    
    # Execute action
    $success = $true
    switch ($Action) {
        "build-cache" {
            $success = Invoke-BuildCachePrune
        }
        "images" {
            $success = Invoke-ImagePrune
        }
        "containers" {
            $success = Invoke-ContainerPrune
        }
        "system" {
            $success = Invoke-SystemPrune
        }
        "all" {
            $success = Invoke-BuildCachePrune
            $success = $success -and (Invoke-ImagePrune)
            $success = $success -and (Invoke-ContainerPrune)
        }
        default {
            Write-Log -Level ERROR "Invalid action: $Action"
            exit 1
        }
    }
    
    # Report
    Get-DiskUsageReport
    
    if ($success) {
        Write-Log -Level INFO "✓ Cleanup completed successfully"
        exit 0
    }
    else {
        Write-Log -Level ERROR "✗ Cleanup completed with errors"
        exit 1
    }
}

# Run main
Main
