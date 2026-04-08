#!/usr/bin/env pwsh
# Secret Setup Script for HyperCode V2.0
# Creates secret files required for docker-compose.prod.yml

Write-Host "🔐 HyperCode Secret Setup Script" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

$secretsDir = "secrets"

# Create secrets directory if it doesn't exist
if (-not (Test-Path $secretsDir)) {
    Write-Host "📁 Creating secrets directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $secretsDir | Out-Null
    Write-Host "✅ Created: $secretsDir`n" -ForegroundColor Green
} else {
    Write-Host "✅ Secrets directory exists`n" -ForegroundColor Green
}

# Function to create secret file
function New-SecretFile {
    param(
        [string]$filename,
        [string]$prompt,
        [string]$default,
        [switch]$generate
    )
    
    $filepath = Join-Path $secretsDir $filename
    
    if (Test-Path $filepath) {
        Write-Host "⚠️  $filename already exists" -ForegroundColor Yellow
        $overwrite = Read-Host "Overwrite? (y/N)"
        if ($overwrite -ne "y" -and $overwrite -ne "Y") {
            Write-Host "⏭️  Skipped: $filename`n" -ForegroundColor Gray
            return
        }
    }
    
    if ($generate) {
        # Generate secure random string
        $bytes = New-Object byte[] 32
        [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
        $value = [Convert]::ToBase64String($bytes) -replace '[/+=]', ''
        Write-Host "🎲 Generated secure random value for $filename" -ForegroundColor Cyan
    } else {
        $value = Read-Host $prompt
        if ([string]::IsNullOrWhiteSpace($value) -and $default) {
            $value = $default
            Write-Host "Using default value" -ForegroundColor Gray
        }
    }
    
    if ([string]::IsNullOrWhiteSpace($value)) {
        Write-Host "❌ No value provided, skipping $filename`n" -ForegroundColor Red
        return
    }
    
    # Write to file
    $value | Out-File -FilePath $filepath -NoNewline -Encoding UTF8
    
    # Set permissions (read-only for owner)
    $acl = Get-Acl $filepath
    $acl.SetAccessRuleProtection($true, $false)
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        [System.Security.Principal.WindowsIdentity]::GetCurrent().Name,
        "Read",
        "Allow"
    )
    $acl.SetAccessRule($rule)
    Set-Acl $filepath $acl
    
    Write-Host "✅ Created: $filename (${value.Length} characters)`n" -ForegroundColor Green
}

# Create each required secret
Write-Host "Creating required secret files...`n" -ForegroundColor Yellow

# PERPLEXITY API Key
New-SecretFile `
    -filename "PERPLEXITY_API_KEY.txt" `
    -prompt "Enter PERPLEXITY API Key"

# PostgreSQL Password
Write-Host "PostgreSQL Password:" -ForegroundColor Cyan
$generatePg = Read-Host "Generate secure random password? (Y/n)"
if ($generatePg -eq "" -or $generatePg -eq "y" -or $generatePg -eq "Y") {
    New-SecretFile `
        -filename "postgres_password.txt" `
        -prompt "" `
        -generate
} else {
    New-SecretFile `
        -filename "postgres_password.txt" `
        -prompt "Enter PostgreSQL Password"
}

# Grafana Admin Password
Write-Host "Grafana Admin Password:" -ForegroundColor Cyan
$generateGrafana = Read-Host "Generate secure random password? (Y/n)"
if ($generateGrafana -eq "" -or $generateGrafana -eq "y" -or $generateGrafana -eq "Y") {
    New-SecretFile `
        -filename "grafana_admin_password.txt" `
        -prompt "" `
        -generate
} else {
    New-SecretFile `
        -filename "grafana_admin_password.txt" `
        -prompt "Enter Grafana Admin Password"
}

# Redis Password (optional for prod)
Write-Host "Redis Password (optional):" -ForegroundColor Cyan
$createRedis = Read-Host "Create Redis password? (Y/n)"
if ($createRedis -eq "" -or $createRedis -eq "y" -or $createRedis -eq "Y") {
    New-SecretFile `
        -filename "redis_password.txt" `
        -prompt "" `
        -generate
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✅ Secret Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "📝 Created files:" -ForegroundColor Yellow
Get-ChildItem $secretsDir -File | ForEach-Object {
    Write-Host "  - $($_.Name)" -ForegroundColor Gray
}

Write-Host "`n⚠️  Important Security Notes:" -ForegroundColor Yellow
Write-Host "  1. Never commit the secrets/ directory to Git" -ForegroundColor Gray
Write-Host "  2. Backup these files securely (encrypted)" -ForegroundColor Gray
Write-Host "  3. Use a password manager for team access" -ForegroundColor Gray
Write-Host "  4. Rotate secrets regularly in production" -ForegroundColor Gray

Write-Host "`n✅ You can now run: docker compose -f docker-compose.prod.yml up -d" -ForegroundColor Green
