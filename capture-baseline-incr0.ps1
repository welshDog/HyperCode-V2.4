# Baseline capture — Increment 0, clean HEAD 2f3e1277
# Run from HyperCode-V2.4 repo root, while the clean HEAD dashboard is live.
# Uses the Playwright CLI (headless chromium) — does NOT need the MCP server or any browser extension.
#
# NOTE 2026-09-09: `npx playwright` resolves an unmatched older build on this box.
# Use the REPO-LOCAL binary (node_modules\.bin\playwright) so the version matches
# the installed chromium. If chromium is missing:
#   node_modules\.bin\playwright.cmd install chromium
# The node equivalent `capture-baseline-incr0.mjs` is the one actually used and is
# more robust (handles networkidle never settling on live-polling pages).

$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8088"
$out  = "docs/reports/baseline-incr0"

# Fixed viewport — do NOT change before the Increment 2 diff pass.
$viewport = "1440,900"

$routes = @(
  @{ path = "/";           name = "home" },
  @{ path = "/ide";        name = "ide" },
  @{ path = "/agents";     name = "agents" },
  @{ path = "/mission";    name = "mission" },
  @{ path = "/control";    name = "control" },
  @{ path = "/flows";      name = "flows" },
  @{ path = "/mcp";        name = "mcp" },
  @{ path = "/docker-zone";name = "docker-zone" },
  @{ path = "/health";     name = "health" },
  @{ path = "/grafana";    name = "grafana" }
)

New-Item -ItemType Directory -Force -Path $out | Out-Null
$failed = @()

foreach ($r in $routes) {
  $url  = "$base$($r.path)"
  $file = Join-Path $out "$($r.name).png"
  Write-Host "Capturing $($r.name) -> $file"
  # --wait-for-timeout lets live panels (fleet, safety feed, docker-zone iframe) settle
  & "node_modules\.bin\playwright.cmd" screenshot `
    --viewport-size="$viewport" `
    --wait-for-timeout=5000 `
    $url $file
  if ($LASTEXITCODE -ne 0 -or !(Test-Path $file)) {
    $failed += $r.name
  }
}

Write-Host ""
if ($failed.Count -eq 0) {
  Write-Host "All 10 pages captured to $out — baseline locked." -ForegroundColor Green
} else {
  Write-Host "FAILED: $($failed -join ', ') — rerun just those routes before tonight's rebuild." -ForegroundColor Red
  exit 1
}

# Record the capture context next to the PNGs so tonight's diff is honest
@"
# Baseline capture metadata
- Captured: $(Get-Date -Format "yyyy-MM-dd HH:mm K")
- Deployed image: a0f531ac9708 (clean HEAD 2f3e1277)
- Viewport: $viewport, full-page
- CSS chunk: 0.8ppsn43~8wl.css
- Webfonts loaded: none (documented in MEASURED_BASELINE.md)
"@ | Set-Content (Join-Path $out "CAPTURE_METADATA.md")

Write-Host "Metadata written. DO NOT rebuild the dashboard until you've confirmed all 10 PNGs."
