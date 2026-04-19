# scripts/init-secrets.ps1 — Windows equivalent of init-secrets.sh
# Run once before first Docker secrets deployment.

$Root = Split-Path $PSScriptRoot -Parent
$SecretsDir = Join-Path $Root "secrets"
$EnvFile = Join-Path $Root ".env"

# Load .env
$env_vars = @{}
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match "^\s*([^#=]+)=(.*)$") {
            $env_vars[$Matches[1].Trim()] = $Matches[2].Trim()
        }
    }
}

if (-not (Test-Path $SecretsDir)) {
    New-Item -ItemType Directory -Path $SecretsDir | Out-Null
}

function Write-Secret {
    param([string]$Name, [string]$Value)
    $file = Join-Path $SecretsDir "$Name.txt"
    if (Test-Path $file) {
        Write-Host "  [SKIP] $Name already exists" -ForegroundColor Yellow
        return
    }
    if (-not $Value) {
        $secure = Read-Host "  Enter value for $Name" -AsSecureString
        $Value = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        )
    }
    [IO.File]::WriteAllText($file, $Value)
    Write-Host "  [OK]   $Name written" -ForegroundColor Green
}

Write-Host ""
Write-Host "HyperCode V2.4 — Docker Secrets Initialisation" -ForegroundColor Cyan
Write-Host "================================================"
Write-Host "Secrets directory: $SecretsDir"
Write-Host ""

Write-Secret "postgres_password"      ($env_vars["POSTGRES_PASSWORD"] ?? "")
Write-Secret "api_key"                ($env_vars["API_KEY"] ?? "")
Write-Secret "jwt_secret"             ($env_vars["JWT_SECRET"] ?? ($env_vars["HYPERCODE_JWT_SECRET"] ?? ""))
Write-Secret "memory_key"             ($env_vars["HYPERCODE_MEMORY_KEY"] ?? "")
Write-Secret "orchestrator_api_key"   ($env_vars["ORCHESTRATOR_API_KEY"] ?? "")
Write-Secret "grafana_admin_password" ($env_vars["GF_SECURITY_ADMIN_PASSWORD"] ?? "")
Write-Secret "minio_root_user"        ($env_vars["MINIO_ROOT_USER"] ?? "")
Write-Secret "minio_root_password"    ($env_vars["MINIO_ROOT_PASSWORD"] ?? "")
Write-Secret "discord_token"          ($env_vars["DISCORD_TOKEN"] ?? "")
Write-Secret "openai_api_key"         ($env_vars["OPENAI_API_KEY"] ?? "")
Write-Secret "perplexity_api_key"     ($env_vars["PERPLEXITY_API_KEY"] ?? "")
Write-Secret "anthropic_api_key"      ($env_vars["ANTHROPIC_API_KEY"] ?? "")

Write-Host ""
Write-Host "Done. Validate with:" -ForegroundColor Cyan
Write-Host "  docker compose -f docker-compose.yml -f docker-compose.secrets.yml config --quiet"
Write-Host ""
