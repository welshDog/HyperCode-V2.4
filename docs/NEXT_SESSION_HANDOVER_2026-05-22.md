# 🤝 NEXT SESSION HANDOVER — 2026-05-22 (eve)

> **Fresh-chat boot doc.** Read this first, then `docs/SESSION_REPORT_2026-05-22.md`
> (full session detail) + `docs/PROJECT_TEST_REPORT_2026-05-22.md` (test sweep).
> Written at the end of a long multi-repo session, handing off to a new window.

---

## ⚠️ FIRST — the `/goal` hook does NOT carry over

Last session ran under a `/goal ... finish HYPERFOCUS Z0ne` Stop hook. It is
**session-scoped — it will not exist in the fresh chat.** Do not re-create it
unless Lyndz asks: the goal as written ("finish" = 7 tasks) includes 6 tasks
that **cannot be done by an AI** (npm login, card entry, MetaMask, Discord,
GitHub account settings, prod deploy), so the hook just loops forever. If
Lyndz wants a goal, scope it to something automatable.

---

## ✅ WHERE THINGS STAND — all 5 repos synced + green

| Repo | HEAD | State |
|---|---|---|
| HyperAgent-SDK | `72cb131` | ✅ v0.4.0 code, 72/72 tests. **npm still on 0.1.7 — publish pending** |
| HyperCode-V2.4 | `2151c00` | ✅ 243 pass/6 skip · GitPython 3.1.50 live |
| Hyper-Vibe-Coding-Course | `df8512f` | ✅ e2e 99/99 (3 browsers) |
| BROskiPets-LLM-dNFT | `5485cfe` | ✅ 43 pass/65 skip |
| BROski-Obsidian-Brain | `b32af73` | ✅ 3/3 tests · **30th container LIVE** |

All clean, all pushed. **~460 tests pass ecosystem-wide, 0 regressions.**
⚠️ Lyndz runs a **parallel git workflow** — always `git fetch` + check
`origin/main` before pushing; `git pull --rebase` if it moved; never force-push.

### This session's wins (detail in `SESSION_REPORT_2026-05-22.md`)
- **SDK v0.4.0** — Web3/dNFT manifest types (`web3` block + 2 registry badges).
- **GitPython CVE** — 3.1.45 → **3.1.50**, closed end-to-end: pinned, image
  rebuilt, running `hypercode-core` container swapped + verified (`pip show`
  → 3.1.50, healthy). Trivy showed 5 advisories — 3.1.47 (old target) left an RCE.
- **Course e2e** — 18 failing → **99/99** green (stale-test audit).
- **BROski Brain** — the **30th container is LIVE** (engine 20/20, healthy,
  port 8100). The Brain's own goal is met.
- **Full test sweep** — all 5 repos. 2 drift issues found → both fixed
  (`b32af73` Brain time-drift, `5485cfe` BROskiPets `squad.json`).
- 4 stale-doc contradictions surfaced + corrected (incl. the GitPython "3.1.47").

---

## 🎯 THE 6 REMAINING TASKS — all need Lyndz's hands/credentials

### 1. npm publish — HyperAgent-SDK v0.4.0
The code is `0.4.0`; npm registry is still `0.1.7`. Dry-run already verified
clean (33 files, Web3 types in). `npm whoami` returned **401 — not logged in.**
```bash
cd H:/HYPERFOCUSZONE/HperCore/HyperAgent-SDK
npm login                       # interactive — Lyndz must do this
npm publish --dry-run           # re-confirm file list
npm publish --access public     # scoped pkg → --access public required
```

### 2. Stripe real-card E2E
Automatable Path A is **already covered + green** (`frontend/tests/stripe-checkout.spec.ts`).
Only the real-card test on Stripe's hosted page is left:
```bash
stripe listen --forward-to localhost:8000/api/stripe/webhook
# regenerate a checkout: POST localhost:8000/api/stripe/checkout {"price_id":"starter"}
# pay with 4242 4242 4242 4242, then verify the webhook fired
```

### 3. BROskiPets Web3 mint E2E — Base Sepolia (MetaMask popup = human-only).
### 4. Guardian P3c smoke test — live Discord server; verify ban ONLY on explicit APPROVE.
### 5. GitHub Actions billing lock — github.com/settings/billing.
### 6. Shop Fulfillment v2 — production deploy + E2E.

---

## 🐳 INFRA / CONTAINER STATE

- `hypercode-core` — rebuilt this session, **GitPython 3.1.50**, healthy, `/health` 200.
- `hyper-brain` — **LIVE**, healthy, ports 8100-8101. Started via:
  `docker network create hyper-brain-net` +
  `docker compose -f docker/docker-compose.hyper-brain.yml up -d` (from the Brain repo).
- Docker 29.4.3, ~32 containers running.

---

## ⚠️ GOTCHAS

- **Parallel git workflow** — fetch + rebase before every push; never force-push.
- **Brain repo tracks `__pycache__/*.pyc`** — never `git add` new `.pyc` files;
  stage specific files only.
- **BROskiPets tests need Python 3.11** — a 3.13 venv can't build `ckzg` /
  `pydantic-core` wheels. Run pytest with `-p no:pytest_ethereum` (the web3
  bundled plugin crashes collection on an `eth_typing` skew).
- **Brain `HYPERFOCUS_ZONE/Hub/Brain-Constellation-Live.md`** — a runtime
  artifact the engine auto-writes on every `/constellation/map` hit. Currently
  untracked; gitignore it if the churn is unwanted (Lyndz's call).
- **V2.4 full pytest** — run from a full checkout with repo-root `agents/` +
  `scripts/` on the path, not a `backend/`-only container (5 tests need them).

---

## 🎯 FIRST TASK NEXT SESSION
If Lyndz is at a keyboard: **`npm login` → `npm publish --access public`** in
HyperAgent-SDK — that closes task #1 in one command. Everything else on the
6-task list needs him too. The codeable backlog is genuinely clear.

---

*🐶♾️ Built by @welshDog — handed off clean. Stop apologising for your brain.*
