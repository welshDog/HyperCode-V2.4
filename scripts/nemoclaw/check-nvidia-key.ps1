$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$envPath = Join-Path $repoRoot ".env"

if (-not (Test-Path $envPath)) {
  throw "Missing .env at repo root"
}

$line = Select-String -Path $envPath -Pattern '^\s*NVIDIA_API_KEY\s*=\s*(.+)\s*$' -CaseSensitive
if (-not $line) {
  throw "NVIDIA_API_KEY not found in .env"
}

$value = ($line.Matches[0].Groups[1].Value).Trim()
if (-not $value) {
  throw "NVIDIA_API_KEY is empty"
}

Write-Host "ok: NVIDIA_API_KEY present in .env (value not printed)"

