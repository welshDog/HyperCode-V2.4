# Postmortem — Dashboard Playtest & Fix Sprint

## Outcome
65% → ~90% playable overnight. The cockpit became real, live, and drivable.

## What was broken
- Tailwind was configured but never imported, so Tailwind-only surfaces rendered as raw text.
- The agents roster lied by swallowing auth failures into a fake-empty state.
- There was no auth path, so Tasks, Plans, and approvals dead-ended.
- Task create hit a live-DB enum drift bug.
- Focus mode stacked panels incorrectly.
- /health falsely claimed the orchestrator was unreachable.
- Grafana was mislabeled as /pricing.
- Safety Shepherd had been OOM-dead for 8 hours, silently.

## What got fixed
- Tailwind imported without touching legacy CSS.
- Agents proxy repointed to the open endpoint with honest errors.
- Service JWT injected server-side through all five proxies.
- /api/ws-token handoff enabled approvals WS to connect.
- Enum drift fixed with values_callable, and task create was E2E-proven.
- Focus mode now isolates and exits cleanly.
- /control is in nav.
- Health copy is truthful.
- /grafana works, and /pricing redirects there.

## What still has risk
- Task UI is not optimistic.
- Latent enum twin remains in models.py.
- Service JWT expires 2027-07-13.
- Metrics error rate is still cosmetically misleading.
- DLQ stays superuser-gated by choice.

## What to watch on next restart
- Stage bring-up: redis/postgres → core → the rest.
- Check Shepherd first: curl localhost:8096/health.
- Recreate containers after image rebuilds.
- Expect ~44 containers when full.
- Watch for JWT expiry symptoms first if 401s return.

## Final note
The cockpit is real now.