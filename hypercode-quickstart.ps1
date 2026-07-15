# HyperCode-V2.4 Quick Start Script (Windows/PowerShell)
# Usage: .\hypercode-quickstart.ps1 -Command core|full|agents|health|all

param(
    [ValidateSet("core", "agents", "health", "full", "all", "status", "stop", "help")]
    [string]$Command = "core"
)

$ErrorActionPreference = "Stop"

$HC_DATA_ROOT = $env:HC_DATA_ROOT -or ".\_HC_DATA"
$Colors = @{
    Success = "Green"
    Warning = "Yellow"
    Error   = "Red"
}

Write-Host ""
Write-Host "🚀 HyperCode-V2.4 Docker Ecosystem Starter" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

function Write-Info { Write-Host "✓ $args" -ForegroundColor $Colors.Success }
function Write-Warn { Write-Host "⚠ $args" -ForegroundColor $Colors.Warning }
function Write-Err { Write-Host "✗ $args" -ForegroundColor $Colors.Error; exit 1 }

# Validate Docker
try {
    $DockerVersion = (docker --version)
    Write-Info $DockerVersion
} catch {
    Write-Err "Docker not found. Please install Docker Desktop 27+."
}

try {
    $ComposeVersion = (docker compose version --short)
    Write-Info "Docker Compose $ComposeVersion"
} catch {
    Write-Err "Docker Compose not found. Please install Docker Desktop 27+."
}

Write-Host ""

# Create networks
function Create-Networks {
    Write-Info "Creating docker networks..."
    @("hypercode_backend_net", "hypercode_data_net", "hypercode_agents_net", "hypercode_obs_net", "hypercode_frontend_net") | ForEach-Object {
        try {
            docker network create $_  2>&1 | Out-Null
        } catch {
            Write-Warn "$_ already exists"
        }
    }
    Write-Host ""
}

# Create data directories
function Create-DataDirs {
    Write-Info "Creating data directories at $HC_DATA_ROOT..."
    @("redis", "postgres", "ollama", "prometheus", "grafana", "loki", "tempo", "chroma", "alertmanager", "trivy") | ForEach-Object {
        $Path = Join-Path $HC_DATA_ROOT $_
        if (-not (Test-Path $Path)) {
            New-Item -ItemType Directory -Path $Path -Force | Out-Null
        }
    }
    Write-Host ""
}

# Check .env file
function Check-Env {
    $EnvPath = ".\HyperCode-V2.4\.env"
    $EnvExamplePath = ".\HyperCode-V2.4\.env.example"
    
    if (-not (Test-Path $EnvPath)) {
        Write-Warn ".env file not found. Copying from .env.example..."
        if (Test-Path $EnvExamplePath) {
            Copy-Item $EnvExamplePath $EnvPath
            Write-Warn "Please edit $EnvPath with your secrets (Stripe, GitHub, API keys)"
        } else {
            Write-Err ".env.example not found!"
        }
    }
}

# Start core services
function Start-Core {
    Write-Info "Starting core services (redis, postgres, hypercode-core, ollama, celery)..."
    Push-Location .\HyperCode-V2.4
    docker compose -f docker-compose.core.yml up -d --pull always
    Pop-Location
    
    Write-Info "Waiting for services to be healthy (60s)..."
    Start-Sleep -Seconds 30
    
    $HealthChecks = @(
        @{ Name = "Redis"; Cmd = 'docker compose -f .\HyperCode-V2.4\docker-compose.core.yml exec redis redis-cli ping' },
        @{ Name = "PostgreSQL"; Cmd = 'docker compose -f .\HyperCode-V2.4\docker-compose.core.yml exec postgres pg_isready' }
    )
    
    $HealthChecks | ForEach-Object {
        try {
            Invoke-Expression $_.Cmd | Out-Null
            Write-Info "$($_.Name) is healthy"
        } catch {
            Write-Warn "$($_.Name) not ready yet"
        }
    }
    
    Start-Sleep -Seconds 30
    
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
        Write-Info "HyperCode-Core is healthy → http://localhost:8000"
    } catch {
        Write-Warn "HyperCode-Core still starting... check logs: docker compose logs hypercode-core"
    }
    
    Write-Host ""
    Write-Info "Dashboard available at http://localhost:8088"
    Write-Host ""
}

# Start observability stack
function Start-Observability {
    Write-Info "Starting observability (prometheus, grafana, loki, tempo)..."
    Push-Location .\HyperCode-V2.4
    docker compose -f docker-compose.observability.yml up -d --pull always
    Pop-Location
    
    Start-Sleep -Seconds 10
    Write-Info "Prometheus → http://localhost:9090"
    Write-Info "Grafana → http://localhost:3001"
    Write-Info "Loki → http://localhost:3100"
    Write-Info "Tempo → http://localhost:3200"
    Write-Host ""
}

# Start agents
function Start-Agents {
    Write-Info "Starting agents (crew-orchestrator, coder, frontend-specialist, etc.)..."
    Push-Location .\HyperCode-V2.4
    docker compose --profile agents up -d --pull always
    Pop-Location
    
    Start-Sleep -Seconds 15
    Write-Info "Crew Orchestrator → http://localhost:8081"
    Write-Info "Coder Agent → http://localhost:8002"
    Write-Info "MCP Gateway → http://localhost:8820"
    Write-Host ""
}

# Start health monitoring
function Start-Health {
    Write-Info "Starting health monitoring (hyperhealth, security-scanner, auto-prune)..."
    Push-Location .\HyperCode-V2.4
    docker compose --profile health up -d --pull always
    Pop-Location
    
    Start-Sleep -Seconds 10
    Write-Info "HyperHealth API → http://localhost:8095"
    Write-Host ""
}

# Show status
function Show-Status {
    Write-Host ""
    Write-Info "Service Status:"
    Write-Host "==============="
    Push-Location .\HyperCode-V2.4
    docker compose ps --all
    Pop-Location
    Write-Host ""
}

# Show help
function Show-Help {
    Write-Host "Usage: .\hypercode-quickstart.ps1 -Command [core|agents|health|full|all|status|stop|help]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  core        Start only core services (redis, postgres, hypercode-core, ollama)"
    Write-Host "  agents      Start core + all agents (15+ AI agents)"
    Write-Host "  health      Start core + health monitoring (security scanner, auto-prune)"
    Write-Host "  full        Start core + observability + agents"
    Write-Host "  all         Start everything (core + obs + agents + health + mission)"
    Write-Host "  status      Show running services"
    Write-Host "  stop        Stop all services"
    Write-Host "  help        Show this message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\hypercode-quickstart.ps1 -Command core"
    Write-Host "  .\hypercode-quickstart.ps1 -Command full"
    Write-Host "  .\hypercode-quickstart.ps1 -Command all"
    Write-Host ""
}

# Execute
switch ($Command) {
    "core" {
        Create-Networks
        Create-DataDirs
        Check-Env
        Start-Core
        Show-Status
    }
    "agents" {
        Create-Networks
        Create-DataDirs
        Check-Env
        Start-Core
        Start-Agents
        Show-Status
    }
    "health" {
        Create-Networks
        Create-DataDirs
        Check-Env
        Start-Core
        Start-Health
        Show-Status
    }
    "full" {
        Create-Networks
        Create-DataDirs
        Check-Env
        Start-Core
        Start-Observability
        Start-Agents
        Show-Status
    }
    "all" {
        Create-Networks
        Create-DataDirs
        Check-Env
        Start-Core
        Start-Observability
        Start-Agents
        Start-Health
        Write-Info "Starting mission control..."
        Push-Location .\HyperCode-V2.4
        try {
            docker compose --profile mission up -d --pull always 2>&1 | Out-Null
        } catch {
            Write-Warn "Mission control skipped"
        }
        Pop-Location
        Show-Status
    }
    "status" {
        Push-Location .\HyperCode-V2.4
        docker compose ps --all
        Pop-Location
    }
    "stop" {
        Write-Info "Stopping all services..."
        Push-Location .\HyperCode-V2.4
        docker compose down
        Pop-Location
        Write-Info "Services stopped"
    }
    "help" {
        Show-Help
    }
    default {
        Write-Err "Unknown command: $Command"
    }
}

Write-Info "Done!"
