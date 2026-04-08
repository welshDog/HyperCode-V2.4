$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$sandbox = $env:NEMOCLAW_SANDBOX
if (-not $sandbox) { $sandbox = "broski" }

Write-Host "Running NemoClaw NVIDIA_API_KEY connectivity check for sandbox: $sandbox"

$script = @"
set -euo pipefail
cd '/mnt/h/HyperStation zone/HyperCode/HyperCode-V2.4'
export NEMOCLAW_SANDBOX='$sandbox'
bash scripts/nemoclaw/keycheck.sh
"@

$out = wsl bash -lc $script
Write-Host $out

