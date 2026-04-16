# Changelog

> **built with WelshDog + BROski 🚀🌙**

**Doc Tag:** v2.4.2 | **Last Updated:** 2026-04-16

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.4.2] - 2026-04-16

### Added
- 💳 **Phase 10O — Course → Stripe frontend wired** — `/pricing` → Stripe Checkout → `/payment-success` full flow live; `PaymentSuccess.tsx` auto-enrolls user in all `is_active` courses on subscription; `payments.ts` sends `success_url`/`cancel_url` from browser origin
- 🔄 **Async circuit breakers** (Phase 10N step 4) — 3 breakers: `llm-router` (fail_max=3, reset=30s), `crew-orchestrator` (fail_max=3, reset=15s), `stripe-api` (fail_max=5, reset=60s); state visible at `GET /api/v1/health → circuit_breakers[]`

### Changed
- ✅ **Phase 10L — All 29 containers have healthchecks** — `docker-socket-proxy-build` uses `wget 127.0.0.1:2375/_ping`, `hyper-sweeper-prune` checks `pgrep crond`, `hyper-shield-scanner` uses `CMD true`
- 📡 **Phase 10M — Prometheus 7/7 targets UP** — `minio` added to `obs-net`, `test-agent` scrape target commented out (profile-gated); active config: `monitoring/prometheus/prometheus.yml`
- 🔍 **Phase 10N step 1 — OTLP tracing LIVE in Tempo** — root cause was `OTLP_EXPORTER_DISABLED=true` in `.env`; flipped to `false`; traces visible in Grafana Tempo (`localhost:3001`)
- ⚡ **Phase 10N step 2 — Redis caching** — `@cache_response` decorator on hot endpoints; `/health` 10s TTL, `/api/stripe/plans` 60s TTL, `/pulse` 30s TTL; Redis DB 1 (isolated from rate-limit DB 2)
- 🚦 **Phase 10N step 3 — Per-route rate limiting** — Redis DB 2; Stripe webhook always exempt; 180 tests green (was 172, +8 new cache tests)

### Fixed
- `stripe_service.py` — used `?` separator when `success_url` already contained query params (course_id flow); fixed to `&`
- `OTLP_EXPORTER_DISABLED=true` was silently disabling traces despite Tempo being healthy

## [2.4.1] - 2026-04-15

### Added
- 💳 **Phase 10F — Stripe Checkout API** — `POST /api/stripe/checkout`, `GET /api/stripe/plans`, `POST /api/stripe/webhook` with signature verification
- 🗄️ **Phase 10G — Stripe webhook DB writes** — subscription + payment + enrollment rows written on `checkout.session.completed`
- 🔑 **Phase 10D — Agent-level auth + rate limiting** — `X-API-Key` header enforcement, per-key rate limiting, `hc_`-prefixed 43-char keys
- 💰 **Phase 10H — Pricing page** — `/pricing` in Mission Control dashboard with Starter / Builder / Hyper token packs + Pro / Hyper course tiers
- 🔌 **Phase 10J — CognitiveUplink WebSocket** — `WS /ws/uplink` bridges dashboard chat UI → Crew Orchestrator `/execute`; handles ping/pong, execute dispatch, timeout, HTTP errors, invalid JSON
- 🧪 **Phase 10J — WS test suite** — 7 pytest tests for the uplink handler (`backend/tests/test_uplink_ws.py`)
- 🌐 **Phase 10B — Docker network isolation** — 5 isolated networks: `frontend-net`, `backend-net`, `agents-net`, `data-net` (internal), `obs-net` (internal)
- 🐳 **Phase 10C — Docker Secrets** — secrets via `./secrets/*.txt` + `docker-compose.secrets.yml`
- 🛡️ **Phase 10E — CognitiveUplink WS URL fix** — dashboard was pointing at wrong port (8081→8000) and wrong message type (`command`→`execute`)
- 🏗️ **Phase 10K — Stripe Price IDs** — all 7 live Stripe price IDs wired into `.env` + `docker-compose.yml`

### Changed
- Stripe checkout mode: token packs (`starter`/`builder`/`hyper`) use `mode="payment"`, course plans use `mode="subscription"` — was previously all `subscription` (bug fix)
- `CLAUDE.md` updated to single source of truth, merged from `CLAUDE.md` + `CLAUDE_CONTEXT.md`
- Version badge updated to 2.4.1

### Fixed
- Stripe checkout for one-time token packs would fail on Stripe (wrong `mode="subscription"`). Fixed with `CHECKOUT_MODE` dict in `stripe_service.py`.
- CognitiveUplink WS connected to `crew-orchestrator:8081` instead of `hypercode-core:8000` — message type also wrong (`command` vs `execute`).
- Docker context split: `default` context had stale container references; `desktop-linux` context is the correct one on Windows.

## [Unreleased]

### Added
- 🦅 **Agent X (Meta-Architect)** — autonomous agent designer, deployer and evolver using Docker Model Runner
- 🧠 **Crew Orchestrator** — full agent lifecycle + task execution system (`localhost:8081`)
- 🩺 **Healer Agent** — self-healing monitor, auto-recovers failed services (`localhost:8008`)
- 🖥️ **BROski Terminal** — custom neurodivergent-first CLI UI (`localhost:3000`)
- 🐳 **Docker Model Runner integration** — OpenAI-compatible local LLM backend for agents
- 📡 **MCP Gateway** — fully operational tool gateway for AI agents
- 📊 **Grafana Observability stack** — full metrics/tracing dashboard (`localhost:3001`)
- 📄 **AGENT_X_GUIDE.md** — full guide for Agent X operations
- 📄 **BROSKI_TERMINAL_GUIDE.md** — CLI UI usage and commands
- 📄 **HEALER_AGENT_GUIDE.md** — self-healing agent operations
- 📄 **CREW_ORCHESTRATOR.md** — crew lifecycle and task management
- 📄 **DOCKER_MODEL_RUNNER.md** — Docker Model Runner integration guide

### Changed
- 🏗️ **ARCHITECTURE.md** — updated to reflect full V2.0 agent stack
- 📋 **STATUS_REPORT.md** — updated to current system state (2026-03-25)
- 🔌 **API.md** — expanded with agent endpoints, health checks, MCP routes
- Local-first LLM defaults (TinyLlama-first) with auto model selection and tuned generation options
- Backend documentation links standardized to repo-relative paths

### Fixed
- 🔥 **Tempo container crash on startup** — `grafana/tempo:latest` (v2.10.3+) introduced hardcoded Kafka/ingester config fields that caused immediate exit. Fixed by pinning to `grafana/tempo:2.4.2` and cleaning `tempo/tempo.yaml` of deprecated fields
- 🐳 **`docker-compose.yml`** — Pinned `grafana/tempo` image from `latest` to `2.4.2`
- SQLAlchemy Base migrated to `DeclarativeBase` with SQLAlchemy 2.0 typed models (`Mapped[]`, `mapped_column`)
- Test suite stability improved via deterministic mocks and reduced external side effects during imports

## [2.4.0] - 2026-04-09

### Added
- 🐳 **Docker Zone** in Mission Control (`/docker-zone`) with native chrome + live agent status + dispatch buttons
- 🍞 **Toast system** across dashboard views with action links (e.g., “View”) and a notification history panel + unread badge
- 🎭 **Playwright E2E** dashboard suite (5 tests) + GitHub Actions workflow

### Changed
- 🧪 Updated testing docs to reflect Playwright config + report locations
- 📊 Prometheus: reduced `node-exporter` scrape noise by increasing scrape interval/timeout

## [2.0.0] - 2026-01-15

### Initial Release
- Core microservices architecture
- Basic Coder Agent capabilities
- Next.js Frontend and FastAPI Backend

---
> **built with WelshDog + BROski 🚀🌙**
