# 🤖 HyperAgent-SDK + Hyperfocus Zone — Claude Context Handoff
> Read this first. Every word. Then start the mission.
> **Last updated: April 14, 2026 — Phase 8: CI/CD Trivy Security Pipeline**

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

## Roadmap — Phases 0–7 COMPLETE 🏆 + Phase 8 IN PROGRESS

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
| **8** | **CI/CD Trivy Security Pipeline** | **✅ DONE — April 14, 2026** |

---

## 🚨 PHASE 8 — CI/CD Trivy Security Pipeline (CURRENT MISSION)

### Goal
Every time a Dockerfile is changed and pushed to GitHub, Trivy automatically scans the
rebuilt image. If any CRITICAL CVE is found → the build FAILS and blocks the merge.
No more manual scanning. Security is automated and enforced.

### Deliverables — Build These in Order

#### 1. GitHub Actions Workflow — `.github/workflows/trivy-scan.yml`
```yaml
name: 🔒 Trivy Security Scan

on:
  push:
    branches: [main, develop]
    paths:
      - 'agents/**/Dockerfile'
      - 'docker-compose.yml'
  pull_request:
    branches: [main]
    paths:
      - 'agents/**/Dockerfile'

jobs:
  trivy-scan:
    name: Scan ${{ matrix.agent }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        agent:
          - agent-x
          - healer
          - coder
          - crew-orchestrator
          - 01-frontend-specialist
          - 02-backend-specialist
          - 03-database-architect
          - 04-qa-engineer
          - 05-devops-engineer
          - 06-security-engineer
          - 07-system-architect
          - 08-project-strategist
          - 09-tips-tricks-writer
          - broski-bot
          - throttle-agent
          - coderabbit-webhook

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build image
        run: |
          docker build -t hypercode-scan-${{ matrix.agent }}:ci \
            ./agents/${{ matrix.agent }}/

      - name: Run Trivy scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: hypercode-scan-${{ matrix.agent }}:ci
          format: table
          exit-code: '1'
          severity: CRITICAL
          scanners: vuln

      - name: Upload Trivy SARIF (optional — GitHub Security tab)
        uses: aquasecurity/trivy-action@master
        if: always()
        with:
          image-ref: hypercode-scan-${{ matrix.agent }}:ci
          format: sarif
          output: trivy-${{ matrix.agent }}.sarif
          scanners: vuln

      - name: Upload SARIF to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: trivy-${{ matrix.agent }}.sarif
```

#### 2. Weekly Full-Fleet Scan — `.github/workflows/trivy-weekly.yml`
```yaml
name: 🔒 Weekly Fleet Security Scan

on:
  schedule:
    - cron: '0 6 * * 1'  # Every Monday 06:00 UTC
  workflow_dispatch:      # Also manual trigger

jobs:
  weekly-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build + scan all agents
        run: |
          for dir in agents/*/; do
            agent=$(basename $dir)
            if [ -f "$dir/Dockerfile" ]; then
              echo "🔍 Scanning $agent..."
              docker build -t hypercode-weekly-$agent:scan $dir
              docker run --rm \
                -v /var/run/docker.sock:/var/run/docker.sock \
                aquasec/trivy image \
                --scanners vuln \
                --severity HIGH,CRITICAL \
                --format json \
                --output /tmp/trivy-$agent.json \
                hypercode-weekly-$agent:scan
            fi
          done

      - name: Aggregate results
        run: |
          echo "# 📊 Weekly Trivy Fleet Report" > weekly-report.md
          echo "Generated: $(date -u)" >> weekly-report.md
          for f in /tmp/trivy-*.json; do
            agent=$(basename $f .json | sed 's/trivy-//')
            criticals=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' $f 2>/dev/null || echo 0)
            highs=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH")] | length' $f 2>/dev/null || echo 0)
            echo "| $agent | $criticals CRITICAL | $highs HIGH |" >> weekly-report.md
          done

      - name: Upload report artifact
        uses: actions/upload-artifact@v4
        with:
          name: weekly-trivy-report
          path: weekly-report.md
          retention-days: 90
```

#### 3. Local Pre-Push Hook — `scripts/trivy-pre-push.sh`
```bash
#!/bin/bash
# Run before git push to catch CVEs locally
# Install: cp scripts/trivy-pre-push.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push

set -e
CHANGED=$(git diff --name-only HEAD~1 | grep Dockerfile || true)

if [ -z "$CHANGED" ]; then
  echo "✅ No Dockerfiles changed — skipping Trivy scan"
  exit 0
fi

echo "🔒 Dockerfiles changed — running Trivy pre-push scan..."
FAILED=0

for f in $CHANGED; do
  dir=$(dirname $f)
  agent=$(basename $dir)
  echo "🔍 Building + scanning $agent..."
  docker build -t hypercode-prepush-$agent:check $dir
  trivy image --scanners vuln --severity CRITICAL --exit-code 1 --quiet \
    hypercode-prepush-$agent:check || {
    echo "🔴 CRITICAL CVEs found in $agent — push blocked!"
    FAILED=1
  }
done

if [ $FAILED -eq 1 ]; then
  echo "\n🚨 Fix all CRITICAL CVEs before pushing."
  exit 1
fi

echo "✅ All scans passed! Pushing..."
```

#### 4. Makefile targets — add to existing `Makefile` (or create one)
```makefile
# Security scanning shortcuts
scan-agent:  ## scan a single agent: make scan-agent AGENT=healer
	docker exec hyper-shield-scanner trivy image \
		--scanners vuln --severity HIGH,CRITICAL --quiet \
		hypercode-v24-$(AGENT)

scan-all:  ## scan every agent image
	@for agent in agent-x healer coder crew-orchestrator broski-bot \
	  01-frontend-specialist 02-backend-specialist 03-database-architect \
	  04-qa-engineer 05-devops-engineer 06-security-engineer \
	  07-system-architect 08-project-strategist 09-tips-tricks-writer \
	  throttle-agent coderabbit-webhook; do \
	  echo "🔍 Scanning $$agent..."; \
	  docker exec hyper-shield-scanner trivy image \
	    --scanners vuln --severity CRITICAL --quiet \
	    hypercode-v24-$$agent && echo "✅ $$agent CLEAN" || echo "🔴 $$agent FAILED"; \
	done

build-secure:  ## rebuild all + scan: make build-secure
	docker compose build --no-cache
	$(MAKE) scan-all
```

### Phase 8 File Checklist
```
✅ .github/workflows/trivy-scan.yml         ← blocks PRs with CRITICAL CVEs
✅ .github/workflows/trivy-weekly.yml       ← Monday 06:00 UTC fleet scan
✅ scripts/trivy-pre-push.sh                ← local hook, catches issues before push
✅ Makefile                                 ← make scan-all / make build-secure
✅ SECURITY_PATCH_REPORT.md                 ← Phase 7 audit trail
```

### Phase 8 Done When
- [ ] `trivy-scan.yml` is in `.github/workflows/` and visible in Actions tab
- [ ] A test PR with a deliberately bad Dockerfile fails the scan ✅
- [ ] `trivy-weekly.yml` shows in Actions → scheduled workflows
- [ ] `make scan-all` runs clean against the current fleet
- [ ] `scripts/trivy-pre-push.sh` installed as `.git/hooks/pre-push`
- [ ] `SECURITY_PATCH_REPORT.md` committed with Phase 7 before/after summary

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
- **Dockerfiles:** ALWAYS include apt-get upgrade + pip upgrade — Phase 7 pattern
- **Trivy:** CRITICAL = build fails. HIGH = warning only. Target: 0 CRITICAL, <5 HIGH.
- **GitHub Actions:** Never hardcode secrets — use `${{ secrets.X }}` always

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
1. `backend/alembic/versions/003_add_discord_id.py`
2. `backend/app/models/models.py` — discord_id on User ORM
3. `backend/app/schemas/schemas.py` — discord_id in UserBase
4. `backend/app/api/v1/endpoints/users.py` — GET /api/v1/users/by-discord/{discord_id}
5. `supabase/functions/course-profile/index.ts`
6. `agents/broski-bot/src/cogs/course_stats.py` — /coursestats Discord command
7. `bot.py` + `settings.py` — wired cog + course_profile_edge_url
**Verified:** /coursestats shows dual-system embed ✅

### Phase 2 ✅ DONE + VERIFIED
1. `backend/alembic/versions/004_add_course_sync_events.py`
2. `backend/app/models/broski.py` — CourseSyncEvent ORM model
3. `backend/app/core/config.py` — COURSE_SYNC_SECRET
4. `backend/app/api/v1/endpoints/economy.py` — POST /api/v1/economy/award-from-course
5. `backend/app/api/api.py` — economy router wired
6. `supabase/functions/sync-tokens-to-v24/index.ts`
**Dedup:** App-level 409 check + DB UNIQUE constraint on source_id ✅

### Phase 3 ✅ DONE + VERIFIED
1. `backend/alembic/versions/005_add_access_provisions.py`
2. `backend/app/models/models.py` — AccessProvision ORM model added
3. `backend/app/api/v1/endpoints/access.py` — POST /api/v1/access/provision
4. `backend/app/core/config.py` — SHOP_SYNC_SECRET, DISCORD_BOT_TOKEN, MISSION_CONTROL_URL
5. `supabase/functions/provision-access/index.ts` — fires on shop_purchases INSERT
6. Router wired in `backend/app/api/api.py`
**Verified:** Buy "Agent Sandbox Access" → Discord DM with api_key + mission_control_url ✅

### Phase 4 ✅ DONE + VERIFIED
1. `backend/alembic/versions/006_add_graduation_events.py`
2. `backend/app/models/graduate.py` — GraduationEvent ORM model
3. `backend/app/api/v1/endpoints/graduate.py` — POST /api/v1/graduate/trigger
4. `supabase/functions/graduate-student/index.ts`
5. Router wired in `backend/app/api/api.py`
**Table confirmed:** public.graduation_events ✅

### Phase 5 ✅ DONE + VERIFIED LIVE
1. `backend/app/core/logging.py` — structured JSON logging
2. `backend/app/middleware/metrics.py` — MetricsMiddleware
3. `backend/app/api/v1/endpoints/health.py` — GET /health live
4. `agents/broski-bot/src/cogs/ops_alerts.py` — Discord #ops-alerts
5. `monitoring/prometheus.yml` + `monitoring/grafana/dashboards/hypercode.json`
**Verified:** /health → ok ✅ | /metrics → full Prometheus output ✅ | <5ms latency ⚡

### Phase 6 ✅ DONE + VERIFIED LIVE (2026-04-13 17:59 BST)
**CLI commands in HyperAgent-SDK/cli/commands/:**
1. `status.js` — ✅ VERIFIED
2. `logs.js` — ✅ VERIFIED
3. `tokens.js` — ✅ VERIFIED
4. `agents.js` — ✅ VERIFIED
5. `graduate.js` — ✅ VERIFIED

**Logs routing fix (2026-04-13):**
- Root cause: `dashboard.py` GET /logs shadowing `logs_broadcaster.py`
- Fix: moved `logs_broadcaster.router` BEFORE `dashboard_compat` in api.py
- Result: 200 `{"logs":[],"total":0}` ✅

### Phase 7 ✅ DONE (2026-04-14)
19 Dockerfiles patched across 4 categories:
- **Non-root user:** 12 standard agents
- **Non-root + docker group (GID 999):** healer, coder, agent-x, 05-devops-engineer
- **Full multi-stage rewrite:** 09-tips-tricks-writer (was silently running as root)
- **Env + healthcheck gaps:** coderabbit-webhook, throttle-agent, project-strategist, healer
- **Already clean (no changes):** base-agent, broski-bot, super-hyper-broski-agent, hyper-auto-assistant, hyperhealth, test-agent, dashboard, backend

---

## Paths (copy-paste ready)

```powershell
# HyperAgent-SDK
cd "H:\HyperAgent-SDK"

# HyperCode V2.4
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"

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
make build-secure
docker exec hyper-shield-scanner trivy image --scanners vuln --severity HIGH,CRITICAL --quiet hypercode-v24-agent-x

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
