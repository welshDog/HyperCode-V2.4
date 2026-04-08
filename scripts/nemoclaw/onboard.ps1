$ErrorActionPreference = "Stop"

$sandbox = $env:NEMOCLAW_SANDBOX
if (-not $sandbox) { $sandbox = "broski" }

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$repoRootWsl = wsl wslpath -a "$repoRoot"
$cmd = "cd '$repoRootWsl' && NEMOCLAW_SANDBOX='$sandbox' bash scripts/nemoclaw/onboard.sh"
wsl -d Ubuntu-22.04 bash -lc $cmd
