# 🔗 Hyper Station Integration Inventory

> **Purpose:** Single source of truth for every script, tool, bookmark, or URL that touches Hyper Station.  
> **Created:** 2026-03-16 · **Track:** Research Track 2 — API & Compatibility Testing (v0.12)  
> **Owner:** Platform engineer / Lyndz Williams  
> **Status:** 🟡 In progress — fill in `[TODO]` fields as you audit each entry

---

## 📋 How to use this file

1. Work through each section below
2. Replace every `[TODO]` with the real value from your local setup
3. Set `Risk Level` per row: 🔴 High · 🟡 Medium · 🟢 Low
4. Set `v0.12 Status`: ✅ Tested · ⚠️ Needs fix · ❌ Broken · 🔲 Untested
5. This file becomes your Track 2 test checklist — tick off as you go

---

## 🚀 Section 1 — Startup & Lifecycle Scripts

These scripts start, stop, and verify the Hyper Station stack. Check they still correctly target Grafana 12.4+ endpoints and that health checks hit the right ports.

| Script | What it does | Hyper Station touchpoints | Owner | Risk Level | v0.12 Status |
|--------|-------------|--------------------------|-------|-----------|-------------|
| [`scripts/hyper-station-start.bat`](../../scripts/hyper-station-start.bat) | Starts full Hyper Station stack (Docker containers) | Brings up Grafana + Prometheus + all services | Lyndz | 🔴 High | 🔲 Untested |
| [`scripts/hyper-station-stop.bat`](../../scripts/hyper-station-stop.bat) | Stops Hyper Station containers | Tears down observability stack | Lyndz | 🟡 Medium | 🔲 Untested |
| [`scripts/start-platform.bat`](../../scripts/start-platform.bat) | Starts full platform (bat) | Platform-wide startup including Grafana | Lyndz | 🔴 High | 🔲 Untested |
| [`scripts/start-platform.sh`](../../scripts/start-platform.sh) | Starts full platform (Linux/WSL) | Platform-wide startup including Grafana | Lyndz | 🔴 High | 🔲 Untested |
| [`scripts/start_hypercode_v2.ps1`](../../scripts/start_hypercode_v2.ps1) | PowerShell master startup script | Orchestrates full stack boot including Grafana | Lyndz | 🔴 High | 🔲 Untested |
| [`scripts/dev-up.ps1`](../../scripts/dev-up.ps1) | Dev environment quick-start | Launches dev stack subset | Lyndz | 🟡 Medium | 🔲 Untested |
| [`scripts/verify_launch.ps1`](../../scripts/verify_launch.ps1) | Post-launch verification (PowerShell) | Checks Grafana + Mission Control endpoints respond 200 | Lyndz | 🔴 High | 🔲 Untested |
| [`scripts/verify_launch.sh`](../../scripts/verify_launch.sh) | Post-launch verification (bash) | Checks Grafana + Mission Control endpoints respond 200 | Lyndz | 🔴 High | 🔲 Untested |

**v0.12 check focus:** Do these scripts reference Grafana port (3001) and the Hyper Station: Setup dashboard URL? If so, validate those endpoints still load correctly after v0.12 upgrade.

---

## 🩺 Section 2 — Health Check Scripts

These query service health and could be affected by Grafana toolbar DOM changes or new dashboard URL structures.

| Script | What it does | Hyper Station touchpoints | Owner | Risk Level | v0.12 Status |
|--------|-------------|--------------------------|-------|-----------|-------------|
| [`scripts/health-check.ps1`](../../scripts/health-check.ps1) | General health check (PowerShell) | Likely queries Grafana + Prometheus liveness | Lyndz | 🟡 Medium | 🔲 Untested |
| [`scripts/comprehensive_health_check.py`](../../scripts/comprehensive_health_check.py) | Full Python health checker | Hits multiple service endpoints incl. observability | Lyndz | 🔴 High | 🔲 Untested |
| [`scripts/health_check_controller.py`](../../scripts/health_check_controller.py) | Controller-level health orchestration | Orchestrates health checks across services | Lyndz | 🟡 Medium | 🔲 Untested |
| [`scripts/hyper_health.py`](../../scripts/hyper_health.py) | Hyper Station-specific health checks | Direct Hyper Station / Grafana queries | Lyndz | 🔴 High | 🔲 Untested |
| [`scripts/docker-health-monitor.ps1`](../../scripts/docker-health-monitor.ps1) | Docker container health monitoring | Monitors Grafana + Prometheus containers | Lyndz | 🟡 Medium | 🔲 Untested |
| [`scripts/docker-health-monitor.sh`](../../scripts/docker-health-monitor.sh) | Docker container health monitoring (bash) | Monitors Grafana + Prometheus containers | Lyndz | 🟡 Medium | 🔲 Untested |
| [`scripts/zero_cost_health_check.ps1`](../../scripts/zero_cost_health_check.ps1) | Low-overhead health check | Minimal resource health polling | Lyndz | 🟢 Low | 🔲 Untested |
| [`scripts/generate_health_check_compose.py`](../../scripts/generate_health_check_compose.py) | Generates Docker Compose health config | Creates compose service health definitions | Lyndz | 🟡 Medium | 🔲 Untested |
| [`scripts/run_health_check.bat`](../../scripts/run_health_check.bat) | Runs health check bat wrapper | Entry point for health check runs | Lyndz | 🟢 Low | 🔲 Untested |

**v0.12 check focus:** Any script that checks HTTP 200 on a Grafana dashboard URL — validate those URLs haven't changed structure. Variable query strings (e.g. `?var-env=dev`) need testing against new multi-property variable semantics.

---

## 🧪 Section 3 — Test & Smoke Test Scripts

These run integration/smoke tests and may depend on specific Grafana API responses or dashboard states.

| Script | What it does | Hyper Station touchpoints | Owner | Risk Level | v0.12 Status |
|--------|-------------|--------------------------|-------|-----------|-------------|
| [`scripts/smoke_test.py`](../../scripts/smoke_test.py) | External smoke test (Python) | Tests external-facing endpoints incl. Grafana | Lyndz | 🔴 High | 🔲 Untested |
| [`scripts/smoke_test_internal.py`](../../scripts/smoke_test_internal.py) | Internal smoke test | Tests internal service connectivity | Lyndz | 🟡 Medium | 🔲 Untested |
| [`scripts/external_smoke_test.py`](../../scripts/external_smoke_test.py) | External endpoint smoke test | Validates external service exposure | Lyndz | 🔴 High | 🔲 Untested |
| [`scripts/phase3_smoke_test.ps1`](../../scripts/phase3_smoke_test.ps1) | Phase 3 smoke test suite | Phase-specific integration checks | Lyndz | 🟡 Medium | 🔲 Untested |
| [`scripts/run_test.py`](../../scripts/run_test.py) | General test runner | Runs test suites across platform | Lyndz | 🟡 Medium | 🔲 Untested |
| [`scripts/ollama_benchmark.py`](../../scripts/ollama_benchmark.py) | Ollama model benchmark | Ollama only — low Grafana dependency | Lyndz | 🟢 Low | 🔲 Untested |

**v0.12 check focus:** Any test that validates a Grafana API response shape (dashboard JSON, variable list, panel data) — run against v0.12 and diff the response structure.

---

## ⚙️ Section 4 — MCP Gateway Scripts

MCP gateway tools that may embed or link to dashboard URLs.

| Script | What it does | Hyper Station touchpoints | Owner | Risk Level | v0.12 Status |
|--------|-------------|--------------------------|-------|-----------|-------------|
| [`scripts/mcp-gateway-start.sh`](../../scripts/mcp-gateway-start.sh) | Starts MCP HTTP gateway | May reference Grafana for observability | Lyndz | 🟡 Medium | 🔲 Untested |
| [`scripts/start-mcp-host-gateway.ps1`](../../scripts/start-mcp-host-gateway.ps1) | Starts MCP host gateway (PS) | May reference Grafana for observability | Lyndz | 🟡 Medium | 🔲 Untested |
| [`scripts/verify_mcp_setup.py`](../../scripts/verify_mcp_setup.py) | Verifies MCP setup integrity | Checks MCP tool availability; may reference dashboards | Lyndz | 🟢 Low | 🔲 Untested |

---

## 🔧 Section 5 — Setup & Configuration Scripts

| Script | What it does | Hyper Station touchpoints | Owner | Risk Level | v0.12 Status |
|--------|-------------|--------------------------|-------|-----------|-------------|
| [`scripts/install_shortcuts.ps1`](../../scripts/install_shortcuts.ps1) | Installs desktop/terminal shortcuts | May create shortcuts to Grafana / Hyper Station URLs | Lyndz | 🟡 Medium | 🔲 Untested |
| [`scripts/setup-secrets.ps1`](../../scripts/setup-secrets.ps1) | Sets up secrets (env vars, creds) | Grafana admin creds may be set here | Lyndz | 🔴 High | 🔲 Untested |
| [`scripts/validate_secrets.ps1`](../../scripts/validate_secrets.ps1) | Validates secrets are present | Checks Grafana creds exist | Lyndz | 🟡 Medium | 🔲 Untested |
| [`scripts/verify_resources.ps1`](../../scripts/verify_resources.ps1) | Checks resource availability | CPU/mem available for Grafana container | Lyndz | 🟢 Low | 🔲 Untested |
| [`scripts/start-agents.bat`](../../scripts/start-agents.bat) | Starts agent fleet (bat) | Agents report metrics to Prometheus/Grafana | Lyndz | 🔴 High | 🔲 Untested |
| [`scripts/start-agents.sh`](../../scripts/start-agents.sh) | Starts agent fleet (bash) | Agents report metrics to Prometheus/Grafana | Lyndz | 🔴 High | 🔲 Untested |

---

## 🌐 Section 6 — Dashboard URLs & Bookmarks

Fill in any Grafana/Hyper Station URLs you have bookmarked or use in docs. These need URL round-trip testing against v0.12.

| Name / Description | URL | Variables used | Owner | Risk Level | v0.12 Status |
|--------------------|-----|---------------|-------|-----------|-------------|
| Grafana Home | `http://localhost:3001` | None | Lyndz | 🟡 Medium | 🔲 Untested |
| Mission Control Dashboard | `http://localhost:8088` | None | Lyndz | 🔴 High | 🔲 Untested |
| Hyper Station: Setup Dashboard | `http://localhost:3001/d/[TODO-dashboard-uid]` | `$env`, `$project`, `$agent` | Lyndz | 🔴 High | 🔲 Untested |
| Agent Fleet View | `http://localhost:3001/d/[TODO-uid]?var-agent_type=[TODO]` | `$agent_type`, `$project` | Lyndz | 🔴 High | 🔲 Untested |
| Dev Environment Template | `http://localhost:3001/d/[TODO-uid]?var-env=dev` | `$env`, `$project` | Lyndz | 🟡 Medium | 🔲 Untested |
| HyperCode IDE UX Dashboard | `http://localhost:3001/d/[TODO-uid]` | `$env` | Lyndz | 🟡 Medium | 🔲 Untested |
| Prometheus Targets | `http://localhost:9090/targets` | None | Lyndz | 🟢 Low | 🔲 Untested |
| Grafana Alertmanager | `http://localhost:3001/alerting` | None | Lyndz | 🟢 Low | 🔲 Untested |

**v0.12 check focus:** Replace all `[TODO-uid]` placeholders with real dashboard UIDs. After upgrading to v0.12, open each URL and verify: correct dashboard loads · variables populate · time range preserved · no layout gaps.

---

## 📦 Section 7 — Provisioning & Template Files

Any Grafana provisioning JSON files or dashboard templates stored in the repo.

| File | What it provisions | v0.12 compatible? | Owner | Risk Level | v0.12 Status |
|------|-------------------|------------------|-------|-----------|-------------|
| `[TODO: path/to/grafana-provisioning/]` | [TODO] | [TODO] | Lyndz | 🔲 | 🔲 Untested |

> 💡 **Tip:** Run `find . -name "*.json" -path "*/provisioning/*"` or `find . -name "*.yaml" -path "*/grafana/*"` in your repo root to discover all provisioning files.

---

## 🤖 Section 8 — Embedded / Automated Dashboard Access

Any code that hits Grafana programmatically (API calls, screenshot automation, embed iframes).

| Code location | What it does | Grafana API used | v0.12 DOM/API change risk | Owner | v0.12 Status |
|---------------|-------------|-----------------|--------------------------|-------|-------------|
| `[TODO]` | [TODO] | [TODO] | [TODO] | Lyndz | 🔲 Untested |

> 💡 **Tip:** Search the codebase: `grep -r "localhost:3001" --include="*.py" --include="*.ts" --include="*.js" .`

---

## ✅ Track 2 Test Execution Log

Once you start testing, log results here:

| Date | What was tested | Result | Fix applied | Notes |
|------|----------------|--------|-------------|-------|
| [TODO] | [TODO] | [TODO] | [TODO] | [TODO] |

---

## 🔑 Quick audit commands

Run these in your repo root to find Hyper Station touchpoints you might have missed:

```powershell
# Find all scripts referencing Grafana
Select-String -Path "scripts\*.ps1","scripts\*.py","scripts\*.bat" -Pattern "grafana|3001|dashboard" -CaseSensitive:$false

# Find all hardcoded Grafana URLs
Select-String -Recurse -Pattern "localhost:3001|grafana" -Include "*.py","*.ts","*.js","*.json","*.yaml" .

# Find all variable injection patterns (e.g. ?var-env=)
Select-String -Recurse -Pattern "var-env|var-project|var-agent" -Include "*.py","*.ts","*.md","*.json" .
```

```bash
# Linux/WSL equivalents
grep -r "grafana\|3001\|dashboard" scripts/ --include="*.py" --include="*.sh"
grep -r "localhost:3001" . --include="*.py" --include="*.ts" --include="*.json"
grep -r "var-env\|var-project\|var-agent" . --include="*.py" --include="*.ts" --include="*.md"
```

---

*Part of the Hyper Station v0.12 Research Roadmap · [Full roadmap →](../notes/HyperStation-v0.12-WhatsNew.md)*
