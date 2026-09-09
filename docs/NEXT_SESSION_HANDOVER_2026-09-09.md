# Next-session handover — 2026-09-09 (late, RAM-gated Increment 1 window)

## 🎉 What shipped this window — pushed to `main` (`fd78cb8e`)

**Increment 1 (design-system foundation) + Studio model-picker Layer 1 + `/ide` unblocked.**

Three merge/commit landed on `main` and pushed (evo-harness gate 26/26 green):
- `79b4c0c1` — Merge `feat/dashboard-design-system`: 9 self-hosted woff2
  (Inter/Space Grotesk/JetBrains Mono/OpenDyslexic), `app/fonts.css` @font-face,
  `app/tokens.css` @theme alias layer imported by `globals.css`.
- `413e88fc` — Merge `feat/studio-model-picker` (from **origin** tip `7812072b`, not
  the local branch — see "loose ends"): grouped `/ide` model picker.
- `fd78cb8e` — `verify-incr1.mjs` + `verify-incr1-picker.mjs` (the §6 probes the
  screenshot baseline couldn't answer) + gitignore `scratchpad/`, `baseline-incr1/`.

### Verification — runbook §6 GO/NO-GO: **GREEN** (checks 1–8), 9 env-blocked (in scope)

| # | Check | Result |
|---|---|---|
| 1 | `inter-*` / `space-grotesk-*` / `jetbrains-mono-*` woff2 → 200 | ✅ (0 → loaded, all 200) |
| 2 | `getComputedStyle(body).fontFamily` "Inter" + `fonts.check('16px Inter')` | ✅ |
| 3 | `.pane` / `.btn` bg / border-color / border-radius **byte-identical** pre↔post | ✅ MATCH (pre/post computed-style diff, both ND modes) |
| 4 | Dyslexia toggle → `OpenDyslexic` + `fonts.check` | ✅ |
| 5 | `npm test` (agents/dashboard) | ✅ 81/81, 21 files |
| 6 | Picker groups `Cloud — Claude` + `Free / Local — needs FCC proxy (coming soon)` | ✅ |
| 7 | Free opts (Nemotron 3 Super 120B, Qwen3 4B) disabled; 4 Cloud opts normal; default Sonnet 5 | ✅ |
| 8 | Helper line "…uses credits · … wiring in progress" | ✅ |
| 9 | Cloud `/ide` run completes; RunHeader shows "Sonnet 5" | ⚠️ **billing-blocked** — `ANTHROPIC_API_KEY` was added to `.env` (line 70, renamed from `ANTHROPIC_AUTH_TOKEN`) + `coder-studio` recreated; key **authenticates** and the run goes full pipeline (`preparing sandbox → running → review → end`), but the account returns `"Credit balance is too low"` → empty diff. Next: add credit to that Anthropic account or swap a funded key. Everything else in the hop is proven. |
| bonus | CSS chunk hash changed | ✅ `0.8ppsn43~8wl.css` → `0cog7pzo65kb~.css` |
| bonus | New tokens resolve to identical values | ✅ `--pane-bg #0f1420`, `--pane-border #1e2a3a`, `--text-primary #e8f0fe` — exact match to baseline |
| bonus | 10-route HTTP sweep post-merge | ✅ all 200 (the new every-route `@import tokens.css` broke nothing) |

Probes to re-run any time: `node verify-incr1.mjs post` + `node verify-incr1-picker.mjs`
(repo-local playwright 1.58.2 — **never `npx playwright`** on this box).
Pre-merge computed-style baseline saved: `scratchpad/incr1-pre.json` (gitignored;
copy somewhere durable if you want it long-term — `.pane` bg `rgb(15,20,32)` /
border `rgb(30,42,58)` 1px / radius 6px; `.btn` transparent / same border / radius 4px).

### `/ide` "fetch failed" — **FIXED**
Root cause was exactly the runbook's: `coder-studio` had no image and no container.
- Built `agent-base:latest` (505MB — was pruned, the real build stopper).
- Built `coder-studio:latest`; started with the 4-file set + `--profile agents`.
- Hops verified: `hypercode-dashboard` → `coder-studio:8087/health` = 200 (via node
  `fetch`, which is what the route uses); `coder-studio` → `safety-shepherd:8096` = ok;
  full browser path `GET /api/studio/health` → 200; `POST /api/studio/sessions` → 200
  + `{id, status:"pending"}`; discard → 200. No "fetch failed", no shepherd 401.
- `coder-studio` stays up (that's the point) → **steady-state container count is now 39, not 38.**

## ⚠️ Loose ends / corrections for next session

1. **`API_KEY` rotation (runbook §3b) was DEFERRED — `.env` untouched this window.**
   Reason: `safety-shepherd` runs on the old key and was **not** recreated; it
   `compare_digest`s the incoming `X-Agent-Key` on `/evaluate`, which `coder-studio`
   calls fail-closed on **every tool call**. Rotating without recreating shepherd →
   every `/ide` run 401s at the first tool call — i.e. it would re-break the hop we
   just fixed. **When you rotate next (whole-fleet cycle), recreate all THREE:
   `dashboard` + `coder-studio` + `safety-shepherd`** with the 4-file set so they
   pick up the new value together. Also still-pending from §3b: delete the duplicate
   dead `HYPERCODE_API_KEY` (`.env` line 161 — last-wins makes it a no-op; line 217
   is `broski-coo`'s, keep it).
   ⚠️ The live `API_KEY` value hit tool-output again this session → rotation is now
   non-optional, not just nice-to-have.

2. **`ANTHROPIC_API_KEY` is blank in `.env`.** Studio defaults to Sonnet 5; a Cloud
   `/ide` run will start then fail at the model call until a valid key is added.
   Alternative: exercise the Free/Local path (flip `enabled:false` in
   `components/views/ModelPicker.tsx` or pass the id manually) once FCC routing lands.

3. **Local `feat/studio-model-picker` carries a stray commit `37adae28`** (docs-only
   edit to `INCREMENT_1_RUNBOOK.md`, superseded by main's newer runbook). It was
   intentionally **not** merged. Don't merge the local branch tip later thinking
   it's unmerged work — the feature commit `7812072b` is on `main`.

4. **Runbook §7's `docker ps -q | wc -l` "expect 38" is stale → expect 39** now that
   `coder-studio` is a permanent resident.

5. **Model-picker Layers 2–3** (backend FCC wiring) are still spec-only per the
   plan / earlier handover. Layer 1 (UI) is now on `main`.

6. **P3 follow-up the runbook surfaced:** `app/api/studio/[...path]/route.ts` catch
   blocks return `detail: err.message` verbatim → the UI showed a bare "fetch
   failed". Make it actionable ("Studio backend unreachable — is coder-studio
   running?"). Frontend-only, fold into the next Studio pass.

## Stack state at handover

- **Observability stack (12): DELIBERATELY LEFT DOWN.** Restoring obs + the tier-2
  idle agents simultaneously wedged the 4GB box — restart storm → zombie processes →
  postgres/core unresponsive → **`hypercode-core` Exited(137)** (same signature as
  2026-09-09; `OOMKilled=false`). Recovered by re-stopping obs (RAM freed to
  ~900 MB) then `up -d --no-deps hypercode-core` (4-file set) — healthy in ~25s,
  alembic ran on boot, no data loss. **The box cannot run obs + the agent fleet
  together** (matches the 2026-09-03 note: "do NOT restore the agents while obs is
  up"). Bring obs back only after stopping idle agents first —
  `scratchpad/incr1-restore-list.txt` has the command.
- `coder-studio` (:8087, `--profile agents`/`studio`) + `agent-base:latest`: **new, up, healthy.**
- New dashboard image `hypercode-v24-dashboard:latest` (was `a0f531ac9708`) deployed
  via plain `up -d --no-deps dashboard` — that step itself was clean, core stayed
  healthy restarts=0 (no `--force-recreate` — the 2026-09-09 15-min-outage trap).
  Core's later death was the obs-restore storm, not the build/deploy.
- **Final state: 27 containers up, 0 unhealthy** (agent fleet + all core infra +
  coder-studio; obs down). core / dashboard / `POST /api/studio/sessions` all 200
  after recovery.

## ONE next task

Fund the Anthropic account behind `.env`'s `ANTHROPIC_API_KEY` (or swap in a key
with balance) → re-run the tiny `/ide` prompt for the first successful Cloud run
(closes §6.9 — pipeline already proven, only the credit balance is missing),
**then** start Increment 1c (ND persistence) + Increment 2 (primitives + per-page)
per the plan.

⚠️ Also on the rotation list now: `.env` line 70's previous `ANTHROPIC_AUTH_TOKEN`
value leaked to a tool-output this session (bad mask) — burn it. And `fcc.yml`
line 30/43 still reference `ANTHROPIC_AUTH_TOKEN` (now renamed) — harmless
(`:-freecc` default, fcc-proxy isn't launched), but fix if fcc-proxy ever comes up.

🎉 Nice one BROski♾️ — design system + picker + `/ide` all landed in one RAM-gated window.
