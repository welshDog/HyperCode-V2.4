# HyperCode Self-Upgrade Council — Verified Re-Rank (2026-09-12)

> Companion to `docs/upgrades/HYPERCODE SELF-UPGRADE COUNCIL – SPECIALIST AGENT
> OPINIONS` — read that doc first for the 8 agents' full reasoning/evidence
> write-ups. This doc does not replace it; it corrects its prioritization against
> live-verified reality. The original council doc worked from static
> `WHATS_DONE.md`/`NEXT_TASKS.md` snapshots; this doc is built from three
> independent tool-verified investigation passes run the same session (live repo
> greps, `gh run` logs, `docker ps`, and one real fix + CI confirmation). Roughly
> half the original doc turned out stale — several claimed "gaps" were already
> closed, one core premise was flat-out false, and a few real issues surfaced
> that the council never saw at all.

## What changed since the original doc

**Fixed this session:** the docker.io Sacred Rules lint (commit `652fbef7`) —
confirmed via `gh run view` that `health-check.yml` step 1 shows `PASS` for the
first time ever.

**STALE / already shipped** (council thought these were open gaps):
- throttle-agent MemStream dependency (fixed ~2026-08-27)
- dashboard theme toggle / live agent count / healthcheck ports (fixed
  2026-09-08, P1-P5)
- port collisions — `hypercode-ollama-gpu` / `prometheus-cloud` (already resolved)
- Tempo/OTLP distributed tracing (genuinely live, Phase 10N — corroborated by
  `backend/app/core/telemetry.py`, `docs/CHANGELOG.md`, `docs/STATUS.md` — though
  it's `--profile observability`-gated and competes for the 8GB RAM ceiling; that's
  an ops/toggle question, not a build gap)
- governor PASETO capability tokens (confirmed real and live)
- crew-orchestrator SPOF (overstated — only one real hard dependency,
  `mission-executor`, not fleet-wide)

**False premise, corrected:** "the model-router/fallback infra already publishes
to ghcr.io" — actually **`docker-push.yml` has failed on every single run since
inception** (`${{ github.repository }}` interpolates to mixed-case
`welshDog/HyperCode-V2.4`; OCI tags must be lowercase). Nothing has ever reached
GHCR through it. This is a bigger, more urgent problem than anything in the
original doc's CI item.

**New issues the council never saw:**
- `ghost-agents-build.yml`'s 12-agent build matrix has been skipped on every run
  since 2026-08-31 — its `port-check` job fails first on the same stale
  `brain-agent` roster bug shared with `health-check.yml` steps 7/8.
- `check_fleet_controller_capabilities.py` (health-check.yml step 9) references
  `docker-compose.agents-full.yml` for `fleet-controller`, which moved to
  `docker-compose.fleet.yml` on 2026-09-04 — script never updated.
- `docker-compose.observability.yml` has a `!override` YAML tag PyYAML's
  `safe_load` can't parse — breaks `validate_compose_yaml.py` (step 6).
- `docker-compose.prod.yml` (labeled "PRODUCTION HARDENED") used
  `read_only_root_filesystem: true` — **not a valid Compose key** (the real key
  is `read_only: true`) — on all 8 of its services. Its OCI hardening never
  actually took effect. Worse: the file is orphaned — not consumed by any real
  launch script, referenced a phantom `app-net` network, and (until this
  session) its images pointed at docker.io. An older archived copy
  (`docs/archive/docker/docker-compose.prod.yml`) actually had the correct
  `read_only: true` key — this is a regression, not just an oversight.
- `tests/test_compose_validator.py` imports a `validate` function that doesn't
  exist in `scripts/compose_validator.py` — 0 tests currently collected for the
  repo's better-scoped (but unwired) compose validator.
- Two vendored `.venv`/`.venv311` directories appear to be tracked in git
  (repo bloat/hygiene, unrelated to CI logic).

---

## The re-ranked roadmap

### Tier 1 — Do next (small, mechanical, unblocks everything downstream)

These four share a property the original doc missed entirely: fixing them
plausibly turns `health-check.yml` **fully green** and re-enables
`ghost-agents-build.yml`'s entire build matrix, for a fraction of the effort the
council estimated for "Fix CI/CD Pipeline" (3 days). Recommended order:

1. **Fix `docker-push.yml`'s GHCR case-sensitivity bug** (lowercase the repo-name
   interpolation in the tag). Highest leverage single fix in this whole
   roadmap — currently **zero** images have ever published to GHCR through CI.
   Also makes this session's `docker-compose.prod.yml`/k8s ghcr.io rewrites go
   from aspirational to real.
2. **Fix the shared `brain-agent` roster mismatch** in `check_duplicate_ports.py`
   / `check_expected_ports.py` (health-check.yml steps 7-8) and update
   `check_fleet_controller_capabilities.py`'s stale
   `docker-compose.agents-full.yml` reference to `docker-compose.fleet.yml`
   (step 9). One root cause, three gates — and it's the same bug blocking
   `ghost-agents-build.yml`'s `port-check` job, so this also un-skips the
   12-agent build matrix that hasn't run since 2026-08-31.
3. **Fix the 9 stale `backend.app` imports** (health-check.yml step 2) — 4 files,
   mechanical rename to `app.X`.
4. **Fix `docker-compose.observability.yml`'s `!override` tag** so
   `validate_compose_yaml.py` (step 6) can parse it.

Effort: small, roughly a session each, no architectural decisions needed for any
of the four. Impact: the biggest, most concrete "CI/CD" win available — much more
achievable than the original 3-day estimate because the real blockers were
narrower and more mechanical than the council assumed.

### Tier 2 — Do after Tier 1 (real security gap, needs one decision first)

5. **Resolve `docker-compose.prod.yml`'s dead-config problem before hardening
   anything else.** This file currently *looks* like the hardened production
   config but isn't consumed anywhere, references a phantom network, and its
   `read_only_root_filesystem` key had silently done nothing on any of its 8
   services. Decide: either fix it for real (correct key, wire it into an actual
   deploy path) or explicitly label/retire it as aspirational so it stops
   implying protection that doesn't exist. Then apply the missing hardening
   (non-root user, real `read_only: true`) to the services that are *actually*
   live (`docker-compose.agents.yml`/`agents-full.yml`), which already have
   `no-new-privileges`+`cap_drop` but nothing else. Real gap, smaller than the
   council's "apply to all agent services" framing once you exclude the dead
   file.

### Tier 3 — Re-scoped, smaller than originally estimated

6. **Smart Model Router — auto-routing heuristic only.** ~70% of this already
   exists (Anthropic→OpenRouter→Ollama fallback in 15 agent files,
   `ModelPicker.tsx`, `fcc-proxy`). The only missing piece is proactive
   complexity-based model selection instead of reactive-failure fallback or
   manual picking. The original 5-day estimate should shrink substantially once
   scoped to just this.

### Tier 4 — Real, but needs one verification pass before committing effort

7. **Agent Autonomy & Safety — dispatch-seam + post-DONE guard.** Governor/PASETO
   is confirmed real and live. The *specific* claims about wiring
   `crew-orchestrator/main.py:524`'s dispatch-seam to
   `safety_client.check_dispatch()` and an automated post-DONE guard were never
   checked this session — UNCLEAR, not confirmed either way. Recommend a short
   verification pass (same approach as this session) before scoping real work
   here, since half of this roadmap's other "gaps" turned out to already be
   closed.

### Tier 5 — Real, but lower urgency than infra/safety

8. **Skill/agent discoverability + onboarding.** Re-confirmed 2026-09-12 (still
   true after everything else this session shipped): no `/ide/skill-suggest` or
   matcher exists in the dashboard, no onboarding tutorial route. The separate
   HYPER-SILLs project (semantic search, MiniLM embeddings) does NOT close this
   gap — it's wired into HyperCode-V2.4 only as a static, non-searchable
   agent-boot loadout injection (`agents/shared/loadout.py` reading two JSON
   files), never exposed to a human through `/ide`. This is a real, vaguer,
   product-shaped feature — worth keeping on the roadmap, but behind the
   infra/safety tiers above since it doesn't unblock anything else.

   **What `/ide` actually is today**: `agents/dashboard/app/ide/page.tsx` is a
   9-line file that renders `<StudioView />` — the coder-agent code-run studio
   (model picker, agent execution surface), not a skill browser of any kind.
   "Add skill discoverability to `/ide`" means adding a genuinely new capability
   to (or alongside) this view, not extending an existing partial one.

   **Approach options, not yet chosen or built**:
   - **(a) Static fuzzy-match search** — a small `/api/skills/search` endpoint
     doing keyword/fuzzy matching over each skill's name+description (the same
     metadata already in every `SKILL.md` frontmatter across `.claude/skills/`),
     surfaced as a search box in `/ide`. Smallest effort, no new infra, no LLM
     call — closest to what the original council doc's Product Agent described.
     Weakest for vague/natural-language goals ("deploy a Discord bot" won't
     obviously match a skill named `hypercode-broski-discord-bot`).
   - **(b) LLM-backed matcher** — a small endpoint that sends the user's goal +
     the skill catalog (name+description, already compact) to a cheap model
     (matches this repo's own established free/local-first pattern —
     OpenRouter/Ollama fallback, same as `broski-coo`) and returns ranked
     suggestions with a one-line rationale. Better recall for natural-language
     goals, small ongoing cost/latency, reuses existing LLM-client plumbing
     rather than inventing new infra.
   - **(c) Wire in HYPER-SILLs' real semantic search** — the MiniLM embedding
     index already exists and is live for a different project; exposing it to
     HyperCode-V2.4 would mean a new cross-project API call (HYPER-SILLs isn't
     currently network-reachable from HyperCode-V2.4, only filesystem-mounted
     as static JSON). Best long-term fit if HYPER-SILLs is meant to be the
     canonical skill index across projects, but the largest lift — needs
     HYPER-SILLs to expose a real endpoint first, not just files.
   - Onboarding tutorial (the doc's second half of this item) is a separate,
     smaller, unrelated deliverable (a guided first-skill walkthrough) that
     doesn't depend on which search approach is picked.

### Drop from active planning (stale, already resolved, or minor cleanup only)

- Reduce crew-orchestrator SPOF (overstated — one real dependency, not
  fleet-wide)
- Fix throttle-agent MemStream / dashboard bugs (already shipped)
- Resolve port collisions (already resolved)
- Improve Observability via Tempo integration (already shipped and live; the
  only real open question is an ops one — it's profile-gated and competes for
  the 8GB RAM ceiling against ~31 other agents, not a build task)
- Minor cleanup follow-ups, not roadmap items: `Dockerfile.template-hardened`'s
  `docker.io/library/python-hardened` base image (separate registry-policy
  question — likely an accepted exception as the official Python namespace, but
  worth a one-line decision), vendored `.venv`/`.venv311` dirs tracked in git
  (repo hygiene), `tests/test_compose_validator.py`'s broken `validate` import
  (0 tests currently collected for the unwired compose validator)

---

## Do first, per this re-rank

**Fix `docker-push.yml`'s GHCR case bug**, then **the shared brain-agent roster
mismatch** (Tier 1, items 1-2). Together they unblock more of the fleet — real
image publishing, both health-check gates, and the entire ghost-agents build
matrix — than anything else on this list, for less effort than a single item
on the original council's plan.
