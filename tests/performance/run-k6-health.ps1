param(
  [string]$BaseUrl = 'http://host.docker.internal:8000',
  [string]$Image = 'grafana/k6:0.57.0'
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$reportsDir = Join-Path $repoRoot 'reports'

New-Item -ItemType Directory -Force -Path $reportsDir | Out-Null

docker run --rm `
  -e "BASE_URL=$BaseUrl" `
  -v "${repoRoot}:/work" `
  -w /work `
  $Image run tests/performance/k6-health.js
