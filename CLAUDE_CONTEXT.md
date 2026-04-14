# 🤖 HyperAgent-SDK + Hyperfocus Zone — Claude Context Handoff
> Read this first. Every word. Then start the mission.
> **Last updated: April 14, 2026 — Phase 9: CVE Elimination (apt-get + pip pinning)**

---

## Who You're Talking To
- **Lyndz** aka BROski♾️ (GitHub: @welshDog, npm: @w3lshdog) — South Wales
- Autistic + dyslexic + ADHD — chunked output, quick wins first, no waffle
- Windows primary (PowerShell), WSL2 + Raspberry Pi + Docker secondary
- Call them **"Bro"** — that's how we roll
- Short sentences. Emojis. Bold the key stuff. Celebrate wins!

---

## The Ecosystem

```
Hyper-Vibe-Coding-Course     ──── manifest.json ────▶    HyperCode V2.4
github.com/welshDog/             (hyper-agent-spec)       github.com/welshDog/
Hyper-Vibe-Coding-Course                                  HyperCode-V2.4
(Supabase + Vercel)                    │                  (Docker, 26 containers)
Path: H:\the hyper vibe coding hub     │                  Path: H:\HyperStation zone\
                                       │                       HyperCode\HyperCode-V2.4
                              HyperAgent-SDK
                          github.com/welshDog/HyperAgent-SDK
                          npm: @w3lshdog/hyper-agent@0.1.4
                          Path: H:\HyperAgent-SDK
```

---

## Roadmap — Phases 0–8 COMPLETE 🏆 + Phase 9 IN PROGRESS

| Phase | Name | Status |
|---|---|---|
| 0 | Hard Conflict Fixes | ✅ DONE |
| 1 | Identity Bridge | ✅ DONE + VERIFIED LIVE |
| 2 | Token Sync | ✅ DONE + VERIFIED LIVE |
| 3 | Agent Access + Shop Bridge | ✅ DONE + VERIFIED LIVE |
| 4 | npm run graduate 🔥 | ✅ DONE + VERIFIED LIVE |
| 5 | Observability | ✅ DONE + VERIFIED LIVE |
| 6 | Terminal Tools | ✅ DONE + VERIFIED LIVE |
| 7 | Dockerfile Security Hardening | ✅ DONE — April 14, 2026 |
| 8 | CI/CD Trivy Security Pipeline | ✅ DONE — April 14, 2026 |
| **9** | **CVE Elimination (apt + pip pinning)** | **🟡 IN PROGRESS — April 14, 2026** |

---

## 🚨 PHASE 9 — CVE Elimination (CURRENT MISSION)

### Context
Phase 7 added non-root users + Phase 8 wired Trivy into CI.
But Trivy is now CATCHING real CVEs that still exist:
- `libexpat1` — CRITICAL XML parsing CVE (affects most agents)
- `libc6` / `glibc` — HIGH memory safety CVEs
- `openssl` / `libssl3` — HIGH TLS CVEs
- `jaraco.context` / `wheel` — pip package CVEs

Root cause: `apt-get upgrade -y` in Phase 7 Dockerfiles upgrades at **build time**,
but base image cache can be weeks old by the time CI pulls it.
Fix: force fresh `apt-get update` + pin specific patched packages + use `--no-cache` in CI.

### The 3-Part Fix Strategy

#### Part A — Dockerfile OS Package Fix (apply to ALL 19 patched agents)
```dockerfile
# Force fresh package list + upgrade all + install security tools
RUN apt-get update --allow-releaseinfo-change && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libexpat1 \
        openssl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
```

Key additions vs Phase 7:
- `--allow-releaseinfo-change` — avoids apt blocking on Debian point release changes
- Explicitly install `libexpat1` + `openssl` — forces latest patched version
- Clean `/tmp/*` and `/var/tmp/*` — kills temp file CVE surface

#### Part B — pip Pinning Fix (apply to ALL Python agents)
```dockerfile
# Pin exact safe versions (update these when new releases drop)
RUN pip install --upgrade --no-cache-dir \
    "pip>=26.0.0" \
    "setuptools>=80.0.0" \
    "wheel>=0.46.0" \
    "jaraco.context>=6.0.0" \
    "jaraco.functools>=4.1.0" \
    "jaraco.text>=4.0.0"
```

Why explicit jaraco.* pins: these are transitive deps of setuptools.
Trivy flags them as HIGH. Pinning explicitly forces the safe version.

#### Part C — CI `--no-cache` enforcement in trivy-scan.yml
Change the build step in `.github/workflows/trivy-scan.yml`:
```yaml
# BEFORE (Phase 8 — could use stale cache)
- name: Build image
  run: |
    docker build -t hypercode-scan-${{ matrix.agent }}:ci \
      ./agents/${{ matrix.agent }}/

# AFTER (Phase 9 — always fresh, no stale package cache)
- name: Build image (no cache)
  run: |
    docker build --no-cache --pull \
      -t hypercode-scan-${{ matrix.agent }}:ci \
      ./agents/${{ matrix.agent }}/
```

`--pull` forces GitHub Actions to always pull the latest `python:3.11-slim` base,
so new OS patches in the upstream image are picked up automatically.

### Priority Order — Do These Agents First
```
1. agent-x              ← 🔴 Was 11 CRITICAL — highest risk
2. healer               ← 🔴 Docker socket access — high blast radius
3. coder                ← 🔴 Docker socket access
4. 05-devops-engineer   ← 🔴 Docker socket access
5. crew-orchestrator    ← 🕾️ Orchestrates all others
6-19. All remaining agents (alphabetical order fine)
```

### Verify After Each Agent
```powershell
# Rebuild single agent (from H:\HyperStation zone\HyperCode\HyperCode-V2.4)
docker compose build --no-cache <agent-service-name>

# Scan it
make scan-agent AGENT=agent-x

# Target per agent: 0 CRITICAL, <5 HIGH
```

### Phase 9 Done When
- [ ] `make scan-all` shows 0 CRITICAL across ALL 19 agents
- [ ] CI `trivy-scan.yml` passes green on a test PR
- [ ] `trivy-scan.yml` updated with `--no-cache --pull`
- [ ] `SECURITY_PATCH_REPORT.md` updated with Phase 9 before/after CVE counts
- [ ] All 19 Dockerfiles have the Part A + Part B pattern

---

## ✅ Phase 8 — CI/CD Trivy Pipeline COMPLETE (April 14, 2026)

### 4 Deliverables Shipped

**1. `.github/workflows/trivy-scan.yml` — PR Gate**
- Triggers on any `agents/**/Dockerfile` or `backend/Dockerfile` change
- Matrix of 19 agents — all parallel, `fail-fast: false`
- Smart build context split: root context (`.`) for healer/agent-x/hyper-agents/05-devops (root-relative COPY paths), local context for everyone else
- CRITICAL gate: `exit-code: 1` — blocks merge on any CRITICAL CVE
- SARIF upload → GitHub Security tab
- Pinned `aquasecurity/trivy-action@0.28.0` (not `@master` — avoids supply-chain irony 😄)
- Job summary written on every run

**2. `.github/workflows/trivy-weekly.yml` — Monday Fleet Scan**
- Cron `0 6 * * 1` + manual `workflow_dispatch`
- Same 19-agent matrix, `exit-code: 0` — never blocks, just reports
- Python aggregator job: collects all JSON outputs, generates markdown fleet report with CRITICAL/HIGH counts per agent
- Artifacts retained 90 days

**3. `scripts/trivy-pre-push.sh` — Local Pre-Push Hook**
- Install: `make trivy-hook-install`
- Detects changed Dockerfiles via `git diff HEAD~1 HEAD`
- Auto-detects Trivy (local binary or Docker image fallback)
- Blocks push if any CRITICAL found, prints fix tips
- Cleans up built images after scan

**4. `Makefile` — 4 New Targets**
```makefile
make scan-agent AGENT=healer   # scan live image via hyper-shield-scanner
make scan-all                   # scan entire fleet
make scan-build AGENT=healer    # build + scan from Dockerfile source
make trivy-hook-install         # wire up the pre-push hook
```

---

## 🚨 Known Rules (never re-debate these)

- **Docker imports:** `from app.X import Y` — NEVER `from backend.app.X import Y`
- **FastAPI routing:** First-match wins — public routes BEFORE auth-gated compat routes
- **Alembic down_revision:** Must match EXACT revision string
- **CLI folder:** All `hyper-agent` commands run from `H:\HyperAgent-SDK`
- **Logs empty on fresh boot:** Normal — Redis `hypercode:logs` populates as agents run
- **Port convention:** 3100-3199 writing, 3200-3299 code, 3300-3399 data, 3400-3499 discord, 3500-3599 automation
- **Supabase ↔ V2.4 Postgres:** NEVER merge schemas
- **`.env` files:** Never committed — use Docker secrets in production
- **One bot:** broski-bot. Old Replit bot = dead.
- **API keys:** `hc_` prefix + `secrets.token_urlsafe(32)`
- **Dockerfiles:** apt-get upgrade + pip upgrade + explicit libexpat1/openssl install — Phase 9 pattern
- **Trivy:** CRITICAL = build fails. HIGH = warning only. Target: 0 CRITICAL, <5 HIGH.
- **GitHub Actions:** Never hardcode secrets — use `${{ secrets.X }}` always
- **CI builds:** Always `--no-cache --pull` in security scanning workflows
- **jaraco.* packages:** Always pin explicitly — they’re Trivy HIGH via setuptools transitive

---

## ✅ Phases 0–7 — Full History

### HyperAgent-SDK ✅ SHIPPED
- `cli/validate.js` — AJV validator, coloured output, exit codes
- `hyper-agent-spec.json` — JSON Schema, if/then port enforcement
- `templates/python-starter/` + `templates/node-starter/` — both valid
- `npm test` — 2/2 passing ✅
- Published: `@w3lshdog/hyper-agent@0.1.4` live on npm ✅

### Phase 0 ✅ DONE
- `docker-compose.yml` — port 5432 removed, apps/web dropped
- `discord-bot/cogs/xp.py` — /leaderboard → /xp-leaderboard
- `002_add_discord_id_to_users.py` — Alembic migration created

### Phase 1 ✅ DONE + VERIFIED
- discord_id bridge: Alembic migration, ORM, schema, endpoint, Edge Function, /coursestats Discord command

### Phase 2 ✅ DONE + VERIFIED
- Token sync: CourseSyncEvent ORM, /award-from-course endpoint, sync Edge Function, dedup guards

### Phase 3 ✅ DONE + VERIFIED
- Agent access: AccessProvision ORM, /provision endpoint, shop_purchases trigger, Discord DM delivery

### Phase 4 ✅ DONE + VERIFIED
- Graduation: GraduationEvent ORM, /graduate/trigger endpoint, Edge Function

### Phase 5 ✅ DONE + VERIFIED LIVE
- Observability: structured JSON logging, MetricsMiddleware, /health + /metrics live, Grafana dashboard

### Phase 6 ✅ DONE + VERIFIED LIVE (2026-04-13)
- CLI: status / logs / tokens / agents / graduate — all 5 verified
- Logs routing fix: broadcaster moved before dashboard_compat in api.py

### Phase 7 ✅ DONE (2026-04-14)
- 19 Dockerfiles patched: non-root users, docker group, multi-stage rewrite for tips-tricks-writer, env+healthcheck gaps filled

### Phase 8 ✅ DONE (2026-04-14)
- trivy-scan.yml (PR gate), trivy-weekly.yml (Monday fleet scan), trivy-pre-push.sh (local hook), Makefile targets

---

## Paths (copy-paste ready)

```powershell
# HyperCode V2.4
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"

# HyperAgent-SDK
cd "H:\HyperAgent-SDK"

# Hyper-Vibe-Coding-Course
cd "H:\the hyper vibe coding hub"

# Docker
docker compose up -d
docker compose build --no-cache
docker compose exec api alembic upgrade head
docker compose logs api --tail 50

# Security scanning
make scan-all
make scan-agent AGENT=healer
make scan-build AGENT=agent-x
make build-secure

# CLI (from H:\HyperAgent-SDK)
$env:HYPERCODE_API_URL = "http://localhost:8000"
node cli/index.js status
node cli/index.js agents list
node cli/index.js logs --tail 20
node cli/index.js tokens award <discord_id> <amount>
node cli/index.js graduate <discord_id> --tokens 100
```

---

## npm / SDK Quick Reference

```powershell
npx @w3lshdog/hyper-agent validate .agents/my-agent/
npm version patch --no-git-tag-version
npm publish --access public --tag alpha
```

---

## BROski$ Token Economy

- `public.users.broski_tokens` — balance column
- `token_transactions` — append-only ledger with idempotency guards
- `award_tokens()` + `spend_tokens()` — SECURITY DEFINER, server-side only
- `shop_items` + `shop_purchases` — JSONB metadata fields
- `shop_purchases.item_slug` — used to filter for "agent-sandbox-access"
- Stripe integration for token packs (Starter/Builder/Hyper)
