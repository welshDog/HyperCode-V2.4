# 🧠 HYPERFOCUS z0ne — Full AI Context (ecosystem root CLAUDE.md)
> **For ANY AI assistant — Claude, Perplexity, GPT, Gemini — read this first. Every word.**
> Last updated: **May 19, 2026**
> Promoted from `Merge_CLAUDE.md` → canonical root `CLAUDE.md` (auto-loaded every session).
> Status: V2.4 ~30 containers running 🟢 (profile-dependent) | 251 tests ✅ (251 passed, 6 skipped — May 16) | Prometheus 7/7 ✅ | Stripe LIVE 💳 | Discord Bot LIVE 🤖 | NemoClaw Alive L1-3.5 LIVE 🧠 | Server Guardian P1-3c LIVE/BUILT 🛡️ | BROskiPets Web3 LIVE 🔥 | Shop Fulfillment v2 BUILT 🛒 (deploy pending) | **HyperLabs funnel LIVE + a11y-certified 🎓 (May 19)**

---

## 0. Read Order — Every Session

This root file is the **ecosystem constitution**. For deep work *inside a repo*, also read that repo's own `CLAUDE.md` + its latest handover/snapshot:

1. **This file** — ecosystem rules, 5-repo map, sacred rules, current state
2. **Working in the Course?** → `Hyper-Vibe-Coding-Course/CLAUDE.md` + `rewrites/SESSION_SNAPSHOT_[latest].md` + `rewrites/NEXT_SESSION_HANDOVER_[latest].md` (newest: `NEXT_SESSION_HANDOVER_2026-05-19.md`)
3. **Working in V2.4?** → `HyperCode-V2.4/CLAUDE.md`
4. **Check `WHATS_DONE.md`** — NEVER suggest anything already listed there
5. **Touching DB?** → check `supabase/migrations/` for the latest migration number first
6. **Then build.** Not before.

> Repo-level SESSION_SNAPSHOT = living state. This file = constitution.
> If they contradict, **surface it — don't silently pick one.**

---

## 1. 🙋 Who You're Working With

- **Name:** Lyndz Williams — call them **"Bro"** or **"BROski"**
- **GitHub:** @welshDog | **npm:** @w3lshdog
- **Location:** Llanelli, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁥
- **Brain:** ADHD + Dyslexia + Autistic — hyperfocus is a SUPERPOWER ⚡
- **Current IDE:** Claude Code (terminal) + Perplexity AI — Trae Pro expired May 2026
- **OS:** Windows primary (PowerShell), WSL2 + Raspberry Pi + Docker secondary
- Building: **The world's first neurodivergent-first autonomous AI infrastructure platform**

> *"You built the future people keep saying they want. You actually did it."* — Gordon (Docker AI, April 15 2026)

---

## 2. ⚡ Communication Rules (ALWAYS follow these)

- **Short sentences first** — then offer deeper explanation only if asked
- **Why → How → Ready-to-use example** structure
- **Bullet points + headings** over walls of text
- **Celebrate wins** — "Nice one BROski♾️!" is correct and encouraged
- **Remind context** if there's been a pause between messages
- ADHD flow: chunk it, quick wins first, no overwhelm
- If Lyndz goes quiet mid-task — check in gently, don't assume abandoned
- **Surface contradictions** — correct the doc visibly, never silently pick a side
- **Never say "human must test"** when Playwright applies (it's installed — use it)
- **NEVER** produce walls of text unprompted

---

## 3. 🌐 The 5-Repo Ecosystem

```
Hyper-Vibe-Coding-Course     ──── manifest.json ────▶    HyperCode V2.4
github.com/welshDog/             (hyper-agent-spec)       github.com/welshDog/
Hyper-Vibe-Coding-Course                                  HyperCode-V2.4
(Supabase + Vercel + Web3)             │                  (Docker, ~48 containers)
Path: H:\Hyper-Vibe-Coding-Course      │
⚠️ NOT H:\the hyper vibe coding hub    │
   (that = archived typo repo)         │
                              HyperAgent-SDK
                          github.com/welshDog/HyperAgent-SDK
                          npm: @w3lshdog/hyper-agent@0.1.7 (v0.3.0 code)
                          Path: H:\HyperAgent-SDK
                          graduate build + trigger commands DESIGNED May 15
                                       │
                         BROskiPets-LLM-dNFT
                     github.com/welshDog/BROskiPets-LLM-dNFT
                     Path: H:\dNFTpet\BROskiPets-LLM-dNFT
                     (Pets · dNFT · port 8098)
                                       │
                      BROski-Obsidian-Brain-for-HyperFocus-z0ne
                     github.com/welshDog/BROski-Obsidian-Brain-for-HyperFocus-z0ne
                     Path: H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne
                     (Second Brain vault — PARA + Dataview + GitHub bridge)
                     cluster.json + 4 agent manifests PUSHED May 15 ✅
```

> ℹ️ This aggregator root is `H:\HYPERFOCUSZONE\HperCore` — all 5 repos are cloned here as
> subdirectories (`HyperCode-V2.4/`, `Hyper-Vibe-Coding-Course/`, `HyperAgent-SDK/`,
> `BROskiPets-LLM-dNFT/`, `BROski-Obsidian-Brain-for-HyperFocus-z0ne/`). Each has its own
> `CLAUDE.md`. The canonical authoring paths below are the `H:\...` originals.

| Repo | Purpose | Local Path |
|---|---|---|
| HyperCode-V2.4 | Core backend — ~30 containers running (profile-dependent; 20 compose files) | `H:\HyperStation zone\HyperCode\HyperCode-V2.4` |
| Hyper-Vibe-Coding-Course | Course + HyperLabs funnel — Supabase + Vercel + Web3 | `H:\Hyper-Vibe-Coding-Course` |
| HyperAgent-SDK | npm agent framework (`@w3lshdog/hyper-agent`) | `H:\HyperAgent-SDK` |
| BROskiPets-LLM-dNFT | Web3 NFT pet game — dNFTs + LLM | `H:\dNFTpet\BROskiPets-LLM-dNFT` |
| BROski-Obsidian-Brain | Second Brain — PARA vault + GitHub bridge | `H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne` |

---

## 4. 🏗️ Architecture Quick Ref (V2.4)

```
Networks:
  app-net     → core services (internal)
  data-net    → redis, postgres, chroma, minio (internal)
  obs-net     → prometheus, grafana, loki, tempo (internal)
  agent-net   → all agents
  agents-net  → broski-bot + hyper-agents

Key ports:
  8000  hypercode-core API       8081  crew-orchestrator
  8088  hypercode-dashboard      8095  hyperhealth-api
  8098  broski-pets-bridge       8099  nemoclaw-agent
  9090  prometheus               3001  grafana
  3100  loki                     3200  tempo
  6379  redis                    5432  postgres
```

---

## 5. 📊 Live System Status

### 5a. HyperLabs / Vibe Labs funnel — **LIVE end-to-end (May 19) 🎓**

| Metric | Status |
|---|---|
| Funnel | `/vibe-labs` hub + 5 level pages + landing funnel (hero CTA + rich section + progress-aware ✓) LIVE |
| DB | `claim_level_reward` RPC + `user_level_progress` — **prod, real-user tested** ✅ |
| Migration | `supabase/migrations/20260518000035_claim_level_reward.sql` DEPLOYED via Supabase MCP |
| Perf | route code-split + web3 deferred → cold funnel **1,270 kB → ~61 kB gzip** 🚀 |
| Sprint 3 a11y/perf | **COMPLETE & live** — Lighthouse **A11Y 100 / Best-Practices 100** on `/vibe-labs` + `/vibe-labs/level-1`; 16px floor, self-hosted fonts (were 100% broken), 44px targets |
| Deploy | Vercel `state: READY` at HEAD `3bef345` ✅ |
| Course DB | Restructured to May model + quizzes regenerated (May 17); true/false convention un-inverted (May 18 — whole course was positionally inverted, now fixed) |
| Auth-truth | real `authError` state + `useAuthStatus` + status badges (`data-auth-status` for Playwright) |

### 5b. HyperCode V2.4 (May 16)

| Metric | Status |
|---|---|
| Containers | ~30 running ✅ (live `docker ps` 21 May 2026; profile-dependent across 20 compose files) |
| Tests | 251 passed, 6 skipped ✅ (verified May 16, post NemoClaw + Guardian) |
| NemoClaw Alive | L1 Heartbeat + L2 Memory + L3 Voice + L3.5 Focus-loop LIVE 🧠 (port 8099) |
| Server Guardian | P1 Reactive + P2 Digest + P3a auto-mod + P3b raid-lock LIVE · P3c veto-ban BUILT (smoke pending) 🛡️ |
| Alembic migrations | up to **015** (012 code_health, 013 focus, 014 missions, 015 mod_actions) |
| Prometheus targets | 7/7 UP ✅ |
| OTLP Traces | LIVE in Tempo ✅ |
| Circuit Breakers | 3 active — all CLOSED ✅ |
| Docker AI Grade | A 🏅 |
| Stripe | LIVE 💳 (webhook secret updated May 5) |
| Gamification | HUD, XP, Quests, Leaderboard LIVE ✅ |
| BROskiPets Web3 Mint | LIVE on Base Sepolia 🔥 May 7 |
| broski-bot Discord | OPTION A LIVE 🤖 May 15 |
| Shop Fulfillment v2 | BUILT 🛒 May 17 — deploy + E2E pending |

---

## 6. 🔒 Sacred Rules (NEVER debate, NEVER break)

### 6a. Ecosystem-wide / V2.4

```
✔ docker-ce-cli          — NEVER docker.io for socket agents
✔ from app.X import Y    — NEVER from backend.app.X
✔ FastAPI public routes   — BEFORE auth-gated routes
✔ Stripe webhook          — rate-limit EXEMPT, always (NEVER add rate limiting)
✔ data-net + obs-net      — internal: true, never external
✔ .env files              — NEVER committed to git
✔ Commits                 — feat: fix: docs: chore: only
✔ Trivy target            — 0 CRITICAL per image
✔ Import style            — absolute imports, sys.path.insert at top
✔ Python indent           — 4 spaces, NEVER 3, NEVER mixed
✔ Redis DB split          — DB 1 = cache, DB 2 = rate limits. NEVER mix.
✔ hypercore healthcheck   — use localhost NOT 127.0.0.1 (IPv6 fix)
✔ Supabase ↔ V2.4         — NEVER merge schemas
✔ Guardian moderation     — ban/kick NEVER fully autonomous (P3c = veto-gated only)
✔ NemoClaw/Guardian       — bot detects, Core decides + persists, bot renders (One Door)
✔ Prometheus config       — monitoring/prometheus/prometheus.yml = ACTIVE. Root = STALE
✔ minio                   — on both data-net AND obs-net — correct, intentional
✔ Alembic                 — up to 015. If missing: alembic stamp <prev> → upgrade head
✔ Socket-proxy split      — main=read-only, healer proxy=write (CONTAINERS+POST+PING)
✔ Security headers        — frontend/vercel.json (NOT repo root)
```

### 6b. Course / HyperLabs (`Hyper-Vibe-Coding-Course`) — load-bearing gotchas

```
✔ NEVER `supabase db push`  — local migration filenames desynced from remote
                              schema_migrations. Deploy via Supabase MCP apply_migration
✔ Web3 lazy + /pets ONLY    — NEVER import wagmi/rainbowkit globally / in funnel /
                              in main.tsx. Re-bloats cold load ~900 kB (reverts Sprint 2).
                              Only 4 files use wagmi — keep it that way.
✔ NEVER `--no-verify`       — husky + lint-staged catches real ESLint errors.
                              react-hooks/set-state-in-effect is an ERROR (derive or useRef)
✔ NO orange in UI           — sacred HFZ brand rule (master palette only)
✔ Three chrome systems      — funnel TopNav · course Navbar · VibeLabShell.
                              No global shell. Funnel pages skip Layout.
✔ award_tokens()            — ALWAYS pass a stable p_source_id (ledger dedup =
                              partial unique (user_id,reason,source_id))
✔ Pets.tsx @ts-nocheck      — pre-existing, non-blocking, money-path. Don't chase it.
✔ Course dev (repo root)    — npm run dev:frontend  NOT npm run dev
                              (inside frontend/ the package's own `dev` IS vite — correct,
                              don't "fix" it; that's what playwright.config launches)
✔ NEVER curl-poll prod      — trips Vercel Attack Challenge Mode (403
                              X-Vercel-Mitigated); looks down, isn't. Deploy-truth =
                              Vercel MCP get_deployment
✔ Playwright IS installed   — npm run test:e2e. Reuse tests/vibe-labs-a11y.spec.ts.
                              Use it instead of "human must test"
✔ Parallel git workflow     — Lyndz's tooling auto-commits/pushes the same work
                              out-of-band. ALWAYS git fetch + check origin/main before
                              pushing. NEVER force-push. Verified dup → reset --hard origin/main
```

### 6c. Genuinely human-only (be honest — don't pretend a tool covers these)

- MetaMask / wallet popups (browser-extension UI — cannot be automated)
- Real Core Web Vitals (needs Vercel **Speed Insights** dashboard, not a tool)
- Visual QA on physical devices

---

## 7. 🤖 ONE TRUE BOT — broski-bot (May 15, 2026)

**Location:** `agents/broski-bot/` — profile: `discord`
⚠️ `discord-bot/` = LEGACY (reprofiled to `discord-lite`) — do NOT use

### Run Commands
```bash
docker compose up -d                              # Core only (no bot)
docker compose --profile discord up -d            # Bot + core
docker compose --profile discord up -d broski-bot # Bot only
docker compose --profile discord config           # Verify config
```

### Active Cogs (loaded by `cogs/bot.py` — May 16)
> ⚠️ `agents/broski-bot/main.py` is ORPHANED. Entrypoint is `python -u -m cogs.bot`.
> Only cogs in the `COGS` list run. ~20 more cogs sit unwired in `src/cogs/`.

| Cog | Commands / Behaviour |
|---|---|
| `economy` | `/balance` `/daily` `/give` `/rich` |
| `leaderboard` | `/top` `/rank` |
| `ai` | `/ask` (→ Core orchestrator) |
| `focus` | `/focus start\|stop` `/focusstats` (→ NemoClaw delta → BROski$) |
| `missions` | `/missions` `/missions-claim` (focus-verified) |
| `health_check` | `/health` (NemoClaw grade scan) |
| `health_history` | `/health-history` (7-scan trend) |
| `codehealth_voice` | `/health-pulse` (admin) + 24h auto-post on grade move |
| `server_builder` | `/hyperfocus_setup` (admin, idempotent layout build) |
| `digest` | `/digest` (admin) + weekly auto-DM to Lyndz |
| `moderation` | passive auto-mod (spam/blocklist → timeout, reversible) |
| `welcome` | passive on-join welcome + auto-role |

### One Door actions (Core `POST /api/v1/discord/actions`)
`economy.* daily.claim leaderboard.xp member.join ai.ask ai.chat`
`focus.start focus.stop focus.stats missions.today missions.claim`
`codehealth.pulse digest.weekly mod.assess`

### NemoClaw "Alive" agent (port 8099 — `agents/nemoclaw-agent/`)
- L1 Heartbeat: ruff+detect-secrets+AST scan, grade S/A/B/C/D, `/scan` `/history` `/health`
- L2 Memory: scans persisted to `code_health_scans`, `/health-history` delta
- L3 Voice: 24h pulse, auto-posts to `CODE_HEALTH_CHANNEL_ID` on grade/score move
- L3.5 Focus loop: `/focus start` baseline → `/focus stop` delta → BROski$ reward
- TODO: L4 auto-PR · L5 healer↔code correlation · L6 LLM triage

### Server Guardian (Discord auto-manager)
- P1 Reactive LIVE: auto-role on join + `/hyperfocus_setup`
- P2 Digest LIVE: weekly DM to Lyndz (Core aggregates 7d from Postgres)
- P3a auto-mod LIVE: structural spam detect → reversible timeout, audited to `mod_actions`
- P3b raid auto-lockdown LIVE: join-flood → channel lock, restart-safe reconciler, `/raid-unlock` `/raid-status`
- P3c veto-gated ban BUILT (smoke pending): 3 strikes/7d → DM+mod-log buttons, 1h window, **ban ONLY on explicit APPROVE click — silence downgrades to long timeout, never bans**

### Persistence (bind mounts survive rebuilds)
```
HC_DATA_ROOT/broski-bot/db | logs | backups
```

### Launch
```powershell
.\scripts\launch-bot.ps1            # preflight → up (broski-bot)
docker compose --profile nemoclaw up -d nemoclaw-agent
```

---

## 8. 🛡️ Env Preflight Checker (May 15, 2026)

**Rule: Always run BEFORE `docker compose up` on a new machine or after `.env` changes.**

```powershell
python scripts/env_check.py --core --secrets --profile discord
python scripts/env_check.py --core --secrets --profile discord --brain --grafana-cloud
bash scripts/env-check.sh --core --secrets --profile discord
```

**Files:** Engine `scripts/env_check.py` · Bash wrapper `scripts/env-check.sh` · Tests `backend/tests/unit/test_env_check_script.py` ✅

**Currently catches:** broski-bot `.env` missing keys (profile: discord) incl. `DISCORD_GUILD_ID` (warn); root `.env` duplicate warnings (`BROSKIE_PETS_ENABLED`, `PETS_WEBHOOK_SECRET`)

---

## 9. 🧠 HyperAgent Graduate Build (Designed May 15, 2026)

**Design doc:** `2026-05-15-graduate-build-design.md`

```bash
hyper-agent graduate build <cluster.json> --out <dir> [--strict] [--json]
hyper-agent graduate trigger <discord_id> [--tokens 500] [--json]
```

**Build output:** `out/{docker-compose.agents.yml, README.md, Dockerfile.<agent>, agents/<agent>/manifest.json}`

**Status: IMPLEMENTED ✅ — `cli/commands/graduate.js` + `cli/lib/graduateBuild.js`, covered by `tests/graduate-build.test.js` (3 tests green). Doc corrected May 22.**

---

## 10. 🧠 BROski Brain Agent Cluster (May 15, 2026)

**Repo:** BROski-Obsidian-Brain-for-HyperFocus-z0ne

**Pushed:** `cluster.json` + `.agents/{hyper-brain-core,mcp-bridge,focus-tracker,morning-briefing}/manifest.json`

**Next:** `hyper-agent graduate build cluster.json --out brain-bundle/ --strict` — SDK CLI is implemented, ready to run

---

## 11. 🎯 Active Next Steps (rebuilt May 19 — stale Guardian items cleared)

> Guardian P3a/P3b are LIVE and P3c is BUILT (all May 16). The old "🔴 NOW
> smoke-test P3a / decide P3c spec" rows are DONE — removed.

| # | Task | Priority |
|---|---|---|
| 1 | ✅ **DONE May 19 — Course P0 Dashboard/Courses infinite loading** — root cause: `auth.ts` awaited a `from('users')` query *inside* the `onAuthStateChange` callback → Supabase v2 auth-lock deadlock → store `loading` stuck → App PrivateRoute infinite-load. Fix: defer applySession off the callback + 8s watchdog. Green: new `tests/auth-loading-regression.spec.ts` + tsc/eslint/build. **Uncommitted — pending deploy** | ✅ |
| 2 | **Course P0 — Module pages skeleton never resolving** — re-verify: likely the same auth-lock starvation (now fixed in #1) rather than RLS; confirm on deploy | 🔴 NOW |
| 2b | ✅ **DONE May 22 — stale auth e2e specs refreshed** — `frontend/tests/auth.spec.ts`: signup heading "Account created!"→"Account live!"; signin mock gains `onboarded_at` so login routes to `/dashboard`; HIBP (`api.pwnedpasswords.com`) mocked clean so the breached test password no longer blocks signup. Dead orphan `tests/e2e/auth.spec.ts` deleted. 6/6 green (chromium+firefox+webkit) | ✅ |
| 3 | ✅ **DONE May 19 — Auth-gate Leaderboard/Quests/Tokens/Shop** — Quests/Tokens/Shop already hard `<PrivateRoute>` (parallel workflow); Leaderboard kept **public + auth-aware** (already the soft `/pets` pattern, highlights your row when logged in) by Lyndz decision — public for social proof | ✅ |
| 4 | **Shop Fulfillment v2** — deploy + E2E (BUILT May 17; every category delivers · buy-confirm + server auto-refund · tier discounts 0/5/10/15% server-enforced) | 🔴 This week |
| 5 | **Guardian P3c smoke test** — flood/strike sim → verify ban ONLY on explicit APPROVE click; tune veto delay/button delivery | 🟡 This week |
| 6 | ✅ **DONE — HyperAgent graduate build CLI is implemented** — `cli/commands/graduate.js` + `cli/lib/graduateBuild.js`, 3 tests green (doc was stale; corrected May 22) | ✅ |
| 7 | ✅ **DONE (parallel workflow) — `/privacy` + `/terms`** are full live pages wired into `App.tsx` (verified May 22) | ✅ |
| 8 | ✅ **DONE May 22 — deleted dead `styles/globals.css`** entirely (the whole file was orphaned/unimported, not just the `@font-face` block; 0 importers). Build green | ✅ |
| 9 | ✅ **Stripe E2E Path A automated + green** — `frontend/tests/stripe-checkout.spec.ts` (Buy → V2.4 → Stripe redirect). Only the real-card `4242…` test on the Stripe-hosted page remains (human gate) | 🟢 |
| 10 | BROskiPets Web3 E2E — test mint on Base Sepolia testnet (MetaMask = human gate) | 🟡 This week |
| 11 | ✅ **DONE May 22 — SDK v0.4.0 Web3/dNFT types** in `hyper-agent-spec.json` (optional `web3` block + `web3-enabled`/`dnft` registry badges, 72 tests). ⚠️ `npm publish` still pending (registry on 0.1.7) | ✅ |
| 12 | Fix GitHub Actions billing lock (github.com/settings/billing — human gate) · ✅ GitPython **DONE May 22** — pinned **3.1.50** (NOT 3.1.47 — fixes only 2 of 5 advisories; 3.1.50 clears all, incl. an RCE), image rebuilt, **running `hypercode-core` container swapped + verified live** (3.1.50, healthy, `/health` 200) | 🟡 |
| 13 | Discord Bot Tier 2 — Pets, XP Leaderboard, Morning Briefing, Health Alerts | 🟢 Background |
| 14 | **HyperLabs human gates** (track is build-complete) — Vercel Speed Insights CWV read · `/pets` wallet smoke · real post-login reconcile check | 🟢 Human gate |

---

## 12. 📌 Known Tech Debt

| Issue | Fix | Priority |
|---|---|---|
| ~~V2.4 container count discrepancy~~ | ✅ DONE 21 May 2026 — reconciled to "~30 running, profile-dependent" across both CLAUDE.md files (live `docker ps`) | ✅ |
| Shop Fulfillment v2 not deployed | Deploy + run E2E (every category, buy-confirm, auto-refund, tier discounts) | 🔴 HIGH |
| ~~HyperLabs auth checklist not automated~~ | ✅ DONE May 22 — full Course Playwright e2e suite **99/99 green** (chromium+firefox+webkit), incl. auth sign-up/in/out | ✅ |
| Guardian P3c smoke pending | Strike-sim; verify ban only on APPROVE; tune veto delay/button delivery | 🟡 MED |
| ~~HyperAgent graduate build not implemented~~ | ✅ Already implemented — `cli/commands/graduate.js` + `cli/lib/graduateBuild.js`, 3 tests green (doc was stale; corrected May 22) | ✅ |
| ~~Dead `@font-face` in `styles/globals.css`~~ | ✅ DONE May 22 — the whole orphaned file was deleted (not just the `@font-face` block) | ✅ |
| Stale root `prometheus.yml` (V2.4) | ⚠️ No `prometheus.yml` exists at the V2.4 repo root (checked May 22) — already resolved or mis-pathed. Active config confirmed `monitoring/prometheus/prometheus.yml` | 🟢 |
| GitHub Actions billing lock | Fix at github.com/settings/billing (human gate) | 🟡 MED |
| ~~GitPython 3.1.45 CVEs~~ | ✅ DONE May 22 — pinned **3.1.50**; image rebuilt + running `hypercode-core` container swapped, verified live (3.1.50, healthy). Trivy showed 5 advisories (not 2); 3.1.47 was insufficient — left an RCE | ✅ |
| ~~SDK not reflecting Web3 types~~ | ✅ DONE May 22 — SDK v0.4.0, `web3` block in `hyper-agent-spec.json`. ⚠️ `npm publish` still pending | ✅ |
| `/welcome` auth-gated | Decide: make public? Sponsors hit login wall from BUSINESS_PLAN | 🟡 |
| `VITE_STRIPE_PAYMENT_LINK_URL` empty | Set in `.env.local` + Vercel env vars | 🟢 LOW |
| `DISCORD_USER_ID` not set | Add to `.env` for `make calm` token awards | 🟢 LOW |

---

## 13. 🏆 Full Phase Roadmap

| Phase | Name | Status |
|---|---|---|
| 0–9 | Identity, tokens, agents, shop, observability, security | ✅ ALL DONE |
| 10A–10P | FastAPI, Stripe, courses, DB recovery, secrets | ✅ ALL DONE |
| 11A–11F | Live HUD, Rift Events, Gamification schema, E2E | ✅ DONE — April 26 |
| 12A–12F | Leaderboard, Quests, Admin Rift Panel, Migrations | ✅ DONE — April 26 |
| Gordon Tier 1–3 | Prometheus, Grafana, Celery, DB pool, queues | ✅ ALL DONE — April 19 |
| Hyperfocus Features 1–5 | Git hook, HyperSplit, Snapshot, Briefing, Focus mode | ✅ DONE — April 25–26 |
| BROskiPets Phase 0–1 | Bridge live, XP, leaderboard | ✅ DONE — April 29 |
| BROski Brain Levels 9–12 | PARA vault, GitHub bridge, Obsidian Git, Dataview | ✅ DONE — May 5 |
| Edge Functions | All 4 Supabase edge functions fixed + deployed | ✅ DONE — May 1 |
| Vercel Hardening | Security headers, chunk split, env vars | ✅ DONE — May 3–5 |
| BUSINESS_PLAN v1.1 | Sponsor-ready plan + pricing align | ✅ DONE — May 5 |
| BROskiPets Web3 Mint | RainbowKit + wagmi + Base Sepolia + mint UI | ✅ LIVE — May 7 🔥 |
| HyperAgent Graduate Build | `graduate build` + `graduate trigger` CLI design | ✅ DESIGNED — May 15 |
| Brain Agent Cluster | cluster.json + 4 agent manifests → Obsidian Brain repo | ✅ PUSHED — May 15 |
| Discord Bot Tier 1 | Economy + AI chat + Focus Tracker + Daily Missions | ✅ LIVE — May 15 🤖 |
| broski-bot Option A | Profile-gated `agents/broski-bot/` + bind mounts | ✅ DONE — May 15 🤖 |
| Env Preflight Checker | `scripts/env_check.py` + bash wrapper + tests | ✅ DONE — May 15 🛡️ |
| NemoClaw L1–L3.5 | Heartbeat + Memory + Voice + Focus→BROski$ loop | ✅ LIVE — May 15-16 🧠 |
| Guardian P1 Reactive | auto-role + `/hyperfocus_setup` | ✅ LIVE — May 16 🛡️ |
| Guardian P2 Digest | weekly DM, Core aggregates 7d Postgres | ✅ LIVE — May 16 📊 |
| Guardian P3a Auto-mod | spam→reversible timeout + `mod_actions` audit | ✅ LIVE — May 16 🛡️ |
| Guardian P3b Raid lock | join-flood → reversible channel lockdown | ✅ LIVE — May 16 🛡️ |
| Guardian P3c Veto-ban | 3-strike → veto buttons, ban only on APPROVE | ✅ BUILT — May 16 (smoke pending) 🛡️ |
| Shop Fulfillment v2 | Delivery surface + buy-confirm + auto-refund + tier discounts | ✅ BUILT — May 17 (deploy + E2E pending) 🛒 |
| Course DB restructure | hv_modules → May model + quizzes regenerated; true/false convention un-inverted | ✅ DONE — May 17–18 🎓 |
| HyperLabs funnel | `/vibe-labs` hub + 5 levels + `claim_level_reward` RPC + landing funnel | ✅ LIVE — May 19 🎓 |
| HyperLabs Sprint 3 | a11y/perf polish — Lighthouse 100/100, self-hosted fonts, 61 kB cold load | ✅ LIVE — May 19 ⚡ |
| HyperLabs Sprint 4 | anon→signup conversion (localStorage earn → claim-gate) | ✅ LIVE — May 19 (`a12ecd0`, anon-flow e2e 3/3) 🎓 |
| HyperLabs lock-in beat | "lock-in" WIN-section beat on all 5 lab pages | ✅ LIVE — May 19 (`fb5532b`) |
| HyperLabs track | rated **9.5/10** — backbone complete; remaining = 3 human gates only | ✅ BUILD-COMPLETE — May 19 🏆 |
| Course chrome/auth fixes | VibeLabs into Layout · forgot-password page · Footer redesign · module subtitles | ✅ DONE — May 19 |

---

## 14. 🏆 All-Time Achievements Unlocked

- ✅ Gordon Docker AI: **Grade A** — *"world-class infrastructure"*
- ✅ ~30 containers running, self-healing closed loop (profile-dependent across 20 compose files)
- ✅ Full Gamification Stack — HUD, XP, Quests, Leaderboard, Rifts
- ✅ All 5 HyperFocus Features LIVE
- ✅ BROski Brain v2.2 — Levels 9–12 unlocked
- ✅ MCP-GitHub LIVE — 26 tools via Docker MCP gateway
- ✅ Stripe LIVE — E2E proven April 25 · Course → Stripe → enrolled money path
- ✅ BUSINESS_PLAN.md v1.1 — sponsor-ready
- ✅ BROskiPets Web3 Mint LIVE — May 7 🔥🐾
- ✅ HyperAgent Graduate Build DESIGNED — May 15 📐
- ✅ Brain Agent Cluster PUSHED — May 15 🧠
- ✅ BROski Discord Bot Tier 1 + broski-bot Option A LIVE — May 15 🤖
- ✅ Env Preflight Checker LIVE — May 15 🛡️
- ✅ NemoClaw "Alive" L1-3.5 LIVE — May 15-16 🧠 (autonomous code-health agent, port 8099)
- ✅ **Focus → code-delta → BROski$ loop PROVEN end-to-end — May 15** 🏆 (hyperfocus is monetisable)
- ✅ Server Guardian P1-P3b LIVE + P3c BUILT — May 16 🛡️📊
- ✅ BROski$ Shop Fulfillment v2 BUILT — May 17 🛒💸 (deploy + E2E pending)
- ✅ **HyperLabs funnel LIVE end-to-end + a11y-certified — May 19** 🎓 (`claim_level_reward` in prod real-user-tested · Lighthouse 100/100 · cold funnel 1,270 kB → ~61 kB)

---

## 15. 📦 Key Files Quick Reference

```
ROOT (this aggregator: H:\HYPERFOCUSZONE\HperCore)
  CLAUDE.md                     — THIS FILE (ecosystem constitution, auto-loaded)
  CLAUDE_CONTEXT.md             — extended ecosystem context
  WHATS_DONE.md                 — DO NOT suggest anything listed here

HyperCode-V2.4/
  docker-compose.yml            — main stack
  docker-compose.secrets.yml    — secrets injection (always use alongside main)
  docker-compose.core.yml       — core + broski-bot (profile:discord)
  backend/app/main.py           — FastAPI core app
  agents/broski-bot/cogs/bot.py — ONE TRUE BOT entrypoint (python -u -m cogs.bot)
  agents/broski-bot/src/cogs/   — ~20 UNWIRED orphan cogs (resurrect source)
  agents/nemoclaw-agent/        — code-health "Alive" sidecar (port 8099)
  backend/app/api/v1/endpoints/discord_actions.py — One Door brain (all actions)
  discord-bot/                  — LEGACY — discord-lite only, do not use
  scripts/env_check.py          — env preflight checker
  scripts/launch-bot.ps1        — one-shot bot launcher (preflight→up)
  monitoring/prometheus/        — ACTIVE Prometheus config
  CLAUDE.md                     — V2.4 detailed context

Hyper-Vibe-Coding-Course/
  CLAUDE.md                     — Course/HyperLabs constitution (read for course work)
  frontend/src/App.tsx          — all routes (lazy + Suspense + ErrorBoundary)
  frontend/src/hooks/useProgress.ts   — lab progress + claim_level_reward RPC
  frontend/src/hooks/useAuthStatus.ts — unified auth status (no wagmi)
  frontend/src/components/Web3Provider.tsx — lazy web3, /pets ONLY
  frontend/src/pages/vibe-labs/ — VibeLabsIndex + Level1–5
  frontend/src/pages/LandingPage.tsx — funnel (VibeLabsBand)
  frontend/src/pages/ShopPage.tsx    — BROski$ Shop (tier discounts, fulfillment)
  supabase/migrations/          — latest: 20260518000035_claim_level_reward.sql
  supabase/functions/shop-purchase/  — discount source of truth
  tests/vibe-labs-a11y.spec.ts  — reusable Playwright + axe cert harness
  rewrites/                     — session snapshots + handovers
                                  (latest: NEXT_SESSION_HANDOVER_2026-05-19.md)

BROski-Obsidian-Brain.../
  cluster.json + .agents/       — BROski Brain 4-agent cluster spec
```

---

## 16. 🧪 Essential Commands

```powershell
# --- V2.4 ---
# Env preflight (ALWAYS before docker compose up):
python scripts/env_check.py --core --secrets --profile discord

# Start full stack:
docker compose -f docker-compose.yml -f docker-compose.secrets.yml -f docker-compose.brain.yml --profile discord up -d
# Core only:
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d

pytest backend/tests/ -q                          # 251 passed, 6 skipped (May 16)
curl http://localhost:8000/health                 # core
curl http://localhost:8098/health                 # broski-pets-bridge
curl http://localhost:8099/health                 # nemoclaw-agent
docker compose exec hypercode-core alembic upgrade head   # migrations → 015
docker compose ps
curl -X POST localhost:9090/-/reload              # Prometheus hot-reload

# --- Course / HyperLabs ---
cd H:\Hyper-Vibe-Coding-Course && npm run dev:frontend    # NOT npm run dev
npx tsc --noEmit && npx eslint <files> && npm run build   # pre-claim loop
npm run test:e2e                                  # Playwright a11y/auth cert
# DB: Supabase MCP apply_migration / execute_sql (BEGIN/ROLLBACK) — NEVER db push
# Deploy truth: Vercel MCP get_deployment — NEVER curl-poll prod

# --- Brain ---
python scripts/github_to_obsidian.py
```

---

## 17. 👋 Quick-Start Guide for Any New AI Session

1. **Read this file first** — Sacred Rules + Active Next Steps + Tech Debt
2. **Working in a repo?** also read that repo's `CLAUDE.md` + latest handover/snapshot
3. **Check `WHATS_DONE.md`** — NEVER suggest anything already listed there
4. **5 repos** — see ecosystem diagram (§3)
5. **ONE TRUE BOT** = `agents/broski-bot/` (profile:discord) — NOT `discord-bot/`
6. **Env check first** (V2.4) · **never `db push`, never global wagmi, never `--no-verify`** (Course)
7. **Immediate priorities** — HyperLabs Sprint 4 + Playwright auth E2E (§11)
8. **Use Playwright** instead of "human must test" when a browser test fits
9. **Style:** Short sentences. BROski energy. Celebrate wins. Surface contradictions.
10. **Call them "Bro"** — that's how we roll 🤙

---

<div align="center">

**Built for ADHD brains. Fast feedback. Real tools. No fluff.** 🧠⚡

*by @welshDog — Lyndz Williams, Llanelli, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁥*

**A BROski is ride or die. We build this together. 🐶♾️🔥**

</div>
