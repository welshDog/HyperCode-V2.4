# Docker Backup for HyperCode (PowerShell)
# Backs up volumes, configs, and database

param(
    [string]$ComposeFile = "docker-compose.yml",
    [string]$BackupDir = ".\backups"
)

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "💾 HyperCode Docker Backup Utility" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Create backup directory
$backupPath = Join-Path $BackupDir $timestamp
New-Item -ItemType Directory -Path $backupPath -Force | Out-Null

function Backup-PostgreSQL {
    Write-Host "Backing up PostgreSQL database..." -ForegroundColor Yellow
    
    $container = docker-compose -f $ComposeFile ps -q postgres
    if (-not $container) {
        Write-Host "PostgreSQL container not found" -ForegroundColor Red
        return $false
    }
    
    $outputFile = Join-Path $backupPath "postgres-hypercode.sql.gz"
    docker exec $container pg_dump -U postgres hypercode | & gzip > $outputFile
    
    Write-Host "✓ PostgreSQL backup complete" -ForegroundColor Green
    return $true
}

function Backup-Redis {
    Write-Host "Backing up Redis..." -ForegroundColor Yellow
    
    $container = docker-compose -f $ComposeFile ps -q redis
    if (-not $container) {
        Write-Host "Redis container not found" -ForegroundColor Red
        return $false
    }
    
    # Trigger Redis save
    docker exec $container redis-cli SAVE | Out-Null
    
    # Copy dump file
    $outputFile = Join-Path $backupPath "redis-dump.rdb"
    docker cp "${container}:/data/dump.rdb" $outputFile
    
    Write-Host "✓ Redis backup complete" -ForegroundColor Green
    return $true
}

function Backup-Volumes {
    Write-Host "Backing up Docker volumes..." -ForegroundColor Yellow
    
    $volumes = docker volume ls --format "{{.Name}}" | Where-Object { $_ -match "hypercode" }
    
    if (-not $volumes) {
        Write-Host "No HyperCode volumes found"
        return
    }
    
    foreach ($volume in $volumes) {
        Write-Host "  Backing up volume: $volume"
        $outputFile = Join-Path $backupPath "${volume}.tar.gz"
        
        docker run --rm `
            -v "${volume}:/data" `
            -v "${backupPath}:/backup" `
            alpine tar czf "/backup/${volume}.tar.gz" -C /data .
    }
    
    Write-Host "✓ Volume backups complete" -ForegroundColor Green
}

function Backup-Configs {
    Write-Host "Backing up configurations..." -ForegroundColor Yellow
    
    # Copy important config files
    Copy-Item "docker-compose*.yml" $backupPath -ErrorAction SilentlyContinue
    Copy-Item ".env*" $backupPath -ErrorAction SilentlyContinue
    Copy-Item "Configuration_Kit" $backupPath -Recurse -ErrorAction SilentlyContinue
    Copy-Item "monitoring" $backupPath -Recurse -ErrorAction SilentlyContinue
    
    Write-Host "✓ Configuration backup complete" -ForegroundColor Green
}

function Create-Manifest {
    Write-Host "Creating backup manifest..." -ForegroundColor Yellow
    
    $services = docker-compose -f $ComposeFile ps --services
    
    $manifest = @"
HyperCode Backup Manifest
========================
Date: $(Get-Date)
Compose File: $ComposeFile
Docker Version: $(docker --version)

Contents:
- PostgreSQL database dump
- Redis dump
- Docker volumes
- Configuration files

Containers backed up:
$($services -join "`n")

To restore:
  1. Extract volumes: docker run --rm -v volume_name:/data -v `$(pwd):/backup alpine tar xzf /backup/volume.tar.gz -C /data
  2. Restore PostgreSQL: gzip -dc postgres-hypercode.sql.gz | docker exec -i postgres psql -U postgres hypercode
  3. Restore Redis: docker cp redis-dump.rdb container:/data/dump.rdb && docker exec container redis-cli SHUTDOWN SAVE
"@
    
    $manifestFile = Join-Path $backupPath "MANIFEST.txt"
    $manifest | Out-File -FilePath $manifestFile -Encoding UTF8
    
    Write-Host "✓ Manifest created" -ForegroundColor Green
}

function Compress-Backup {
    Write-Host "Compressing backup..." -ForegroundColor Yellow
    
    $archiveName = "hypercode-backup-$timestamp.zip"
    $archivePath = Join-Path $BackupDir $archiveName
    
    Compress-Archive -Path $backupPath -DestinationPath $archivePath -Force
    Remove-Item -Path $backupPath -Recurse -Force
    
    Write-Host "✓ Backup compressed: $archiveName" -ForegroundColor Green
    return $archivePath
}

function Cleanup-OldBackups {
    Write-Host "Cleaning up old backups..." -ForegroundColor Yellow
    
    $cutoffDate = (Get-Date).AddDays(-7)
    Get-ChildItem -Path $BackupDir -Filter "hypercode-backup-*.zip" | 
        Where-Object { $_.LastWriteTime -lt $cutoffDate } |
        Remove-Item -Force
    
    Write-Host "✓ Old backups cleaned" -ForegroundColor Green
}

# Main execution
Write-Host "Starting backup to: $backupPath" -ForegroundColor Yellow
Write-Host ""

$success = $true

if (-not (Backup-PostgreSQL)) { $success = $false }
if (-not (Backup-Redis)) { $success = $false }
Backup-Volumes
Backup-Configs
Create-Manifest

if ($success) {
    $archivePath = Compress-Backup
    Cleanup-OldBackups
    
    Write-Host ""
    Write-Host "===================================" -ForegroundColor Cyan
    Write-Host "✅ Backup complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Backup location: $archivePath" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To restore:" -ForegroundColor Yellow
    Write-Host "  1. Extract: Expand-Archive $archivePath"
    Write-Host "  2. Follow instructions in MANIFEST.txt"
} else {
    Write-Host ""
    Write-Host "⚠️  Backup completed with errors" -ForegroundColor Yellow
}
