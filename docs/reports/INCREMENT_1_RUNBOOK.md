# Increment 1 window — paste-ready runbook

Plan: `~/.claude/plans/h-hyperfocuszone-hpercore-hypercode-v2-4-delightful-donut.md`
Branch: `feat/dashboard-design-system` (pushed, 1 commit, NOT merged)
Baseline: `docs/reports/baseline-incr0/` (PNGs + `MEASURED_BASELINE.md`)

Run from `H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4`. 4-file compose set is
`-f docker-compose.yml -f docker-compose.secrets.yml -f docker-compose.registry.yml -f docker-compose.hyperhealth.yml`.

---

## 0. PREREQ — before you start

- [ ] 8–10 page PNG baseline of **clean HEAD** captured (`/`, `/ide`, `/agents`,
      `/mission`, `/control`, `/flows`, `/mcp`, `/docker-zone`, `/health`, `/grafana`),
      fixed viewport, saved to `docs/reports/baseline-incr0/<page>.png`.
      **If HEAD has already been rebuilt past `2f3e1277`, the clean baseline is gone —
      capture is only valid before step 4.**
- [ ] Low-usage window (obs stack about to go down for ~20 min).

## 1. RAM window — tear obs down

```bash
docker stop grafana prometheus prometheus-cloud grafana-agent loki tempo pyroscope \
  promtail node-exporter cadvisor alertmanager celery-exporter
wsl -e free -m        # need: free >= 900 MB  AND  swap-used < 1024 MB
```

## 2. Merge both branches (one build covers both — failure domains don't overlap)

```bash
git fetch origin
git checkout main && git pull --ff-only
git merge --no-ff feat/dashboard-design-system
# clean merge: app/fonts.css, app/tokens.css, app/globals.css,
# public/fonts/*.woff2, 3 doc deprecation headers.
git merge --no-ff feat/studio-model-picker
# clean merge, ZERO file overlap with the above: components/views/ModelPicker.tsx
# + ModelPicker.test.tsx (new) + StudioView.tsx. Studio model-picker Layer 1.
```

> Bundling is safe: the fonts check (`document.fonts.check` / computed `fontFamily`)
> is CSS/asset-level; the picker change is TSX-only and touches no styles. If step 6's
> fonts GO/NO-GO fails, it's unambiguously the design-system branch — revert just that
> merge (`git rebase --onto` or re-merge without it) and rebuild picker-only.

## 3. Tests first (cheap, catches the @theme / @import risk before a 10-min build)

```bash
cd agents/dashboard && npm test        # vitest run — must be green
cd ../..
```

## 3b. Rotate the Studio agent key — BEFORE the build (saves a recreate cycle)

Only needed if you're doing §5b (`coder-studio`) this window. Do it now so §4's
dashboard recreate picks up the new key for free.

**What actually drives the auth (verified 2026-09-09):** both the dashboard proxy
(`agents.yml:175`) and `coder-studio` (`agents.yml:1321`) build their `X-Agent-Key`
from `${API_KEY:-dev-master-key}` — i.e. **`.env`'s `API_KEY` (line 162)**. They are
already matched by construction; there is nothing to "align". `.env`'s
`HYPERCODE_API_KEY` is NOT read by either (only `broski-coo` uses it).

Two fixes to `.env`:
1. **`HYPERCODE_API_KEY` is defined twice** (lines 161 + 217, different values).
   dotenv = last-wins → line 161 is dead, editing it is a silent no-op.
   **Delete line 161.** (217 stays — it's `broski-coo`'s key.)
2. **Rotate `API_KEY` (line 162).** Its value (`hc_b040…f7449`, the one that resolves
   into the running dashboard container) was printed to a tool-output → burned.

```bash
cp .env ".env.bak-$(date +%Y%m%d-%H%M%S)-studiokey"
# generate, do NOT echo it back:
#   python -c "import secrets; print('hc_' + secrets.token_hex(32))"
# edit .env:  delete the line-161 HYPERCODE_API_KEY  ·  set  API_KEY=<new hc_ value>
# confirm without printing:  [ -n "$API_KEY" ] && echo SET || echo UNSET
```

`API_KEY` also feeds ~10 other agents (some with `${API_KEY:?...}` guards) — down
tonight, they pick up the new value when they next start. Tonight only `dashboard`
(§4 recreate) and `coder-studio` (§5b) need it, both automatically.

§4's `up -d --no-deps dashboard` picks up the changed `.env` on recreate — no extra step.
⚠️ Still **never `docker compose config`** after this edit — it dumps resolved `.env`.

## 4. Build dashboard ONLY (crew-orchestrator image is already built — do not touch it)

```bash
docker compose -f docker-compose.yml -f docker-compose.secrets.yml \
  -f docker-compose.registry.yml -f docker-compose.hyperhealth.yml \
  build dashboard

docker compose -f docker-compose.yml -f docker-compose.secrets.yml \
  -f docker-compose.registry.yml -f docker-compose.hyperhealth.yml \
  up -d --no-deps dashboard
```

> ⚠️ Plain `up -d --no-deps dashboard`. **Do NOT add `--force-recreate`** — on
> 2026-09-09 that cascaded a recreate to `hypercode-core` (dashboard `depends_on` it)
> and wedged core for 15 min. Plain `up` recreates on a changed image anyway.
> ⚠️ **Never `docker compose config` after this** — it prints resolved `.env` secrets
> (leaked the rotated `DASHBOARD_SERVICE_JWT` once already).

Wait for health:
```bash
until [ "$(docker inspect hypercode-dashboard --format '{{.State.Health.Status}}')" = healthy ]; do sleep 5; done
docker inspect hypercode-core --format 'core: {{.State.Health.Status}} restarts={{.RestartCount}}'   # must stay healthy / 0
```

## 5. (Optional, RAM permitting) bring agent-registry up for real P4 data

```bash
wsl -e free -m     # only if free still comfortably > 900 MB
docker compose -f docker-compose.yml -f docker-compose.secrets.yml \
  -f docker-compose.registry.yml -f docker-compose.hyperhealth.yml \
  --profile agents up -d --no-deps agent-registry
```

## 5b. Studio backend — build + start `coder-studio` (fixes `/ide` "fetch failed")

**Root cause (2026-09-09):** `/ide` run-submit dies at the proxy hop. Dashboard route
`app/api/studio/[...path]/route.ts` does `fetch('http://coder-studio:8087/…')` → the
name doesn't resolve → the route catches and returns raw `detail: "fetch failed"`,
which the UI shows verbatim. **`coder-studio` has no image and no container on this
box** — it's `profiles: ["agents","studio"]`, never started by the standard 4-file
launch. Prompt size is irrelevant; the agent is never reached (no stream, no diff).
`safety-shepherd` (its only `depends_on`, `service_healthy`) is already up + healthy.

**5b.0 — build `agent-base:latest` first (the real build stopper).**
`Dockerfile.coder-studio` (and safety-shepherd, and coder) do `FROM agent-base:latest`.
That image is built by NEITHER compose NOR any running container — a dangling base
layer, so `docker image prune -a` deletes it and nothing notices until the next child
build. Rebuild from the repo root (documented in `agents/Dockerfile.base`'s header):
```bash
docker images --format '{{.Repository}}' | grep -qx agent-base \
  || docker build -t agent-base:latest -f agents/Dockerfile.base agents/
```
`python:3.12-slim` + apt upgrade + `docker-ce-cli` + one pip layer — a few minutes,
modest RAM. Worth adding that one-liner to `boot.ps1` pre-flight (same "never pull,
always build what's local" guard as the Scout script).

**5b.1 — build + start with the 4-file set ONLY. Do NOT hand-roll a
`core.yml + agents.yml` 2-file command** — `frontend-net` is created by the root
`docker-compose.yml` (`name: hypercode_frontend_net`); a 2-file set skips it and the
dashboard (which sits on `frontend-net`) can't recreate.
```bash
wsl -e free -m     # need free comfortably > 900 MB — coder-studio mem limit is 1G

docker compose -f docker-compose.yml -f docker-compose.secrets.yml \
  -f docker-compose.registry.yml -f docker-compose.hyperhealth.yml \
  --profile agents build coder-studio

docker compose -f docker-compose.yml -f docker-compose.secrets.yml \
  -f docker-compose.registry.yml -f docker-compose.hyperhealth.yml \
  --profile agents up -d --no-deps coder-studio
```

Verify the hop that was broken:
```bash
until [ "$(docker inspect coder-studio --format '{{.State.Health.Status}}')" = healthy ]; do sleep 5; done
docker exec hypercode-dashboard curl -fsS http://coder-studio:8087/health   # expect 200
```

If the earlier 2-file attempt left the dashboard down, re-run §4's `up -d --no-deps
dashboard` with the 4-file set and confirm `docker ps | grep dashboard` = healthy.

Then a real `/ide` run (the tiny `/healthz` prompt): expect plan → stream → diff.
- **401** instead → `API_KEY` (`.env` line 162) is stale in one of the two
  containers; re-run the 4-file `up -d --no-deps dashboard coder-studio`.
- run starts, then **fails on the model** → `ANTHROPIC_API_KEY` blank in `.env`
  (Studio default = Sonnet 5). Add a valid key, or accept the first verified run
  being a local model via DMR (the ModelPicker Free/Local path — `enabled:false` in
  Layer 1, so flip the flag or pass the id manually for one test).

If RAM won't allow it tonight: `/ide` stays down, everything else in this window is
independent — ship the rest, do `coder-studio` next window.

## 6. Verify — one browser pass

**GO / NO-GO (this is the whole gate — everything else is bonus):**
1. [ ] Network tab: `inter-*`, `space-grotesk-*`, `jetbrains-mono-*` woff2 → 200
2. [ ] `getComputedStyle(document.body).fontFamily` starts `Inter` (not `system-ui`)
       AND `document.fonts.check('16px Inter')` true
3. [ ] `.pane` / `.btn` computed `background` / `border-color` / `border-radius`
       byte-identical to clean HEAD (aliases are a no-op — any shift = NO-GO)
4. [ ] Dyslexia toggle → `getComputedStyle(document.body).fontFamily` becomes
       `OpenDyslexic`; `document.fonts.check('16px OpenDyslexic')` true
5. [ ] `npm test` green (already run in step 3 — re-confirm nothing regressed)

If 1–5 pass: merge is good, push (step 8). If any fail: `git reset --hard` the merge,
diagnose on the branch, don't ship.

**Model-picker Layer 1 checks (`/ide`) — gate for the picker branch:**
6. [ ] Picker shows two groups: `Cloud — Claude` and `Free / Local — needs FCC proxy
       (coming soon)`.
7. [ ] Free options (Nemotron 3 Super 120B, Qwen3 4B) are visible + greyed
       (`disabled`); the 4 Cloud options behave as before; default still Sonnet 5.
8. [ ] Helper line under the select reads "…uses credits · … wiring in progress".
9. [ ] Start a Cloud run → completes; `RunHeader` shows "Sonnet 5" (friendly label),
       not `sonnet-5` or a raw id. **Needs §5b done** (`coder-studio` running) — until
       then a run submit fails with "fetch failed", which is the §5b bug, not a
       picker regression.
   If 6–9 fail but 1–5 passed: revert only the `feat/studio-model-picker` merge,
   keep the design-system ship.

**Bonus (nice to see, NOT gate):** headings visibly Space Grotesk · CSS chunk hash
!= `0.8ppsn43~8wl.css` · re-screenshot 10 pages → `docs/reports/baseline-incr1/`
(`/ide` picker region is an **expected** diff vs `baseline-incr0/ide.png`).

**NOT in tonight's scope — do not chase:**
- ND persistence / Focus-mode density → that's Increment 1c, not on this branch;
  `data-nd-mode` still resets on reload, expected.
- P4 fleet *data* → only if step 5 brought `agent-registry` up and RAM is fine; else skip.
- Error-rate 403 classification → Increment 2c.
- P3/P4 already rendered-verified on clean HEAD (`baseline-incr0/health.png`,
  `control.png`) — no need to re-verify unless Increment 1 visibly changed them.

## 7. Restore steady state

```bash
docker start grafana prometheus prometheus-cloud grafana-agent loki tempo pyroscope \
  promtail node-exporter cadvisor alertmanager celery-exporter
# if you started agent-registry in step 5 and want RAM back:
#   docker stop agent-registry
docker ps -q | wc -l      # expect 38 (39 if agent-registry left up)
```

## 8. Land it

```bash
git push origin main
```
Then: memory update, and pick up **Increment 1c** (ND consolidation) + **Increment 2**
(primitives + per-page) per the plan.

---

## If something breaks

- **core Exited(137) again** → `docker compose <4-file> up -d --no-deps hypercode-core`,
  wait for healthy (runs alembic on boot). No data loss last time.
- **build fails on `@theme` / `@import`** → the `@theme` block is in `app/tokens.css`
  imported by `globals.css`. Move the `@theme {…}` block inline into `globals.css` if the
  postcss plugin doesn't resolve it through the import.
- **fonts still 404** → confirm `public/fonts/*.woff2` are in the build context at build
  time (they were committed on the branch; a stale context snapshot was the 2026-09-09
  gotcha — don't edit files mid-build).
- **`/ide` "fetch failed" on run submit** → `coder-studio` not running. `docker ps |
  grep coder-studio`; if absent, do §5b (build `agent-base` first; 4-file set for the
  compose calls). If it's up but the run 401s → `API_KEY` (`.env` line 162) stale in
  the dashboard or coder-studio container; re-run the 4-file `up -d --no-deps
  dashboard coder-studio`.
- **build fails `pull access denied for agent-base`** → §5b.0, the base image was
  pruned. `docker build -t agent-base:latest -f agents/Dockerfile.base agents/`.
- **`network frontend-net declared as external, but could not be found`** → you used a
  hand-rolled compose file set. Use the 4-file set (§5b.1) — the root
  `docker-compose.yml` creates it.

---

## Follow-ups this window surfaced

- **P3 candidate — Studio proxy returns raw `fetch failed`.** The catch blocks in
  `agents/dashboard/app/api/studio/[...path]/route.ts` return `detail: err.message`
  verbatim, so `/ide` shows "fetch failed" — which cost two debugging rounds to trace
  to "backend not running". Make it actionable, e.g. _"Studio backend unreachable — is
  coder-studio running? (`docker compose --profile agents up -d coder-studio`)"_. Same
  fix class as the `/mcp` honest up/down copy and the P3/P4 recovery hints.
  Frontend-only, fold into the next Studio code pass.
