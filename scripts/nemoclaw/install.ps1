$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$sandbox = $env:NEMOCLAW_SANDBOX
if (-not $sandbox) { $sandbox = "broski" }

Write-Host "Running NemoClaw installer in WSL (logs will be written under logs/nemoclaw/)"

$script = @"
set -euo pipefail
cd '/mnt/h/HyperStation zone/HyperCode/HyperCode-V2.4'
export NEMOCLAW_SANDBOX='$sandbox'
bash scripts/nemoclaw/install.sh
"@

wsl -d Ubuntu-22.04 bash -lc $script

