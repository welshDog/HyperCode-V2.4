# Check for required environment variables before deployment

$RequiredVars = @(
    "API_KEY",
    "HYPERCODE_JWT_SECRET",
    "POSTGRES_PASSWORD",
    "PERPLEXITY_API_KEY",
    "HYPERCODE_MEMORY_KEY"
)

$MissingVars = @()
$WeakSecrets = @()

Write-Host "---------------------------------------------------------------------------------"
Write-Host "   HYPERCODE SECURITY VALIDATION"
Write-Host "---------------------------------------------------------------------------------"

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-Warning ".env file not found! Please create one from .env.production.template"
    exit 1
}

# Load .env (naive parsing)
$EnvContent = Get-Content ".env"
$EnvVars = @{}
foreach ($line in $EnvContent) {
    if ($line -match "^([^#=]+)=(.*)$") {
        $EnvVars[$matches[1]] = $matches[2]
    }
}

# Validate
foreach ($var in $RequiredVars) {
    if (-not $EnvVars.ContainsKey($var) -or [string]::IsNullOrWhiteSpace($EnvVars[$var])) {
        $MissingVars += $var
    } else {
        # Check for weak secrets (basic heuristic)
        $val = $EnvVars[$var]
        if ($val -eq "dev-master-key" -or $val -eq "secret" -or $val.Length -lt 8) {
            $WeakSecrets += "$var (Value too weak or default)"
        }
    }
}

if ($MissingVars.Count -gt 0) {
    Write-Error "MISSING REQUIRED VARIABLES:"
    foreach ($v in $MissingVars) { Write-Host " - $v" -ForegroundColor Red }
}

if ($WeakSecrets.Count -gt 0) {
    Write-Error "WEAK SECRETS DETECTED (DO NOT USE IN PRODUCTION):"
    foreach ($v in $WeakSecrets) { Write-Host " - $v" -ForegroundColor Red }
}

if ($MissingVars.Count -eq 0 -and $WeakSecrets.Count -eq 0) {
    Write-Host "✅ Security Check Passed. Ready for deployment." -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ Security Check Failed." -ForegroundColor Red
    exit 1
}
