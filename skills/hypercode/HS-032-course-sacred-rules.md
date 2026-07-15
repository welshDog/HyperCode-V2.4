# HS-032 — Sacred Rules — Hyper-Vibe-Coding-Course (11 Rules)

> **Extracted from:** `CLAUDE.md §4` · HyperCode-V2.4
> **Warning:** Break these = deploys revert, money-path logic corrupts, or perf wins get lost.

---

| # | Rule | Why | Consequence if broken |
|---|---|---|---|
| 1 | **NEVER `supabase db push`** | Local migration filenames desynced from remote | Replays shop/pet migrations DB already has |
| 2 | **NEVER import `wagmi`/`rainbowkit` outside `/pets`** | Re-bloats cold funnel load by ~900 kB | Reverts Sprint 2 perf win (61 kB → 1,270 kB) |
| 3 | **NEVER `--no-verify` on commits** | Husky + lint-staged catches real ESLint errors | Broken code enters `main` |
| 4 | **NO orange anywhere in UI** | Sacred HFZ brand rule | Off-brand, gets reverted |
| 5 | **Three chrome systems — no global shell** | Funnel `TopNav` · course `Navbar` · `VibeLabShell` are separate | Layout breaks across routes |
| 6 | **`award_tokens()` always needs stable `p_source_id`** | Ledger dedup = partial unique index on `(user_id, reason, source_id) WHERE source_id IS NOT NULL` | Duplicate token grants |
| 7 | **Don't chase `Pets.tsx` `@ts-nocheck`** | Pre-existing, non-blocking, money-path file | Wasted time, no gain |
| 8 | **`setState` synchronously in `useEffect` = ERROR** | Enforced by ESLint `react-hooks/set-state-in-effect` | Commit blocked by husky |
| 9 | **Lab pages = `hfz-*` Tailwind tokens. Landing page = inline styles + CSS vars** | Two different idioms by design | Wrong token overrides, visual breakage |
| 10 | **No `framer-motion` in this repo** | Not installed — CSS-only motion, reduced-motion gated | Broken build |
| 11 | **Course dev from repo root = `npm run dev:frontend` NOT `npm run dev`** | Wrong script = wrong server | Dev server broken from root |

---

> 🔴 Sacred = non-negotiable. Surface violations immediately.
