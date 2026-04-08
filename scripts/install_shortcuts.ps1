param(
    [string]$StartupScript = "hyper-station-start.bat",
    [string]$ShutdownScript = "hyper-station-stop.bat"
)

# --- Configuration ---
$DesktopPath = [System.Environment]::GetFolderPath("Desktop")
# The batch scripts are in the same directory as this PowerShell script
$ScriptsPath = $PSScriptRoot
$StartupPath = Join-Path $ScriptsPath $StartupScript
$ShutdownPath = Join-Path $ScriptsPath $ShutdownScript

# --- Helper Function ---
function Create-Shortcut {
    param(
        [string]$TargetFile,
        [string]$ShortcutPath,
        [string]$Description,
        [string]$IconFile
    )

    $WScriptShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $TargetFile
    $Shortcut.Description = $Description
    $Shortcut.WorkingDirectory = $ScriptsPath
    
    # Optional: Set Icon
    if ($IconFile -ne "") {
        $Shortcut.IconLocation = $IconFile
    }
    
    $Shortcut.Save()
    Write-Host "Created shortcut: $ShortcutPath"
}

# --- Main Logic ---

Write-Host "---------------------------------------------------------------------------------"
Write-Host "   HYPER STATION SHORTCUT INSTALLER"
Write-Host "---------------------------------------------------------------------------------"

# Check if scripts exist
if (-not (Test-Path $StartupPath)) {
    Write-Error "Startup script not found: $StartupPath"
    exit 1
}

if (-not (Test-Path $ShutdownPath)) {
    Write-Error "Shutdown script not found: $ShutdownPath"
    exit 1
}

# 1. Create Startup Shortcut
$StartupLnk = Join-Path $DesktopPath "HYPER STATION START.lnk"
Create-Shortcut `
    -TargetFile $StartupPath `
    -ShortcutPath $StartupLnk `
    -Description "Launch HyperCode V2.0 Mission Control" `
    -IconFile "C:\Windows\System32\shell32.dll,137" # Rocket/Computer Icon

# 2. Create Shutdown Shortcut
$ShutdownLnk = Join-Path $DesktopPath "HYPER STATION STOP.lnk"
Create-Shortcut `
    -TargetFile $ShutdownPath `
    -ShortcutPath $ShutdownLnk `
    -Description "Shutdown HyperCode V2.0 Mission Control" `
    -IconFile "C:\Windows\System32\shell32.dll,27" # Power/Off Icon

Write-Host "---------------------------------------------------------------------------------"
Write-Host "   INSTALLATION COMPLETE"
Write-Host "---------------------------------------------------------------------------------"
Write-Host "Shortcuts created on Desktop."
Write-Host "Run 'HYPER STATION START' to begin mission."
