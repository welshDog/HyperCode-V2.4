# 🚀 AGENT-START.md — HyperFocus Z0ne MASTER Boot File
> **For ANY AI, agent, or human joining the full HyperFocus Z0ne ecosystem.**
> Read this file FIRST. Every session. No exceptions.
> Built by @welshDog — **v3.1 (upgraded 2026-06-07)** · supersedes v3.0 (2026-06-01)

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
| `HyperCode-V2.4` | 🧠 Core platform — **~30 containers running** (profile-dependent across 20+ compose files; 80+ services defined) | Python (FastAPI) + Docker + TS | `CLAUDE.md` |
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
```

> 💡 Mission Control + Course share **one** Supabase project (`yhtmuibgdnxhbgboajhc`). Anything that breaks there breaks both.

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

> 💡 **Cross-repo confusion guard:** When a session brief lists "sacred rules", check the **repo** named in the brief and only apply rules that match. A brief saying "FastAPI `main.py`" for MC is wrong — MC is Express.

---

## 🧰 LOCAL ENDPOINTS (when running)

| Service | URL |
|---|---|
| HyperCode Dashboard | http://127.0.0.1:8088 |
| Grafana | http://127.0.0.1:3001 |
| Prometheus | http://127.0.0.1:9090 |
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
