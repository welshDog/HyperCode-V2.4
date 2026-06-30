# ✅ WHATS_DONE — HyperCode-V2.4

> Last synced: 2026-06-30 09:43 BST by BROski AI ⚡

## Done & Locked — Do NOT re-suggest

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
- **Hyper MCP Server v2** — FastAPI MCP server (`hyper-mcp-server/`) built on skills HS-081 PORTAL FORGE + HS-129 SKILLS-OVER-MCP. Exposes 3 agents as MCP tools (`broski_agent`, `brain_core_agent`, `hyper_skill_agent`) via `/tools/list` + `/tools/call`. SEP-2640 Resources surface (`/resources/list` + `/resources/read?uri=skill://HS-NNN`) for HYPER-SILLs discovery. Dockerfile + requirements.txt + `.env.example` included. Merged via PR #292 to main (2026-06-30). Smoke tested locally — all 3 endpoints confirmed live. **TRAE IDE integration**: single MCP server config pointing to Railway live URL `https://hyper-sills-by-welshdog-production.up.railway.app` (HTTP transport). TRAE free tier = 1 MCP server at a time. Railway service confirmed Online (1 replica, sfo, `python mcp_server.py --http`, healthcheck `/health`). Do NOT re-add localhost:8765 and Railway as two separate servers — TRAE only supports one.

## Sacred Rules (NEVER break)

- `docker-ce-cli` — NEVER `docker.io` for socket agents
- `from app.X import Y` — NEVER `from backend.app.X`
- `.env` files — NEVER committed to git
- Stripe webhook — rate-limit EXEMPT, always
- Python indent — 4 spaces, NEVER 3, NEVER mixed
- Redis DB 1=cache, DB 2=rate limits. NEVER mix.
- TRAE IDE — 1 MCP server at a time (free tier). Use Railway URL, not localhost.
