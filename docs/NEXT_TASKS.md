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
| 6 | **Wire BROski$ XP to postgres** — `broski_economy_consumer.py` writes only to volatile redis db1 (wiped on stack restart; redis is LRU cache, do NOT add AOF). Durable tables `broski_wallets`/`broski_transactions` already exist in local pg but are empty/unwired. Point the consumer at them when economy goes live. (investigated 2026-06-18) | 🟢 Economy go-live |

> ✅ Done this session: Course module pages, Shop Fulfillment v2 E2E, SDK npm publish `@w3lshdog/hyper-agent@0.4.0`, Guardian P3c smoke test (8/8)
