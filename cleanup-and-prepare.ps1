#!/usr/bin/env powershell
# Memory & Docker Cleanup Script
# Purpose: Free up system memory and prepare for container startup
# Usage: .\cleanup-and-prepare.ps1 [-Aggressive] [-DryRun]

param(
    [switch]$Aggressive = $false,
    [switch]$DryRun = $false,
    [switch]$Verbose = $true
)

$ErrorActionPreference = 'Continue'

function Write-Status {
    param([string]$Message, [string]$Status = "INFO")
    
    $colors = @{
        "INFO"    = "Cyan"
        "SUCCESS" = "Green"
        "WARNING" = "Yellow"
        "ERROR"   = "Red"
    }
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] [$Status] $Message" -ForegroundColor $colors[$Status]
}

# Banner
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║      BROski Memory & Docker Cleanup Suite v1.0            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Status "DRY RUN MODE - No changes will be made" "WARNING"
}

# Phase 1: System Memory Report
Write-Status "Phase 1: System Memory Audit" "INFO"
Write-Host ""

$os = Get-CimInstance Win32_OperatingSystem
$totalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
$freeGB = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
$usedGB = [math]::Round($totalGB - $freeGB, 2)
$percent = [math]::Round(($usedGB / $totalGB) * 100, 2)

Write-Host "Total RAM:       $totalGB GB"
Write-Host "Used:            $usedGB GB"
Write-Host "Available:       $freeGB GB"
Write-Host "Utilization:     $percent%"
Write-Host ""

if ($percent -gt 85) {
    Write-Status "WARNING: System RAM above 85%!" "WARNING"
    Write-Status "Proceeding with aggressive cleanup" "WARNING"
}

# Top memory processes
Write-Status "Top Memory Consumers:" "INFO"
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 5 `
@{N = "Process"; E = { $_.ProcessName } }, `
@{N = "PID"; E = { $_.Id } }, `
@{N = "Memory (MB)"; E = { [math]::Round($_.WorkingSet / 1MB, 2) } } | Format-Table -AutoSize
Write-Host ""

# Phase 2: PowerShell Garbage Collection
Write-Status "Phase 2: PowerShell Garbage Collection" "INFO"
if (-not $DryRun) {
    [gc]::Collect()
    [gc]::WaitForPendingFinalizers()
    Write-Status "Garbage collection complete" "SUCCESS"
}
else {
    Write-Status "Would run garbage collection" "INFO"
}
Write-Host ""

# Phase 3: Windows Temp Cleanup
Write-Status "Phase 3: Windows Temporary Files Cleanup" "INFO"
$tempPaths = @(
    "$env:TEMP\*",
    "$env:LOCALAPPDATA\Temp\*",
    "C:\Windows\Temp\*",
    "C:\Windows\Prefetch\*"
)

foreach ($path in $tempPaths) {
    if (Test-Path $path) {
        if (-not $DryRun) {
            try {
                $itemCount = (Get-ChildItem $path -Force -Recurse -ErrorAction SilentlyContinue | Measure-Object).Count
                Remove-Item $path -Force -Recurse -ErrorAction SilentlyContinue
                Write-Status "Cleaned: $path ($itemCount items)" "SUCCESS"
            }
            catch {
                Write-Status "Error cleaning $path : $_" "WARNING"
            }
        }
        else {
            $itemCount = (Get-ChildItem $path -Force -Recurse -ErrorAction SilentlyContinue | Measure-Object).Count
            Write-Status "Would clean: $path ($itemCount items)" "INFO"
        }
    }
}
Write-Host ""

# Phase 4: Recycle Bin
Write-Status "Phase 4: Empty Recycle Bin" "INFO"
if (-not $DryRun) {
    try {
        Clear-RecycleBin -Force -ErrorAction SilentlyContinue
        Write-Status "Recycle bin emptied" "SUCCESS"
    }
    catch {
        Write-Status "Could not empty recycle bin (may require UAC)" "WARNING"
    }
}
else {
    Write-Status "Would empty recycle bin" "INFO"
}
Write-Host ""

# Phase 5: Docker Cleanup
Write-Status "Phase 5: Docker System Cleanup" "INFO"
$docker_check = docker ps 2>&1
if ($LASTEXITCODE -eq 0) {
    if (-not $DryRun) {
        Write-Status "Pruning unused Docker images..." "INFO"
        docker system prune -f --quiet
        
        Write-Status "Pruning dangling images..." "INFO"
        docker image prune -a --force --quiet
        
        Write-Status "Docker cleanup complete" "SUCCESS"
    }
    else {
        Write-Status "Would run: docker system prune -f" "INFO"
        Write-Status "Would run: docker image prune -a --force" "INFO"
    }
    
    Write-Host ""
    Write-Status "Docker Disk Usage:" "INFO"
    docker system df | Select-Object -Skip 1 | Format-Table
}
else {
    Write-Status "Docker not running - skipping Docker cleanup" "WARNING"
}
Write-Host ""

# Phase 6: Aggressive Cleanup (optional)
if ($Aggressive) {
    Write-Status "Phase 6: Aggressive Application Shutdown" "WARNING"
    
    $appsToKill = @("chrome", "firefox", "slack", "teams", "outlook")
    
    foreach ($app in $appsToKill) {
        $proc = Get-Process -Name $app -ErrorAction SilentlyContinue
        if ($proc) {
            if (-not $DryRun) {
                Write-Status "Stopping $app..." "WARNING"
                $proc | Stop-Process -Force -ErrorAction SilentlyContinue
            }
            else {
                Write-Status "Would stop $($proc.Count) instance(s) of $app" "INFO"
            }
        }
    }
    
    if (-not $DryRun) {
        Start-Sleep -Seconds 2
        Write-Status "Aggressive cleanup complete" "SUCCESS"
    }
    Write-Host ""
}

# Phase 7: Post-Cleanup Memory Report
Write-Status "Phase 7: Post-Cleanup Memory Report" "INFO"
Write-Host ""

Start-Sleep -Seconds 2

$os2 = Get-CimInstance Win32_OperatingSystem
$totalGB2 = [math]::Round($os2.TotalVisibleMemorySize / 1MB, 2)
$freeGB2 = [math]::Round($os2.FreePhysicalMemory / 1MB, 2)
$usedGB2 = [math]::Round($totalGB2 - $freeGB2, 2)
$percent2 = [math]::Round(($usedGB2 / $totalGB2) * 100, 2)
$freed = [math]::Round($freeGB2 - $freeGB, 2)

Write-Host "Total RAM:       $totalGB2 GB"
Write-Host "Used:            $usedGB2 GB"
Write-Host "Available:       $freeGB2 GB (⬆️ +$freed GB freed)"
Write-Host "Utilization:     $percent2%"
Write-Host ""

if ($percent2 -lt 85) {
    Write-Status "✅ System memory optimized successfully!" "SUCCESS"
}
else {
    Write-Status "⚠️  Still above 85% - consider closing more applications" "WARNING"
}

Write-Host ""

# Phase 8: Readiness Check
Write-Status "Phase 8: Docker Startup Readiness Check" "INFO"
Write-Host ""

if ($freeGB2 -ge 2) {
    Write-Status "✅ Available memory sufficient for Docker startup" "SUCCESS"
    Write-Host ""
    Write-Host "Recommended startup command:" -ForegroundColor Green
    Write-Host "cd h:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4" -ForegroundColor Green
    Write-Host "docker compose -f docker-compose.yml -f docker-compose.core.yml up -d" -ForegroundColor Green
}
else {
    Write-Status "❌ Insufficient memory for Docker startup" "ERROR"
    Write-Host "Available: $freeGB2 GB (Need: >= 2 GB)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "1. Run this script with -Aggressive flag to close more apps" -ForegroundColor Yellow
    Write-Host "2. Manually close large applications" -ForegroundColor Yellow
    Write-Host "3. Increase virtual memory (paging file)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Cleanup Complete - Ready to proceed with Docker ops      ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
