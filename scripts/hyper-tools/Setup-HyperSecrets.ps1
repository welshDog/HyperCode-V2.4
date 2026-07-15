# Setup-HyperSecrets.ps1
# One-time interactive secrets setup for Hyper.Tools
# Saves to %USERPROFILE%\.bro\secrets.json  (NEVER committed to git)
# Usage: .\Setup-HyperSecrets.ps1

$secretsDir  = "$env:USERPROFILE\.bro"
$secretsFile = "$secretsDir\secrets.json"

Write-Host "`nHyper.Tools Secrets Setup" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan
Write-Host "Saves to: $secretsFile" -ForegroundColor Gray
Write-Host "NEVER committed to git.`n" -ForegroundColor Yellow

# Load existing secrets if they exist
$existing = @{}
if (Test-Path $secretsFile) {
    $existing = Get-Content $secretsFile | ConvertFrom-Json -AsHashtable
    Write-Host "Existing secrets found -- press Enter to keep current value.`n" -ForegroundColor Green
}

function Prompt-Secret {
    param(
        [string]$Key,
        [string]$Label,
        [string]$Example = "",
        [bool]$Required = $false
    )
    $current = if ($existing.ContainsKey($Key)) { $existing[$Key] } else { "" }
    $display = if ($current) { " [current: ***$(($current.Substring([Math]::Max(0,$current.Length-6))))]" } else { "" }
    $hint    = if ($Example) { " (e.g. $Example)" } else { "" }
    $req     = if ($Required) { " [REQUIRED]" } else { " [optional]" }

    $input = Read-Host "$Label$req$hint$display"
    if ($input) { return $input }
    return $current
}

$secrets = @{
    discord_webhook  = Prompt-Secret -Key "discord_webhook"  -Label "Discord Webhook URL"     -Example "https://discord.com/api/webhooks/..."
    supabase_url     = Prompt-Secret -Key "supabase_url"     -Label "Supabase URL"             -Example "https://yhtmuibgdnxhbgboajhc.supabase.co"
    supabase_anon    = Prompt-Secret -Key "supabase_anon"    -Label "Supabase Anon Key"        -Required $true
    supabase_service = Prompt-Secret -Key "supabase_service" -Label "Supabase Service Role Key"
    grafana_url      = Prompt-Secret -Key "grafana_url"      -Label "Grafana URL"              -Example "http://localhost:3001"
    openai_api_key   = Prompt-Secret -Key "openai_api_key"   -Label "OpenAI API Key"           -Example "sk-..."
    stripe_secret    = Prompt-Secret -Key "stripe_secret"    -Label "Stripe Secret Key"        -Example "sk_live_..."
    mcp_gateway_url  = Prompt-Secret -Key "mcp_gateway_url"  -Label "MCP Gateway URL"          -Example "http://localhost:8823"
}

# Create the .bro dir if needed
if (-not (Test-Path $secretsDir)) {
    New-Item -ItemType Directory -Path $secretsDir -Force | Out-Null
    Write-Host "Created: $secretsDir" -ForegroundColor Gray
}

# Write secrets
$secrets | ConvertTo-Json -Depth 3 | Set-Content -Path $secretsFile -Encoding UTF8

# Lock down permissions (Windows)
try {
    $acl  = Get-Acl $secretsFile
    $acl.SetAccessRuleProtection($true, $false)
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $env:USERNAME, "FullControl", "Allow"
    )
    $acl.SetAccessRule($rule)
    Set-Acl $secretsFile $acl
    Write-Host "Permissions locked to current user only." -ForegroundColor Gray
} catch {
    Write-Warning "Could not set file permissions: $_"
}

Write-Host "`nSecrets saved to: $secretsFile" -ForegroundColor Green
Write-Host "Run: Import-Module .\Hyper.Tools.psm1 then Get-HyperSecrets to verify.`n" -ForegroundColor Cyan

# Verify .gitignore has .bro entry
$gitignorePath = (Get-Item "$PSScriptRoot\..\.." -ErrorAction SilentlyContinue).FullName + "\.gitignore"
if ($gitignorePath -and (Test-Path $gitignorePath)) {
    $content = Get-Content $gitignorePath -Raw
    if ($content -notmatch '\.bro') {
        Add-Content $gitignorePath "`n# BRO secrets`n.bro/`n"
        Write-Host ".bro/ added to .gitignore -- secrets are safe!" -ForegroundColor Yellow
    } else {
        Write-Host ".bro/ already in .gitignore -- you're good." -ForegroundColor Green
    }
}
