# ============================================================
# 🚀 MCP Server Runner — Lyndz HyperCode Stack
# ============================================================
# Usage: pwsh -File start.ps1
# Requires: PowerShell 7.5+, pwsh.mcp module installed
# Install module: Install-Module pwsh.mcp -Scope CurrentUser -Force
# ============================================================

# Validate env vars are set before launching
$required = @(
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "GRAFANA_URL",
    "GRAFANA_TOKEN",
    "PROMETHEUS_URL",
    "LOKI_URL"
)

$missing = $required | Where-Object { -not [System.Environment]::GetEnvironmentVariable($_) }

if ($missing) {
    Write-Warning "⚠️  Missing env vars: $($missing -join ', ')"
    Write-Warning "Some tools will return errors until these are set."
    Write-Warning "Set them in your PowerShell profile or .env loader — NEVER hardcode."
}

Write-Host "🚀 Starting Lyndz MCP Server..." -ForegroundColor Cyan
Write-Host "📦 14 tools: DevOps + Supabase + Grafana + Observability" -ForegroundColor Green

pwsh -NoProfile -NoLogo -File "$PSScriptRoot/mcp-server.ps1"
