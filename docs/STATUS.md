# 📊 Live System Status
> **This is the living state doc.** Update every session.
> Last updated: **August 19, 2026**
> For sacred rules + architecture → `CLAUDE.md`

---

## HyperLabs / Vibe Labs Funnel

| Metric | Status |
|---|---|
| Funnel | `/vibe-labs` hub + 5 level pages + landing funnel LIVE ✅ |
| DB | `claim_level_reward` RPC + `user_level_progress` — prod, real-user tested ✅ |
| Migration | `supabase/migrations/20260518000035_claim_level_reward.sql` DEPLOYED ✅ |
| Perf | cold funnel **1,270 kB → ~61 kB gzip** 🚀 |
| a11y | Lighthouse A11Y 100 / Best-Practices 100 ✅ |
| Deploy | Vercel `state: READY` at HEAD `3bef345` ✅ |
| Sprint 4 | Anon→signup conversion LIVE (`a12ecd0`) ✅ |

---

## HyperCode V2.4 — Core Platform

| Metric | Status |
|---|---|
| Containers | **25 agents** total (13 existing + 12 ghost agents building) 🔨 |
| **Ghost Agent Fleet** | 12 new agents committed & building — see Agent Fleet table below |
| **HyperStudio** | agent write path LIVE 🏗️ — `coder-studio` :8087 (profiles `agents`/`studio`) |
| Dashboard | celery-worker restored · `/docker-zone` · `/pricing` redirects LIVE ✅ |
| Tests | 251 passed, 6 skipped ✅ |
| NemoClaw | L1–L3.5 LIVE 🧠 (port 8099) |
| Server Guardian | P1–P3b LIVE · P3c BUILT 🛡️ |
| Alembic | up to **015** |
| Prometheus | 7/7 targets UP ✅ |
| OTLP Traces | LIVE in Tempo ✅ |
| Circuit Breakers | 3 active — all CLOSED ✅ |
| Docker AI Grade | A 🏅 |
| Stripe | **TEST mode** 💳 — LIVE wiring pending |
| Gamification | HUD, XP, Quests, Leaderboard LIVE ✅ |
| BROskiPets Web3 | LIVE on Base Sepolia 🔥 |
| broski-bot | OPTION A LIVE 🤖 |
| Shop Fulfillment v2 | BUILT 🛒 — deploy + E2E pending |
| Mission Control `/control` | ✅ LIVE — `localhost:8088/control` |
| Governance Ledger | ✅ LIVE + PROVEN |
| Safety Loop | ✅ HyperFlow ✅ Studio ✅ Crew-orchestrator ✅ Ledger |

---

## 🤖 Agent Fleet — 25 Total

> 🔴 **STALE — this section's ports do not match reality.** It predates the
> 2026-08-19/08-20 fleet reconciliation (`docker-push.yml` build matrix is
> canonical — see `CLAUDE.md`'s "CURRENT STATE" section, kept current as of
> 2026-08-20). Example: this table says `crew-orchestrator :8010` and
> `safety-shepherd :8012`; the real, live values are `:8081` and `:8096`. Don't
> trust the port numbers below — read `CLAUDE.md` instead. Left as-is rather than
> silently rewritten, per "surface contradictions visibly" — needs a real pass,
> not a drive-by fix. See `docs/NEXT_TASKS.md`.

### ✅ Existing Agents (13)
> Core stack — live and stable

| Agent | Port | Status |
|---|---|---|
| crew-orchestrator | :8010 | ✅ Live |
| hyperflow | :8011 | ✅ Live |
| safety-shepherd | :8012 | ✅ Live |
| coder-studio | :8087 | ✅ Live |
| nemo-claw | :8099 | ✅ Live |
| server-guardian | :8013 | ✅ Live |
| mission-control | :8088 | ✅ Live |
| broski-identity | :8020 | ✅ Live |
| brain-constellation | :8021 | ✅ Live |
| hyper-skills | :8022 | ✅ Live |
| evo-harness | :8023 | ✅ Live |
| governance-ledger | :8024 | ✅ Live |
| specialist-bibles | :8025 | ✅ Live |

### 🔨 Ghost Agents — Now Building (12)
> Committed: `296e3a36`, `22089803`, `61bc5ca5`

| Agent | Port | Status |
|---|---|---|
| security-engineer | :8007 | ✅ Built |
| system-architect | :8008 | 🔨 Building |
| test-agent | :8080 | 🔨 Building — ⚠️ check port clash |
| throttle-agent | :8014 | 🔨 Building |
| tips-tricks-writer | :8009 | 🔨 Building |
| super-hyper-broski | :8015 | 🔨 Building |
| hyper-architect | :8091 | 🔨 Building |
| hyper-observer | :8092 | 🔨 Building |
| hyper-worker | :8093 | 🔨 Building |
| hyper-split-agent | :8096 | 🔨 Building |
| session-snapshot | :8097 | 🔨 Building |
| agent-x | custom | 🔨 Building |

---

## ⚠️ Known Risks

| Risk | Action |
|---|---|
| Port :8080 collision | Run `grep -r "ports:" docker-compose*.yml \| sort` before launch |
| Memory pressure at 25 agents | Add `mem_limit: 256m` + `cpus: "0.25"` to new agent compose entries |
| crew-orchestrator SPOF | Confirm `restart: unless-stopped` + `/health` endpoint live |
| Service JWT expiry | `DASHBOARD_SERVICE_JWT` expires 2027-07-13 — re-mint before then |
