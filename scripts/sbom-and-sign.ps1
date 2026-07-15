#!/usr/bin/env pwsh
# ════════════════════════════════════════════════════════════════════════════════
# sbom-and-sign.ps1 — SUPPLY CHAIN SECURITY
# Generate SBOM for all images + sign with Cosign
# Usage: .\scripts\sbom-and-sign.ps1
# Created: May 21, 2026
# ════════════════════════════════════════════════════════════════════════════════

param(
    [string]$Registry = "docker.io",
    [string]$Namespace = "w3lshdog"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "🔐 Supply Chain Security — SBOM + Signing" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
$tools = @("docker", "syft", "cosign")
foreach ($tool in $tools) {
    try {
        & $tool --version > $null
        Write-Host "✅ $tool installed" -ForegroundColor Green
    } catch {
        Write-Host "❌ $tool not found. Install it." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

$images = @(
    "hypercode-core:v2.4.2",
    "hypercode-crew-orchestrator:v2.4.2",
    "hypercode-agent-x:v2.4.2",
    "hypercode-brain-agent:v2.4.2",
    "hypercode-coder-agent:v2.4.2",
    "hypercode-tips-tricks-agent:v2.4.2",
)

# Generate SBOM for each image
Write-Host "📋 Generating SBOMs..." -ForegroundColor Yellow
foreach ($image in $images) {
    $full_image = "$Registry/$Namespace/$image"
    $sbom_file = "sbom-$(($image -split ':')[0]).json"
    
    Write-Host "  Scanning: $full_image" -ForegroundColor Cyan
    
    # Generate SBOM using Syft
    syft "$full_image" -o json > $sbom_file
    
    Write-Host "    📄 SBOM: $sbom_file" -ForegroundColor Green
}

Write-Host ""
Write-Host "🔑 Signing Images with Cosign..." -ForegroundColor Yellow
Write-Host ""
Write-Host "⚠️  Ensure COSIGN_EXPERIMENTAL=1 and COSIGN_KEY env vars are set" -ForegroundColor Yellow
Write-Host ""

foreach ($image in $images) {
    $full_image = "$Registry/$Namespace/$image"
    
    Write-Host "  Signing: $full_image" -ForegroundColor Cyan
    
    try {
        cosign sign --key $env:COSIGN_KEY "$full_image"
        Write-Host "    ✅ Signed" -ForegroundColor Green
    } catch {
        Write-Host "    ⚠️  Signing failed (key not configured?)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ SBOM Generation and Signing Complete" -ForegroundColor Green
Write-Host ""
Write-Host "📁 SBOMs generated: sbom-*.json" -ForegroundColor Cyan
Write-Host "🔐 Images signed with Cosign (if key configured)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Commit SBOMs to repo: git add sbom-*.json && git commit -m 'chore: update SBOMs'" -ForegroundColor Gray
Write-Host "  2. Verify signature: cosign verify --key cosign.pub $Registry/$Namespace/<image>" -ForegroundColor Gray
Write-Host "  3. Automate in CI/CD: add to GitHub Actions workflow" -ForegroundColor Gray
Write-Host ""
