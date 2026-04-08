# 🚀 HyperCode V2.0 Automated Startup & Healing Script
# Neurodivergent-friendly: Clear output, color-coded, automated.

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message, [string]$Color = "Cyan")
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor $Color
}

Write-Log "🦅 HYPERCODE V2.0 AUTO-START SEQUENCE INITIATED" "Green"

# 1. Docker Daemon Check
Write-Log "1. Checking Docker Daemon..." "Yellow"
if (!(docker info)) {
    Write-Log "❌ Docker is not running! Please start Docker Desktop." "Red"
    exit 1
}
Write-Log "✅ Docker is online." "Green"

# 2. Ensure required external networks exist
Write-Log "2. Ensuring required Docker networks exist..." "Yellow"
$requiredNetworks = @("hypercode_public_net", "hypercode_data_net", "hypercode-v20_hypercode-net")
foreach ($netName in $requiredNetworks) {
    $net = docker network ls --format "{{.Name}}" | Where-Object { $_ -eq $netName }
    if (-not $net) {
        Write-Log "Creating network: $netName" "Cyan"
        docker network create $netName | Out-Null
        Write-Log "✅ Network '$netName' created." "Green"
    } else {
        Write-Log "✅ Network '$netName' exists." "Green"
    }
}

# 3. Cleanup Phase (The "Janitor" Logic)
Write-Log "3. Cleaning up Zombie Containers..." "Yellow"
# Remove only HyperCode specific stopped containers to avoid killing other work
$zombies = docker ps -a --filter "status=exited" --filter "name=hypercode" -q
if ($zombies) {
    docker rm $zombies
    Write-Log "🧹 Removed $(($zombies).Count) zombie containers." "Green"
} else {
    Write-Log "✨ No zombies found." "Green"
}

# 4. Build & Start Sequence
Write-Log "4. Building and Starting Services..." "Yellow"
# We use --remove-orphans to clean up old service definitions
# We use --build to ensure new agents (Tips Architect) are compiled
docker compose up -d --build --remove-orphans

if ($LASTEXITCODE -ne 0) {
    Write-Log "❌ Docker Compose failed! Check logs." "Red"
    exit 1
}

# 5. Health Check Loop (The "Healer" Logic)
Write-Log "5. Waiting for System Health (Timeout: 60s)..." "Yellow"
$critical_services = @("hypercode-core", "redis", "postgres", "healer-agent", "tips-tricks-writer")
$max_retries = 12 # 12 * 5s = 60s
$retry = 0

while ($retry -lt $max_retries) {
    $healthy_count = 0
    foreach ($svc in $critical_services) {
        # Check if container is running
        $status = docker inspect --format='{{.State.Status}}' $svc 2>$null
        
        if ($status -eq "running") {
            # Check internal health if available
            $health = docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no_check{{end}}' $svc 2>$null
            if ($health -eq "healthy" -or $health -eq "no_check") {
                $healthy_count++
            }
        }
    }

    if ($healthy_count -eq $critical_services.Count) {
        Write-Log "✅ All critical services are RUNNING and HEALTHY!" "Green"
        break
    }

    Write-Log "⏳ Waiting for services... ($healthy_count/$($critical_services.Count) ready)" "Cyan"
    Start-Sleep -Seconds 5
    $retry++
}

if ($retry -eq $max_retries) {
    Write-Log "⚠️ Timeout reached. Some services may be unhealthy. Checking details..." "Red"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.State}}"
}

# 6. Network & Volume Verification
Write-Log "6. Verifying Network & Volumes..." "Yellow"
$net = docker network ls --filter "name=hypercode_public_net" -q
if ($net) {
    Write-Log "✅ Network 'hypercode_public_net' is active." "Green"
} else {
    Write-Log "❌ Network missing!" "Red"
}

Write-Log "🦅 MISSION CONTROL READY: http://localhost:8088" "Green"
Write-Log "👁️ OBSERVABILITY READY: http://localhost:3001" "Green"
Write-Log "🧠 CORE API READY: http://localhost:8000" "Green"
