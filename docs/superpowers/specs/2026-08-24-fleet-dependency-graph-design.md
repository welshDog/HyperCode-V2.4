# Fleet Dependency Graph — Design Spec

Status: approved for planning
Owner: mission-director track (Phase 2)
Depends on: `docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md`,
`docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md`

## 1. Problem

`mission-director` can already produce a previewed, Safety-Shepherd-reviewed
infrastructure-change plan (Phase 1, 2026-08-21). But both the truth-registry
and Safety Shepherd's policy reason about a plan at **category** granularity
("profile `docker` is dangerous") — neither knows what a profile's services
actually touch. `fleet_registry.py`'s `ServiceInfo` is a flat fact per
service (name, port, source file, profiles); there are no edges between
services at all, and `docker-compose.core.yml` (postgres, redis, prometheus)
is entirely outside the parsed set.

This means a human reviewing a mission proposal has no answer to "what does
this actually affect?" beyond a category label. The two most useful signals
for that question — "what does this profile's services depend on" and "what
already-running services depend on those same things" — don't exist
anywhere in the system today.

## 2. Scope

**In scope**: extend the canonical `fleet_registry.py` with a dependency
graph (including core infra) and an `impact_set()` query; compute and
surface that impact set, purely as advisory data, on `mission-director`'s
`MissionProposal`.

**Out of scope** (deliberately, not oversight):
- Feeding impact data into Safety Shepherd's ALLOW/BLOCK/ESCALATE policy.
  The policy engine is load-bearing for the whole containment story; this
  data hasn't been proven live yet. A future phase can revisit this once
  impact data has a track record — not now.
- Network/volume-overlap-based edge inference. Nearly every service shares
  `agents-net` for routing without actually depending on each other;
  inferring edges from that would be high-noise and need its own filtering
  pass. Edges come only from `depends_on` and a small curated env-var map.
- Feeding impact data back into the LLM's plan-generation call. The LLM
  picks the `profile` a plan touches; impact can't be computed until that
  profile exists, so it's necessarily a post-generation, human-facing
  artifact for v1. A second LLM round-trip to let it react to its own
  impact set is possible later but isn't justified yet (YAGNI).
- Touching `fleet-controller` or the shared `PlanRequest`/`PlanResponse`/
  `canonical_hash` types it keeps byte-for-byte in sync with
  `mission-director`. `mission-director` already has its own read-only
  bind-mount of the compose files (for `truth_snapshot_ref`); it computes
  and stores impact data on its own `MissionProposal` type only.

## 3. Data model — `fleet_registry.py` extension

Extends the existing canonical module (`.github/scripts/fleet_registry.py`),
bind-mounted read-only into `mission-director` exactly as it is today for
`truth_snapshot.py`. Still "never writes a generated snapshot to disk —
always computed fresh at call time," same as the existing design note.

**Parse set**: add `docker-compose.core.yml` to the files `build()` parses,
so `postgres`, `redis`, `prometheus`, etc. become real `ServiceInfo` nodes.
The existing 4 fleet files are untouched.

**`ServiceInfo` gains**:
- `depends_on: frozenset[str]` — parsed directly from each service's
  `depends_on` key (dict or list form).
- Environment-derived edges are *not* stored per-service; they're computed
  in a new function (below) from a curated constant map, so the mapping
  logic lives in one place and stays reviewable as a diff, not scattered
  across parsing code.

**New curated constant**, the "small hand-maintained list of facts compose
can't express" pattern `fleet_overlay.yml` already established:

```python
_SHARED_RESOURCE_ENV_VARS = {
    "POSTGRES_HOST": "postgres",
    "DATABASE_URL": "postgres",
    "POSTGRES_URL": "postgres",
    "HYPERCODE_DB_URL": "postgres",
    "REDIS_HOST": "redis",
    "REDIS_URL": "redis",
    "CORE_URL": "hypercode-core",
}
```

A service's `environment` block (dict or `KEY=value` list form) is scanned
for these variable names (not their values — `${POSTGRES_HOST:-postgres}`
interpolation is irrelevant here, only the *name being referenced* matters).
A match adds an edge from that service to the mapped target.

**New function**:

```python
def build_edges(registry: FleetRegistry) -> dict[str, frozenset[str]]:
    """service name -> set of service names it depends on (depends_on
    union env-var-inferred). Pure function of the registry; not cached."""

def impact_set(registry: FleetRegistry, profile: str) -> ImpactResult:
    """For every service tagged with `profile`:
    - upstream: transitive closure of what those services depend on
      (what this profile *needs* to function)
    - downstream_already_running: services with no profile (base compose,
      i.e. presumed always-running) that depend on any service in this
      profile (who's affected if this profile's services change)
    Raises RegistryError/FileNotFoundError on registry build failure —
    same as `build()` itself; the caller decides how to degrade."""
```

`ImpactResult` is a plain dataclass (`profile`, `upstream: frozenset[str]`,
`downstream_already_running: frozenset[str]`) — kept dependency-free
(stdlib + existing `FleetRegistry` types only), matching this module's
existing convention.

## 4. Flow — `mission-director`

New `agents/mission-director/impact_snapshot.py`, sibling to the existing
`truth_snapshot.py`, same bind-mount (`/app/truth/`), same "never cache,
compute fresh" rule:

```python
def get_impact(profiles: list[str]) -> list[ImpactView]:
    """One ImpactView per requested profile. Never raises — a registry
    failure here degrades to available=False, it does not abort the
    propose call the way truth_snapshot's failure does."""
```

`ImpactView` (new, in `mission-director/models.py` only — does not touch
the byte-for-byte-shared `RequestedAction`/`Constraints`/`PlanRequest`/
`SafetyView`/`ExecutionView`/`PlanResponse`/`canonical_hash` section):

```python
class ImpactView(BaseModel):
    profile: str
    upstream: list[str] = Field(default_factory=list)
    downstream_already_running: list[str] = Field(default_factory=list)
    available: bool = True
    reason: Optional[str] = None
```

`MissionProposal` gains `impact: list[ImpactView] = Field(default_factory=list)`.

**Ordering in `main.py`'s propose flow** (extends the existing sequence,
does not reorder anything already there):

1. Compute `truth_snapshot_ref` (existing — still fails closed to
   `preview_unavailable` on registry failure, unchanged).
2. Call `plan_generator.generate(goal)` → `LLMPlanOutput` (existing,
   unchanged).
3. **New**: for each `RequestedAction` in the LLM's output that has a
   `profile` set, call `impact_snapshot.get_impact()`. Build the
   `MissionProposal.impact` list. A registry failure here produces one
   `ImpactView(profile=..., available=False, reason=str(exc))` entry, not
   an aborted propose call — same "checkable, not just trusted" tagging
   `broski-coo` already uses for its own source health.
4. Call `fleet_client.preview()` against `fleet-controller` (existing,
   completely unchanged — no new fields on the wire between
   mission-director and fleet-controller).
5. Persist the `MissionProposal`, now including `impact`.

Actions with `kind: "crew.workflow.preview"` (no `profile`) get no impact
entry — there's no profile to compute impact for. This is a gap, not a bug:
that action kind doesn't touch compose-level infrastructure the graph
models at all.

## 5. Persistence — backend

`backend/app/models/mission.py`'s `MissionProposal` already stores `plan`
and `plan_response` as nullable JSONB columns (`with_variant(SQLiteJSON(),
"sqlite")` for test-DB compatibility). Add `impact` as one more column,
same pattern, one new migration. `backend/app/services/mission_store.py`
and the `propose`/`review` endpoint responses pass it through unchanged —
no new logic beyond "store and return this dict too."

## 6. Error handling summary

| Failure | Behavior | Why |
|---|---|---|
| Registry fails building `truth_snapshot_ref` | Propose call aborts, `status=preview_unavailable` (existing, unchanged) | Safety-adjacent — the snapshot grounds what the plan is reviewed against |
| Registry fails building impact data | One `ImpactView(available=False, reason=...)`, propose call continues | Purely advisory — a human still gets a reviewable proposal, just missing one non-authoritative field |
| `fleet-controller` preview call | Unchanged (existing `FleetControllerUnavailable` → `preview_unavailable`) | Not touched by this design at all |

## 7. Testing

- Unit tests, `fleet_registry.py`: `depends_on` parsing (dict + list form),
  env-var edge matching against the curated map (including the exact
  `POSTGRES_HOST`/`REDIS_HOST` pattern from the 2026-08-23 indirection
  work), `impact_set()` against fixture compose files that include a
  core-infra dependency case.
- Unit tests, `impact_snapshot.py`: happy path (real fixture registry) and
  the degrade-to-`available=False` path (mocked `RegistryError`).
- One integration test running `impact_set()` against the real, live
  compose files (mirrors the truth-registry's own precedent for catching
  drift fixtures can't).
- Live verification: propose a real mission whose LLM-chosen profile
  touches a postgres/redis-dependent agent; confirm the stored
  `MissionProposal.impact` is populated and correct. Full-fleet sweep
  (zero unhealthy containers) before/after, matching this repo's standing
  verification convention.

## 8. Task breakdown (for the implementation plan)

1. Extend `fleet_registry.py` (core-infra parsing, `depends_on` field,
   `_SHARED_RESOURCE_ENV_VARS`, `build_edges()`, `impact_set()`) + unit and
   integration tests.
2. New `impact_snapshot.py` in `mission-director` + `ImpactView` /
   `MissionProposal.impact` in its `models.py` + unit tests.
3. Wire `main.py`'s propose flow (step 3 in §4) + backend migration +
   `mission_store.py`/endpoint pass-through.
4. Live verification + docs (`WHATS_DONE.md` entry, this spec's
   self-review already folded in below).

## 9. Self-review notes

- No placeholders/TBDs above; every field and function signature is
  concrete.
- Checked for contradiction with the truth-registry's "never write a
  generated snapshot to disk" rule — `impact_snapshot.py` follows it
  identically (computed fresh per call, nothing cached).
- Checked for contradiction with fleet-controller's containment
  invariant ("no component may both interpret LLM output and possess
  infrastructure mutation authority") — this design adds zero mutation
  capability anywhere; it's a read-only query over already-parsed compose
  facts, surfaced to a human.
- Scope is comparable to the original truth-registry build (4 tasks, no
  fix rounds expected) — not decomposed further.
