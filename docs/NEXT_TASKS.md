# 🎯 Active Next Tasks
> Update this every session. Completed items → `WHATS_DONE.md`.
> For sacred rules + architecture → `CLAUDE.md`

---

| # | Task | Priority |
|---|---|---|
| 1 | **BROskiPets Web3 E2E** — test mint on Base Sepolia testnet (MetaMask = human gate) | 🟡 This week |
| 2 | **Fix GitHub Actions billing lock** — github.com/settings/billing (human gate) | 🟡 |
| 3 | **Discord Bot Tier 2** — Pets, XP Leaderboard, Morning Briefing, Health Alerts | 🟢 Background |
| 4 | **HyperLabs human gates** — Vercel Speed Insights CWV · `/pets` wallet smoke · post-login reconcile | 🟢 Human gate |
| 5 | **`/welcome` auth-gate decision** — make public? Sponsors hit login wall from BUSINESS_PLAN | 🟡 |
| 6 | ~~**Wire BROski$ XP to postgres**~~ ✅ **DONE 2026-06-18** — `broski_economy_consumer.py` now dual-sinks: redis (fast) + best-effort POST to `hypercode-core` `POST /api/v1/economy/award-dev-xp`, which routes through `broski_service.award_xp` into durable `broski_wallets`/`broski_transactions`. Owner = discord `418075243404591106` (auto-provisioned user). Proven E2E (redis publish → pg row). Redis AOF (commit a87c81a) kept as the fast-path stopgap; postgres is now the system of record. | ✅ Done |

> ✅ Done this session: Course module pages, Shop Fulfillment v2 E2E, SDK npm publish `@w3lshdog/hyper-agent@0.4.0`, Guardian P3c smoke test (8/8)

---

## 🔴 P0 — Control Plane (AGENT-START.md roadmap)

| # | Task | Status |
|---|---|---|
| P0-1 | **HyperFlow** — declarative agent mission graphs (schema + runner + `hyperflow_runs` mig 016 + `/api/v1/flows` SSE + Prometheus metric + example flow) | ✅ Done 2026-06-19 |
| P0-2 | **Safety Shepherd Agent** — runtime policy brain (ALLOW/BLOCK/ESCALATE) on port 8096 | ✅ Done 2026-06-19 |
| P0-3 | **Mission Graph Dashboard Panel** — visualise active HyperFlow runs (`GET /flows/active` + SSE) | ✅ Done 2026-06-19 |

## 🟡 P1 — Identity + Governance

| # | Task | Status |
|---|---|---|
| P1-1 | **BROski Identity Agent per user** — `broski_identity_agents` (mig 017) + `IdentityAgent` (award_tokens/check_permission/log_action) + `/api/v1/identity` + `X-BROSKI-IDENTITY` | ✅ Done 2026-06-19 |
| P1-2 | **Governance Ledger** — `governance_ledger` (mig **018**, not 016 — head was 017); `IdentityAgent.log_action()` persists there (fail-soft); `GET /api/v1/governance/ledger`; Grafana Postgres datasource + timeline panel | ✅ Done 2026-06-19 |
| P1-4 | Fill empty specialist HYPER-AGENT-BIBLEs | ✅ Done 2026-06-19 (10 filled; crew-orchestrator already existed) |

## 🟢 P2 — Continuous Evolution + Course

| # | Task | Status |
|---|---|---|
| P2-3 | **Brain Levels 18 + 19** — L18 AI distraction monitor (3 signals → nudge) + L19 DifficultyDial dynamic XP (intensity × quality × HyperSplit chunk difficulty) | ✅ Done 2026-06-20 (in BROski-Obsidian-Brain, engine :8100, commit 10cee0e) |
| P2-1 | Evo Harness — long-horizon agent regression test | ⬜ |
| P2-2 | Brain Constellation (Level 20) | ⬜ |
| P2-4 | Course "AI Agents 2.0" track (M11+) | ⬜ |
| P1-3 | Extract CATALOGUED skills to HYPER-SILLs vault | ✅ Done 2026-06-19 (index was stale: 22/37 already on disk; 15 genuinely-missing written + web3/ created + vault-index reconciled — in HYPER-SILLs-By-WelshDog) |

> ✅ `safety_decisions_total` Grafana panel done (commit 142e989). P1-1 follow-up: retrofit existing economy/shop/agent-dispatch call-sites to route through `IdentityAgent.log_action()` (the agent + table are built; central money path not yet retrofitted to avoid risk).

> Safety Shepherd follow-ups (deferred): Grafana panel for `safety_decisions_total` / `/safety/events`; persist decisions/governance ledger (P1-2). ✅ HyperFlow dispatch now consults `/evaluate` (`SAFETY_SHEPHERD_MODE` off|monitor|enforce, default monitor). Remaining intercept: wire the crew-orchestrator's own downstream tool calls (docker/http/file) through `/evaluate` too.

> HyperFlow MVP follow-ups (deferred): crash-resume durability (Celery path), multi-worker `/resume` (currently in-core single-worker), concurrency caps.
