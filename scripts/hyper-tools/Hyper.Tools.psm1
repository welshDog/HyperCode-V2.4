# Hyper.Tools.psm1
# AI-callable PowerShell module for HyperCode-V2.4
# Usage: Import-Module .\Hyper.Tools.psm1

$script:Config = @{
    DashboardUrl  = "http://127.0.0.1:8088"
    CoreUrl       = "http://127.0.0.1:8000"
    NemoclawUrl   = "http://localhost:8099"
    McpUrl        = "http://localhost:8823"
    LogPath       = "C:\bro-logs"
    SecretsFile   = "$env:USERPROFILE\.bro\secrets.json"
}

function Get-HyperConfig {
    <#
    .SYNOPSIS Returns the current Hyper.Tools config
    #>
    return $script:Config
}

function Get-HyperSecrets {
    <#
    .SYNOPSIS Loads secrets from ~/.bro/secrets.json
    #>
    if (Test-Path $script:Config.SecretsFile) {
        return Get-Content $script:Config.SecretsFile | ConvertFrom-Json
    }
    Write-Warning "No secrets file at $($script:Config.SecretsFile) — run Setup-HyperSecrets.ps1"
    return $null
}

function Get-HyperContainerHealth {
    <#
    .SYNOPSIS AI-callable: Returns health of all Docker containers as objects
    .DESCRIPTION Lists all containers, flags unhealthy/exited ones
    #>
    param([switch]$UnhealthyOnly)

    $raw = docker ps -a --format "{{json .}}" 2>$null |
           ForEach-Object { $_ | ConvertFrom-Json }

    $results = $raw | ForEach-Object {
        [PSCustomObject]@{
            Name    = $_.Names
            Status  = $_.Status
            Image   = $_.Image
            Ports   = $_.Ports
            Healthy = $_.Status -match "healthy" -and $_.Status -notmatch "unhealthy"
        }
    }

    if ($UnhealthyOnly) {
        return $results | Where-Object { -not $_.Healthy }
    }
    return $results
}

function Restart-HyperContainer {
    <#
    .SYNOPSIS AI-callable: Restart a named Docker container
    #>
    param([Parameter(Mandatory)][string]$Name)
    Write-Host "Restarting: $Name" -ForegroundColor Yellow
    docker restart $Name
    Write-Host "Done" -ForegroundColor Green
}

function Get-HyperAgentStatus {
    <#
    .SYNOPSIS AI-callable: Poll /api/v1/agents/status from HyperCode dashboard
    #>
    try {
        $response = Invoke-RestMethod -Uri "$($script:Config.DashboardUrl)/api/v1/agents/status" -Method Get -TimeoutSec 5
        return $response
    } catch {
        Write-Warning "Dashboard unreachable: $_"
        return $null
    }
}

function Get-HyperNemoclawHealth {
    <#
    .SYNOPSIS AI-callable: Check NemoClaw agent health endpoint
    #>
    try {
        $response = Invoke-RestMethod -Uri "$($script:Config.NemoclawUrl)/health" -Method Get -TimeoutSec 5
        return $response
    } catch {
        Write-Warning "NemoClaw unreachable: $_"
        return $null
    }
}

function Get-HyperProcessHealth {
    <#
    .SYNOPSIS AI-callable: Top processes by CPU usage
    #>
    param(
        [int]$Top = 10,
        [double]$MinCPU = 0
    )

    return Get-Process |
        Where-Object { $_.CPU -gt $MinCPU } |
        Sort-Object CPU -Descending |
        Select-Object -First $Top |
        Select-Object Name, Id,
            @{Name="CPU_s";  Expression={ [math]::Round($_.CPU, 2) }},
            @{Name="RAM_MB"; Expression={ [math]::Round($_.WorkingSet / 1MB, 1) }}
}

function Get-HyperLogHits {
    <#
    .SYNOPSIS AI-callable: Scan log folder for error keywords
    #>
    param(
        [string]$LogPath = $script:Config.LogPath,
        [string[]]$Keywords = @("ERROR", "FATAL", "Exception"),
        [int]$Tail = 200
    )

    $pattern = $Keywords -join "|"
    $files   = Get-ChildItem -Path $LogPath -Filter "*.log" -Recurse -ErrorAction SilentlyContinue
    $hits    = @()

    foreach ($f in $files) {
        $lines = if ($Tail -gt 0) { Get-Content $f.FullName -Tail $Tail } else { Get-Content $f.FullName }
        $lines | Select-String -Pattern $pattern | ForEach-Object {
            $hits += [PSCustomObject]@{
                File    = $f.Name
                Line    = $_.LineNumber
                Message = $_.Line.Trim()
            }
        }
    }
    return $hits
}

function Send-HyperDiscordAlert {
    <#
    .SYNOPSIS AI-callable: Post a message to your Discord webhook
    #>
    param(
        [Parameter(Mandatory)][string]$Message,
        [string]$Username = "BRO-Watcher",
        [string]$WebhookUrl = ""
    )

    if (-not $WebhookUrl) {
        $secrets = Get-HyperSecrets
        $WebhookUrl = $secrets?.discord_webhook
    }

    if (-not $WebhookUrl) {
        Write-Warning "No Discord webhook URL. Run Setup-HyperSecrets.ps1"
        return
    }

    $body = @{ username = $Username; content = $Message } | ConvertTo-Json
    Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $body -ContentType "application/json"
    Write-Host "Discord alert sent!" -ForegroundColor Green
}

function Invoke-HyperHealthCheck {
    <#
    .SYNOPSIS AI-callable: Full system health snapshot
    .DESCRIPTION Checks containers, agents, NemoClaw, and top CPU processes
    #>
    Write-Host "`nHYPER HEALTH CHECK -- $(Get-Date -Format 'HH:mm:ss')`n" -ForegroundColor Cyan

    Write-Host "Container Health:" -ForegroundColor White
    $unhealthy = Get-HyperContainerHealth -UnhealthyOnly
    if ($unhealthy.Count -eq 0) {
        Write-Host "  All containers healthy" -ForegroundColor Green
    } else {
        $unhealthy | Format-Table -AutoSize
    }

    Write-Host "`nAgent Status:" -ForegroundColor White
    $agents = Get-HyperAgentStatus
    if ($agents) { $agents | Format-Table -AutoSize } else { Write-Host "  Unreachable" -ForegroundColor Yellow }

    Write-Host "`nNemoClaw:" -ForegroundColor White
    $nemo = Get-HyperNemoclawHealth
    if ($nemo) {
        Write-Host "  OK: $($nemo | ConvertTo-Json -Compress)" -ForegroundColor Green
    } else {
        Write-Host "  Unreachable" -ForegroundColor Yellow
    }

    Write-Host "`nTop 5 CPU Hogs:" -ForegroundColor White
    Get-HyperProcessHealth -Top 5 | Format-Table -AutoSize

    Write-Host "`nHealth check complete.`n" -ForegroundColor Yellow
}

Export-ModuleMember -Function *-Hyper*, Invoke-HyperHealthCheck
