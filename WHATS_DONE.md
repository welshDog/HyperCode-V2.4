# ✅ WHATS_DONE.md — HyperCode Ecosystem
> One file. Short bullets. No walls of text.
> **Updated: May 21, 2026 (dashboard rebuild + audit)** — update this every session.

---

## 🏗️ THE 5 REPOS

| Repo | What it is | Where |
|---|---|---|
| HyperCode-V2.4 | Main platform — Docker, FastAPI, agents, infra | `H:\HyperStation zone\HyperCode\HyperCode-V2.4` |
| HyperAgent-SDK | TypeScript SDK — agent spec, CLI, templates | `H:\HyperAgent-SDK` |
| Hyper-Vibe-Coding-Course | Course frontend + Supabase + token shop + Web3 pets | `H:\Hyper-Vibe-Coding-Course` |
| BROskiPets-LLM-dNFT | Pet NFT system — LLM + on-chain | `H:\dNFTpet\BROskiPets-LLM-dNFT` |
| BROski-Obsidian-Brain | Second Brain vault — Obsidian + GitHub bridge | `H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne` ✅ May 5 |

---

## 📋 SESSION REPORT — May 21, 2026

### 🖥️ Dashboard — Agent Monitor LIVE + rebuilt (corrected 2026-05-21 audit)
- ✅ **Agent Monitor tab WORKS** — `useAgentStatus` now polls REST `/api/v1/agents/status` every 5s (the WS `/api/v1/ws/agents` returns 404). Commit `1bd0a9a`.
- ✅ **Dashboard rebuilt + deployed** — image `88f2c40`, `hypercode-dashboard` healthy, `/agents` + `/api/health` → 200.
- ✅ Dockerfile healthcheck hardened `5s/15s → 10s/90s` — commit `31f9f7c`
- ✅ `AGENT-START.md` boot-file path fixed (`rewrites/` → `docs/`) — commit `4d3a18e`
- ✅ **MCP tab + IDE FULLY WORKING** — `mcp-rest-adapter` was never running (started it), then rewrote `app.py` from the dead MCP SSE transport to **Streamable HTTP** (what `docker/mcp-gateway:latest` actually speaks). Verified: `/tools/discover` → 28 real gateway tools; IDE file-open returns real content; path-escape → 403. See `docs/DASHBOARD_BACKEND_SCOPE.md`.
- ✅ **`mcp-rest-adapter` compose-managed** — first-class service in `docker-compose.agents.yml` (profile: agents). Commit `dfc4c31`.
- ✅ **Claude Code ↔ MCP chat tested** — `.mcp.json` → `:8823` → Core proven live. Fixed `hypercode_list_agents` (was 401 on auth-gated `/orchestrator/agents` → now public `/agents/status`).
- ✅ **`DASHBOARD_UPGRADE_COMPONENTS/` DELETED 2026-05-21** — dead staging prototype, never the live dashboard (`agents/dashboard/` is). Its bogus "0/8 backend endpoints" claim caused a whole misdirected audit. Gone now.

### 🔍 Full Ports Audit (39 containers)
- ✅ 37/39 Healthy (95%)
- ⚠️ `github-sync` — unhealthy (needs GITHUB_PAT in .env)
- ❌ `project-strategist` — exited (needs pip install perplexity-api)
- Full report: `FULL-PORTS-AUDIT-UPGRADE-REPORT.md`

### 🧹 System Cleanup Done
- 3 old hyper-vibe artifact containers removed
- ~600 MB freed (images + volumes)
- Report: `SYSTEM-CLEANUP-COMPLETE.md`

---

## 📋 SESSION REPORT — May 16, 2026

### 🔌 Live System Status (checked May 16)
| Platform | Status |
|---|---|
| Supabase `Hyper Vibe Coding Course` | ✅ ACTIVE_HEALTHY |
| Vercel `hyper-vibe-coding-course` | ✅ Live — BROskis team |
| Stripe `vibe-hook` | ✅ Active — 3 deliveries, 0 failures, avg 615ms |
| Edge Functions (10 total) | ✅ All ACTIVE |
| Supabase DB Webhook | ✅ Firing since April 27 |

### 🔒 Security Fixes Applied May 16 (migration: fix_security_invoker_functions)
| Function | Before | After |
|---|---|---|
| `complete_module` | ⚠️ SECURITY DEFINER — anon callable | ✅ SECURITY INVOKER |
| `complete_quest` | ⚠️ SECURITY DEFINER — anon callable | ✅ SECURITY INVOKER |
| `get_or_create_referral_code` | ⚠️ SECURITY DEFINER — anon callable | ✅ SECURITY INVOKER |
- **6 security warnings → all addressed** — leaked password protection (the last one) closed via a free HaveIBeenPwned check on Course signup; Supabase's own toggle is Pro-only

### ✅ Stripe Webhook Code Audit — PASSED (May 16)
- `stripe-webhook` v32 — signature verified, 5-step handlePurchase flow, idempotency built in ✅
- Events: `checkout.session.completed` + `customer.subscription.created` + `invoice.payment_succeeded` ✅
- All 5 price IDs mapped: starter/builder/hyper_legend tiers ✅

### ⚡ Performance Findings (INFO only — not urgent)
- 25 unused indexes across various tables
- `shop_items` — duplicate permissive RLS policies for SELECT — merge eventually

### 📦 Edge Functions Live (all 10 ACTIVE)
| Function | Version | JWT |
|---|---|---|
| `stripe-webhook` | v32 | ❌ Public (correct) |
| `sync-tokens-to-v24` | v23 | ❌ Public |
| `shop-purchase` | v28 | ✅ Auth required |
| `course-profile` | v26 | ✅ Auth required |
| `token-sync-to-v24` | v20 | ✅ Auth required |
| `mint-pet-auth` | v9 | ✅ Auth required |
| `get-pet-balance` | v5 | ✅ Auth required |
| `mint-pet-confirm` | v6 | ✅ Auth required |
| `truth-report` | v4 | ❌ Public |
| `pet-evolve-check` | v1 | ✅ Auth required |

---

## ✅ BUILT AND WORKING

### 🖥️ Dashboard — live + all 5 tabs working (May 21, 2026)
- Source: `agents/dashboard/` (Next.js) — builds the `hypercode-dashboard` image
- 5 tabs at `http://127.0.0.1:8088`: `/agents` `/mission` `/ide` `/docker-zone` `/mcp` — all verified working
- Backed by Next.js API proxy routes (`app/api/*`) → Core + `mcp-rest-adapter`
- ⚠️ The old `DASHBOARD_UPGRADE_COMPONENTS/` staging prototype was deleted — it was never the live dashboard

### 🧠 May 15–16, 2026 — NemoClaw "Alive" + Server Guardian
**NemoClaw autonomous code-health agent** (`agents/nemoclaw-agent/`, port 8099):
- L1 Heartbeat ✅ — ruff + detect-secrets + AST scan, grade S/A/B/C/D
- L2 Memory ✅ — scans persisted to `code_health_scans` (migration 012)
- L3 Voice ✅ — 24h pulse, auto-posts to Discord on grade/score move
- L3.5 Focus loop ✅ PROVEN — `/focus start` → `/focus stop` → BROski$ reward
- Mission tie-in ✅ — `/missions` + `/missions-claim`
- TODO: L4 auto-PR · L5 healer↔code correlation · L6 LLM triage

**Server Guardian** (autonomous Discord manager):
- P1 Reactive ✅ LIVE — auto-role on join + `/hyperfocus_setup`
- P2 Digest ✅ LIVE — weekly DM, Core aggregates last-7d from Postgres
- P3a Auto-mod ✅ LIVE — structural spam detect + reversible timeout
- P3b Raid lockdown ✅ LIVE — join-flood detect → reversible channel lock
- P3c Veto-ban ✅ BUILT — ban ONLY on explicit ✅ APPROVE click (NEVER autonomous)

**Infra:** Alembic up to **015**. Tests: **251 passed, 6 skipped** ✅

### 🔥 May 15, 2026 — Discord "One Brain" Lock-In
- **Option A enforced:** `broski-bot` calls Core only — no Supabase in bot ✅
- **Discord bot library locked:** `discord.py==2.4.0` ✅
- **Bot entrypoint locked:** `python -u -m cogs.bot` ✅
- **Core "One Door" endpoint:** `POST /api/v1/discord/actions` + idempotency ✅

### Infrastructure
- 39 containers audited May 21 — 37/39 healthy ✅
- 48 containers total (post-cleanup May 3) ✅
- 5 isolated networks — `data-net` + `obs-net` internal ✅
- Docker secrets pattern — `.txt` files, never baked into images ✅
- Kubernetes + Helm charts in `k8s/` + `helm/` ✅
- Memory limits on ALL services ✅
- Socket-proxy split — main read-only, healer proxy write-only ✅
- Weekly cleanup: `docker system prune -a --filter "until=168h"`

### Observability
- Prometheus 7/7 targets UP ✅
- Grafana at `:3001` ✅
- OTLP traces live in Tempo ✅
- Loki + Promtail — log aggregation running ✅
- Gordon Tier 3 dashboard + 10 alerts ✅

### Backend (FastAPI — hypercode-core)
- `/metrics` Prometheus endpoint ✅
- `/health` with Redis cache (10s TTL) ✅
- Rate limiting — Redis DB 2, Stripe webhook exempt ✅
- Circuit breakers — 3 active: `llm-router`, `crew-orchestrator`, `stripe-api` ✅
- Security headers middleware ✅

### Database
- PostgreSQL running, Alembic migrations up to `015` ✅
- Async engine + connection pooling (`asyncpg`, pool_size=10) ✅

### Stripe + Payments
- Full Stripe checkout + webhook + BROski$ awards ✅
- Webhook code audited May 16 — PERFECT ✅
- `scripts/Test-ShopPurchase.ps1` — E2E test passing ✅

### BROski$ Token Economy
- `public.users.broski_tokens` balance + `token_transactions` ledger ✅
- `award_tokens()` + `spend_tokens()` SECURITY INVOKER ✅
- Token grants: starter=200, builder=800, hyper=2500 ✅

### Course Frontend (Hyper-Vibe)
- `/pricing` → Stripe checkout → `/payment-success` → enrolled ✅
- Certificates, Quiz, Referral system ✅
- `/welcome` hero onboarding page LIVE on Vercel ✅
- Security headers 6/6 ✅

### 🐾 BROskiPets — WEB3 MINT LIVE 🔥 (May 7, 2026)
- RainbowKit + wagmi + viem Web3 wallet integration ✅
- Base Sepolia testnet + Base mainnet configured ✅
- Two-step mint flow (Edge Function auth + on-chain tx) ✅
- 10 pet species images + species catalogue ✅

### Agents (25+)
- healer-agent, agent-x, crew-orchestrator, hyper-architect, hyper-observer ✅
- MCP-GitHub LIVE — 26 tools via `mcp-gateway` ✅
- coder-agent ↔ Ollama end-to-end working ✅

### 🏆 Hyperfocus Features — ALL 5 DONE ✅
- Feature 1: Micro-Achievement Git Hook ✅
- Feature 2: HyperSplit Agent ✅
- Feature 3: Session Snapshot Agent ✅
- Feature 4: Morning Briefing `/briefing` ✅
- Feature 5: Focus/Panic Mode `make focus` / `make calm` ✅

### 🧠 BROski Brain — COMPLETE May 5 ✅
- Full PARA vault scaffold + Dashboard + Dataview live queries ✅
- GitHub bridge syncs 4 repos → vault ✅
- Obsidian Git: auto-commits vault every 10 mins ✅

### Security
- 3 DB functions fixed SECURITY DEFINER → INVOKER ✅ May 16
- Stripe keys rotated + scrubbed from 218 commits ✅
- GitPython 3.1.45 → **3.1.50** pinned ✅ May 22 — clears ALL 5 advisories (CVE-2026-42215, -42284, -44243, -44244 + GHSA-mv93-w799-cj2w RCE). ⚠️ The long-tracked "3.1.47" target was wrong — 3.1.47 still leaves 3 HIGH vulns open. Image rebuild pending.

### HyperAgent-SDK
- `@w3lshdog/hyper-agent@0.1.7` published ✅
- 57 tests passing ✅
- **⚠️ SDK needs update** — Web3/dNFT types not yet in spec — bump to v0.4.0

---

## 🔧 ONE-TIME MANUAL STEPS REMAINING

- [x] **Leaked password protection** — DONE via free HaveIBeenPwned check on Course signup (`48d2f9e`). Supabase's own toggle is Pro-plan only, so not used.
- [ ] **Fix GitHub Actions billing lock** — github.com/settings/billing
- [ ] Add `env_file: .env` to `hypercode-core` in `docker-compose.yml` (tech debt)
- [ ] Set `VITE_STRIPE_PAYMENT_LINK_URL` in `.env.local` + Vercel env vars
- [ ] Add `DISCORD_USER_ID=<your_id>` to `.env` so `make calm` awards tokens correctly
- [ ] Add `GITHUB_PAT` to `.env` + spin up `github-sync` Docker container → fixes unhealthy container
- [x] **GitPython CVE fix** — pinned 3.1.45 → 3.1.50 in `backend/requirements.txt` (May 22). 3.1.50 clears all 5 advisories; 3.1.47 (the old tracked target) was insufficient. ⚠️ Rebuild `hypercode-core` image for it to take effect.
- [ ] SDK bump to v0.4.0 — add Web3/dNFT types to `hyper-agent-spec.json`
- [ ] Clean up `shop_items` duplicate RLS policies
- [ ] Tidy 25 unused DB indexes (low priority — after launch)
- [ ] Fix `project-strategist`: `docker exec project-strategist pip install perplexity-api`

---

## 🚀 NEXT UP (in order)

1. **E2E checkout test** — `stripe listen + card 4242 4242 4242 4242`
2. **BROskiPets Web3 E2E** — test mint on Base Sepolia testnet with real wallet
3. **First student invite** — `/welcome` is green 🎓
4. **HyperAgent-SDK v0.4.0** — Web3/dNFT types in spec
5. **Fix GitHub Actions billing lock**
6. **Level 13** — Morning Briefing live
7. **Level 14** — GitHub Webhooks real-time
8. **Level 15** — HyperAgent AI Daily Briefing

---

## 🔑 KEY FACTS (never re-look-up)

```
Start command:    docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
AI backend:       docker compose --profile ai up -d
Discord bot:      docker compose --profile discord up -d broski-bot
Tests:            pytest backend/tests -q  (251 passed, 6 skipped — verified May 16)
Dashboard:        http://127.0.0.1:8088 — tabs: /agents /mission /ide /docker-zone /mcp
Prometheus live:  monitoring/prometheus/prometheus.yml
Redis DB split:   DB 1 = cache  |  DB 2 = rate limits
Stripe webhook:   ALWAYS rate-limit exempt
Alembic:          up to 015
Supabase table:   courses uses price_pence (int) + is_active (bool)
Docker context:   must be 'desktop-linux' on Windows
Memory limits:    ALL services capped
healthcheck:      hypercode-core uses localhost not 127.0.0.1 (IPv6)
make focus:       stops 14 non-essential containers + 25-min timer
make calm:        restores all + awards 75 BROski$
broski-pets:      health → http://localhost:8098/health
nemoclaw-agent:   health → http://localhost:8099/health  (profile: nemoclaw)
launch bot:       .\scripts\launch-bot.ps1
Guardian P3c:     ban ONLY on explicit APPROVE click — NEVER autonomous ban
Course path:      H:\Hyper-Vibe-Coding-Course
Course dev:       npm run dev:frontend
Brain repo:       H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne
GitHub sync:      python scripts/github_to_obsidian.py (needs GITHUB_PAT env var)
Obsidian Git:     auto-commits vault every 10 mins to brain repo
IDE:              Claude Code terminal + Perplexity AI (Windows)
Stripe webhook:   secret updated May 5 ✅ — fresh whsec_ live in Supabase
BROskiPets Web3:  RainbowKit + wagmi + Base Sepolia — mint live May 7 🔥
Mint flow:        Edge Function auth → on-chain Base Sepolia tx
GitPython:        pinned 3.1.50 (clears all 5 CVEs) — rebuild core image to apply
Security funcs:   complete_module, complete_quest, get_or_create_referral_code → SECURITY INVOKER ✅
Supabase project: yhtmuibgdnxhbgboajhc (eu-west-2)
Vercel team:      BROskis (team_Uy6hGYD4AZqclHqUeEsmZuDP)
github-sync:      unhealthy — add GITHUB_PAT to .env to fix
project-strategist: exited — pip install perplexity-api to fix
```

---

## 📁 WHERE THINGS LIVE

```
docker-compose.yml                    — main stack
docker-compose.secrets.yml            — secrets injection
backend/app/main.py                   — FastAPI core
backend/app/core/config.py            — all settings
monitoring/prometheus/                — LIVE Prometheus config
frontend/vercel.json                  — Vercel config + security headers
frontend/src/pages/Welcome.tsx        — hero onboarding page (LIVE)
scripts/Test-ShopPurchase.ps1         — E2E shop test
scripts/STRIPE_E2E_RUNBOOK.md         — Stripe E2E test steps
agents/                               — all agent code
secrets/                              — Docker secrets (.txt files, gitignored)
DASHBOARD_UPGRADE_COMPONENTS/         — Dashboard v2.0 source + deploy scripts ✅ NEW
SESSION_SNAPSHOT_2026-05-21.md        — today's brain save file ✅ NEW
```
