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
