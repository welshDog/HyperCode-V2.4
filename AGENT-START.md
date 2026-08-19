# 🚀 AGENT-START.md — HyperFocus Z0ne MASTER Boot File
> **For ANY AI, agent, or human joining the full HyperFocus Z0ne ecosystem.**
> Read this file FIRST. Every session. No exceptions.
> Built by @welshDog — **v3.3 (upgraded 2026-08-19)** · supersedes v3.2 (2026-06-16)

> 📌 **Live truth ALWAYS wins:** Read the newest `DASHBOARD_STATUS_YYYY-MM-DD.md` + newest `NEXT_SESSION_HANDOVER_*.md` BEFORE anything else. **This file is the constitution, not the news.**

---

## ⚡ WHO YOU'RE WORKING WITH

- **Name:** Lyndz Williams (@welshDog) — call them **Bro** or **BROski**
- **Location:** Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁧
- **Brain:** ADHD + Dyslexia + Autistic — hyperfocus is a SUPERPOWER ⚡
- **Mission:** Building the world's first neurodivergent-first autonomous AI infrastructure platform
- **Vibe:** Friendly, fast, casual. Short sentences. Celebrate every win.

---

## 📋 STEP 1 — READ THESE FILES (in order, every session)

```
Workspace root: H:\HYPERFOCUSZONE\HperCore   (NOT a git repo — workspace only)
```

1. `DASHBOARD_STATUS_[latest date].md` → 🔴 LIVE blockers + proof status **(WINS HERE)**
2. `ECOSYSTEM_HANDOVER.md` → cross-repo contracts + P0s
3. `PORTAL.md` → tabs hub + jump points
4. In your target repo → see the **§4 doc-authority map** below — some repos use `CLAUDE.md`, others use `WHATS_DONE.md` + `CHANGELOG.md`. Read whatever exists.

> ⚠️ **Conflict rule:** Live handover beats CLAUDE.md. CLAUDE.md beats this file. **Newest always wins.**

---

## 🌐 STEP 2 — THE FULL REPO MAP

| Repo | What it is | Stack | First doc |
|---|---|---|---|
| `HyperCode-V2.4` | 🧠 Core platform — **CANONICAL PRODUCTION** (25 agents, 48+ containers, 80+ services across 20+ compose files) | Python (FastAPI) + Docker + TS | `CLAUDE.md` |
| `THE-HYPERCODE` | 🔬 **Next-gen / V3 EXPERIMENTAL** — successor to HyperCode-V2.4. NOT production, NOT canonical. Cold agents: use V2.4 as source of truth. | Python + Docker (evolving) | `README.md` |
| `hyper-agents-ide` | 🎛️ Control room UI — agents, chat, skills dashboard | FastAPI + Vite/React | `README.md` |
| `Hyper-Vibe-Coding-Course` | 🎓 ND-first AI education platform — Course + HyperLabs funnel | Vite + Supabase + Stripe | `CLAUDE.md` |
| `HyperAgent-SDK` | 📦 npm agent orchestration package `@w3lshdog/hyper-agent` | Node/JS | `README.md` |
| `showcase-web` | 🌐 Public showcase + registry UI | Next.js | `README.md` |
| `BROskiPets-LLM-dNFT` | 🐾 Web3 AI pet game — LLM + Base blockchain + shop | Python + Solidity | `README.md` |
| `BROski-Obsidian-Brain` | 🧠 Second Brain vault — Obsidian + GitHub bridge + Python tools | Obsidian + Python | `CLAUDE.md` |
| `HYPER-SILLs-By-WelshDog` | 🦸 Skills vault — 72+ hero-named skills for ALL agents | Markdown + Python | `vault-index.md` + `WHATS_DONE.md` |
| `Hyper-Docker` | 🐳 Infra overview — 22 compose files, 5 networks, 80+ services | Docs | `EXECUTIVE_SUMMARY.md` |
| `WelshDog-Mission-Control` | 🛸 **Course-ops dashboard** — Kanban + Agent Actions (DM / Grant / Refund / Pulse / Brief) + Discord DM relay + Stripe refund. **NOT an agent orchestrator.** | **Vite + React + Express** | `WHATS_DONE.md` + `CHANGELOG.md` |
| `welshdog-designs-web3-shop` | 🛒 Web3 merch + designs shop | Web3 + React | `README.md` |
| `hyperfocuszone.com-Support-Hub` | 💬 Support hub + community docs | Docs | `README.md` |
| `HC` (HperCore) | 🔧 Local workspace hub — **NOT a commit target, NOT a git repo** | Workspace | `PORTAL.md` |
| `trae-ide` | 🗃️ Local Trae IDE state/data | SQLite | `data/` |

> ⚠️ `HC` / `HperCore` is a **workspace hub only** — commit inside the repo you changed, never at HperCore root. This `AGENT-START.md` lives at the root and is NOT git-tracked here; mirror copies in sub-repos drift.

> 🔬 **THE-HYPERCODE vs HyperCode-V2.4:** V2.4 is the running production system. THE-HYPERCODE is the V3 experimental successor — treat it as a lab, not as core infra.

---

## 🔌 STEP 3 — HOW THE ECOSYSTEM CONNECTS

```
Course ──Stripe──▶ Supabase Edge (stripe-webhook)            ──▶ DB (yhtmuibgdnxhbgboajhc)
Course ──Auth──▶ Supabase (users, enrollments, BROski$ tokens)
Mission Control ──▶ same Course Supabase (mc_missions + mc_events)
                ──▶ Discord bot REST (DM relay via DISCORD_BOT_TOKEN, server-side only)
                ──▶ Stripe REST (refunds, server-side, Idempotency-Key per session)
Agents IDE ──API──▶ HyperCode-V2.4 (must match CORS origin)
BROskiPets ──▶ agents-net (Docker profile: pets)
Brain ──▶ agents-net (Docker profile: brain) + Obsidian Git
HYPER-SILLs ──▶ ALL agents load skills from here
Showcase ──▶ pulls status from ecosystem (public registry)
All 25 agents ──▶ crew-orchestrator (:8100) — central routing + health coordination
```

> 💡 Mission Control + Course share **one** Supabase project (`yhtmuibgdnxhbgboajhc`). Anything that breaks there breaks both.

---

## 🤖 THE FULL 25-AGENT FLEET (HyperCode-V2.4)

> Launch with: `docker compose -f docker-compose.yml -f docker-compose.agents-full.yml up -d`
> All agents route through **crew-orchestrator** at `:8100`.

### ✅ Original 13 Agents (Established)

| # | Agent | Port | Role |
|---|---|---|---|
| 1 | `crew-orchestrator` | :8100 | 🎯 Master coordinator — routes all 25 agents |
| 2 | `broski-bot` | :8001 | 🤖 Discord bot — `discord.py==2.4.0`, entrypoint: `python -u -m cogs.bot` |
| 3 | `money-maker` | :8002 | 💰 Revenue + monetisation agent |
| 4 | `client-liaison` | :8003 | 🤝 Client comms + relationship agent |
| 5 | `content-creator` | :8004 | ✍️ Content + copywriting agent |
| 6 | `analytics-agent` | :8005 | 📊 Data analysis + reporting |
| 7 | `code-doctor` | :8006 | 🩺 Code review + refactoring |
| 8 | `ai-gateway` | :8010 | 🌐 LLM routing + token cost management |
| 9 | `redis-cache` | :6379 | ⚡ Cache (DB 1) + rate limits (DB 2) — NEVER mix |
| 10 | `postgres-db` | :5432 | 🗄️ Main database |
| 11 | `dashboard-api` | :8088 | 📈 HyperCode Dashboard backend |
| 12 | `grafana` | :3001 | 📉 Metrics visualisation |
| 13 | `prometheus` | :9090 | 🔍 Metrics scraping |

### 🔨 12 New Ghost Agents (Built 2026-08-19)

| # | Agent | Port | Role |
|---|---|---|---|
| 14 | `security-engineer` | :8007 | 🔐 Security scanning, secrets audit, hardening |
| 15 | `system-architect` | :8008 | 🏗️ Architecture decisions, infra design |
| 16 | `tips-tricks-writer` | :8009 | 💡 ND-friendly tips, docs, onboarding content |
| 17 | `ai-training-specialist` | :8011 | 🧪 Model fine-tuning, training pipeline management |
| 18 | `performance-optimizer` | :8012 | ⚙️ Latency, throughput, container resource tuning |
| 19 | `data-pipeline-engineer` | :8013 | 🔄 ETL pipelines, data flow orchestration |
| 20 | `throttle-agent` | :8014 | 🚦 Rate limiting, API throttle management |
| 21 | `super-hyper-broski` | :8015 | 🦸 BROski$ economy, rewards, Discord events |
| 22 | `test-agent` | :8080 | 🧪 Automated testing, CI health checks |
| 23 | `hyper-architect` | :8091 | 🧠 High-level system design + code scaffolding |
| 24 | `hyper-observer` | :8092 | 👁️ System observability, log aggregation, alerts |
| 25 | `hyper-worker` | :8093 | 🔧 Background jobs, queue processing, async tasks |
| 26 | `hyper-split-agent` | :8096 | ✂️ Task decomposition, parallel sub-agent spawning |
| 27 | `session-snapshot` | :8097 | 📸 Session state capture, handover doc generation |
| 28 | `agent-x` | custom | 🕵️ Custom routing, experimental agent harness |

> ⚠️ **Port :8080** — Test Agent. Double-check nothing else claims this (common default for dashboards/proxies).
> ⚠️ **crew-orchestrator is the SPOF** — must have `restart: unless-stopped` + `/health` endpoint. If it's down, ALL agents stall.

### Resource Limits (apply to all new agents)
```yaml
deploy:
  resources:
    limits:
      memory: 256m
      cpus: "0.25"
```

---

## 📚 §4 — DOC AUTHORITY MAP (per-repo)

**Not every repo has a CLAUDE.md.** Read whatever the target repo actually ships:

| Repo | Authoritative doc(s) | Notes |
|---|---|---|
| `HyperCode-V2.4` | `CLAUDE.md` + `WHATS_DONE.md` | Read CLAUDE.md first (constitution); WHATS_DONE.md is the "do not rebuild" list |
| `Hyper-Vibe-Coding-Course` | `CLAUDE.md` + `rewrites/SESSION_SNAPSHOT_*` + `rewrites/NEXT_SESSION_HANDOVER_*` | Latest snapshot/handover wins over CLAUDE.md |
| `BROski-Obsidian-Brain` | `CLAUDE.md` | Plus repo's own brain agent manifests |
| `WelshDog-Mission-Control` | **`WHATS_DONE.md` + `CHANGELOG.md`** — **no CLAUDE.md exists** | If a brief says "read CLAUDE.md" for this repo, the brief is wrong |
| `HYPER-SILLs-By-WelshDog` | `WHATS_DONE.md` + `vault-index.md` + `NEXT_SESSION_HANDOVER_*` | No CLAUDE.md here either |
| `BROskiPets-LLM-dNFT` | `README.md` + repo-specific snapshots | — |
| `THE-HYPERCODE` | `README.md` | V3 experimental — read before touching |
| Everything else | `README.md` first | — |

---

## 🦸 STEP 5 — LOAD YOUR SKILLS FROM HYPER-SILLs

Skills vault: **`github.com/welshDog/HYPER-SILLs-By-WelshDog`**
72+ hero-named skills. Treat as infrastructure. Always check `vault-index.md` for the full map first.

| Working on... | Load skill from |
|---|---|
| Docker / compose / containers | `dev/` → docker skills |
| AI agents / orchestration | `agents/` → agent skills |
| Frontend / React / Vite | `dev/` → frontend skills |
| BROski$ economy / Discord | `broski/` → broski skills |
| Course content / scripts | `content/` → content skills |
| YouTube / video | `youtube/` → youtube skills |
| Everything | `vault-index.md` |

> 🦸 Skills are hero-named (Marvel convention, e.g. **THE SACRED SIX**). Never rename them.

---

## 🎯 STEP 6 — START THE TASK (NO WAFFLE)

- State the next task in **2 lines max**
- Ask **ONE** decision question only if genuinely blocked
- Otherwise: **"Next up is X — starting now"**
- ❌ NEVER ask "What would you like to work on today?"
- ✅ ALWAYS say "Next up is X — starting now"

---

## 🔴 RULES YOU CANNOT BREAK — Ecosystem-wide

These apply **everywhere**, no exceptions:

| Rule | Why |
|---|---|
| `git fetch` BEFORE any push | Parallel auto-commit workflow — origin can move between your fetch and push; rebase clean, **NEVER force-push** |
| Nothing is done until committed + pushed | Saying "done" without a push = not done |
| Never commit `.env` files | Secrets stay local — NEVER |
| Check `WHATS_DONE.md` (or `CHANGELOG.md` where that's authoritative) before suggesting anything | Never rebuild what's already built |
| One repo at a time | No cross-repo commits in same commit |
| Keep LLM costs low | Cap tokens, avoid polling AI Gateway |
| Short sentences first, detail after | ADHD-friendly communication |
| Celebrate every milestone | "Nice one BROski♾️!" is always correct |
| **Surface contradictions visibly** | If the brief / doc / code disagree, name the contradiction before acting — never silently pick a side |

**Commit prefixes:** `feat:` / `fix:` / `docs:` / `chore:`

---

## 🟠 RULES — Per-repo (NOT universal — verify against your target repo)

These get pasted into briefs as "sacred rules" but actually belong to ONE repo. **Sanity-check before applying.**

| Rule | Belongs to | NOT applicable in |
|---|---|---|
| `npm run dev:frontend` (NOT `npm run dev`) | **Course** | MC uses `npm run dev:full`. Other repos have their own. |
| Never `supabase db push` — use MCP `apply_migration` only | **Course + MC** (both point at `yhtmuibgdnxhbgboajhc`) | Other Supabase projects untested for this |
| Web3 / `wagmi` / `rainbowkit` stays in `/pets` ONLY | **Course** | Wagmi belongs everywhere it belongs in BROskiPets, MC has no Web3 |
| `docker-ce-cli` not `docker.io` | **HyperCode-V2.4** (socket agent compat) | Other repos may not need it |
| `from app.X import Y` (NEVER `from backend.app.X`) | **HyperCode-V2.4** (Python) | Not applicable to Vite/React/Express repos |
| `broski-bot: discord.py==2.4.0`, entrypoint `python -u -m cogs.bot` | **HyperCode-V2.4** (`agents/broski-bot/`) | MC has NO Python bot — its `/api/send-dm` calls Discord REST directly |
| Stripe webhook is rate-limit-exempt | **HyperCode-V2.4 + Course** | — |
| `mc_events` is append-only (UPDATE/DELETE blocked) | **MC** | — |
| Redis DB 1=cache, DB 2=rate limits — NEVER mix | **HyperCode-V2.4** | — |
| Python indent = 4 spaces, NEVER 3, NEVER mixed | **HyperCode-V2.4** | — |

> 💡 **Cross-repo confusion guard:** When a session brief lists "sacred rules", check the **repo** named in the brief and only apply rules that match. A brief saying "FastAPI `main.py`" for MC is wrong — MC is Express.

---

## 🧰 LOCAL ENDPOINTS (when running)

### Core Services
| Service | URL |
|---|---|
| HyperCode Dashboard | http://127.0.0.1:8088 |
| Grafana | http://127.0.0.1:3001 |
| Prometheus | http://127.0.0.1:9090 |
| crew-orchestrator | http://127.0.0.1:8100 |
| AI Gateway | http://127.0.0.1:8010 |

### Original Agents
| Agent | URL |
|---|---|
| broski-bot | http://127.0.0.1:8001 |
| money-maker | http://127.0.0.1:8002 |
| client-liaison | http://127.0.0.1:8003 |
| content-creator | http://127.0.0.1:8004 |
| analytics-agent | http://127.0.0.1:8005 |
| code-doctor | http://127.0.0.1:8006 |

### New Ghost Agents (live from 2026-08-19)
| Agent | URL |
|---|---|
| security-engineer | http://127.0.0.1:8007 |
| system-architect | http://127.0.0.1:8008 |
| tips-tricks-writer | http://127.0.0.1:8009 |
| throttle-agent | http://127.0.0.1:8014 |
| super-hyper-broski | http://127.0.0.1:8015 |
| test-agent | http://127.0.0.1:8080 |
| hyper-architect | http://127.0.0.1:8091 |
| hyper-observer | http://127.0.0.1:8092 |
| hyper-worker | http://127.0.0.1:8093 |
| hyper-split-agent | http://127.0.0.1:8096 |
| session-snapshot | http://127.0.0.1:8097 |

### Dev / Course / MC
| Service | URL |
|---|---|
| Course (dev) | http://localhost:5173 |
| Mission Control (dev SPA) | http://localhost:5174 |
| Mission Control (dev API) | http://localhost:3011 |
| Agents IDE | http://localhost:3000 |

---

## 💳 STRIPE — Mode check FIRST, then runbook

**⚠️ Don't trust "Stripe LIVE 💳" claims in docs without verifying.** As of 2026-06-07, the Course `stripe-webhook` Edge Function (`Hyper-Vibe-Coding-Course/supabase/functions/stripe-webhook/index.ts`) has `PRICE_TO_TIER` populated with **TEST-mode** price IDs — verified because `https://dashboard.stripe.com/test/prices/<id>` resolves and price IDs are mode-scoped. CLAUDE.md status banners have been corrected, but other status docs may still echo the old "LIVE" claim.

### How to verify TEST vs LIVE in 30 seconds

1. Fetch any price ID from `PRICE_TO_TIER` (e.g. via Stripe MCP `fetch_stripe_resources`).
2. Look at the returned dashboard URL: contains `/test/` = TEST mode. No `/test/` = LIVE.
3. Stripe price IDs are mode-scoped — a TEST ID **cannot** exist in LIVE.

### Webhook runbook

| Signal | Meaning | Fix |
|---|---|---|
| `POST 401` | Supabase requiring JWT on webhook | Redeploy without JWT verify: `verify_jwt: false` on the Edge Function (already set on the live Course function) |
| `POST 400` + `signature_verification_failed` | Wrong `whsec_` secret | Use the `whsec_` printed by `stripe listen`, NOT the Dashboard secret |
| `POST 200` + `{received:true,skipped:true}` | ✅ Idempotency dedup (already processed) | Working — `source_id` lookup in `token_transactions` hit |
| `POST 200` (no `skipped`) | ✅ Fresh write | Verify DB: `payments` + `token_transactions` rows exist |

### Smoke-test paths (in order of safety)

```bash
# Safest — no charge, no new event:
# Stripe Workbench → find an existing event → Resend.
# Proves signature path + idempotency in one click.

# TEST-mode fresh write (current Course state):
stripe listen --latest --forward-to https://<project>.supabase.co/functions/v1/stripe-webhook
# Paste the printed whsec_... as STRIPE_WEBHOOK_SECRET in Supabase
stripe trigger checkout.session.completed
```

> 🚫 Stripe public API has **no** "resend event" operation — manual retries are Workbench-only.
> 🚫 Supabase MCP `secrets:read` scope exists but **no MCP tool exposes Edge Function secrets** — can't sign synthetic payloads locally.

---

## 🪤 RECENTLY-BITTEN GOTCHAS (real ones, dated)

| Gotcha | Symptom | Fix |
|---|---|---|
| `python:3.11-slim` has no `ps` / `pgrep` / `curl` | github-sync container ran healthy work for 29 hours with **835 consecutive healthcheck failures** (2026-06-06) | For cron-as-PID-1 containers use `grep -q <proc> /proc/1/comm`. For HTTP services install `curl` explicitly. **If a container shows hours of consecutive failures but the workload is fine — suspect the check binary, not the workload.** |
| Supabase Dashboard SQL editor opens read-only | `ALTER VIEW` errors with `cannot execute ... in a read-only transaction` (hit 2026-06-06) | Flip the "Read-only" toggle in the editor UI off, OR prefer Supabase MCP `apply_migration` for prod DDL |
| `Edit replace_all: true` rewrites `const X = ...` declaration too | `ReferenceError: Cannot access 'X' before initialization` (TDZ self-reference) at boot. `node --check` does NOT catch it. | Use targeted Edit on the declaration + `replace_all` only on the call sites separately |
| "Stripe LIVE 💳" in CLAUDE.md was stale | TEST price IDs everywhere; LIVE checkouts (if any happened) would all fall through to `logUnmatchedPayment` | Always verify via the `/test/` segment in price dashboard URLs |
| Parallel git workflow mid-push origin move | `git push` rejected as non-fast-forward despite a recent fetch — auto-commits land between fetch and push | `git fetch && git rebase origin/main && git push` (NEVER force-push). Should be reflexive. |
| 25-agent stack memory pressure | One runaway agent can starve all others without resource limits | Add `mem_limit: 256m` + `cpus: "0.25"` to all new agent compose definitions before launch |
| Port :8080 collision | Test Agent uses a very common default port — nginx, Traefik, and many dev servers default to :8080 | Run `grep -r "ports:" docker-compose*.yml \| grep 8080` to confirm no collision before launch |

---

## 🧠 WHEN STUCK — QUICK TRIAGE

1. Reproduce once (don't guess)
2. Capture the exact error message / output
3. Find the owning repo + file
4. Fix the **smallest** thing that makes the proof go green
5. Commit + push immediately

---

## 🏁 SESSION END CHECKLIST (MANDATORY)

- [ ] All changes committed + pushed (per-repo, **not** HperCore root)
- [ ] `NEXT_SESSION_HANDOVER_[DATE].md` created + pushed ← **most important step**
- [ ] `WHATS_DONE.md` updated if new things were built (or `CHANGELOG.md` for the repos that use that convention)
- [ ] Ecosystem-level change? → update `ECOSYSTEM_HANDOVER.md` + `DASHBOARD_STATUS_[DATE].md`
- [ ] Memory updated if the session surfaced load-bearing facts that aren't in git
- [ ] Tell Lyndz the ONE next task (one sentence)
- [ ] 🎉 Celebrate the wins — "Nice one BROski♾️!"

---

> 🐶♾️ Built by @welshDog · Llanelli, Wales
> *"Stop apologising for your brain. Start building."*
