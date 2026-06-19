# ✅ WHATS_DONE — HyperCode-V2.4

> Last synced: 2026-06-17 22:50 BST by BROski AI ⚡

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

## Sacred Rules (NEVER break)

- `docker-ce-cli` — NEVER `docker.io` for socket agents
- `from app.X import Y` — NEVER `from backend.app.X`
- `.env` files — NEVER committed to git
- Stripe webhook — rate-limit EXEMPT, always
- Python indent — 4 spaces, NEVER 3, NEVER mixed
- Redis DB 1=cache, DB 2=rate limits. NEVER mix.
