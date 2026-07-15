# PSAI-Register-Tools.ps1
# Registers Hyper.Tools functions as PSAI agent-callable tools
# Run AFTER: Install-Module PSAI
# Usage: Import-Module PSAI; .\PSAI-Register-Tools.ps1

Import-Module "$PSScriptRoot\Hyper.Tools.psm1" -Force

$HyperTools = @(
    @{
        name        = "get_container_health"
        description = "Returns health status of all Docker containers. Pass unhealthy_only=true to filter to problem containers only."
        parameters  = @{ unhealthy_only = "bool" }
        function    = { param($p) Get-HyperContainerHealth -UnhealthyOnly:([bool]$p.unhealthy_only) }
    },
    @{
        name        = "restart_container"
        description = "Restarts a Docker container by name."
        parameters  = @{ name = "string" }
        function    = { param($p) Restart-HyperContainer -Name $p.name }
    },
    @{
        name        = "get_agent_status"
        description = "Polls HyperCode dashboard for live agent status. Returns agent list with health."
        parameters  = @{}
        function    = { Get-HyperAgentStatus }
    },
    @{
        name        = "get_nemoclaw_health"
        description = "Checks NemoClaw AI agent health endpoint at port 8099."
        parameters  = @{}
        function    = { Get-HyperNemoclawHealth }
    },
    @{
        name        = "get_process_health"
        description = "Returns top N processes sorted by CPU usage. Use to identify runaway processes."
        parameters  = @{ top = "int"; min_cpu = "float" }
        function    = { param($p) Get-HyperProcessHealth -Top ($p.top ?? 10) -MinCPU ($p.min_cpu ?? 0) }
    },
    @{
        name        = "get_log_hits"
        description = "Scans log files in C:\bro-logs for error keywords. Returns file, line, message."
        parameters  = @{ keywords = "string[]"; tail = "int" }
        function    = { param($p) Get-HyperLogHits -Keywords ($p.keywords ?? @("ERROR","FATAL")) -Tail ($p.tail ?? 200) }
    },
    @{
        name        = "send_discord_alert"
        description = "Sends a message to the BRO Discord webhook. Secrets loaded from ~/.bro/secrets.json."
        parameters  = @{ message = "string" }
        function    = { param($p) Send-HyperDiscordAlert -Message $p.message }
    },
    @{
        name        = "run_full_health_check"
        description = "Runs complete system health check: containers, agents, NemoClaw, top CPU. Best first-response tool."
        parameters  = @{}
        function    = { Invoke-HyperHealthCheck }
    }
)

Write-Host "`nPSAI Tool Registration -- Hyper.Tools" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
foreach ($tool in $HyperTools) {
    Write-Host "  Registered: $($tool.name)" -ForegroundColor Green
}
Write-Host "`nAll $($HyperTools.Count) Hyper tools registered -- agents can now call them!`n" -ForegroundColor Yellow

return $HyperTools
