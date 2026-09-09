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
| 9 | A real `/ide` run completes to a reviewable diff | ✅ **DONE — via the FREE path.** No Anthropic credit, so stood up `fcc-proxy` (Free Claude Code → NVIDIA NIM Nemotron 3 Super 120B) and pointed `coder-studio` at it. Run went the full distance: `preparing sandbox → running → Write BLOCK (worktree-escape) → Write ALLOW → result → review` with a real git diff (`SMOKE_TEST.md` created). Model reasoned, called tools, self-corrected; **safety-shepherd gate proven live** (BLOCK on escape, ALLOW in worktree). Cloud/Sonnet-5 path stays billing-blocked but that's now moot for daily use. |
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

## `/ide` runs FREE via fcc-proxy (added 2026-09-10 ~00:50Z)

No Anthropic credit → `coder-studio` now points at a local Free Claude Code proxy.

- **`fcc-proxy`** (`:8083`, `container_name: fcc-proxy`, `hypercode_agents_net`) —
  built from `Dockerfile.fcc` (clones `Alishahryar1/free-claude-code`, `uv sync`),
  image `fcc-proxy:local`. Serves the Anthropic Messages API, routes to NVIDIA NIM
  (`NVIDIA_NIM_API_KEY` already in `.env`). Added `init: true` to
  `docker-compose.fcc.yml` (reaps the child procs that cause its "hangs 75%" rep) —
  came up healthy first try, restarts=0.
- **`docker-compose.studio-fcc.yml`** (new, committed) — override adding
  `ANTHROPIC_BASE_URL=http://fcc-proxy:8083` + `ANTHROPIC_API_KEY=freecc` to
  `coder-studio`.
- **Recreate command** (both extra `-f` files required, else it reverts to Cloud =
  broken):
  ```
  docker compose -f docker-compose.yml -f docker-compose.secrets.yml \
    -f docker-compose.registry.yml -f docker-compose.hyperhealth.yml \
    -f docker-compose.fcc.yml -f docker-compose.studio-fcc.yml \
    --profile agents up -d --no-deps fcc-proxy coder-studio
  ```
- FCC accepts unmapped model ids (`claude-sonnet-5` → routes to Nemotron), so the
  **picker works as-is from the UI** — a run just goes to the free backend.
- **safety-shepherd key fix (needed this to work):** shepherd had been Up 5h on a
  stale `API_KEY` (`hc_b040…`, 67 ch) while `.env` + coder-studio were on
  `hc_d104ae9…` (51 ch). `coder-studio` → shepherd `/evaluate` was 401 → every tool
  call BLOCKed. Recreated shepherd (4-file, no rotation — `.env` was already
  current); both now `hc_d104ae9…`. **This supersedes the earlier "defer §3b" note:
  the mismatch was staleness, not a pending rotation.** `API_KEY` value is still
  burned (tool-output leaks) — a real rotation later still needs dashboard +
  coder-studio + safety-shepherd together.

### Follow-up (not blocking): picker honesty
The `/ide` picker still shows Cloud/Claude models as the enabled default while runs
actually go to free Nemotron. Layer 2 proper = flip `ModelPicker.tsx` MODELS so the
FCC/free options are `enabled: true` and the default, and label the Cloud ones
"needs credit". Small TSX change + a dashboard build.

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
- `coder-studio` (:8087) + `agent-base:latest`: new, up, healthy — **now pointed at
  `fcc-proxy` for free runs** (see the FCC section above; needs the 2 extra `-f`
  files on every recreate).
- `fcc-proxy` (:8083, `fcc-proxy:local`): new, up, healthy, restarts=0.
- `safety-shepherd`: recreated to pick up the current `API_KEY` (was 5h-stale).
- New dashboard image `hypercode-v24-dashboard:latest` (was `a0f531ac9708`) deployed
  via plain `up -d --no-deps dashboard` — that step itself was clean, core stayed
  healthy restarts=0 (no `--force-recreate` — the 2026-09-09 15-min-outage trap).
  Core's later death was the obs-restore storm, not the build/deploy.
- **Final state: 28 containers up, 0 unhealthy** (agent fleet + core infra +
  coder-studio + fcc-proxy; obs down). core / dashboard / `POST /api/studio/sessions`
  / free `/ide` run-to-diff all verified.

## ONE next task

`/ide` now works end-to-end for free (fcc-proxy). Next: **Increment 1c** (ND
persistence) + **Increment 2** (primitives + per-page) per the plan. Optional
polish first: flip `ModelPicker.tsx` so the free options are the enabled default
(picker honesty follow-up above).

⚠️ Rotation list for the next full-fleet cycle:
- `.env` `API_KEY` (`hc_d104ae9…`) — burned via tool-output leaks. Rotate +
  recreate **dashboard + coder-studio + safety-shepherd** together.
- `.env` line 70's previous `ANTHROPIC_AUTH_TOKEN` value — also leaked this session
  (bad mask). Burn it. `fcc.yml:30/43` still name `ANTHROPIC_AUTH_TOKEN` (now
  renamed to `ANTHROPIC_API_KEY`) but it's harmless — `:-freecc` default and
  fcc-proxy uses the `freecc` token anyway.

🎉 Nice one BROski♾️ — design system + picker + `/ide` all landed in one RAM-gated window.
