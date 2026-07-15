# Hyper.Tools — AI-Callable PowerShell Module

BRO monitoring toolkit for HyperCode V2.4. Registers PowerShell functions as PSAI agent tools so AI can autonomously monitor your stack.

## Quick Start

```powershell
# 1. Install dependencies (once)
winget install Microsoft.AIShell
Install-Module PSAI -Scope CurrentUser
Install-Module PSScriptAnalyzer -Scope CurrentUser

# 2. Set up secrets (once)
.\Setup-HyperSecrets.ps1

# 3. Import the module
Import-Module .\Hyper.Tools.psm1

# 4. Run a full health check
Invoke-HyperHealthCheck

# 5. Register as PSAI tools
Import-Module PSAI
.\PSAI-Register-Tools.ps1
```

## aish MCP Config

Copy `aish-mcp-config.json` to your aish config folder:

```powershell
# Typical aish config location
Copy-Item .\aish-mcp-config.json "$env:APPDATA\AIShell\mcp-servers.json"

# Then start aish
aish
```

This wires aish to your existing MCP gateway at `:8823` AND registers the BRO PowerShell tools.

## Available Functions

| Function | PSAI Tool Name | What it does |
|---|---|---|
| `Invoke-HyperHealthCheck` | `run_full_health_check` | Full stack snapshot — containers, agents, CPU |
| `Get-HyperContainerHealth` | `get_container_health` | Docker container status list |
| `Restart-HyperContainer` | `restart_container` | Restart a named container |
| `Get-HyperAgentStatus` | `get_agent_status` | Poll dashboard for agent status |
| `Get-HyperNemoclawHealth` | `get_nemoclaw_health` | NemoClaw health at :8099 |
| `Get-HyperProcessHealth` | `get_process_health` | Top N processes by CPU |
| `Get-HyperLogHits` | `get_log_hits` | Scan logs for errors/fatals |
| `Send-HyperDiscordAlert` | `send_discord_alert` | Post to Discord webhook |

## Secrets

Secrets live in `%USERPROFILE%\.bro\secrets.json` — never committed to git.
Run `Setup-HyperSecrets.ps1` to create interactively.
See `secrets.json.example` for the schema.

## Ports Reference

| Service | Port |
|---|---|
| MCP Gateway | 8823 |
| HyperCode Core | 8000 |
| Dashboard | 8088 |
| NemoClaw | 8099 |
| Grafana | 3001 |
