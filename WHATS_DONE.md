# ✅ WHATS_DONE — HyperCode-V2.4

> Last synced: 2026-08-16 by Claude Sonnet 5 ⚡

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
  and a safe-to-expose-later classification. Corrected twice against the
  real compose files after getting the reachability claims wrong on the
  first two passes — `stripe-mcp`/`broski-economy-mcp` have **no**
  `ports:`/`expose:` at all (network-only, more isolated than first
  documented); `mcp-rest-adapter` is actually the *least* isolated of
  the three (`ports: 127.0.0.1:8821:8821`), not "the same as the other
  two" as a second draft claimed. Still-open: the `postgres:<action>`
  passthrough on `mcp-rest-adapter` is unconstrained — auth now controls
  *who* can call it, not *what* it's allowed to do (upstream gateway's
  own `postgres` MCP server capabilities, unaudited, out of scope).

- **`agents/shared/mcp_client.py`** — fixed a latent (currently dead-code,
  nothing imports `MCPClient`) env var mismatch found while fixing
  `mcp-rest-adapter`: it defaulted to that service's URL but read its
  auth token from `MCP_GATEWAY_API_KEY` (a different service's
  outbound-only token) instead of `MCP_REST_ADAPTER_AUTH_TOKEN`.

⚠️ **Known-stale, not touched this session:** `docs/STATUS.md` (dated
July 10, predates most of this file's own content) and
`docs/NEXT_TASKS.md` (dated mid-July, doesn't reflect the Railway P0 or
anything from August) — both need a real reconciliation pass, not
attempted here since it's a bigger job than today's session and neither
file's staleness was caused by today's work.

## 2026-08-15 — Alembic duplicate-revision bug fixed (PR #425)

Two migrations both claimed revision `"010"` (`down_revision "009"`) —
`010_add_access_provisions_event_id.py` (the real chain) and
`010_agent_policy_schema.py` (PR #424, "Policy Engine foundation", merged
08-14 without being rebased against the already-merged `010`). Made
`alembic upgrade head` fail outright on ANY fresh deploy with "Multiple
head revisions are present." Found while standing up a fresh Railway
deployment for the cross-repo `generate-v2-config` `V24_API_URL` P0 (see
`NEXT_SESSION_HANDOVER_2026-08-15.md` for the full cross-repo context).

`010_agent_policy_schema.py` is fully self-contained (3 brand-new tables,
no FKs outside itself, nothing references it) — renamed to `019`,
re-chained after `018` (the real tip). Verified locally (`alembic heads`
→ single head, full linear `alembic history`) and confirmed live: the
next Railway deploy attempt ran the full migration chain clean, zero
errors. Deploy is now blocked on a separate, unrelated Redis connectivity
issue — not yet diagnosed, see the handover doc.

## Done & Locked — Do NOT re-suggest

- Backend test DB: JSONB/UUID columns (governance, hyperflow, identity models) made SQLite-compatible via with_variant() — full pytest suite runnable without a real Postgres instance
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
- **HyperFlow P0-1** — declarative agent mission-graph DSL: Pydantic schema + YAML loader (`app/agents/hyperflow/`), `HyperFlowRunner` (in-core asyncio walk, orchestrator dispatch, approval-gate suspend, retry/loop/fallback edges), `hyperflow_runs` table (migration `016`), control API `/api/v1/flows` (start/status/SSE/resume), Prometheus `hyperflow_node_duration_seconds`, example flow `implement-new-agent`. 8 unit tests green. Live E2E proven (smoke flow + real-agent flow).
- **Safety Shepherd P0-2** — runtime policy brain `agents/safety-shepherd/` (:8096, profile `safety`, agents-net+data-net, no Docker socket): pure decision engine `policy.py` (ALLOW/BLOCK/ESCALATE) + hot-reloaded `capabilities.json` manifest (per-agent tools/paths/domains/max_actions, Stripe exempt). `/evaluate` (agent-key authed), `/safety/events`, `/metrics` (`safety_decisions_total`), structlog JSON → Loki. ESCALATE raises a request on shared `approval_requests` → core `/api/v1/dashboard/approval-requests` (GET/POST/respond). 11 unit tests green; live E2E proven (decisions + escalation→dashboard→respond loop).
- **Brain P2-2 + P2-3** (cross-repo, `BROski-Obsidian-Brain`, engine :8100) — **P2-2** Constellation Level 20: graph (nodes/edges) + auto-generated Obsidian canvas + `/constellation/map` & `/constellation/refresh` (commit `ac972c3`). **P2-3** Brain Levels 18 + 19: AI distraction monitor (3 signals → Discord nudge) + DifficultyDial dynamic XP (intensity × quality × HyperSplit chunk difficulty) (commit `10cee0e`). See that repo's `WHATS_DONE.md`.
- **Evo Harness P2-1** — `scripts/evo_harness.py` (stdlib-only, CI-safe): parses `docs/ROADMAP.md` → milestone DAG (each phase a node + preconditions) → scores with **cascading preconditions** (a broken early phase blocks downstream = long-horizon regression signal) → JSON report to `docs/evo_reports/YYYY-MM-DD.json`. `--live` additionally probes health endpoints + Prometheus SLOs + a HyperFlow smoke mission; `--rollback` gated/never-in-CI. Separate CI workflow `.github/workflows/evo-harness.yml` (push/PR/weekly) runs unit tests + `--check --fail-under 0.9` + uploads the report. 7 unit tests. First run: 25/26 milestones green (0.962).
- **Specialist HYPER-AGENT-BIBLEs P1-4** — filled the 10 empty 0-byte stubs (crew-orchestrator's already existed as the shared hub, left intact): frontend, backend, database-architect, qa-engineer, devops-engineer, security-engineer, system-architect, tips-tricks-writer, project-strategist, test-agent. Each has role def + role-specific sacred rules + capabilities manifest (aligned with the live Safety Shepherd `capabilities.json` — flags explicit-grant vs wildcard-default) + decision tree (escalate → Safety Shepherd :8096) + HyperFlow `agent_role` mapping + governance via `IdentityAgent.log_action` → governance_ledger + a real example task.
- **Governance Ledger P1-2** — durable audit trail. `governance_ledger` table (mig **018**, NOT 016 — head was 017; id UUID gen_random_uuid, user_id/action/tool_used/payload JSONB/decision/agent_name/approved_by/timestamp; idx user_id/timestamp/action) + `GovernanceLedger` model. `IdentityAgent.log_action()` now writes a ledger row (fail-soft — never blocks the action) on top of the in-state ring. `GET /api/v1/governance/ledger` (filter user_id/action, paginated, newest-first). 7 unit tests (incl. fail-soft) + live E2E proven (award → ledger row with UUID/decision/approved_by). Grafana: HyperCode Postgres datasource + governance timeline panel on hypercode_overview (needs obs profile up + grafana on data-net).
- **BROski Identity Agent P1-1** — resident agent object per user. `broski_identity_agents` table (mig `017`, FK users.id, JSONB state, last_active), `BROskiIdentityAgent` model, `IdentityAgent` class (`app/agents/identity_agent.py`): `get_or_create`, `award_tokens` (logs → wraps durable `broski_service.award_xp`), `check_permission`, `log_action` (capped ring). `/api/v1/identity/me` (+`/award`, `/actions`, `/check-permission`), `X-BROSKI-IDENTITY` header. 6 unit tests + live E2E proven (provision, award +75 XP durable 385→460, action logged). Retrofit of existing economy/shop/dispatch call-sites to IdentityAgent = follow-up.
- **Mission Graph Dashboard Panel P0-3** — `GET /api/v1/flows/active` (active runs) + Next.js panel in hypercode-dashboard (`/flows` route, nav "🕸️ Flows"): `useMissionGraph` hook polls `/flows/active` + streams the run's transitions via SSE (EventSource direct to core); shows flow name, active node, per-node status, last-transition time; one flow at a time (ADHD); colour-coded (running=blue, completed=green, awaiting_approval=yellow, failed=red). Verified live via headless Chrome (rendered panel shows live awaiting_approval run; empty-state when idle).
- **HyperFlow ↔ Safety Shepherd wiring** — `HyperFlowRunner._safety_gate` consults Safety Shepherd `/evaluate` before every agent/tool dispatch. `SAFETY_SHEPHERD_MODE` = `off` | `monitor` (record decision, never block) | `enforce` (BLOCK→fail node, ESCALATE→park `awaiting_approval` until human approves via dashboard, then proceed). Optional `safety:` hint on a flow node declares the dangerous category/target/domain. Fail-open (3s) if Shepherd unreachable. Decisions recorded in the run timeline + SSE. 6 new unit tests (14 total green); live enforce E2E proven via `safety-demo` flow (escalate→approve→completed).
- **Hyper MCP Server v2** — FastAPI MCP server (`hyper-mcp-server/`) built on skills HS-081 PORTAL FORGE + HS-129 SKILLS-OVER-MCP. **Now a spec-compliant JSON-RPC 2.0 server** (Streamable HTTP) — single transport endpoint `POST /mcp` handling `initialize` → `notifications/initialized` → `tools/list` → `tools/call`, plus `resources/list` / `resources/read` (SEP-2640) and `ping`. Proper JSON-RPC error codes (`-32601` method-not-found etc.); tool failures returned in-band as `isError` (not protocol errors); notifications return `202`. Exposes 3 agents as MCP tools (`broski_agent`, `brain_core_agent`, `hyper_skill_agent`). `resources/read` fetches the **live skill body** from `SKILLS_API_URL` (vault) with seed-metadata fallback. **API-key auth**: when `MCP_API_KEY` is set, every `/mcp` call must send `X-API-Key` (→ `401` otherwise); open for local dev. Legacy `GET /tools/list` REST routes kept for curl smoke-tests only — NOT the MCP surface. Dockerfile now honours Railway `$PORT`. Local E2E **proven** 2026-06-30: full handshake + tools/list + resources/read (fallback) + tools/call(isError) + unknown-method(-32601) + auth gate (401/200) all verified via curl.
  - 🚨 **CRITICAL — the Railway URL is NOT this server.** `https://hyper-sills-by-welshdog-production.up.railway.app` runs the **`hyper-sills` vault MCP** (serverInfo `hyper-sills` v1.28.1, 120 skills, MiniLM dense search), a *separate, already-online, already-spec-compliant* Streamable HTTP MCP server. Railway facts (health check 2026-06-30): **Online, 1/1 replica, sfo, runtime `python mcp_server.py`** (← THIS is where the old "`python mcp_server.py --http`" line came from — it's the VAULT's entrypoint, not this repo's; the `--http` flag was never real), ~6% mem, 0×5xx. 2 build failures 2026-06-28 (commit `2baefe8a` registry 96→120 reconcile) — resolved. The `hyper-mcp-server/` (3-agent) in THIS repo has **never been deployed anywhere** — it only ran locally; its Dockerfile runs `uvicorn`.
  - 🔌 **TRAE → vault config (verified transport map 2026-06-30).** Only `/mcp` exists and it speaks **Streamable HTTP** (not legacy SSE). Probes: `POST /mcp` + `Accept: application/json, text/event-stream` → **200** ✅; `/sse` (GET & POST) → **404** (no SSE endpoint); `GET /mcp` → 400; root → 404. So the correct TRAE entry is **`transport: http`, url `…/mcp`** — NOT `sse`/`/sse`. ✅ **TRAE handshake VERIFIED 2026-06-30**: with `transport: http` + `…/mcp`, TRAE's agent completed `initialize` and ran `list_skills_by_category` returning the live 120-skill counts (agents 51 / dev 39 / hypercode 12 / broski 7 / web3 7 / youtube 4) — TRAE sends both `Accept` types correctly, **no 406**. (Gotcha for reference: the server returns **`406 Not Acceptable`** if a client sends `text/event-stream` only; that 406 would hide inside Railway's "healthy 4xx" count, so green health ≠ connected. The ~5-line vault-side Accept loosening is NOT needed since TRAE behaves.)
  - ✅ **RESOLVED 2026-06-30 — folded into the vault.** Decision (a) made: the standalone 3-agent server is NOT separately deployed. Its two *action* tools were folded into the live vault server (`HYPER-SILLs-By-WelshDog/mcp_server.py`, v1.1.1→1.2.0, commit `14c21fe`, pushed → Railway redeploy): **`broski_agent(task)`** → `POST $BROSKI_AGENT_URL/run`, **`brain_core_agent(query)`** → `POST $BRAIN_CORE_URL/query` — async, env-configurable, fail-soft (Mercy ethos). The 3rd tool `hyper_skill_agent` was intentionally dropped (duplicated the vault's `load_skill`). So TRAE now gets skills + agent-actions from ONE endpoint (free-tier-friendly). Verified locally: 8-tool registry, fail-soft + happy-path(mock) proven, `--test` green, plugin bundle rebuilt. `hyper-mcp-server/` in THIS repo is now **reference code only**.
  - ⚠️ **Remaining (small):** (b) the folded action tools advertise but report "not wired up" until `BROSKI_AGENT_URL` / `BRAIN_CORE_URL` are set in **Railway env** to reachable agent hosts. (e) confirm the Railway deploy flips `/health` to `1.2.0` + `tools/list` shows the 2 new tools (build was in flight at write time). **TRAE IDE**: free tier = 1 MCP server = the vault `…/mcp`. Do NOT register two servers.
- **HyperStudio — the agent write path (Phase 1)** — 2026-07-10, merged to `main` via **PR #315** (HEAD `ee229ef`). The one thing the studio was missing: agents that could *talk about* code but never *write* it. Now you hand an AI agent a coding task in the dashboard, it works in a **throwaway git worktree**, every tool call is gated by **Safety Shepherd**, you review a diff, and **nothing lands until you click merge**. Live + browser-verified on Bro's own repo.
  - **New service `agents/coder-studio/` (FastAPI, port `8087`)** — NOT 8097 (that's evolve-relay). `worktree.py` = git sandbox: worktrees live **outside** the repo via `STUDIO_WORKTREE_ROOT` (a checkout under `.git/` can't be pruned on Windows — stranded 2476 files once); `_git()` uses `encoding="utf-8", errors="replace"` (emoji in diffs crashed cp1252); `merge_worktree` is **`--ff-only`** and raises `BaseMovedError` if the base moved. `shepherd.py` = the `can_use_tool` hook, **fails CLOSED** (Shepherd unreachable ⇒ deny — inverts HyperFlow's fail-open); normalises the target to a worktree-relative POSIX path. `agent_runner.py` uses the **Claude Agent SDK** (`claude-agent-sdk==0.2.115`) via **`ClaudeSDKClient`** (NOT `query()` — that closes stdin so the permission callback never fires); `assert_gate_not_shadowed` refuses to run if `allowed_tools` would shadow the gate; **default model `claude-sonnet-5`**; `Bash`/`WebFetch`/`WebSearch`/`Task` withheld. `main.py` = session lifecycle + SSE (named events); session-start returns immediately and builds the worktree in a background task (a 14s checkout was timing the proxy out); discard **cancels the live agent**; merge catches `BaseMovedError` → friendly **409** ("'main' has moved on since this task started…"). Pinned `fastapi==0.139.0` / `uvicorn==0.51.0` (0.109 crashed on `on_startup`).
  - **Safety Shepherd wired for real** — `capabilities.json` gained a `coder_studio` grant (`file_read`/`file_write`/`git`, `max_actions:300`). **Also closed a platform-wide security hole** (commit `3c79df8`): root-level `.env`/`secrets` were unblocked for **every** agent because a `**/.env` glob doesn't match a bare `.env`. Added `.env`, `.env.*`, `secrets/**`, `*_key.txt`, `id_rsa*`. Verified live-blocking.
  - **Dashboard Studio UI at `/ide`** — `StudioView.tsx` (3-pane: task input + live agent stream + diff review), `useStudioSession.ts` (SSE via `addEventListener` per named event — `onmessage` never fires for named frames), proxy `app/api/studio/[...path]/route.ts` → `coder-studio:8087` (injects `X-Agent-Key`, SSE passthrough). **Model picker** (Sonnet default, Opus/Haiku/Fable selectable per task). Merge shows the service's plain-language reason on a collision instead of a false "Merged!" toast.
  - **Compose**: `coder-studio` service in `docker-compose.agents.yml` (profiles `agents`/`studio`, `127.0.0.1:8087`, rw `.:/workspace`, named vol `studio-worktrees`, `depends_on` safety-shepherd healthy). Dashboard got `HYPERCODE_API_KEY` + `STUDIO_AGENT_URL`. Image `Dockerfile.coder-studio` (`FROM agent-base`, `git config --system --add safe.directory '*'` for the bind-mount dubious-ownership, `mkdir /studio-worktrees` + chown).
  - **Tests**: 121 coder-studio + 26 shepherd unit tests green (all RED→GREEN TDD, incl. the mutation test proving an ungated run is refused). **Adversarial E2E proven**: path-escape write BLOCKED, `.env` read BLOCKED, legit edit ALLOWED, working tree stayed clean throughout, block landed in the stream.
  - **Interactive ESCALATE approval (Phase 2)** — 2026-07-11, **merged to `main` as `9f532fb` (PR #316)**. An `ESCALATE` no longer auto-denies: the `can_use_tool` gate (already `async`, running *inside* the suspended tool call) now **awaits a human decision** on a per-session `asyncio.Event` instead of denying, then returns Allow/Deny. **Studio-native — no Redis, no `ApprovalModal`, no orchestrator**: the pause happens in-process where the tool call is already suspended, and the approval flows over the session's existing SSE stream. `Approval.settle()` (`sessions.py`) is atomic + **first-wins** (lock-guarded PENDING→terminal, event set once); the wait closure (`main.py::_make_escalation_resolver`) **registers before emitting** the `approval_request` SSE (a fast click can't beat the entry into existence), awaits up to **`STUDIO_APPROVAL_TIMEOUT`** (default **300s**, read fresh per-call so it's env-tunable), emits `approval_resolved`, and **always cleans up in `finally`**. Fail-closed: walk-away → deny. Endpoint `POST /sessions/{id}/approvals/{approval_id}` (`{"decision":"approved"|"denied"}`) → **200** accepted/idempotent · **404** unknown-or-cleaned · **409** concurrent *opposite* human decision (a click that loses to timeout/discard → 200, not 409). `discard()` settles pending approvals **before** cancelling the task so the gate unblocks cleanly. Frontend: `/ide` shows a live **Approve/Deny card** per pending approval (`ApprovalCard` in `StudioView.tsx`, derived from `pendingApprovals(stream)`); `respondApproval` **checks `res.ok`** and surfaces a failure toast (the card stays up for retry) — no false "Approved" on a failed POST. **Tests: 140 coder-studio (incl. race/cleanup/timeout/endpoint-contract) + 66 dashboard (hook + card) green.** Memory: `[[hyperstudio-worktree-sandbox]]`.
    - **Deployment record (2026-07-11):** PR #316 merged as `9f532fb`; targeted coder-studio/dashboard redeploy healthy; approval route verified live (browser → `/api/studio/*` proxy → new endpoint returns the new handler's `404 no-such-session`); 2 real Haiku runs post-deploy = no regression. Full live ESCALATE *click* deferred because all default Studio tools are intentionally granted (nothing escalates naturally) and forcing one would alter shared production safety policy — the escalate→approve/deny/timeout/discard/race path is instead proven by the automated suite via a fake-Shepherd ESCALATE (the exact integration boundary). ⚠️ PR CI checks showed `unstable` = GitHub Actions **account billing lock** (jobs never started, 2-3s fails), NOT code — CodeRabbit + GitGuardian passed, state was MERGEABLE.
  - 🚀 **NEXT UP (not built):** lighting up the **specialist agents** roster (they were never healthy — no restart policy / stale images); optional governance-ledger HTTP write of each verdict.

## Sacred Rules (NEVER break)

- `docker-ce-cli` — NEVER `docker.io` for socket agents
- `from app.X import Y` — NEVER `from backend.app.X`
- `.env` files — NEVER committed to git
- Stripe webhook — rate-limit EXEMPT, always
- Python indent — 4 spaces, NEVER 3, NEVER mixed
- Redis DB 1=cache, DB 2=rate limits. NEVER mix.
- TRAE IDE — 1 MCP server at a time (free tier). Use Railway URL, not localhost.
