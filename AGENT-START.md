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

> 🪤 **REWRITTEN 2026-08-19 — three different "25-agent fleet" docs existed the same day and
> disagreed with each other.** This table originally listed `money-maker`/`client-liaison`/
> `ai-gateway`/etc. — checked against `agents/` folder + all `docker-compose*.yml`: 12 of those 28
> rows had zero trace anywhere. Meanwhile `.github/workflows/docker-push.yml` and `CLAUDE.md` (both
> pushed the same day, commits `e764bf3b`/`8b70094`) each named a *third and fourth* roster, neither
> matching this one or each other. Bro decided **`docker-push.yml`'s roster is canonical** — this
> table now matches it. `CLAUDE.md` still needs the same correction (flagged there, not yet done as
> of this edit). Full forensic trail in `DASHBOARD_STATUS_2026-08-19.md`.

> Launch with: `docker compose -f docker-compose.yml -f docker-compose.agents-full.yml up -d`
> All agents route through **crew-orchestrator** at `:8081` (not `:8100` — `:8100` is `hyper-brain`).

### ✅ Core Crew + Specialist Squad (13) — per `docker-push.yml`'s `push-agents` build matrix

| # | Agent | Real compose context | Port | Status (verified 08-19) |
|---|---|---|---|---|
| 1 | `crew-orchestrator` | `./agents/crew-orchestrator` | :8081 | ✅ LIVE |
| 2 | `brain-agent` | `./agents/brain` | :8082 | 🟡 built, not running as this exact container (`hyper-brain`/`agent-hyper-brain-core` are live but separate) |
| 3 | `coder` | `./agents/coder` | — | 🟡 built, not running under this name (`coder-agent` is live — likely the same code, different container_name) |
| 4 | `agent-x` | `./agents/agent-x` | :8083 or :8084 (⚠️ two different compose files disagree — `agents.yml` vs `agents-full.yml`, not reconciled here) | 🟡 built, not running |
| 5 | `frontend-specialist` (01) | `./agents/01-frontend-specialist` | :8012 | ✅ LIVE |
| 6 | `backend-specialist` (02) | `./agents/02-backend-specialist` | :8003 | ✅ LIVE |
| 7 | `database-architect` (03) | `./agents/03-database-architect` | :8004 | ✅ LIVE |
| 8 | `qa-engineer` (04) | `./agents/04-qa-engineer` | :8005 | ✅ LIVE |
| 9 | `devops-engineer` (05) | `./agents/05-devops-engineer` | :8006 | ✅ LIVE |
| 10 | `security-engineer` (06) | `./agents/06-security-engineer` | :8007 | 🟡 built, not running |
| 11 | `system-architect` (07) | `./agents/07-system-architect` | :8008 | 🟡 built, not running — ⚠️ collides with live `healer-agent :8008` |
| 12 | `project-strategist` (08) | `./agents/08-project-strategist` | :8001 | 🟡 built, not running |
| 13 | `tips-tricks-writer` (09) | `./agents/09-tips-tricks-writer` | :8009 | 🟡 built, not running |

> Plus `broski-bot`, `redis`, `postgres`, `grafana`, `prometheus`, `hypercode-dashboard` are also
> live core infra — not in this specific CI matrix (they're built by the `push-backend` job or
> pulled as base images) but part of the real running stack.

### 🔨 12 Ghost Agents — per `docker-push.yml`'s `push-ghost-agents` build matrix

| # | Agent | Real compose context (fixed 08-19) | Port | Status (verified 08-19) |
|---|---|---|---|---|
| 14 | `hyper-architect` | `./agents/architect` | :8091 | 🟡 built, not running |
| 15 | `hyper-observer` | `./agents/hyper-agents/observer` (was wrongly `./agents/hyper-agents` + `Dockerfile.observer` — fixed) | :8092 | 🟡 built, not running |
| 16 | `hyper-worker` | `./agents/hyper-agents/worker` (same fix) | :8093 | 🟡 built, not running |
| 17 | `hyper-split-agent` | `./agents/hyper-split-agent` (was wrongly under `./agents/hyper-agents` — fixed) | :8096 | 🟡 built, not running — ⚠️ collides with live `safety-shepherd :8096` |
| 18 | `session-snapshot` | `./agents/session-snapshot` (same fix) | :8097 | 🟡 built, not running — ⚠️ collides with live `evolve-relay :8097` |
| 19 | `throttle-agent` | `./agents/throttle-agent` | :8014 | 🟡 built, not running |
| 20 | `super-hyper-broski-agent` | `./agents/super-hyper-broski-agent` | :8015 | 🟡 built, not running |
| 21 | `test-agent` | `./agents/test-agent` | :8100 | 🟡 built, not running — ⚠️ collides with live `hyper-brain :8100` |
| 22 | `goal-keeper` | `./agents/goal_keeper` | :8050 | ✅ LIVE |
| 23 | `business-agent` | `./agents/business-agent` — ❌ **still broken**, no Dockerfile exists at this or any sensible path (`./agents/business/project-strategist/Dockerfile` exists but looks like a stray copy, not a real `business-agent`). Needs a human call. | — | ❌ blocked |
| 24 | `coderabbit-webhook` | `./agents/coderabbit-webhook` | :8024 | 🟡 built, not running |
| 25 | `hypercode-mcp-server` | `./services/hypercode-mcp-server` (was wrongly `./agents/hypercode-mcp-server` — fixed) | — | ⚠️ **name collision**: a *different*, already-live `hypercode-mcp-server` container exists at `:8823` (the real MCP gateway) — building this ghost-agent image under the same name will produce a same-named-but-different image. Needs reconciling, not just a build. |

> ⚠️ **Port :8080** is `bropets_api` right now, not any agent in this table.
> ⚠️ **crew-orchestrator is the SPOF** — must have `restart: unless-stopped` + `/health` endpoint. If it's down, ALL agents stall.
> 🪤 **5 of 6 broken CI paths were fixed in `docker-push.yml` on 08-19** (`hyper-observer`,
> `hyper-worker`, `hyper-split-agent`, `session-snapshot`, `hypercode-mcp-server`). `business-agent`
> is still broken — no valid path exists, needs a real decision, not a path fix.
> 🪤 **Launching `agents-full.yml` as-is will still hit 3 port-bind failures** (`system-architect`,
> `test-agent`, `hyper-split-agent`/`session-snapshot`) against services already running. Not
> resolved — resolving compose port collisions is a separate task from fixing CI build paths.

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
