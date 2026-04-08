# Quick Docker Commands for HyperCode (PowerShell)
# Collection of useful one-liners

Write-Host "🐳 HyperCode Docker Quick Commands" -ForegroundColor Cyan
Write-Host "===================================`n" -ForegroundColor Cyan

# Development
Write-Host "DEVELOPMENT" -ForegroundColor Yellow
Write-Host "Start dev environment:"
Write-Host "  docker-compose -f docker-compose.dev.yml up`n"

# Testing
Write-Host "TESTING" -ForegroundColor Yellow
Write-Host "Run all tests:"
Write-Host "  docker-compose -f docker-compose.test.yml up --abort-on-container-exit"
Write-Host "Run specific tests:"
Write-Host "  docker-compose -f docker-compose.test.yml run unit-tests"
Write-Host "  docker-compose -f docker-compose.test.yml run integration-tests"
Write-Host "  docker-compose -f docker-compose.test.yml run e2e-tests`n"

# Production
Write-Host "PRODUCTION" -ForegroundColor Yellow
Write-Host "Build all images:"
Write-Host "  `$env:REGISTRY='myregistry.com'; `$env:VERSION='v1.0.0'; docker buildx bake"
Write-Host "Start production:"
Write-Host "  docker-compose -f docker-compose.prod.yml up -d"
Write-Host "Scale services:"
Write-Host "  docker-compose -f docker-compose.prod.yml up -d --scale hypercode-core=5`n"

# Monitoring
Write-Host "MONITORING" -ForegroundColor Yellow
Write-Host "Health check:"
Write-Host "  .\scripts\docker-health-monitor.ps1"
Write-Host "Watch mode:"
Write-Host "  .\scripts\docker-health-monitor.ps1 -Watch"
Write-Host "View logs:"
Write-Host "  docker-compose logs -f [service]"
Write-Host "View specific logs:"
Write-Host "  docker logs -f hypercode-core --tail 100`n"

# Maintenance
Write-Host "MAINTENANCE" -ForegroundColor Yellow
Write-Host "Cleanup:"
Write-Host "  .\scripts\docker-cleanup.ps1"
Write-Host "Backup:"
Write-Host "  .\scripts\docker-backup.ps1"
Write-Host "Update images:"
Write-Host "  docker-compose pull && docker-compose up -d"
Write-Host "Restart service:"
Write-Host "  docker-compose restart hypercode-core`n"

# Debug
Write-Host "DEBUGGING" -ForegroundColor Yellow
Write-Host "Shell into container:"
Write-Host "  docker exec -it hypercode-core /bin/bash"
Write-Host "Check container:"
Write-Host "  docker inspect hypercode-core"
Write-Host "View stats:"
Write-Host "  docker stats"
Write-Host "View disk usage:"
Write-Host "  docker system df`n"

# Quick access URLs
Write-Host "SERVICE URLs" -ForegroundColor Yellow
Write-Host "Core API:          http://localhost:8000"
Write-Host "Dashboard:         http://localhost:8088"
Write-Host "Orchestrator:      http://localhost:8080"
Write-Host "Prometheus:        http://localhost:9090"
Write-Host "Grafana:           http://localhost:3001"
Write-Host "Jaeger:            http://localhost:16686"
Write-Host "Redis Commander:   http://localhost:8081 (dev)"
Write-Host "pgAdmin:           http://localhost:5050 (dev)"
Write-Host ""
