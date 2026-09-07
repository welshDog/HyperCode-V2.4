#!/usr/bin/env pwsh
# ============================================================================
# docker-scout-baseline.ps1 - first-party Scout CVE baseline of the LOCAL images
#
# Unlike scripts/docker-scout-audit.ps1 (which scans the pushed
# docker.io/w3lshdog/*:v2.4.2 registry tags), this scans the images actually
# running / built on THIS box, so the numbers reflect what is deployed now.
#
# Output: docs/health-reports/scout-baseline-<yyyy-MM-dd>.md
#
# Prereqs:
#   - docker login  (Scout needs a Docker Hub account)
#   - RAM gate: wsl -e free -m  ->  free >= 900 MB AND swap-used < 1024 MB
#   - Do NOT run while the observability stack is up (scanning the ~9GB
#     ollama image + SBOM analysis will OOM the 4GB WSL VM).
#   - Runs strictly serially - concurrent scout processes hit a cache lock
#     (docs/health-reports/vulnerability-scan-report.md:118).
#
# Usage:
#   .\scripts\docker-scout-baseline.ps1
#   .\scripts\docker-scout-baseline.ps1 -IncludeOllama      # also scan ollama/ollama (~9GB, heavy)
#   .\scripts\docker-scout-baseline.ps1 -OutDir docs/health-reports
# ============================================================================

param(
    [switch]$IncludeOllama = $false,
    [string]$OutDir = "docs/health-reports"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# name -> running container to resolve the real image ref from (preferred),
# with a fallback image ref if no such container exists. Refs that are not
# present locally are SKIPPED (never pulled - Scout would try Docker Hub and
# fail on private names).
$targets = @(
    @{ Name = "hypercode-core";       Container = "hypercode-core";       Fallback = "hypercode-core:latest" }
    @{ Name = "healer-agent";         Container = "healer-agent";         Fallback = "hypercode-v24-healer-agent:latest" }
    @{ Name = "safety-shepherd";      Container = "safety-shepherd";      Fallback = "safety-shepherd:latest" }
    @{ Name = "hyper-brain";          Container = "hyper-brain";          Fallback = "hypercode-v24-hyper-brain:latest" }
    @{ Name = "hyperhealth-worker";   Container = "hyperhealth-worker";   Fallback = "hypercode-v20-hyperhealth-worker:latest" }
    @{ Name = "hypercode-mcp-server"; Container = "hypercode-mcp-server"; Fallback = "hypercode-v24-hypercode-mcp-server:latest" }
    @{ Name = "agent-mcp-bridge";     Container = "agent-mcp-bridge";     Fallback = "hypercode-v24-agent-mcp-bridge:latest" }
    @{ Name = "memstream";            Container = "memstream";            Fallback = "hypercode-memstream:latest" }
    @{ Name = "postgres";             Container = "postgres";             Fallback = "postgres:16-alpine" }
    @{ Name = "redis";                Container = "redis";                Fallback = "redis:8-alpine" }
)
if ($IncludeOllama) {
    $targets += @{ Name = "ollama"; Container = "hypercode-ollama"; Fallback = "ollama/ollama:0.3.14" }
}

function Resolve-ImageRef {
    param($t)
    try {
        $img = docker inspect $t.Container --format '{{.Config.Image}}' 2>$null
        if ($LASTEXITCODE -eq 0 -and $img) { return $img.Trim() }
    } catch {}
    return $t.Fallback
}

function Get-Digest {
    param($ref)
    try {
        $d = docker inspect $ref --format '{{index .RepoDigests 0}}' 2>$null
        if ($LASTEXITCODE -eq 0 -and $d) { return $d.Trim() }
        $id = docker inspect $ref --format '{{.Id}}' 2>$null
        if ($LASTEXITCODE -eq 0 -and $id) { return $id.Trim() }
    } catch {}
    return "(unresolved)"
}

# Pull the "C  H  M  L" summary numbers out of `docker scout quickview` text.
function Parse-Counts {
    param([string[]]$Lines)
    $c = 0; $h = 0; $m = 0; $l = 0; $matched = $false
    foreach ($ln in $Lines) {
        # quickview rows look like:  Target | image:tag | 0C | 2H | 15M | 30L
        if ($ln -match '(\d+)C\b.*?(\d+)H\b.*?(\d+)M\b.*?(\d+)L\b') {
            # take the first data row (the target image itself)
            $c = [int]$Matches[1]; $h = [int]$Matches[2]; $m = [int]$Matches[3]; $l = [int]$Matches[4]
            $matched = $true
            break
        }
    }
    return @{ Critical = $c; High = $h; Medium = $m; Low = $l; Matched = $matched }
}

Write-Host "Docker Scout baseline" -ForegroundColor Cyan
Write-Host ""

# sanity: scout present + logged in
$scoutOk = $true
try { docker scout version 2>&1 | Out-Null; if ($LASTEXITCODE -ne 0) { $scoutOk = $false } } catch { $scoutOk = $false }
if (-not $scoutOk) {
    Write-Host "docker scout not available - run 'docker scout version' / 'docker login' first." -ForegroundColor Red
    exit 1
}

$scoutVersion = (docker scout version 2>&1 | Select-String -Pattern 'version' | Select-Object -First 1).ToString().Trim()
$now = Get-Date
$dateStr = $now.ToString("yyyy-MM-dd")
$stamp   = $now.ToString("yyyy-MM-dd HH:mm:ss zzz")

$rows = @()
$details = New-Object System.Text.StringBuilder

foreach ($t in $targets) {
    $ref = Resolve-ImageRef $t

    # Never let Scout pull: skip anything not present locally.
    docker image inspect $ref 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host ("Skipping {0}  ({1}) - not present locally" -f $t.Name, $ref) -ForegroundColor DarkGray
        $rows += [pscustomobject]@{
            Image = $t.Name; Ref = $ref; SizeMB = "-"
            Critical = "-"; High = "-"; Medium = "-"; Low = "-"
            Status = "SKIPPED (not local)"; Digest = "(not local)"
        }
        continue
    }

    Write-Host ("Scanning {0}  ({1})" -f $t.Name, $ref) -ForegroundColor Yellow

    $digest = Get-Digest $ref
    $sizeBytes = try { (docker inspect $ref --format '{{.Size}}' 2>$null).Trim() } catch { "" }
    $sizeMB = if ($sizeBytes -match '^\d+$') { [math]::Round([long]$sizeBytes / 1MB, 0) } else { "?" }

    $quick = @()
    try { $quick = docker scout quickview $ref 2>&1 } catch { $quick = @("(quickview failed: $_)") }
    $counts = Parse-Counts $quick

    $cves = @()
    try { $cves = docker scout cves $ref --only-severity critical,high 2>&1 } catch { $cves = @("(cves failed: $_)") }

    $status = "OK"
    if ($counts.Critical -gt 0) { $status = "CRITICAL" }
    elseif ($counts.High -gt 0) { $status = "HIGH" }

    $rows += [pscustomobject]@{
        Image    = $t.Name
        Ref      = $ref
        SizeMB   = $sizeMB
        Critical = $counts.Critical
        High     = $counts.High
        Medium   = $counts.Medium
        Low      = $counts.Low
        Status   = $status
        Digest   = $digest
    }

    [void]$details.AppendLine("### $($t.Name)")
    [void]$details.AppendLine("")
    [void]$details.AppendLine("- ref: ``$ref``")
    [void]$details.AppendLine("- digest: ``$digest``")
    [void]$details.AppendLine("- size: ${sizeMB} MB")
    [void]$details.AppendLine("")
    [void]$details.AppendLine('```')
    [void]$details.AppendLine(($quick -join "`n"))
    [void]$details.AppendLine('```')
    [void]$details.AppendLine("")
    [void]$details.AppendLine("<details><summary>critical + high CVEs</summary>")
    [void]$details.AppendLine("")
    [void]$details.AppendLine('```')
    [void]$details.AppendLine(($cves -join "`n"))
    [void]$details.AppendLine('```')
    [void]$details.AppendLine("</details>")
    [void]$details.AppendLine("")
}

# ---- assemble markdown ----
$md = New-Object System.Text.StringBuilder
[void]$md.AppendLine("# Docker Scout CVE Baseline - $dateStr")
[void]$md.AppendLine("")
[void]$md.AppendLine("> First-party ``docker scout`` baseline of the images running / built on this box.")
[void]$md.AppendLine("> Companion to ``scripts/docker-scout-audit.ps1`` (which scans the pushed v2.4.2 registry tags).")
[void]$md.AppendLine("")
[void]$md.AppendLine("| Field | Value |")
[void]$md.AppendLine("|---|---|")
[void]$md.AppendLine("| Generated | $stamp |")
[void]$md.AppendLine("| Scout | $scoutVersion |")
[void]$md.AppendLine("| Host | WSL2 / Docker Desktop |")
[void]$md.AppendLine("")
[void]$md.AppendLine("## Summary")
[void]$md.AppendLine("")
[void]$md.AppendLine("| Image | Size (MB) | CRITICAL | HIGH | MEDIUM | LOW | Status |")
[void]$md.AppendLine("|---|---:|---:|---:|---:|---:|---|")
$tc = 0; $th = 0
foreach ($r in $rows) {
    [void]$md.AppendLine("| $($r.Image) | $($r.SizeMB) | $($r.Critical) | $($r.High) | $($r.Medium) | $($r.Low) | $($r.Status) |")
    if ($r.Critical -is [int]) { $tc += $r.Critical }
    if ($r.High -is [int])     { $th += $r.High }
}
[void]$md.AppendLine("")
[void]$md.AppendLine("**Totals across scanned images: CRITICAL $tc | HIGH $th**")
[void]$md.AppendLine("")
[void]$md.AppendLine("## Image digests (for comparable re-scan)")
[void]$md.AppendLine("")
foreach ($r in $rows) { [void]$md.AppendLine("- **$($r.Image)** ``$($r.Digest)``") }
[void]$md.AppendLine("")
[void]$md.AppendLine("## Per-image detail")
[void]$md.AppendLine("")
[void]$md.Append($details.ToString())
[void]$md.AppendLine("## Next")
[void]$md.AppendLine("")
[void]$md.AppendLine("- ``docker scout recommendations <ref>`` for base-image bump guidance on the worst offenders.")
[void]$md.AppendLine("- Re-run after any base-image change and diff the digests + counts above.")

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }
$outFile = Join-Path $OutDir "scout-baseline-$dateStr.md"
$md.ToString() | Out-File -FilePath $outFile -Encoding utf8

Write-Host ""
Write-Host ("Wrote {0}" -f $outFile) -ForegroundColor Green
Write-Host ("Totals: CRITICAL {0} | HIGH {1}" -f $tc, $th) -ForegroundColor $(if ($tc -gt 0) { "Red" } else { "Green" })
