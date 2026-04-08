# Backup and Restore Utility for Hyper-Mission System

param (
    [string]$Action = "backup", # backup or restore
    [string]$File = "production_backup.sql"
)

$ContainerName = "hyper-mission-system-postgres-1"
$DBUser = "user"
$DBName = "hypermission"
$BackupDir = "../backups" # Relative to scripts folder

# Ensure backup directory exists
if (!(Test-Path -Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

if ($Action -eq "backup") {
    Write-Host "Creating backup of $DBName from $ContainerName..."
    # Use explicit encoding for PowerShell output redirection to avoid BOM issues if possible, but standard redirection usually works for text dumps
    docker exec -t $ContainerName pg_dump -U $DBUser $DBName > "$BackupDir/$File"
    if ($?) { Write-Host "Backup successful: $BackupDir/$File" -ForegroundColor Green }
    else { Write-Host "Backup failed!" -ForegroundColor Red }
}
elseif ($Action -eq "restore") {
    if (!(Test-Path -Path "$BackupDir/$File")) {
        Write-Host "Backup file not found: $BackupDir/$File" -ForegroundColor Red
        exit 1
    }
    Write-Host "Restoring $DBName to $ContainerName from $BackupDir/$File..."
    # Using Get-Content and piping to docker exec -i
    Get-Content "$BackupDir/$File" | docker exec -i $ContainerName psql -U $DBUser -d $DBName
    if ($?) { Write-Host "Restore successful!" -ForegroundColor Green }
    else { Write-Host "Restore failed!" -ForegroundColor Red }
}
else {
    Write-Host "Invalid action. Use 'backup' or 'restore'."
}
