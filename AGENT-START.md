# 🚀 AGENT-START.md — HyperFocus Z0ne MASTER Boot File
> **For ANY AI, agent, or human joining the full HyperFocus Z0ne ecosystem.**
> Read this file FIRST. Every session. No exceptions.
> Built by @welshDog — **v3.4 (upgraded 2026-08-21)** · supersedes v3.3 (2026-08-19)

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
| `HyperCode-V2.4` | 🧠 Core platform — **CANONICAL PRODUCTION** (26 agents, 68+ containers, 80+ services across 20+ compose files) | Python (FastAPI) + Docker + TS | `CLAUDE.md` |
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
All agents ──▶ crew-orchestrator (:8081) — central routing + health coordination (:8100 is hyper-brain, a separate service — do not confuse the two)
```

> 💡 Mission Control + Course share **one** Supabase project (`yhtmuibgdnxhbgboajhc`). Anything that breaks there breaks both.

---

## 🤖 THE FULL 26-AGENT FLEET (HyperCode-V2.4)

> ✅ **Fully rewritten 2026-08-21, matching `CLAUDE.md`'s verified-live table exactly** —
> this section previously predated the 2026-08-20 real fleet launch and was actively
> wrong (ports, statuses, even a fictional roster from an even older rewrite). The
> fleet below was composed up as one system for the first time ever 2026-08-20 late
> night — item #0 (a compose same-name-merge risk) resolved for real, not just
> mitigated — verified via a full box sweep, zero unhealthy containers. A 26th agent,
> `fleet-controller`, was added the same night as Phase 0 of a new mission-director
> architecture — see `docs/superpowers/specs/2026-08-20-fleet-controller-phase0-design.md`
> and `docs/NEXT_SESSION_HANDOVER_2026-08-20-late-night.md` for the full session.
>
> Launch with: `docker compose --profile agents --profile hyper -f docker-compose.yml
> -f docker-compose.agents-full.yml up -d` (add `--profile fleet` too for
> `fleet-controller`, deliberately excluded from the standard command). All agents
> route through **crew-orchestrator** at `:8081` (not `:8100` — that's `hyper-brain`,
> a separate service).
>
> `CLAUDE.md`'s "CURRENT STATE" section is the one updated every session — if the two
> ever disagree again, trust that one and flag it here, per "surface contradictions
> visibly."

### ✅ Core Crew + Specialist Squad (13)

| Agent | Port | Status |
|---|---|---|
| `crew-orchestrator` | :8081 | ✅ Live |
| `brain-agent` | :8082 | ✅ Live — real code shipped 2026-08-20 (was a missing directory) |
| `coder` | — | 🟡 not running under this name (`coder-agent` live, likely same code) |
| `agent-x` | :8084 | ✅ Live — `agents-full.yml`'s duplicate (:8083) deleted 2026-08-20, `agents.yml`'s :8084 is the sole definition |
| `frontend-specialist` | :8012 | ✅ Live |
| `backend-specialist` | :8003 | ✅ Live |
| `database-architect` | :8004 | ✅ Live |
| `qa-engineer` | :8005 | ✅ Live |
| `devops-engineer` | :8006 | ✅ Live |
| `security-engineer` | :8007 | ✅ Live |
| `system-architect` | :8010 | ✅ Live — moved off :8008 2026-08-20 (was colliding with `healer-agent`) |
| `project-strategist` | :8001 | ✅ Live — context fixed 2026-08-20 (was pointing at a deleted directory), also missing `base_agent.py` (fixed) |
| `tips-tricks-writer` | :8018 | ✅ Live — moved off :8009 2026-08-20 (was colliding with `chroma`) |

> Plus `broski-bot`, `redis`, `postgres`, `grafana`, `prometheus`, `hypercode-dashboard` are also
> live core infra — not agents in this table, part of the real running stack.

### 🔨 12 Ghost Agents

| Agent | Port | Status |
|---|---|---|
| `hyper-architect` | :8091 | ✅ Live — needed a `.dockerignore` carve-out (found during the 2026-08-20 launch) |
| `hyper-observer` | :8092 | ✅ Live — build-context path bug fixed 2026-08-20 |
| `hyper-worker` | :8093 | ✅ Live — build-context path bug fixed 2026-08-20 |
| `hyper-split-agent` | :8013 | ✅ Live — moved off :8096 2026-08-20 (was colliding with `safety-shepherd`) |
| `session-snapshot` | :8017 | ✅ Live — moved off :8097 2026-08-20 (was colliding with `evolve-relay`) |
| `throttle-agent` | :8014 | ✅ Live — Docker socket access fixed 2026-08-20 via `docker-socket-proxy-healer`; still logs `MemStream unreachable`, a separate unbuilt dependency |
| `super-hyper-broski-agent` | :8015 | ✅ Live |
| `test-agent` | :8019 | ✅ Live — moved off :8100 2026-08-20 (was colliding with `hyper-brain`) |
| `goal-keeper` | :8050 | ✅ Live |
| `business-agent` | :8020 | ✅ Live — real code built 2026-08-20 (was a mislabeled `project-strategist` clone) |
| `coderabbit-webhook` | :8024 | ✅ Live |

### 🛡️ Phase 0: Fleet Controller (1, behind `--profile fleet`)

| Agent | Port | Status |
|---|---|---|
| `fleet-controller` | :8094 | ✅ Live — new 2026-08-20 late night, Phase 0 of a mission-director/fleet-controller architecture. Structurally incapable of executing anything: no Docker socket, no `DOCKER_HOST`, no crew-orchestrator credential, no LLM client. Fails **closed** if Safety Shepherd is unreachable. Behind its own `--profile fleet`, never launches with the standard command. |

> `hypercode-mcp-server` is not in this roster — it's the real, live MCP gateway
> defined in `docker-compose.agents.yml` (`:8823`), not a distinct 25th/26th agent. A
> phantom duplicate of it in `agents-full.yml` was deleted 2026-08-20.
>
> **Total: 26 agents in this roster — 26 live**, 0 not running except the
> intentionally-nonexistent `coder` alias. `crew-orchestrator` is the SPOF (single
> point of failure) — has `restart: unless-stopped` + `/health`, confirmed live.

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

> ✅ **Rewritten 2026-08-21.** This section previously listed an "Original Agents"
> roster (`money-maker`, `client-liaison`, `content-creator`, `analytics-agent`,
> `code-doctor`) and an `AI Gateway` service — neither exists anywhere in any
> `docker-compose*.yml` in this repo (confirmed by grep before rewriting), same
> fictional-roster class this file's own banner already disclaimed for the fleet
> table above. Also had `crew-orchestrator` at `:8100` (wrong — that's `hyper-brain`)
> and several ghost-agent ports from before the 2026-08-20 collision fixes. Full,
> always-current per-agent table: `CLAUDE.md`'s "CURRENT STATE" section.

### Core Services
| Service | URL |
|---|---|
| HyperCode Dashboard | http://127.0.0.1:8088 |
| Grafana | http://127.0.0.1:3001 |
| Prometheus | http://127.0.0.1:9090 |
| crew-orchestrator | http://127.0.0.1:8081 |
| hyper-brain (not crew-orchestrator — common mix-up) | http://127.0.0.1:8100 |
| safety-shepherd | http://127.0.0.1:8096 |
| fleet-controller (Phase 0, `--profile fleet`) | http://127.0.0.1:8094 |

### Ghost Agents (live from 2026-08-20)
| Agent | URL |
|---|---|
| security-engineer | http://127.0.0.1:8007 |
| system-architect | http://127.0.0.1:8010 |
| tips-tricks-writer | http://127.0.0.1:8018 |
| throttle-agent | http://127.0.0.1:8014 |
| super-hyper-broski-agent | http://127.0.0.1:8015 |
| test-agent | http://127.0.0.1:8019 |
| hyper-architect | http://127.0.0.1:8091 |
| hyper-observer | http://127.0.0.1:8092 |
| hyper-worker | http://127.0.0.1:8093 |
| hyper-split-agent | http://127.0.0.1:8013 |
| session-snapshot | http://127.0.0.1:8017 |
| goal-keeper | http://127.0.0.1:8050 |
| business-agent | http://127.0.0.1:8020 |
| coderabbit-webhook | http://127.0.0.1:8024 |

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
| 26-agent stack memory pressure | One runaway agent can starve all others without resource limits | ✅ Proven safe, not just planned — 68 containers ran simultaneously 2026-08-20, zero unhealthy. Still add `mem_limit: 256m` + `cpus: "0.25"` to any new agent compose definition. |
| Port :8080 collision (host port) | Test Agent used to sit on a very common default port | ✅ Resolved 2026-08-20 — every agent's *container-internal* port is now uniformly `8080` (never a host port), and all real host-port collisions were fixed the same night. Still run `grep -r "ports:" docker-compose*.yml \| sort` before adding a new agent's host port. |

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
