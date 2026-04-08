$ErrorActionPreference = "Stop"

$name = "openshell-cluster-nemoclaw"

try {
  $exists = (docker ps -a --format "{{.Names}}" | Select-String -SimpleMatch $name -Quiet)
} catch {
  throw "Docker not available. Start Docker Desktop and retry."
}

if (-not $exists) {
  Write-Host "Container not found: $name"
  exit 1
}

docker update `
  --health-interval 30s `
  --health-timeout 30s `
  --health-start-period 90s `
  --health-retries 3 `
  $name | Out-Null

docker ps -a --filter "name=$name" --format "table {{.Names}}\t{{.Status}}"

