param(
  [switch]$Monitor
)

Write-Host "Starting HyperCode core stack..." -ForegroundColor Cyan
docker-compose up -d

if ($Monitor -or $true) {
  Write-Host "Starting monitoring stack..." -ForegroundColor Cyan
  docker-compose -f docker-compose.monitoring.yml up -d
}

Start-Sleep -Seconds 3

Write-Host "Opening URLs..." -ForegroundColor Green
Start-Process "http://localhost:8000/health"
Start-Process "http://localhost:3001/d/hypercode-overview/hypercode-overview"
Start-Process "http://localhost:5173"
Start-Process "http://localhost:3000"

Write-Host "Dev stack launched. Use Ctrl+C to stop foreground processes, or docker-compose down to stop." -ForegroundColor Yellow
