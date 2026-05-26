# NEXT_SESSION_HANDOVER — 2026-05-26

## Boot Order
- Read latest handover first, then `CLAUDE.md`, then `WHATS_DONE.md`.
- If docs contradict: the newest handover wins.

## Status
- HyperCode V2.4 is a Docker-based cognitive architecture (FastAPI core + dashboard + agent swarm + observability).
- Multiple launch profiles exist; use the smallest profile needed to validate.

## What’s Done (per repo truth docs)
- Dashboard/MCP stability improvements are captured in `WHATS_DONE.md`.

## First Task Next Session (highest priority)
- Implement “One Door” pet actions in Core: `core/actions/pets.py`
  - `get_status`, `get_leaderboard`, `get_powers`, `award_xp`
- Then rewire the Discord `pets.py` cog to call CoreClient (do not start by editing the cog first).

## Gotchas / Risks
- Prior mismatch incidents were called out in older handovers (entrypoint/file changes not matching commit intent).
- Human-gated items remain: SDK publish, Stripe real-card E2E, Base Sepolia mint E2E, billing locks.
