# ✅ WHATS_DONE — HyperCode-V2.4

> Last synced: 2026-08-20 (evening) by Claude + welshDog ⚡

---

## 2026-08-20 (evening, part 2) — Fleet Dedupe Decision

Asked Bro to pick between 4 options for the item-#0 finding below (retire
agents-full.yml's 14 duplicate agent definitions / rename them / give them
distinct names / stop composing the two files together). **Decision: stop
composing them together** — nothing deleted, fully reversible, kills the
silent-merge hazard immediately. The permanent fix (who owns these 14 agents
long-term) is still open. Documented in `CLAUDE.md`, `agents-full.yml`'s header,
`NEXT_TASKS.md` item #0, and `fleet-roster-check.sh`.

While in the same area: corrected `business-agent`'s status. It does have a
Dockerfile (`agents/business/project-strategist/Dockerfile`), but the code it
builds identifies itself as `"Project Strategist"` and exposes the wrong port —
a project-strategist directory cloned as a starting scaffold, never customized.
Did not wire compose to it. `NEXT_TASKS.md` P2-1 updated with the precise finding.

---

## 2026-08-20 (evening) — agents-full.yml Real Collision Fixes + Architecture Audit

Verified the 08-20 morning session's "3 port collisions" claim against the actual
merge (`docker compose config`), not just grep — found the real picture was worse.
Commit: `e9638019`.

### ✅ Fixed & pushed
- `hypercode-mcp-server` phantom ghost block **deleted** from `docker-compose.agents-full.yml`
  — pointed at `./agents/hypercode-mcp-server`, which never existed; was silently
  swapping the real live service's build context on merge. Not a 25th agent to rename.
- 3 real port collisions fixed, each verified against a live container:
  `system-architect` 8008→8010 (was `healer-agent`), `hyper-split-agent` 8096→8013
  (was `safety-shepherd`), `session-snapshot` 8097→8017 (was `evolve-relay`).
- Documented launch command was missing `--profile agents` — without it
  `crew-orchestrator` silently drops from the merge and the compose project is
  invalid. Fixed in `CLAUDE.md` + the compose file's own header.
- Synced `scripts/fleet-roster-check.sh` (24-entry roster now, re-ran it, exit 0)
  and `.github/workflows/health-check.yml`'s `EXPECTED_PORTS` dict.

### 🔴 Found, not fixed — needs Bro's call
- **14 of ~24 agent names in `agents-full.yml` are also defined in
  `docker-compose.agents.yml`** with different build contexts/ports/profiles.
  Same-name services merge silently across compose files instead of erroring —
  proven on `hypercode-mcp-server` and `hyper-architect`. Most of "the 25-agent
  fleet" launch has never deployed what the docs describe. This is an
  architecture decision (rename scheme / dedupe / retire one side), not a port
  patch. Logged as `NEXT_TASKS.md` item #0.
- `tips-tricks-writer` (:8009) collides with live `chroma` — new, not in the
  original list.
- `test-agent` (:8100) still collides with live `hyper-brain` — entangled with
  the item-#0 decision, not just a port move.
- `business-agent` still has no Dockerfile anywhere (pre-existing, unchanged).
- `docs/STATUS.md`'s "Agent Fleet — 25 Total" table is stale (predates the
  08-19/08-20 reconciliation) — flagged with a banner in place, not rewritten.
- `.github/workflows/ghost-agents-build.yml`'s build matrix `context:` paths are
  wrong for most of its 12 entries (point at directories that don't exist).
- Two pre-existing, always-broken CI checks found (not caused tonight): the
  `port-check` job's dedup regex in `ghost-agents-build.yml`, and the port
  parser in `health-check.yml`'s `EXPECTED_PORTS` gate — both would fail to
  ever correctly extract a real host port from `"127.0.0.1:PORT:PORT"` syntax.

Full detail + evidence commands: `docs/NEXT_TASKS.md` items #0, 1a, 1b, 5–8.

---

## 2026-08-19 — STATUS.md + NEXT_TASKS.md Reconciliation Pass

Full docs reconciliation. Both files were stale (July 10 / mid-July). Now accurate and live.

### ✅ docs/STATUS.md — Fully Updated

- Bumped from **July 10 → August 19, 2026**
- Full **25-agent fleet table** added (13 existing + 12 ghost agents)
- Each agent shows port + live/building status
- ⚠️ Known Risks section added: port clash, memory pressure, crew-orchestrator SPOF, JWT expiry
- Commit: `da91777b`

### ✅ docs/NEXT_TASKS.md — Fully Restructured

- Restructured into priority tiers: 🔴 Immediate → 🟡 This Week → 🟢 Background
- Pre-launch checklist (port check, resource limits, crew-orchestrator health, launch command) surfaced at top
- August 2026 completions (ghost agent session) properly logged
- Stale July items carried forward or marked done
- Commit: `da91777b`

---

## 2026-08-19 — 12 Ghost Agents Built + CI/CD Pipeline + AGENT-START v3.3

Full ghost-agent fleet session. All 12 previously-missing agents identified, scaffolded, and registered. Full CI/CD pipeline created for parallel GHCR builds.

### ✅ 12 Ghost Agents Registered & Building

All 12 agents identified, port-mapped, and registered in compose + AGENT-START:

| Agent | Port | Status |
|---|---|---|
| `security-engineer` | :8007 | ✅ Ready |
| `system-architect` | :8008 | 🔨 Building |
| `tips-tricks-writer` | :8009 | 🔨 Building |
| `throttle-agent` | :8014 | 🔨 Building |
| `super-hyper-broski` | :8015 | 🔨 Building |
| `test-agent` | :8080 | 🔨 Building — ⚠️ check port clash |
| `hyper-architect` | :8091 | 🔨 Building |
| `hyper-observer` | :8092 | 🔨 Building |
| `hyper-worker` | :8093 | 🔨 Building |
| `hyper-split-agent` | :8096 | 🔨 Building |
| `session-snapshot` | :8097 | 🔨 Building |
| `agent-x` | custom | 🔨 Building |

### ✅ AGENT-START.md upgraded to v3.3

Commit `9e6a695` — supersedes v3.2 (2026-06-16). Key additions:
- Full 25-agent fleet table (13 original + 12 ghost) with ports + roles
- Resource limits guidance (`256m` / `0.25 cpus`) baked in
- crew-orchestrator SPOF warning flagged
- 2 new gotchas: memory pressure + `:8080` collision risk
- Per-repo doc authority map (`§4`) expanded
- Launch command documented: `docker compose -f docker-compose.yml -f docker-compose.agents-full.yml up -d`

### ✅ 4 Comprehensive Build Guides Created

- `BUILD_ALL_AGENTS_GUIDE.md` — full architecture + getting started
- `AGENTS_BUILD_STATUS.md` — detailed status tracking
- `AGENT_BUILD_SESSION_SUMMARY.md` — session breakdown
- `QUICK_START_12_AGENTS.md` — one-page reference

### ✅ Build Automation Scripts

- `build-all-agents.ps1` — PowerShell: checks status + initiates builds
- `start-all-agents.sh` — shell: starts the full 25-agent stack

### ✅ CI/CD Workflow: ghost-agents-build.yml

Commit `d8a0f32` — `.github/workflows/ghost-agents-build.yml`

Three-job pipeline:
1. **`port-check`** — scans all compose files for duplicate ports; fails hard if found. Specifically warns on `:8080`.
2. **`build-ghost-agents`** — parallel matrix: all 12 agents build simultaneously. `fail-fast: false` so one failure doesn't cancel the rest. Skips gracefully if agent dir doesn't exist yet. Pushes to `ghcr.io/welshdog/<agent>:latest` + SHA tag. Uses GHA layer cache.
3. **`fleet-status`** — always runs; drops launch command into Actions summary.

Triggers:
- Push to `main` (agent files / compose files changed)
- `workflow_dispatch` (manual) — optionally target a single agent via `agent:` input

---

## 2026-08-16 — Evolution Plan Phase 0.3/1.3 + 3x MCP server auth gap closed

Working from `🚀 HYPERCODE EVOLUTION PLAN — 2026 & BEYOND` (HperCore root).
Corrected the plan's own Phase 0.1/1.1-1.3 assumptions against actual code
before building anything (found HyperFlow already covers most of Phase
1.3's "goal-based orchestration", MCP gateway is live infra not
greenfield, ECOSYSTEM_TRUTH.md would duplicate the already-generated
AGENT-START.md repo map) — see that file's inline annotations.

- **Phase 0.3 — Agent registry manifest.** `agents/agent-registry/agent_registry.py`'s
  `ROSTER` (43 agents) gained `capabilities`/`tools_exposed`/`events_subscribed`
  (honestly `None` — no invented data), `health_endpoint` (derived only
  from ports already documented in each agent's `role` string), `mcp`
  (`True` for the 4 agents whose name/role already says MCP), `a2a`
  (`False` for all — nothing implements it yet). Surfaced via the
  existing `GET /agents/status` — no new endpoints. 6 new tests
  (`backend/tests/test_agent_registry_manifest.py`).

- **HyperFlow goal matcher (Phase 1.3 v1).** `POST /api/v1/flows/runs`
  now accepts `{"description": "..."}` as an alternative to
  `{"flow": "name"}` — deterministic keyword (Jaccard) matcher
  (`app/agents/hyperflow/goal_matcher.py`) against each flow's
  `name + intent`, env-tunable threshold (`HYPERFLOW_MATCH_THRESHOLD`,
  default 0.4). Explicitly NOT an LLM-generated graph compiler — routes
  only to existing, already-reviewed flows; a confident match runs the
  exact same `start_flow_run` path an explicit `flow` name would.
  Exact top-two tie → ambiguous, 422 (never silently picks one). Zero
  changes to `HyperFlowRunner` or Safety Shepherd. Spec:
  `docs/superpowers/specs/2026-08-15-hyperflow-goal-matcher-design.md`.

- **MCP server auth — closed on all three internal MCP servers**, found
  and fixed one at a time this session, each with zero application-level
  auth before this (network-isolation-only):
  - `agents/stripe-mcp/server.py` — creates real Stripe checkout sessions.
  - `agents/broski-economy-mcp/server.py` — the serious one:
    `award_tokens`/`spend_tokens` wrap `SECURITY DEFINER` SQL functions
    with **no caller-identity check** before this fix; an unauthenticated
    caller could have minted unlimited BROski$ or drained any account.
  - `services/mcp-rest-adapter/app.py` — REST shim in front of the
    generic `docker/mcp-gateway` (github/postgres/filesystem tools).
    **Real live caller** (unlike the other two) — the dashboard's IDE
    view proxies through it; the fix had to also teach
    `agents/dashboard/app/api/mcp/[...path]/route.ts` to send the token,
    or every IDE tool call would have silently 401'd while `/health`
    kept reporting green.

  All three: shared-secret `Authorization: Bearer <token>` per server
  (`STRIPE_MCP_AUTH_TOKEN` / `BROSKI_ECONOMY_MCP_AUTH_TOKEN` /
  `MCP_REST_ADAPTER_AUTH_TOKEN`, never shared across servers),
  `hmac.compare_digest` on UTF-8-encoded bytes (not `str` — non-ASCII
  tokens crash `compare_digest` on `str` args), both sides `.strip()`'d
  (an unstripped secret rejects the *correct* token — real bug an
  independent review caught live against the first two servers; baked
  the fix into the third from the start). Fails closed: unset/empty
  secret rejects everything. `/health` stays open on all three. 23 tests
  across the three auth suites (`test_stripe_mcp_auth.py`,
  `test_broski_economy_mcp_auth.py`, `test_mcp_rest_adapter_auth.py`).
  Spec: `docs/superpowers/specs/2026-08-15-mcp-tool-server-auth-design.md`.

- **`docs/MCP_TOOL_INVENTORY.md`** (new) — every tool across all four MCP
  servers (the three above + the generic gateway's github/postgres/
  filesystem), tagged read-only/write, auth status, actual reachability,
  and a safe-to-expose-later classification.

- **`agents/shared/mcp_client.py`** — fixed a latent env var mismatch.

---

## 2026-08-15 — Alembic duplicate-revision bug fixed (PR #425)

Two migrations both claimed revision `"010"` — made `alembic upgrade head`
fail on fresh deploys. `010_agent_policy_schema.py` renamed to `019`,
re-chained after `018`. Verified locally + live on Railway.

---

## Done & Locked — Do NOT re-suggest

- Backend test DB: JSONB/UUID columns made SQLite-compatible via with_variant()
- 48 Docker containers scaffolded and mapped
- docker-ce-cli locked (NEVER docker.io)
- Redis DB split: DB1=cache, DB2=rate limits
- .env.example committed (never .env itself)
- Stripe webhook rate-limit exempt — confirmed
- Python indent: 4 spaces enforced via .pylintrc
- CI smoke check pipeline in place (.ci-smoke-check)
- Pre-commit hooks configured (.pre-commit-config.yaml)
- Full port map documented (PORT_MAP_COMPLETE.md)
- Health checks documented (HEALTH_CHECK_FULL_REPORT_MAY9_2026.md)
- Makefile + Makefile.observability complete
- Docker production + hardened templates built
- Self-improving agents setup documented
- Master integration plan written
- Obsidian sync integration documented
- Dashboard status tracked (2026-06-16)
- Session handovers logged (May–June 2026)
- **HyperFlow P0-1** — declarative agent mission-graph DSL
- **Safety Shepherd P0-2** — runtime policy brain
- **Brain P2-2 + P2-3** (cross-repo, BROski-Obsidian-Brain)
- **Evo Harness P2-1** — milestone DAG scorer
- **Specialist HYPER-AGENT-BIBLEs P1-4** — 10 filled stubs
- **Governance Ledger P1-2** — durable audit trail
- **BROski Identity Agent P1-1** — resident agent object per user
- **Mission Graph Dashboard Panel P0-3** — `/flows` route + SSE panel
- **HyperFlow ↔ Safety Shepherd wiring** — safety gate on every dispatch
- **Hyper MCP Server v2** — spec-compliant JSON-RPC 2.0 (vault-deployed)
- **HyperStudio Phase 1** — agent write path (PR #315, `ee229ef`)
- **HyperStudio Phase 2** — interactive ESCALATE approval (PR #316, `9f532fb`)
- **AGENT-START.md v3.3** — full 25-agent fleet registered (commit `9e6a695`)
- **ghost-agents-build.yml** — parallel CI/CD for 12 ghost agents (commit `d8a0f32`)
- **docs/STATUS.md reconciliation** — fully updated Aug 19 2026 (commit `da91777b`)
- **docs/NEXT_TASKS.md reconciliation** — fully restructured Aug 19 2026 (commit `da91777b`)

---

## Sacred Rules (NEVER break)

- `docker-ce-cli` — NEVER `docker.io` for socket agents
- `from app.X import Y` — NEVER `from backend.app.X`
- `.env` files — NEVER committed to git
- Stripe webhook — rate-limit EXEMPT, always
- Python indent — 4 spaces, NEVER 3, NEVER mixed
- Redis DB 1=cache, DB 2=rate limits. NEVER mix.
- TRAE IDE — 1 MCP server at a time (free tier). Use Railway URL, not localhost.
