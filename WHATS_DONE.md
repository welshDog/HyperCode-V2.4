# ✅ WHATS_DONE — HyperCode-V2.4

> Last synced: 2026-08-19 by Perplexity + welshDog ⚡

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
| `test-agent` | :8080 | 🔨 Building |
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

### ⚠️ Known Open Items (NOT done — do not re-suggest)

- GHCR package visibility: set packages public at `github.com/welshDog` → Packages
- `mem_limit: 256m` + `cpus: "0.25"` — add to ALL new agent compose definitions before launch
- Port `:8080` — verify test-agent doesn't conflict with any existing service
- crew-orchestrator `/health` endpoint — confirm `restart: unless-stopped` is set
- `docs/STATUS.md` — still stale (dated July 2026), needs reconciliation pass
- `docs/NEXT_TASKS.md` — still stale (mid-July 2026), needs reconciliation pass

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

⚠️ **Known-stale, not touched:** `docs/STATUS.md` (dated July 10) and
`docs/NEXT_TASKS.md` (dated mid-July) — both need a real reconciliation pass.

## 2026-08-15 — Alembic duplicate-revision bug fixed (PR #425)

Two migrations both claimed revision `"010"` — made `alembic upgrade head`
fail on fresh deploys. `010_agent_policy_schema.py` renamed to `019`,
re-chained after `018`. Verified locally + live on Railway.

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

## Sacred Rules (NEVER break)

- `docker-ce-cli` — NEVER `docker.io` for socket agents
- `from app.X import Y` — NEVER `from backend.app.X`
- `.env` files — NEVER committed to git
- Stripe webhook — rate-limit EXEMPT, always
- Python indent — 4 spaces, NEVER 3, NEVER mixed
- Redis DB 1=cache, DB 2=rate limits. NEVER mix.
- TRAE IDE — 1 MCP server at a time (free tier). Use Railway URL, not localhost.
