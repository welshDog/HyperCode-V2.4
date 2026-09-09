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
9. [ ] Start a Cloud run → completes as today; `RunHeader` shows "Sonnet 5"
       (friendly label), not `sonnet-5` or a raw id.
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
