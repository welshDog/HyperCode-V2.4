# Next Session Handover — 2026-08-15

# Fresh Railway deployment for the cross-repo `generate-v2-config` P0 — Alembic bug found + fixed, now blocked on Redis connectivity

## Why this session touched HyperCode-V2.4 at all

Cross-repo P0 from `Hyper-Vibe-Coding-Course`'s Wave 1 truth-audit: the
`generate-v2-config` Supabase edge function needs a live `V24_API_URL`
pointing at this backend's `/api/v1/access/provision` endpoint. The
original documented Railway project (`3d66bd92-cac3-4fde-ae9a-07f269b58791`)
was never reachable this session — every access attempt (direct MCP calls,
the `railway-agent` tool) returned "you don't have the required role" —
this is a Railway account/workspace permissions issue, not fixable from
either Claude Code session, and is still unresolved on that original
project.

Lyndz brought in a separate collaborator (with their own Railway access)
to stand up a **fresh** deployment instead of chasing access to the old
one.

## Live state

- New Railway project: **`cozy-luck`** (id `0999ba63-e4bf-4898-b1a8-9ab1daabcffb`),
  workspace "WelshDog's Projects", environment `production`
  (id `9f81a30c-fc14-4aca-8555-49a1f953d8bc`).
- Services in that project:
  - `Postgres` (id `2ef4f456-0b93-4037-b212-bc8818c37e03`) — deployed, **SUCCESS**.
  - `Redis` (id `c0f60334-36b2-4ac7-9d89-2d593019c2b1`) — deployed, **SUCCESS**.
  - `HyperCode V2.4` (with a space, id `e1ad1459-42ce-471f-aa8f-f1fcaf9d8f55`) —
    **the real one**, points at `welshDog/HyperCode-V2.4` main branch,
    `backend` root dir. Currently **FAILED** (see "Still open" below —
    Redis connectivity, not the alembic bug, which is now fixed).
  - `HyperCode-V2.4` (hyphenated, id `70cfe43b-84f0-4acd-9668-fb1c8ece0fe7`) —
    a **stray duplicate**, has failed instantly on every attempt since
    creation (23:42:16 UTC 08-14) — almost certainly misconfigured
    (wrong root dir or no valid start command). Not investigated — the
    hyphenated one is dead weight, not the deploy path. Consider deleting
    it once the spaced one is confirmed healthy, to stop it cluttering
    `get-status` output.
- No public URL confirmed live yet. `V24_API_URL` has **not** been set on
  the Supabase side (`tlavrxiaegbtyfmjfdcz`) — there's nothing working to
  point it at yet.

## What shipped this session (in this repo)

**PR #425 — fixed a real Alembic duplicate-revision bug**, merged to
`main` (`01778dd`). Two migrations both claimed revision `"010"`
(`down_revision "009"`):
- `010_add_access_provisions_event_id.py` (the real chain, merged first)
- `010_agent_policy_schema.py` (PR #424, "Policy Engine foundation",
  merged 08-14 — this is what actually caused the collision, since it was
  never rebased against the already-merged `010`)

This wasn't a Railway config problem — it was a genuine code bug in this
repo that made `alembic upgrade head` fail outright on ANY fresh deploy
(new DB, empty `alembic_version` table), not just this one. Found because
the container built and started fine on the first deploy attempt, but
crash-looped through the full 3-minute healthcheck retry window because
the DB migration step errored before the app ever came up:
```
ERROR [alembic.util.messaging] Multiple head revisions are present for
given argument 'head'
```

**Fix:** `010_agent_policy_schema.py` is fully self-contained (creates
`agent_registry`/`policy_rules`/`audit_log` — three brand-new tables, no
FKs outside itself, nothing else references it) — safe to move to the
tail rather than guess at merge intent. Renamed to `019`, re-chained
after `018` (the actual tip of the other branch). Verified locally before
pushing (`alembic heads` → single `019 (head)`; `alembic history` → one
linear chain, no other duplicates anywhere) **and** confirmed live in the
Railway deploy logs of the next attempt: the full chain from `<base>`
through `018 -> 019, agent_policy_schema` ran with zero errors.

**Note on the PR itself:** the first commit on that branch accidentally
staged the pre-edit file content (a `git add` with two paths failed
atomically on the already-renamed old path, so the real edits never got
staged) — caught immediately via `git show HEAD:<path>` before anyone
pulled it, fixed with an immediate follow-up commit on the same branch
before merge. Worth knowing if `git log` on that branch looks odd.

## Still open

1. **Redis connectivity — the new blocker.** Latest deploy
   (`cc3effa2-59f7-4a48-80f5-0ca932350db9`) got past Alembic clean, the
   app started, but the first request (the healthcheck hitting `/health`,
   which apparently runs through a rate-limiter) failed:
   ```
   redis.exceptions.TimeoutError: Timeout connecting to server
   ```
   Also present in the same logs: repeated OpenTelemetry trace-export
   warnings to `tempo:4317` (`StatusCode.UNAVAILABLE`) — likely a
   separate, non-fatal, optional-observability issue (no Tempo service in
   this project), probably not the root cause but noise worth filtering
   out when reading these logs again.
   **Not yet diagnosed**: is this a transient race (Redis's private
   network DNS not warmed up yet on a brand-new service) worth just
   retrying, or a real misconfiguration (`HYPERCODE_REDIS_URL` reference
   syntax, missing auth, wrong port)? Next step: redeploy once, see if it
   self-resolves; if not, check `HYPERCODE_REDIS_URL`'s actual resolved
   value and the Redis service's actual connection details side by side.
2. **Missing required secrets**, per the collaborator's own status
   report — still needs adding directly in Railway's dashboard (per the
   safe-handoff agreement this session: **no secret values go through
   chat**):
   - `SHOP_SYNC_SECRET` — must match Supabase's live value. This is the
     one that actually matters for the P0's own proof (see
     `backend/app/api/v1/endpoints/access.py` — validates inbound
     `X-Sync-Secret` against exactly this var, not `COURSE_SYNC_SECRET`).
   - `COURSE_SYNC_SECRET` — separate secret, used by
     `backend/app/api/v1/endpoints/economy.py`, also required for that
     endpoint's own contract (not the P0 blocker itself, but the app
     needs it too).
   - `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`.
3. Once healthy + secrets set: get the confirmed base HTTPS URL, then
   back in the course repo — `supabase secrets set
   V24_API_URL=<url> --project-ref tlavrxiaegbtyfmjfdcz`, re-run the
   negative 401 check (should flip from `503` to `401`), then the
   positive-path proof with the real `SHOP_SYNC_SECRET`
   (`success: true` or `provision_status: "already_provisioned"`).
4. The stray hyphenated `HyperCode-V2.4` duplicate service — cleanup, not
   urgent, not blocking anything.

## First task next session

Check Railway status on the `cozy-luck` project — has the collaborator
added the missing secrets and redeployed? If the Redis timeout is still
happening even with a real Redis connection configured, that needs actual
debugging (compare `HYPERCODE_REDIS_URL`'s resolved value against Redis's
real connection string — Railway's `${{Redis.REDIS_URL}}` reference
syntax should auto-populate correctly, but worth confirming rather than
assuming). If it's healthy, get the URL and finish the P0 proof in the
course repo — that's the very last step.
