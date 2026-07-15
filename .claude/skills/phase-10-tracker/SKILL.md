---
name: phase-10-tracker
description: HyperCode V2.4 Phase 10 status board (10A FastAPI/starlette → 10N OTLP tracing) — what shipped, what's next, where each phase lives. Use when the user asks "what phase are we on", "phase 10X status", "what's next after 10K", "is 10F live", or wants to plan/extend a Phase 10 mission.
---

# phase-10-tracker

The authoritative phase map for HyperCode V2.4. Phases 0–6 are foundational (identity bridge, token sync, agent access, graduation, observability, terminal). Phase 7+ is the security + payments + tracing era.

## Phase Status (current)

| Phase | What | Status | Verified |
|---|---|---|---|
| 0–6 | Identity / token sync / shop / graduate / Grafana / CLI | ✅ DONE | Live |
| 7 | Dockerfile security hardening (non-root, multi-stage, GID 999) | ✅ DONE | Apr 14 |
| 8 | CI/CD Trivy pipeline (PR gate + weekly Mon 06:00 UTC) | ✅ DONE | Apr 14 |
| 9 | CVE elimination — apt + pip pinning across 20 Dockerfiles | ✅ DONE | Apr 14 |
| 10A | FastAPI/starlette CVE — `fastapi==0.135.3` + `starlette==0.47.2` | ✅ DONE | Apr 14 |
| 10B | Docker network isolation — `data-net` + `obs-net` `internal: true` | ✅ DONE | Apr 14 |
| 10C | Docker secrets — `.env` removed from prod containers | ✅ DONE | Apr 14 |
| 10D | Per-agent rate limiting + auth | ✅ DONE | Apr 14 |
| 10E | CognitiveUplink WS type fix (`type: "execute"`) | ✅ DONE | Apr 15 |
| 10F | Stripe Checkout API (3 endpoints + service layer + tests) | ✅ DONE | Apr 14 |
| 10G | DB — Stripe webhook writes (subscriptions + payments) | ✅ DONE | Apr 14 |
| 10H | Pricing page in dashboard | ✅ DONE | Apr 14 |
| 10I | Stripe CLI e2e — routes + webhook LIVE | ✅ DONE | Apr 15 |
| 10J | CognitiveUplink `/ws/uplink` served from `hypercode-core` | ✅ DONE | Apr 15 |
| 10K | Stripe Price IDs locked in `.env` | ✅ DONE | Apr 15 |
| 10N | OTLP tracing — Tempo via Grafana | ✅ DONE | Apr 15 |
| 10? | **NEXT** — see "What's Open" below | ⏳ | |

## What's Open / Next

| Candidate | What | Priority |
|---|---|---|
| CVE patching | 13–14 HIGH remaining (Debian-unfixable) — wait for upstream or accept | Wait |
| Frontend video URL | Module 1.1 record + add `video_url` to DB | Ongoing |
| Phase 11 | TBD — ask Bro for next mission |  |

## Phase Pattern Cheatsheet (where things live)

| Phase | Key files |
|---|---|
| 7 (Dockerfile) | All 20 Dockerfiles in `agents/*/Dockerfile`, `backend/Dockerfile`, etc. |
| 8 (CI) | `.github/workflows/trivy-scan.yml`, `trivy-weekly.yml`, `Makefile` scan targets |
| 9 (pip pin) | Every Dockerfile's runtime stage — Part B block |
| 10A | `backend/requirements.txt` |
| 10B | `docker-compose.yml` networks block; `scripts/network-migrate.sh` |
| 10C | `secrets/` directory + `docker-compose.yml` `secrets:` block |
| 10D | `backend/app/middleware/rate_limit.py` + per-agent middleware |
| 10F-10K | `backend/app/api/stripe.py` + `frontend/.../Pricing*.tsx` |
| 10N | `backend/app/core/telemetry.py` + `OTLP_EXPORTER_DISABLED=false` in `.env` |

## Companion Skills

- `docker-stack-ops` — running, rebuilding, debugging the 29 containers
- `cve-trivy-scan` — Phase 8/9 scanning workflow
- `stripe-webhook-handler` — Phase 10F–10K Stripe flow
- `otlp-tempo-tracing` — Phase 10N tracing setup

## Hard Rules (carry across phases)

- **Phase 9 pattern** is mandatory in every new Dockerfile (apt hardening + pip pinning) — see `cve-trivy-scan` skill
- **`data-net` + `obs-net`** stay `internal: true` forever — never expose redis/postgres/grafana to internet
- **Trivy baseline** = 13 HIGH (Debian-unfixable). New scans should match. Increases = regression.
- **Stripe webhook** is rate-limit-exempt — never put rate limiting on `/api/stripe/webhook`
- **CognitiveUplink** WS message type is `"execute"`, served from `hypercode-core` at `/ws/uplink`

## Plan a Phase Extension

Before opening Phase 11 (or extending 10):

1. Update root `CLAUDE_CONTEXT.md` roadmap table
2. Cross-check: does this affect SDK or Course? → use the SDK's `cross-repo-sync` skill
3. Open a feature branch + add a phase-N entry to AGENT_SYNC_NOTES.md if the change is observable from outside V2.4
4. Trivy scan still green at end (`make scan-all`)
