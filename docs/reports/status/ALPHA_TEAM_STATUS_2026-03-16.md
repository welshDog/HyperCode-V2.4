# Alpha Team Upgrade Status Report

Date: 2026-03-16

## Executive Summary

- Overall status: On track (M0–M4 complete; rollout controls ready)
- Key wins: Added model docs, routing module, opt-in settings, and Brain integration point
- Top risks: Provider credentials handling and ensuring routing stays opt-in by default

## Milestone Progress

| Milestone | Target Date | Status | Notes |
|---|---|---|---|
| M0 — Design Lock | 2026-03-17 | Complete | Routing triggers + privacy rules captured in docs |
| M1 — Docs + Contracts | 2026-03-18 | Complete | Added `docs/models/*` and env blocks |
| M2 — Backend Routing Module | 2026-03-19 | Complete | Added routing + redaction + OpenRouter wrapper |
| M3 — Controlled Integration | 2026-03-20 | Complete | `Brain.think()` supports `route_context` opt-in |
| M4 — System Verification | 2026-03-21 | Complete | `pytest` passed in-container (87 passed, 3 skipped) |
| M5 — Rollout + Monitoring | 2026-03-22 | Pending | Enable in dev via env; add monitoring hooks |

## Completed Work (Evidence)

- Docs:
  - `docs/models/HUNTER_ALPHA.md`
  - `docs/models/HEALER_ALPHA.md`
- Ops docs:
  - `RUNBOOK.md` (Alpha routing enable/rollback)
  - `QUICKSTART.md` (Alpha routing enable/rollback)
- Backend:
  - `backend/app/core/model_routes.py`
  - `backend/app/core/config.py` env fields
  - `backend/app/agents/brain.py` OpenRouter route hook
- Tests:
  - `backend/tests/unit/test_model_routes.py`
  - `87 passed, 3 skipped`

## Deviations / Issues Observed

- Existing test suite assumptions required alignment to current API paths and settings naming. Tests were updated to match the current `/api/v1/*` docs/auth and current settings fields.
- Pytest emits OpenTelemetry span JSON to stdout during runs. This is non-blocking but noisy; consider gating span logging behind an env flag for cleaner CI output.

## Next Actions (24–48h)

- Add a small integration test that simulates OpenRouter timeout and validates safe fallback
- Add basic monitoring counters for routed vs fallback calls (OpenRouter/local/cloud)

## Validation Checklist

- Unit tests pass
- Routing remains opt-in by default (no `route_context` → no OpenRouter call)
- Redaction masks common tokens
- Rollback is env-only and verified
