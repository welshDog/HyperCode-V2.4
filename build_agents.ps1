# List of 12 ghost agents to build
$agents = @(
    'system-architect',
    'test-agent', 
    'throttle-agent',
    'tips-tricks-writer',
    'super-hyper-broski-agent',
    'hyper-architect',
    'hyper-observer',
    'hyper-worker',
    'hyper-split-agent',
    'session-snapshot',
    'agent-x',
    'security-engineer'
)

foreach ($agent in $agents) {
    Write-Host "Building $agent..." -ForegroundColor Cyan
    docker images "hypercode-v24-${agent}:latest" | Write-Host
}
