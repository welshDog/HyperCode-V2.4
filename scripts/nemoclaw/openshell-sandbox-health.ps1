$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$repoRootWsl = wsl wslpath -a "$repoRoot"
$cmd = "cd '$repoRootWsl' && bash scripts/nemoclaw/openshell-sandbox-health.sh"
wsl -d Ubuntu-22.04 bash -lc $cmd

