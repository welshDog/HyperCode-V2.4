# LOOP_EVO_EVAL.md — Evo Harness Eval Loop (P2-1)
> The first true **Eval Engineering** loop. An eval with a trigger + a verifiable
> goal that records its own verdict. Keeps HyperCode GREEN across multi-phase changes.

---

## The Loop (LOOP_TEMPLATE shape)

**REPO:** HyperCode-V2.4

**GOAL:** Every push keeps the milestone-DAG eval at or above the regression floor —
no change silently breaks an earlier phase's preconditions.

**SUCCESS TEST:** `python scripts/evo_harness.py --check --fail-under 0.9` exits `0`
(i.e. `pass_rate >= 0.9`). Today: **25/26 green (0.962)**.

---

## Trigger — local git pre-push GATE

The billing-locked GitHub Actions `evo-harness.yml` can't fire, so the live trigger is local:

- **Hook:** `scripts/git_hooks/pre-push` → installed at `.git/hooks/pre-push`
- Runs the eval before **every push**; **blocks** the push if `pass_rate` drops below the floor,
  printing the broken milestone(s).
- **Install (after clone):** `cp scripts/git_hooks/pre-push .git/hooks/pre-push` (`chmod +x` on *nix)
- **Floor override:** `export EVO_FAIL_UNDER=0.95`  ·  **Emergency bypass:** `git push --no-verify`

When Actions billing is restored, `evo-harness.yml` (push + PR + weekly Mon 06:00 cron) becomes a
second, redundant trigger — belt and braces.

---

## Closing the circle — registry logging

`HYPERFOCUS-LOOPS/scripts/run_evo_loop.py` runs the eval **and records the verdict** in `LOOP_REGISTRY.md`:

```bash
python HYPERFOCUS-LOOPS/scripts/run_evo_loop.py            # check mode, log result
python HYPERFOCUS-LOOPS/scripts/run_evo_loop.py --live     # + health/SLO/HyperFlow probes (stack up)
python HYPERFOCUS-LOOPS/scripts/run_evo_loop.py --floor 0.95
```
- **green** → `loop_log done` row (e.g. `green 25/26 (0.962)`)
- **regression** → `loop_log blocked` row naming the red milestone + the fix action

Use the pre-push hook as the always-on gate; use this runner for on-demand / scheduled
runs that should appear in the loop history.

---

## What the eval actually checks
1. Parses `docs/ROADMAP.md` → milestone DAG (each phase depends on the previous).
2. Scores own status (`DONE`/`LIVE`/… vs `pending`/`todo`/…) **+ cascading preconditions** —
   a broken early phase BLOCKS everything downstream (the long-horizon regression signal).
3. `--live` additionally probes health endpoints + Prometheus SLOs + a HyperFlow smoke mission.
4. Writes `docs/evo_reports/YYYY-MM-DD.json`.

## Exit / Done
- **Done** = pre-push gate green + this loop logged in `LOOP_REGISTRY.md`.
- **Blocked** = `pass_rate < floor` → fix the milestone status/precondition in `docs/ROADMAP.md`,
  re-run, push. NICE ONE BROski♾️
