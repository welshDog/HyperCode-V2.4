$ErrorActionPreference = "Stop"

function Require-Command($name) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if (-not $cmd) {
    throw "Missing required command: $name"
  }
}

Require-Command "wsl"

$sandbox = $env:NEMOCLAW_SANDBOX
if (-not $sandbox) { $sandbox = "broski" }

Write-Host "Validating NemoClaw sandbox: $sandbox"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$envPath = Join-Path $repoRoot ".env"
$nvidiaApiKey = $env:NVIDIA_API_KEY
if (-not $nvidiaApiKey -and (Test-Path $envPath)) {
  $line = Select-String -Path $envPath -Pattern '^\s*NVIDIA_API_KEY\s*=\s*(.+)\s*$' -CaseSensitive
  if ($line) {
    $nvidiaApiKey = ($line.Matches[0].Groups[1].Value).Trim()
  }
}

$keyOk = [bool]($nvidiaApiKey -and $nvidiaApiKey.Trim().Length -gt 0)

$repoRootWsl = wsl wslpath -a "$repoRoot"
$cmd = "cd '$repoRootWsl' && NEMOCLAW_SANDBOX='$sandbox' bash scripts/nemoclaw/validate.sh"
$out = if ($keyOk) {
  wsl env NVIDIA_API_KEY="$nvidiaApiKey" bash -lc $cmd 2>&1
} else {
  wsl bash -lc $cmd 2>&1
}
Write-Host $out
if ($LASTEXITCODE -ne 0) {
  throw "NemoClaw validation failed"
}
