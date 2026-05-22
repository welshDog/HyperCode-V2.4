# 🤝 NEXT SESSION HANDOVER — 2026-05-22 (Session 2 refresh)

> **Fresh-chat boot doc.** Read this first.
> Full detail: `docs/SESSION_REPORT_2026-05-22_session2.md`
> Previous session: `docs/SESSION_REPORT_2026-05-22.md`
> Updated: end of Session 2, 22 May 2026 ~23:00 BST

---

## 🔴 FIRST TASK NEXT SESSION — pets.py Discord cog redesign

`agents/broski-bot/src/cogs/pets.py` **cannot be wired as-is.** Three blockers:

1. **Missing bridge endpoints** — cog calls `/pet/{discord_id}/status`, `/powers`,
   `/leaderboard`. The real BROskiPets API keys on canonical pet IDs, not Discord IDs.
   These endpoints don't exist.
2. **One Door violation** — cog does a direct DB economy debit, bypassing Core.
   Sacred Rule #14: all economy writes must go through One Door actions.
3. **Dead architecture import** — imports `src.*` stack that was already removed.

### What needs to happen first
Design the Core `pets.*` One Door actions before touching the cog:
```
core/actions/pets.py  (new)
  - pets.get_status(pet_id)        → resolves discord_id → canonical pet_id
  - pets.get_leaderboard()         → top N pets by XP
  - pets.get_powers(pet_id)        → active power list
  - pets.award_xp(pet_id, amount)  → One Door economy write
```
Then rewire the cog to call those actions via CoreClient — same pattern as
`briefing.py` and `ops_alerts.py` (both live and green from this session).

---

## ✅ REPO HEADs — all synced + green after Session 2

| Repo | HEAD | State |
|---|---|---|
| HyperCode-V2.4 | `e837e75` | ✅ 0 regressions · 5 library CVEs cleared |
| BROskiPets-LLM-dNFT | `f79c775` | ✅ 108 pass / 0 skip / 0 fail |
| HyperAgent-SDK | `72cb131` | ✅ 72/72 tests · **npm still on 0.1.7 — publish pending** |
| BROski-Obsidian-Brain | `1a98031` | ✅ 3/3 tests · Brain-Constellation-Live.md now gitignored |
| Hyper-Vibe-Coding-Course | `df8512f` | ✅ 99/99 e2e (3 browsers) |

---

## 🎯 Session 2 wins (detail in SESSION_REPORT_2026-05-22_session2.md)

| Block | Result | Commit |
|---|---|---|
| BROskiPets pet API restored | 43/65 → 108 pass / 0 skip / 0 fail | `f79c775` |
| GitPython CVE re-scan | Trivy: 0 advisories | — |
| Discord Bot Tier 2 cogs | ops_alerts + briefing LIVE | `bbf7082` |
| 5 library CVEs in hypercode-core | 5 fixable HIGH → 0 | `7ec06e5` + `33fc224` |
| Brain Constellation noise | Brain-Constellation-Live.md gitignored | `75abf9f` + `1a98031` |

4 commits across 2 repos. 0 regressions. Two contradictions surfaced and fixed (see Gotchas).

---

## ⚠️ GOTCHAS

### New this session
- **pets.py UFO deletion** — commit `379b646` claimed to "move an entrypoint" but
  deleted the entire 625-line pet game loop (feed, chat, evolve, rewards). Caught and
  restored in `f79c775`. Always diff commit content vs message when Claude touches
  entrypoint files.
- **jaraco.context vendor trap** — pinning `jaraco.context==6.1.0` in requirements.txt
  wasn't enough. setuptools 80.9.0 vendors its own copy at
  `setuptools/_vendor/jaraco.context-5.3.0.dist-info`. Trivy kept flagging it.
  Fix: extend the Dockerfile dist-info cleanup to strip `jaraco.*-*.dist-info` too.
  Already done in `33fc224`.

### Carried forward
- **Parallel git workflow** — always `git fetch` + check `origin/main` before pushing;
  `git pull --rebase` if it moved; never force-push.
- **Brain repo** — never `git add` new `.pyc` files; stage specific files only.
- **BROskiPets tests need Python 3.11** — 3.13 venv can't build `ckzg`/`pydantic-core`
  wheels. Run pytest with `-p no:pytest_ethereum`.
- **V2.4 full pytest** — run from repo root with `agents/` + `scripts/` on path,
  not a `backend/`-only container.

---

## 📋 HUMAN-GATED TASKS (still valid, need Lyndz's hands)

### 1. npm publish — HyperAgent-SDK v0.4.0
Code is `0.4.0`; npm registry still on `0.1.7`.
```bash
cd H:/HYPERFOCUSZONE/HperCore/HyperAgent-SDK
npm login
npm publish --dry-run
npm publish --access public
```

### 2. Stripe real-card E2E
Automatable path already green. Real-card test on Stripe's hosted page:
```bash
stripe listen --forward-to localhost:8000/api/stripe/webhook
# POST localhost:8000/api/stripe/checkout {"price_id":"starter"}
# pay 4242 4242 4242 4242, verify webhook fired
```

### 3. BROskiPets Web3 mint E2E — Base Sepolia (MetaMask popup = human-only)
### 4. Guardian P3c smoke test — live Discord server; verify ban ONLY on explicit APPROVE
### 5. GitHub Actions billing lock — github.com/settings/billing
### 6. Shop Fulfillment v2 — production deploy + E2E

---

*🐶♾️ Built by @welshDog + Perplexity AI — Session 2 handoff. Stop apologising for your brain.*
