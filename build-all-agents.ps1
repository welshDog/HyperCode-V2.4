# Build all 12 ghost agents
$agents = @(
    @{ name = 'system-architect'; dir = 'agents/07-system-architect'; image = 'hypercode-v24-system-architect:latest' },
    @{ name = 'test-agent'; dir = 'agents/test-agent'; image = 'hypercode-v24-test-agent:latest' },
    @{ name = 'throttle-agent'; dir = 'agents/throttle-agent'; image = 'hypercode-v24-throttle-agent:latest' },
    @{ name = 'tips-tricks-writer'; dir = 'agents/09-tips-tricks-writer'; image = 'hypercode-v24-tips-tricks-writer:latest' },
    @{ name = 'super-hyper-broski-agent'; dir = 'agents/super-hyper-broski-agent'; image = 'hypercode-v24-super-hyper-broski-agent:latest' },
    @{ name = 'hyper-architect'; dir = 'agents/architect'; image = 'hypercode-v24-hyper-architect:latest' },
    @{ name = 'hyper-observer'; dir = 'agents/hyper-agents/hyper-observer'; image = 'hypercode-v24-hyper-observer:latest' },
    @{ name = 'hyper-worker'; dir = 'agents/hyper-agents/hyper-worker'; image = 'hypercode-v24-hyper-worker:latest' },
    @{ name = 'hyper-split-agent'; dir = 'agents/hyper-split-agent'; image = 'hypercode-v24-hyper-split-agent:latest' },
    @{ name = 'session-snapshot'; dir = 'agents/session-snapshot'; image = 'hypercode-v24-session-snapshot:latest' },
    @{ name = 'agent-x'; dir = 'agents/agent-x'; image = 'hypercode-v24-agent-x:latest' },
    @{ name = 'security-engineer'; dir = 'agents/06-security-engineer'; image = 'hypercode-v24-security-engineer:latest' }
)

Write-Host "Building 12 Ghost Agents..." -ForegroundColor Cyan
$existing = 0
$missing = @()

foreach ($agent in $agents) {
    $img = docker images $agent.image -q 2>$null
    if ($img) {
        $existing++
        Write-Host "O $($agent.name)" -ForegroundColor Green
    }
    else {
        $missing += $agent
        Write-Host "X $($agent.name)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Status: $existing existing, $($missing.Count) to build"
Write-Host ""

if ($missing.Count -eq 0) {
    Write-Host "All agents ready!" -ForegroundColor Green
}
else {
    Write-Host "Building agents..." -ForegroundColor Cyan
    foreach ($agent in $missing) {
        $dockerfile = "$($agent.dir)/Dockerfile"
        if (Test-Path $dockerfile) {
            Write-Host "Building $($agent.name)..." -ForegroundColor Yellow
            docker build -t $agent.image -f $dockerfile . 2>&1 | Out-Null
        }
    }
    Write-Host "Build started!" -ForegroundColor Cyan
}
