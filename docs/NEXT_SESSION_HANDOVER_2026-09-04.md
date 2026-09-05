# NEXT_SESSION_HANDOVER — HyperCode-V2.4 — 2026-09-04

> This session's clock crossed midnight during the live smoke test (ran
> 2026-09-04 23:38 → 2026-09-05 00:09 local) — kept the 2026-09-04 filename
> since that's the SDD plan's own date and what the task-20 brief mandated.
>
> Session mission: Governor + capability tokens (Phase 2 of the
> autonomous-control-plane north star). Full SDD cycle, 20 tasks, all
> implemented + independently reviewed. Ledger:
> `.superpowers/sdd/2026-09-04-governor-capability-tokens-phase2/progress.md`.
> Spec: `docs/superpowers/specs/2026-09-04-autonomous-control-plane-north-star-design.md`.
> Full narrative: `WHATS_DONE.md`'s 2026-09-04 entry.

## State: Phase 2 shipped and live smoke-tested

- **`governor` service, `:8089`, `--profile fleet`** — PASETO v4.public
  (Ed25519) capability mint/verify, Redis (DB 3) replay guard, kill-switch
  (Redis flag + off-box sentinel file, sentinel wins), renewing system
  lease, two-person approval rule for dangerous action classes.
- **`fleet-controller` now verifies a governor capability** on
  `/v1/plans/preview` (`capability_check.presented`/`.valid`/`.reason`).
  `execution.performed` stays hard-`false` throughout — this phase only
  gates *whether a capability can be minted*, never executes anything.
- **CI containment check** added — asserts the rendered fleet manifest never
  grants either service a Docker socket, `DOCKER_HOST`, or a
  crew-orchestrator credential.
- **Closed a real Phase 0 gap**: `fleet-controller` had zero compose wiring
  until this session's Task 18 — `docker-compose.fleet.yml` is new. Every
  earlier "Live" claim about it in `CLAUDE.md`/`docs/STATUS.md` was true only
  of the built image + its test suite, never a real `docker compose up`.
- **Live smoke test (Task 20) passed** against real containers: real
  Shepherd `ESCALATE` → two-person approval → mint → fleet-controller
  capability-verify (valid, `execution.performed` false) → kill-switch
  (Redis + sentinel-beats-Redis, both proven) → Shepherd-down fail-closed →
  replay rejection (`code: "replayed"` on 2nd verify) → lease actually
  expiring for real once unrenewed under kill. 125/125 tests green across
  all 4 suites (governor/fleet-controller/safety-shepherd/CI check), no
  regressions.
- Two non-blocking findings from the live run (full detail in
  `WHATS_DONE.md`): (1) `docker-compose.fleet.yml` sets no `API_KEY` for
  either service, so Shepherd calls 401 and get misread as "Shepherd
  unavailable" rather than an auth gap; (2) the task-20 brief's own
  Step 2→3 example plan_hash predates Task 17's real hash-binding fix and
  can never validate as written — not a code defect.

## Launch command (for anyone picking this up)

```bash
docker compose -f docker-compose.yml -f docker-compose.fleet.yml \
  --profile agents --profile fleet up -d governor fleet-controller
```

`--profile agents` is required only so `safety-shepherd`'s `depends_on`
resolves — it does not add the rest of the agents fleet to this specific
`up` (naming the services keeps it scoped). Without
`docker-compose.secrets.yml` layered in, `GOVERNOR_PRIVATE_KEY_FILE` won't
resolve to a real file — `keys.py` falls back to `GOVERNOR_PRIVATE_KEY_PEM`
env var, and `OPERATOR_KEY_FILE`/`OPERATOR_KEY` needs the same treatment for
`/v1/kill`/`/v1/unkill` to work. `agent_api_key_governor.txt` remains
unprovisioned (Task 18 finding) — CI/ledger writes no-op safely without it.

## Next: Phase 1 or Phase 3 (per the north-star spec's roadmap)

The spec's phase table (`docs/superpowers/specs/2026-09-04-autonomous-control-plane-north-star-design.md`,
"The phase roadmap, mapped onto this architecture") lists Phase 2 (this
session) as the first build, ahead of Phase 1 in delivery order. Two real
options for next:

- **Phase 1 — typed dispatch queue.** `crew.plan.submit` action kind; a
  durable proposal queue (queue-mediated realization); investigate
  `workflow_engine.py`'s `/workflow/execute` as the eventual dispatch
  target. Still zero mutation authority — this is plumbing, not a new
  execution capability.
- **Phase 3 — human-approval dashboard UI.** Surface the two-person rule and
  mint/verify flow in `hypercode-core` Mission Control (where
  `mission-director`'s `propose`/`review` already live) instead of raw
  curl calls to `governor`. Approval gating becomes usable by an actual
  human; still no execution.

Neither is scoped yet — pick one and write a spec before touching code, per
the project's SDD convention.

## Deferred findings worth a look before Phase 4/5 (execution) ships

Pulled from this plan's own SDD ledger
(`.superpowers/sdd/2026-09-04-governor-capability-tokens-phase2/progress.md`)
— both are pre-existing/residual, neither blocked Phase 2, but both sit
directly in the corrigibility-critical path any execution phase will lean on:

1. **Sentinel-file ENOENT-swallow residual gap (Task 8).** The kill-switch
   sentinel check wraps `Path.exists()` in try/except, which catches the
   `EACCES` case, but Python's `pathlib.Path.exists()` internally swallows
   `OSError` for the `ENOENT`/`ENOTDIR`/`ELOOP` family and returns `False`
   **without ever raising** — so a mount fault manifesting that way is
   structurally unfixable by exception-wrapping alone; it would silently
   read as "no kill sentinel" instead of failing closed. A robust fix needs
   `os.stat()` called directly to distinguish a legitimately-absent file
   from a mount-fault-shaped `ENOENT`, and even then the two aren't cleanly
   separable at the stat level. Defense in depth exists today (the
   independent Redis-flag kill path is unaffected), so this only bites the
   narrow compound case of "Redis healthy AND sentinel mount silently fails
   AND a human is relying on the sentinel specifically" — worth a dedicated
   hardening task before Phase 5 (live infra mutation) ships.
2. **`fleet_registry.py` roster-resolution issue (found in Task 19's
   review).** `fleet_registry.py`'s `FILES` list never included
   `docker-compose.fleet.yml`, and the roster-resolution code raises on only
   the **first** alphabetical miss — masking roughly 13 total unresolvable
   agent names (including `fleet-controller`, and now `governor` too,
   consistently) rather than surfacing all of them. Pre-existing
   (`fleet-controller` was already broken identically before this session);
   not a regression from Phase 2, but compounds every time a new fleet-file
   service is added without a matching `FILES` entry. Worth a follow-up
   ticket, not urgent.

## One-sentence next task

Write a spec for Phase 1 (typed dispatch queue) or Phase 3 (approval
dashboard UI) — both are unscoped, pick one and don't start coding first.

🎉 Nice one BROski♾️ — Phase 2 shipped, live-proven end to end, zero
containers left running that weren't already up before this session.
