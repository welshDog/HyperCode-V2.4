# Alpha Team Upgrade Initiative — Roadmap (2026-03-16)

## Goal

Add an explicit premium-model routing layer for long-horizon planning and incident response:
- **Hunter Alpha** for cross-repo planning and architecture.
- **Healer Alpha** for incident response and multimodal debugging.

The upgrade must be safe-by-default (privacy redaction, opt-in flags), tested, and easy to roll back.

## Scope

In scope:
- Create official model docs and env contract
- Add backend routing module and OpenRouter client wrapper
- Integrate routing into Core’s “Brain” entrypoint (optional routing context)
- Add unit tests for routing and privacy redaction
- Provide operational rollout + rollback procedures
- Provide recurring status report template

Out of scope (Phase 2):
- Full Healer Agent v2 multimodal pipeline (image ingestion + storage + redaction tooling)
- Full mission planner refactor of all agents to use route_context everywhere

## Roles & Responsibilities (RACI)

| Task Area | Responsible (R) | Accountable (A) | Consulted (C) | Informed (I) |
|---|---|---|---|---|
| Routing policy + triggers | Hunter Alpha | Core Maintainer | Security Engineer | Stakeholders |
| Incident routing + recovery playbooks | Healer Alpha | Healer Agent Owner | DevOps Engineer | Stakeholders |
| Backend implementation | Backend Engineer | Core Maintainer | Security Engineer | QA Engineer |
| Testing strategy + execution | QA Engineer | Core Maintainer | Backend Engineer | Stakeholders |
| Deployment + rollback | DevOps Engineer | Core Maintainer | Healer Alpha | Stakeholders |
| Docs updates | Docs Owner | Core Maintainer | Hunter Alpha | Stakeholders |

## Milestones & Deadlines

Dates assume a 10-day execution window starting **2026-03-16**.

### M0 — Design Lock (Due 2026-03-17)

- Finalize routing triggers and privacy rules
- Confirm env var naming and defaults

Success criteria:
- Routing rules documented, unambiguous, and match implementation plan

### M1 — Docs + Contracts (Due 2026-03-18)

- Add:
  - `docs/models/HUNTER_ALPHA.md`
  - `docs/models/HEALER_ALPHA.md`
- Document env contract (`OPENROUTER_API_KEY`, enable flags, max tokens, privacy mode)

Success criteria:
- Docs render correctly and contain copy/paste env blocks

### M2 — Backend Routing Module (Due 2026-03-19)

- Add `backend/app/core/model_routes.py`
  - routing decision function
  - redaction helper
  - OpenRouter chat wrapper
- Extend settings with Alpha model env fields

Success criteria:
- Unit tests cover routing logic and redaction patterns
- OpenRouter calls are opt-in and never log secrets

### M3 — Controlled Integration (Due 2026-03-20)

- Integrate routing into `Brain.think()` via optional `route_context`
- Ensure default behavior is unchanged when `route_context` is absent

Success criteria:
- Existing tests pass unchanged
- New tests validate OpenRouter route path

### M4 — System Verification (Due 2026-03-21)

Testing phases:
- Unit: routing decisions, redaction, error handling
- Integration: simulated OpenRouter responses and timeouts
- Regression: existing agent tests and API tests

Success criteria:
- `pytest` passes
- No new flake failures in core workflow (seed → swarm test)

### M5 — Rollout + Monitoring (Due 2026-03-22)

- Enable in dev/staging only via env flags
- Monitor:
  - error rate of OpenRouter calls
  - fallback frequency to local/provider
  - latency impact to task processing

Success criteria:
- No unexpected external routing when disabled
- When enabled, routing works and fallbacks are safe

## Rollback Plan

Rollback is “one switch”:
- Set `HUNTER_ALPHA_ENABLED=false`
- Set `HEALER_ALPHA_ENABLED=false`
- Remove `OPENROUTER_API_KEY` from runtime environment

Validation after rollback:
- Local Ollama route works when available
- Cloud fallback returns to existing provider behavior
- No OpenRouter requests observed in logs/metrics

## Status Reporting Cadence

- Daily during M0–M3, then every 2 days through M5.
- Each status report includes: progress vs milestones, risks/blockers, next actions, validation status.

Template: `docs/reports/status/ALPHA_TEAM_STATUS_TEMPLATE.md`

