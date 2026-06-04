# ============================================================
# 🔧 Lyndz MCP Server — DevOps + Supabase + Grafana + BROski$
# ============================================================
# Sacred Rules:
#   - docker-ce-cli ONLY (never docker.io)
#   - .env vars NEVER committed
#   - Python indent: 4 spaces (not relevant here but noted)
#   - Redis DB1=cache, DB2=rate limits
# ============================================================

Import-Module pwsh.mcp -Force -ErrorAction Stop

# ============================================================
# SECTION 1 — DEVOPS TOOLS
# ============================================================

function get_docker_status {
    <#
    .SYNOPSIS
        Returns the status of all running Docker containers.
    .DESCRIPTION
        Lists all Docker containers with their name, state, and port mappings.
        Use this to check if services are healthy or stopped.
    .EXAMPLE
        get_docker_status
    #>
    [CmdletBinding()]
    param()

    try {
        $containers = docker ps -a --format "{{json .}}" |
            ForEach-Object { $_ | ConvertFrom-Json }

        if (-not $containers) { return "No containers found." }

        $containers | ForEach-Object {
            [PSCustomObject]@{
                Name   = $_.Names
                Status = $_.Status
                Ports  = $_.Ports
                Image  = $_.Image
            }
        } | ConvertTo-Json
    } catch {
        return "Docker error: $_"
    }
}

function get_log_tail {
    <#
    .SYNOPSIS
        Returns the last N lines from a log file.
    .DESCRIPTION
        Tails a specified log file. Useful for reviewing recent errors or events.
    .EXAMPLE
        get_log_tail -LogPath "C:/logs/app.log" -Lines 50
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true, HelpMessage = "Full path to the log file")]
        [ValidateScript({ Test-Path $_ })]
        [string]$LogPath,

        [Parameter(Mandatory = $false, HelpMessage = "Number of lines to return (default 30)")]
        [ValidateRange(1, 500)]
        [int]$Lines = 30
    )

    try {
        Get-Content -Path $LogPath -Tail $Lines | Out-String
    } catch {
        return "Error reading log: $_"
    }
}

function test_endpoint_health {
    <#
    .SYNOPSIS
        Sends an HTTP GET to a URL and reports its status.
    .DESCRIPTION
        Useful for checking if a web service, API, or deployment is alive.
        Returns status code and response time.
    .EXAMPLE
        test_endpoint_health -Url "https://myapp.vercel.app/health"
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true, HelpMessage = "URL to test")]
        [string]$Url
    )

    try {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        $response  = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        $stopwatch.Stop()

        [PSCustomObject]@{
            Url          = $Url
            StatusCode   = $response.StatusCode
            ResponseTime = "$($stopwatch.ElapsedMilliseconds)ms"
            Status       = "OK"
        } | ConvertTo-Json
    } catch {
        return "Endpoint unreachable: $_"
    }
}

function get_git_status {
    <#
    .SYNOPSIS
        Returns the current git status of a repository.
    .DESCRIPTION
        Shows branch name, uncommitted changes, and last 5 commits.
    .EXAMPLE
        get_git_status -RepoPath "C:/projects/my-app"
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $false, HelpMessage = "Path to the git repo (defaults to current dir)")]
        [string]$RepoPath = (Get-Location).Path
    )

    try {
        Push-Location $RepoPath
        $branch  = git rev-parse --abbrev-ref HEAD
        $status  = git status --short
        $commits = git log --oneline -5

        [PSCustomObject]@{
            Branch          = $branch
            UncommitedFiles = $status
            RecentCommits   = $commits
        } | ConvertTo-Json
    } catch {
        return "Git error: $_"
    } finally {
        Pop-Location
    }
}

function get_system_resources {
    <#
    .SYNOPSIS
        Returns CPU and memory usage of the local system.
    .DESCRIPTION
        Useful for checking if the machine is under load during deploys or tests.
    .EXAMPLE
        get_system_resources
    #>
    [CmdletBinding()]
    param()

    $cpu = (Get-CimInstance Win32_Processor).LoadPercentage
    $os  = Get-CimInstance Win32_OperatingSystem

    $totalRAM = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    $freeRAM  = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
    $usedRAM  = [math]::Round($totalRAM - $freeRAM, 2)

    [PSCustomObject]@{
        CPU_Percent  = "$cpu%"
        RAM_Total_GB = $totalRAM
        RAM_Used_GB  = $usedRAM
        RAM_Free_GB  = $freeRAM
    } | ConvertTo-Json
}

function list_directory {
    <#
    .SYNOPSIS
        Lists files in a directory with name, size, and modified date.
    .DESCRIPTION
        Returns a structured list of files. Useful for exploring project folders.
    .EXAMPLE
        list_directory -Path "C:/projects/hyperfocus"
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $false, HelpMessage = "Directory path to list")]
        [string]$Path = (Get-Location).Path,

        [Parameter(Mandatory = $false, HelpMessage = "Include subdirectories")]
        [switch]$Recurse
    )

    Get-ChildItem -Path $Path -Recurse:$Recurse |
        Select-Object Name,
                      @{ Name = "SizeKB"; Expression = { [math]::Round($_.Length / 1KB, 1) } },
                      LastWriteTime,
                      FullName |
        ConvertTo-Json
}

# ============================================================
# SECTION 2 — SUPABASE TOOLS
# ============================================================
# Set env vars in session — NEVER hardcode keys here
# $env:SUPABASE_URL = "https://yhtmuibgdnxhbgboajhc.supabase.co"
# $env:SUPABASE_KEY = "your-service-role-key"

function query_supabase_table {
    <#
    .SYNOPSIS
        Query any Supabase table via the REST API and return results.
    .DESCRIPTION
        Runs a SELECT against a named table. Supports optional PostgREST filters.
        Uses the Supabase REST API with service role key.
    .EXAMPLE
        query_supabase_table -Table "payments" -Filter "status=eq.pending" -Limit 20
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true, HelpMessage = "Table name to query")]
        [string]$Table,

        [Parameter(Mandatory = $false, HelpMessage = "PostgREST filter e.g. status=eq.pending")]
        [string]$Filter = "",

        [Parameter(Mandatory = $false, HelpMessage = "Max rows to return")]
        [ValidateRange(1, 100)]
        [int]$Limit = 20,

        [Parameter(Mandatory = $false, HelpMessage = "Order by column e.g. created_at.desc")]
        [string]$OrderBy = "created_at.desc"
    )

    $url = $env:SUPABASE_URL
    $key = $env:SUPABASE_KEY

    if (-not $url -or -not $key) {
        return "ERROR: SUPABASE_URL or SUPABASE_KEY env var not set."
    }

    $endpoint = "$url/rest/v1/$Table?limit=$Limit&order=$OrderBy"
    if ($Filter) { $endpoint += "&$Filter" }

    try {
        $headers = @{
            "apikey"        = $key
            "Authorization" = "Bearer $key"
            "Content-Type"  = "application/json"
        }
        $response = Invoke-RestMethod -Uri $endpoint -Headers $headers -Method GET
        $response | ConvertTo-Json -Depth 5
    } catch {
        return "Supabase query error: $_"
    }
}

function get_supabase_table_list {
    <#
    .SYNOPSIS
        Lists all tables in the Supabase public schema.
    .DESCRIPTION
        Queries information_schema to return table names.
        Great for a quick DB overview.
    .EXAMPLE
        get_supabase_table_list
    #>
    [CmdletBinding()]
    param()

    $url = $env:SUPABASE_URL
    $key = $env:SUPABASE_KEY

    if (-not $url -or -not $key) {
        return "ERROR: SUPABASE_URL or SUPABASE_KEY env var not set."
    }

    $headers = @{
        "apikey"        = $key
        "Authorization" = "Bearer $key"
        "Content-Type"  = "application/json"
    }

    try {
        $endpoint = "$url/rest/v1/information_schema.tables?table_schema=eq.public&select=table_name"
        $response = Invoke-RestMethod -Uri $endpoint -Headers $headers -Method GET
        $response | ConvertTo-Json
    } catch {
        return "Could not list tables: $_"
    }
}

function check_supabase_recent_payments {
    <#
    .SYNOPSIS
        Returns the last N payment records from Supabase.
    .DESCRIPTION
        Queries the payments table ordered by created_at descending.
        Use this to verify the Stripe webhook DB flow is working.
    .EXAMPLE
        check_supabase_recent_payments -Limit 10
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $false, HelpMessage = "How many records to return")]
        [ValidateRange(1, 50)]
        [int]$Limit = 10
    )

    $url = $env:SUPABASE_URL
    $key = $env:SUPABASE_KEY

    if (-not $url -or -not $key) {
        return "ERROR: SUPABASE_URL or SUPABASE_KEY not set."
    }

    $endpoint = "$url/rest/v1/payments?limit=$Limit&order=created_at.desc"
    $headers  = @{
        "apikey"        = $key
        "Authorization" = "Bearer $key"
    }

    try {
        $rows = Invoke-RestMethod -Uri $endpoint -Headers $headers -Method GET
        if (-not $rows) { return "No payment records found." }
        $rows | ConvertTo-Json -Depth 4
    } catch {
        return "Payment query error: $_"
    }
}

function get_supabase_auth_stats {
    <#
    .SYNOPSIS
        Returns recent user signup counts from Supabase Auth.
    .DESCRIPTION
        Queries auth users for recent signups. Useful for monitoring
        course enrollment growth.
    .EXAMPLE
        get_supabase_auth_stats -Days 7
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $false, HelpMessage = "Days to look back")]
        [int]$Days = 7
    )

    $url = $env:SUPABASE_URL
    $key = $env:SUPABASE_KEY

    if (-not $url -or -not $key) {
        return "ERROR: SUPABASE_URL or SUPABASE_KEY not set."
    }

    $since    = (Get-Date).AddDays(-$Days).ToString("yyyy-MM-ddTHH:mm:ssZ")
    $endpoint = "$url/rest/v1/users?created_at=gte.$since&select=id,email,created_at"
    $headers  = @{
        "apikey"        = $key
        "Authorization" = "Bearer $key"
    }

    try {
        $response = Invoke-RestMethod -Uri $endpoint -Headers $headers -Method GET
        [PSCustomObject]@{
            PeriodDays = $Days
            NewSignups = ($response | Measure-Object).Count
            Users      = $response | Select-Object -First 10
        } | ConvertTo-Json -Depth 4
    } catch {
        return "Auth stats error: $_"
    }
}

# ============================================================
# SECTION 3 — GRAFANA / OBSERVABILITY TOOLS
# ============================================================
# $env:GRAFANA_URL    = "http://127.0.0.1:3001"
# $env:GRAFANA_TOKEN  = "your-grafana-sa-token"
# $env:PROMETHEUS_URL = "http://127.0.0.1:9090"
# $env:LOKI_URL       = "http://127.0.0.1:3100"

function get_grafana_alerts {
    <#
    .SYNOPSIS
        Returns all current Grafana alert states (firing, pending, normal).
    .DESCRIPTION
        Hits the Grafana Alertmanager API to list active alerts.
        Use this to check if any services are in a firing state.
    .EXAMPLE
        get_grafana_alerts -StateFilter "firing"
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $false, HelpMessage = "Filter: firing, pending, normal, all")]
        [ValidateSet("firing", "pending", "normal", "all")]
        [string]$StateFilter = "all"
    )

    $grafanaUrl   = $env:GRAFANA_URL   ?? "http://127.0.0.1:3001"
    $grafanaToken = $env:GRAFANA_TOKEN

    $headers = @{ "Content-Type" = "application/json" }
    if ($grafanaToken) { $headers["Authorization"] = "Bearer $grafanaToken" }

    try {
        $alerts = Invoke-RestMethod -Uri "$grafanaUrl/api/alertmanager/grafana/api/v2/alerts" -Headers $headers -Method GET

        if ($StateFilter -ne "all") {
            $alerts = $alerts | Where-Object { $_.status.state -eq $StateFilter }
        }

        if (-not $alerts) { return "No alerts in state: $StateFilter" }

        $alerts | ForEach-Object {
            [PSCustomObject]@{
                Name     = $_.labels.alertname
                State    = $_.status.state
                Severity = $_.labels.severity
                Summary  = $_.annotations.summary
                StartsAt = $_.startsAt
            }
        } | ConvertTo-Json -Depth 4
    } catch {
        return "Grafana alerts error: $_"
    }
}

function get_grafana_datasource_health {
    <#
    .SYNOPSIS
        Checks the health of all Grafana datasources (Prometheus, Loki, Tempo).
    .DESCRIPTION
        Queries the Grafana API for all datasources and tests connectivity.
        Returns name, type, and health status for each.
    .EXAMPLE
        get_grafana_datasource_health
    #>
    [CmdletBinding()]
    param()

    $grafanaUrl   = $env:GRAFANA_URL   ?? "http://127.0.0.1:3001"
    $grafanaToken = $env:GRAFANA_TOKEN

    $headers = @{ "Content-Type" = "application/json" }
    if ($grafanaToken) { $headers["Authorization"] = "Bearer $grafanaToken" }

    try {
        $datasources = Invoke-RestMethod -Uri "$grafanaUrl/api/datasources" -Headers $headers -Method GET

        $results = foreach ($ds in $datasources) {
            try {
                $health = Invoke-RestMethod -Uri "$grafanaUrl/api/datasources/$($ds.id)/health" -Headers $headers -Method GET
                [PSCustomObject]@{
                    Name    = $ds.name
                    Type    = $ds.type
                    Status  = $health.status
                    Message = $health.message
                }
            } catch {
                [PSCustomObject]@{
                    Name    = $ds.name
                    Type    = $ds.type
                    Status  = "ERROR"
                    Message = "$_"
                }
            }
        }

        $results | ConvertTo-Json -Depth 3
    } catch {
        return "Grafana datasource error: $_"
    }
}

function query_prometheus_metric {
    <#
    .SYNOPSIS
        Runs an instant PromQL query and returns the result.
    .DESCRIPTION
        Hits the Prometheus API on port 9090. Use this to check
        CPU, memory, container stats, or any custom metric.
    .EXAMPLE
        query_prometheus_metric -Query "rate(http_requests_total[5m])"
    .EXAMPLE
        query_prometheus_metric -Query "container_memory_usage_bytes{name='hypercode-core'}"
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true, HelpMessage = "PromQL query string")]
        [string]$Query
    )

    $prometheusUrl = $env:PROMETHEUS_URL ?? "http://127.0.0.1:9090"

    try {
        $encoded  = [Uri]::EscapeDataString($Query)
        $endpoint = "$prometheusUrl/api/v1/query?query=$encoded"
        $response = Invoke-RestMethod -Uri $endpoint -Method GET

        if ($response.status -ne "success") {
            return "Prometheus query failed: $($response.error)"
        }

        $response.data.result | ForEach-Object {
            [PSCustomObject]@{
                Metric = $_.metric
                Value  = $_.value[1]
                Time   = [DateTimeOffset]::FromUnixTimeSeconds($_.value[0]).ToString("yyyy-MM-dd HH:mm:ss")
            }
        } | ConvertTo-Json -Depth 4
    } catch {
        return "Prometheus error: $_"
    }
}

function get_loki_recent_logs {
    <#
    .SYNOPSIS
        Fetches recent log lines from Loki for a given service label.
    .DESCRIPTION
        Queries Loki on port 3100 using LogQL. Returns last N log lines
        for a named container or service.
    .EXAMPLE
        get_loki_recent_logs -Service "hypercode-core" -Lines 50
    .EXAMPLE
        get_loki_recent_logs -Service "broski-bot" -Lines 30
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true, HelpMessage = "Service/container name label")]
        [string]$Service,

        [Parameter(Mandatory = $false, HelpMessage = "Number of log lines to return")]
        [ValidateRange(1, 200)]
        [int]$Lines = 30
    )

    $lokiUrl = $env:LOKI_URL ?? "http://127.0.0.1:3100"

    try {
        $query    = [Uri]::EscapeDataString("{container_name=`"$Service`"}")
        $start    = [DateTimeOffset]::UtcNow.AddHours(-1).ToUnixTimeSeconds() * 1000000000
        $end      = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() * 1000000000
        $endpoint = "$lokiUrl/loki/api/v1/query_range?query=$query&start=$start&end=$end&limit=$Lines&direction=backward"

        $response = Invoke-RestMethod -Uri $endpoint -Method GET

        if (-not $response.data.result) {
            return "No logs found for service: $Service"
        }

        $logs = $response.data.result[0].values |
            ForEach-Object {
                $ts = [DateTimeOffset]::FromUnixTimeMilliseconds($_[0] / 1000000).ToString("HH:mm:ss")
                "[$ts] $_[1]"
            }

        $logs -join "`n"
    } catch {
        return "Loki query error: $_"
    }
}

# ============================================================
# SECTION 4 — BROski$ TOKEN ECONOMY TOOLS
# ============================================================
# Reads from Supabase views + RPC functions created by migration:
#   broski_token_balances    view
#   broski_leaderboard       view
#   broski_economy_snapshot  view
#   get_broski_balance()     DB function
#   get_broski_tx_history()  DB function
# ============================================================

function get_broski_balance {
    <#
    .SYNOPSIS
        Returns the BROski$ token balance for a Discord user.
    .DESCRIPTION
        Calls the Supabase RPC function get_broski_balance which reads
        users.broski_tokens + member_state.coins and returns a unified wallet.
        Also returns level, streak, and last_active.
    .EXAMPLE
        get_broski_balance -DiscordId "123456789012345678"
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true, HelpMessage = "Discord snowflake ID")]
        [string]$DiscordId
    )

    $url = $env:SUPABASE_URL
    $key = $env:SUPABASE_KEY
    if (-not $url -or -not $key) { return "ERROR: Supabase env vars not set." }

    $headers = @{
        "apikey"        = $key
        "Authorization" = "Bearer $key"
        "Content-Type"  = "application/json"
    }

    try {
        $body     = @{ p_discord_id = $DiscordId } | ConvertTo-Json
        $endpoint = "$url/rest/v1/rpc/get_broski_balance"
        $result   = Invoke-RestMethod -Uri $endpoint -Headers $headers -Method POST -Body $body

        if (-not $result) { return "No wallet found for Discord ID: $DiscordId" }
        $result | ConvertTo-Json -Depth 3
    } catch {
        return "Balance lookup error: $_"
    }
}

function get_broski_leaderboard {
    <#
    .SYNOPSIS
        Returns the top BROski$ holders ranked by total balance.
    .DESCRIPTION
        Queries the broski_leaderboard view (rank, display_name, web2_balance,
        economy_coins, total_broski, subscription_tier).
    .EXAMPLE
        get_broski_leaderboard -TopN 10
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $false, HelpMessage = "How many top users to return")]
        [ValidateRange(1, 50)]
        [int]$TopN = 10
    )

    $url = $env:SUPABASE_URL
    $key = $env:SUPABASE_KEY
    if (-not $url -or -not $key) { return "ERROR: Supabase env vars not set." }

    $headers = @{
        "apikey"        = $key
        "Authorization" = "Bearer $key"
    }

    try {
        $endpoint = "$url/rest/v1/broski_leaderboard?limit=$TopN"
        $rows     = Invoke-RestMethod -Uri $endpoint -Headers $headers -Method GET
        if (-not $rows) { return "No leaderboard data found." }
        $rows | ConvertTo-Json -Depth 3
    } catch {
        return "Leaderboard error: $_"
    }
}

function get_broski_tx_history {
    <#
    .SYNOPSIS
        Returns unified BROski$ transaction history for a Discord user.
    .DESCRIPTION
        Calls the Supabase RPC function get_broski_tx_history which merges
        token_transactions (Web2) + broski_transactions (Discord bot).
        Returns source, amount, reason, and created_at for each tx.
    .EXAMPLE
        get_broski_tx_history -DiscordId "123456789012345678" -Limit 20
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true, HelpMessage = "Discord snowflake ID")]
        [string]$DiscordId,

        [Parameter(Mandatory = $false, HelpMessage = "Max transactions to return")]
        [ValidateRange(1, 100)]
        [int]$Limit = 20
    )

    $url = $env:SUPABASE_URL
    $key = $env:SUPABASE_KEY
    if (-not $url -or -not $key) { return "ERROR: Supabase env vars not set." }

    $headers = @{
        "apikey"        = $key
        "Authorization" = "Bearer $key"
        "Content-Type"  = "application/json"
    }

    try {
        $body     = @{ p_discord_id = $DiscordId; p_limit = $Limit } | ConvertTo-Json
        $endpoint = "$url/rest/v1/rpc/get_broski_tx_history"
        $result   = Invoke-RestMethod -Uri $endpoint -Headers $headers -Method POST -Body $body

        if (-not $result) { return "No transactions found for Discord ID: $DiscordId" }
        $result | ConvertTo-Json -Depth 3
    } catch {
        return "Transaction history error: $_"
    }
}

function get_broski_economy_stats {
    <#
    .SYNOPSIS
        Returns a full BROski$ economy health snapshot.
    .DESCRIPTION
        Queries the broski_economy_snapshot view — returns total users,
        combined supply, 24h transaction counts + volume across Web2 and Discord.
        Use this for economy health checks and dashboards.
    .EXAMPLE
        get_broski_economy_stats
    #>
    [CmdletBinding()]
    param()

    $url = $env:SUPABASE_URL
    $key = $env:SUPABASE_KEY
    if (-not $url -or -not $key) { return "ERROR: Supabase env vars not set." }

    $headers = @{
        "apikey"        = $key
        "Authorization" = "Bearer $key"
    }

    try {
        $endpoint = "$url/rest/v1/broski_economy_snapshot?limit=1"
        $result   = Invoke-RestMethod -Uri $endpoint -Headers $headers -Method GET
        if (-not $result) { return "Economy snapshot returned no data." }
        $result | ConvertTo-Json -Depth 3
    } catch {
        return "Economy stats error: $_"
    }
}

# ============================================================
# SECTION 5 — FULL STACK HEALTH CHECK
# ============================================================

function get_full_health_check {
    <#
    .SYNOPSIS
        Runs a full health check across the entire HyperCode stack.
    .DESCRIPTION
        Tests: Supabase REST API, Grafana, Prometheus, Loki,
        BROski$ economy snapshot, and Docker container count.
        Returns a unified pass/fail report for each service.
        Run this after any deploy or reboot.
    .EXAMPLE
        get_full_health_check
    #>
    [CmdletBinding()]
    param()

    $url          = $env:SUPABASE_URL     ?? "https://yhtmuibgdnxhbgboajhc.supabase.co"
    $key          = $env:SUPABASE_KEY
    $grafanaUrl   = $env:GRAFANA_URL      ?? "http://127.0.0.1:3001"
    $prometheusUrl = $env:PROMETHEUS_URL  ?? "http://127.0.0.1:9090"
    $lokiUrl      = $env:LOKI_URL         ?? "http://127.0.0.1:3100"

    $results = [System.Collections.Generic.List[PSCustomObject]]::new()

    # Helper: ping an endpoint
    function Test-Service($name, $uri, $headers = @{}) {
        try {
            $sw = [System.Diagnostics.Stopwatch]::StartNew()
            $null = Invoke-RestMethod -Uri $uri -Headers $headers -Method GET -TimeoutSec 8
            $sw.Stop()
            return [PSCustomObject]@{ Service = $name; Status = "✅ OK"; Ms = $sw.ElapsedMilliseconds }
        } catch {
            return [PSCustomObject]@{ Service = $name; Status = "❌ FAIL"; Ms = 0; Error = "$_" }
        }
    }

    # 1. Supabase REST
    $sbHeaders = @{ "apikey" = $key; "Authorization" = "Bearer $key" }
    $results.Add((Test-Service "Supabase REST" "$url/rest/v1/users?limit=1" $sbHeaders))

    # 2. BROski$ economy snapshot
    $results.Add((Test-Service "BROski$ Economy" "$url/rest/v1/broski_economy_snapshot?limit=1" $sbHeaders))

    # 3. BROski leaderboard view
    $results.Add((Test-Service "BROski Leaderboard" "$url/rest/v1/broski_leaderboard?limit=1" $sbHeaders))

    # 4. Grafana
    $grafHeaders = @{}
    if ($env:GRAFANA_TOKEN) { $grafHeaders["Authorization"] = "Bearer $($env:GRAFANA_TOKEN)" }
    $results.Add((Test-Service "Grafana" "$grafanaUrl/api/health" $grafHeaders))

    # 5. Prometheus
    $results.Add((Test-Service "Prometheus" "$prometheusUrl/-/healthy"))

    # 6. Loki
    $results.Add((Test-Service "Loki" "$lokiUrl/ready"))

    # 7. Docker container count
    try {
        $running = (docker ps --format "{{.Names}}" 2>$null | Measure-Object -Line).Lines
        $results.Add([PSCustomObject]@{ Service = "Docker"; Status = "✅ OK"; Ms = 0; Running = "$running containers" })
    } catch {
        $results.Add([PSCustomObject]@{ Service = "Docker"; Status = "❌ FAIL"; Ms = 0; Error = "docker not reachable" })
    }

    # Summary
    $pass = ($results | Where-Object { $_.Status -like "*OK*" } | Measure-Object).Count
    $fail = ($results | Where-Object { $_.Status -like "*FAIL*" } | Measure-Object).Count

    [PSCustomObject]@{
        Timestamp   = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        Passed      = $pass
        Failed      = $fail
        Overall     = if ($fail -eq 0) { "🟢 ALL SYSTEMS GO" } else { "🔴 $fail SERVICE(S) DOWN" }
        Services    = $results
    } | ConvertTo-Json -Depth 5
}

# ============================================================
# 🚀 REGISTER ALL 19 TOOLS — expose to AI Shell via MCP
# ============================================================
New-MCPServer -FunctionInfo @(
    # Section 1 — DevOps (6)
    (Get-Item Function:get_docker_status),
    (Get-Item Function:get_log_tail),
    (Get-Item Function:test_endpoint_health),
    (Get-Item Function:get_git_status),
    (Get-Item Function:get_system_resources),
    (Get-Item Function:list_directory),

    # Section 2 — Supabase (4)
    (Get-Item Function:query_supabase_table),
    (Get-Item Function:get_supabase_table_list),
    (Get-Item Function:check_supabase_recent_payments),
    (Get-Item Function:get_supabase_auth_stats),

    # Section 3 — Grafana / Observability (4)
    (Get-Item Function:get_grafana_alerts),
    (Get-Item Function:get_grafana_datasource_health),
    (Get-Item Function:query_prometheus_metric),
    (Get-Item Function:get_loki_recent_logs),

    # Section 4 — BROski$ Token Economy (4)
    (Get-Item Function:get_broski_balance),
    (Get-Item Function:get_broski_leaderboard),
    (Get-Item Function:get_broski_tx_history),
    (Get-Item Function:get_broski_economy_stats),

    # Section 5 — Health Check (1)
    (Get-Item Function:get_full_health_check)
)
