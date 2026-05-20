#!/usr/bin/env pwsh
# ════════════════════════════════════════════════════════════════════════════════
# docker-scout-audit.ps1 — COMPREHENSIVE CVE SCANNING FOR ALL AGENTS
# Scans all 26 images (25 agents + core) for vulnerabilities
# Usage: .\scripts\docker-scout-audit.ps1
# Generated: May 21, 2026
# ════════════════════════════════════════════════════════════════════════════════

param(
    [ValidateSet("critical", "high", "medium", "low", "all")]
    [string]$Severity = "critical",
    
    [switch]$Export = $false,
    [string]$ExportPath = "scout-results.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "🔍 Docker Scout Security Audit" -ForegroundColor Cyan
Write-Host ""

$images = @(
    # Core
    "docker.io/w3lshdog/hypercode-core:v2.4.2",
    
    # Tier 1
    "docker.io/w3lshdog/hypercode-crew-orchestrator:v2.4.2",
    "docker.io/w3lshdog/hypercode-agent-x:v2.4.2",
    "docker.io/w3lshdog/hypercode-brain-agent:v2.4.2",
    "docker.io/w3lshdog/hypercode-coder-agent:v2.4.2",
    "docker.io/w3lshdog/hypercode-tips-tricks-agent:v2.4.2",
    
    # Tier 2
    "docker.io/w3lshdog/hypercode-frontend-specialist:v2.4.2",
    "docker.io/w3lshdog/hypercode-backend-specialist:v2.4.2",
    "docker.io/w3lshdog/hypercode-database-architect:v2.4.2",
    "docker.io/w3lshdog/hypercode-qa-engineer:v2.4.2",
    "docker.io/w3lshdog/hypercode-devops-engineer:v2.4.2",
    "docker.io/w3lshdog/hypercode-security-engineer:v2.4.2",
    "docker.io/w3lshdog/hypercode-system-architect:v2.4.2",
    "docker.io/w3lshdog/hypercode-project-strategist:v2.4.2",
    
    # Tier 3
    "docker.io/w3lshdog/hypercode-hyper-architect:v2.4.2",
    "docker.io/w3lshdog/hypercode-hyper-observer:v2.4.2",
    "docker.io/w3lshdog/hypercode-hyper-worker:v2.4.2",
    "docker.io/w3lshdog/hypercode-goal-keeper:v2.4.2",
    "docker.io/w3lshdog/hypercode-throttle-agent:v2.4.2",
    "docker.io/w3lshdog/hypercode-super-hyper-broski-agent:v2.4.2",
    "docker.io/w3lshdog/hypercode-test-agent:v2.4.2",
    "docker.io/w3lshdog/hypercode-mcp-server:v2.4.2",
    
    # Tier 4
    "docker.io/w3lshdog/hypercode-session-snapshot:v2.4.2",
    "docker.io/w3lshdog/hypercode-hyper-split-agent:v2.4.2",
    "docker.io/w3lshdog/hypercode-coderabbit-webhook:v2.4.2",
    "docker.io/w3lshdog/hypercode-business-agent:v2.4.2"
)

$results = @()
$critical_count = 0
$high_count = 0
$total_vulns = 0

foreach ($image in $images) {
    Write-Host "Scanning: $image" -ForegroundColor Yellow
    
    try {
        # Run Scout CVE scan
        $cves = docker scout cves "$image" --json | ConvertFrom-Json
        
        if ($cves) {
            $critical = ($cves | Where-Object { $_.severity -eq "CRITICAL" } | Measure-Object).Count
            $high = ($cves | Where-Object { $_.severity -eq "HIGH" } | Measure-Object).Count
            $medium = ($cves | Where-Object { $_.severity -eq "MEDIUM" } | Measure-Object).Count
            $low = ($cves | Where-Object { $_.severity -eq "LOW" } | Measure-Object).Count
            $total = $critical + $high + $medium + $low
            
            $critical_count += $critical
            $high_count += $high
            $total_vulns += $total
            
            $status = "🟢"
            if ($critical -gt 0) { $status = "🔴" }
            elseif ($high -gt 0) { $status = "🟠" }
            
            Write-Host "  $status CRITICAL: $critical | HIGH: $high | MEDIUM: $medium | LOW: $low | TOTAL: $total" -ForegroundColor $(if ($critical -gt 0) { "Red" } else { "Green" })
            
            $results += @{
                image = $image
                critical = $critical
                high = $high
                medium = $medium
                low = $low
                total = $total
            }
        }
    } catch {
        Write-Host "  ⚠️  Scan failed: $_" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "📊 AUDIT SUMMARY" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total images scanned: $(($images).Count)" -ForegroundColor White
Write-Host "Total vulnerabilities: $total_vulns" -ForegroundColor $(if ($total_vulns -gt 0) { "Yellow" } else { "Green" })
Write-Host "  🔴 CRITICAL: $critical_count" -ForegroundColor $(if ($critical_count -gt 0) { "Red" } else { "Green" })
Write-Host "  🟠 HIGH: $high_count" -ForegroundColor $(if ($high_count -gt 0) { "Yellow" } else { "Green" })
Write-Host ""

if ($critical_count -eq 0 -and $high_count -eq 0) {
    Write-Host "✅ PASS: No critical or high-severity vulnerabilities detected" -ForegroundColor Green
} else {
    Write-Host "⚠️  ACTION REQUIRED: Review and remediate vulnerabilities above" -ForegroundColor Red
}

if ($Export) {
    $results | ConvertTo-Json | Out-File $ExportPath
    Write-Host ""
    Write-Host "📁 Results exported to: $ExportPath" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "🔗 For detailed remediation: docker scout recommendations <image>" -ForegroundColor Cyan
