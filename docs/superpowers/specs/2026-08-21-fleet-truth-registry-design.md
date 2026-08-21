# Fleet Truth Registry — Design

## Context & Constraints

- Follows directly from the 2026-08-21 CI-repair session (`WHATS_DONE.md`
  "CI workflow bugs #6/#7/#8 fixed") which found `health-check.yml` had
  never executed a single check, and along the way found a stale hand-copied
  port (`frontend-specialist` was `:8011` in `EXPECTED_PORTS`, real value
  `:8012`) and a hardcoded file list that had silently never read
  `docker-compose.agents.yml` — 13 of the 26 fleet agents' worth of drift,
  invisible to the gate meant to catch exactly that.
- Prompted by an external AI review of the `fleet-controller` Phase 0 work
  (saved locally as `HyperCode-V2.4/AGI-infrastructure upgrade`, not
  committed), which named "documentation drift" as an agent-safety issue —
  a planner fed stale context makes bad plans — and proposed a **truth
  registry**: one machine-readable source that generates the fleet tables
  in `AGENT-START.md`/`CLAUDE.md`, `health-check.yml`'s `EXPECTED_PORTS`,
  and roster/dashboard scripts, instead of each being hand-maintained and
  drifting independently. Full roadmap:
  `brain-agent -> mission-director -> fleet-controller -> Safety Shepherd ->
  Governance Ledger -> human review`, plus a mission evaluator (compares
  intended vs. actual outcome, produces structured lessons rather than raw
  logs) — this registry is the truth-model prerequisite for that planner,
  not the planner itself. Mission-director and the evaluator are future
  phases, not part of this spec.
- Decided via brainstorming dialogue (2026-08-21):
  - **Primary purpose**: single source of truth that generates everything,
    not just a drift-detecting validation layer bolted alongside the
    hand-written docs.
  - **Data source**: auto-derived from the real compose files (ports,
    build context, dockerfile, profiles — anything compose already states)
    plus a thin, explicit, hand-authored overlay for the handful of facts
    compose cannot express (which services count as "the fleet", which
    port collisions are intentional). Rejected: a fully hand-authored
    registry — that's a second source that can itself drift, the exact
    problem this exists to kill.
  - **Scope (v1)**: the 26-agent fleet only — `docker-compose.agents.yml`,
    `docker-compose.agents-full.yml`, plus `docker-compose.bropets.yml` and
    `docker-compose.brain.yml` (the two non-agent files with real
    historical collisions against fleet ports: `evolve-relay` vs
    `session-snapshot`, `hyper-brain` vs `test-agent`, both fixed
    2026-08-20). Same four-file scope `check_duplicate_ports.py` already
    uses. Whole-ecosystem scope (all ~30 compose files, which would also
    cover the `hypercode-ollama`/`hypercode-ollama-gpu` and
    `prometheus`/`prometheus-cloud` port-reuse risk logged as
    `docs/NEXT_TASKS.md` item #8a) is explicitly deferred, not designed
    here.
  - **First consumers (v1)**: `check_expected_ports.py` and
    `check_duplicate_ports.py` only. Generating the `AGENT-START.md`/
    `CLAUDE.md` markdown tables is deferred — it needs a markdown-injection
    mechanism (marker comments) that risks eating the surrounding prose
    both files are explicit about protecting ("read this file FIRST", "the
    constitution"), and is a separable follow-up once the registry itself
    is proven.
  - **No committed generated artifact.** `fleet_registry.py` is an
    importable library computed at run time from the compose files, not a
    JSON/YAML snapshot regenerated-and-committed. A committed snapshot is
    itself a file that can go stale between compose changes and the next
    regeneration — reintroducing the exact bug class this replaces.
  - **Collision allowlist keyed by port** (not by service-pair) —
    confirmed explicitly, matches `check_duplicate_ports.py`'s existing
    `ALLOWED_COLLISIONS` shape from tonight's fix.
  - **Tests required in v1**, mirroring `agents/fleet-controller/tests/`'s
    setup: a `tests/` directory next to the module, plain `pytest` (no
    unittest classes), a `conftest.py` only if a fixture is actually
    needed. Unlike the sibling `.github/scripts/*.py` checks (which have no
    test coverage and are verified by direct execution), `fleet_registry.py`
    is shared logic two CI gates depend on — a parsing bug here breaks both
    silently, which is enough justification to test it even though its
    siblings aren't.

## Goal

Replace the two remaining hand-maintained sources of fleet-port truth
(`EXPECTED_PORTS` in `check_expected_ports.py`, the `FILES` list +
`ALLOWED_COLLISIONS` in `check_duplicate_ports.py`) with a single shared
module that derives service facts from the real compose files and merges in
only the handful of facts compose cannot express. Success looks like: a
service renamed or removed in compose, or an overlay entry that's gone
stale, fails loudly and specifically (not "port missing", but "roster entry
X not found in compose") — the same class of bug tonight's session found
three separate times, now caught at the source instead of independently
rediscovered in each consumer.

## Non-Goals (this spec)

- Generating `AGENT-START.md`/`CLAUDE.md`'s markdown fleet tables. Future
  phase — needs its own design (injection markers, prose-preservation).
- Whole-ecosystem scope (all ~30 compose files). Future phase, if ever
  needed — v1's 4-file scope is deliberately identical to
  `check_duplicate_ports.py`'s existing, working scope.
- Any consumer beyond `health-check.yml`'s two Python checks. No dashboard,
  no roster script changes, no CI workflow restructuring beyond swapping
  what those two scripts import.
- `mission-director`, the mission evaluator, or anything else from the
  bigger roadmap. This registry is a prerequisite building block, not part
  of that work.

## Design

### 1. New module: `.github/scripts/fleet_registry.py`

```python
@dataclass(frozen=True)
class ServiceInfo:
    name: str
    host_port: str
    container_port: str
    source_file: str
    profiles: frozenset[str]

@dataclass(frozen=True)
class FleetRegistry:
    services: dict[str, ServiceInfo]        # keyed by container_name
    roster: frozenset[str]                   # from overlay
    allowed_collisions: dict[str, frozenset[str]]  # port -> service names, from overlay

def build() -> FleetRegistry:
    """Parse the 4 fleet compose files + the overlay, cross-validate, return
    the merged model. Raises RegistryError on any contract violation (see
    Error Handling) — never returns a silently-partial registry."""
```

`ServiceInfo.host_port`/`container_port` reuse the exact
`parts[-2 if len>=2 else 0]` extraction logic `check_duplicate_ports.py`
and `check_expected_ports.py` already have (independently, right now) —
consolidating it into one place is itself part of the fix, since a third
copy of that parsing bug is exactly the kind of thing this registry exists
to prevent.

`FILES = ["docker-compose.agents.yml", "docker-compose.agents-full.yml", "docker-compose.bropets.yml", "docker-compose.brain.yml"]` moves into this module (currently duplicated between the two check
scripts, one of them wrong in different ways at different times tonight).

### 2. Overlay file: `.github/scripts/fleet_overlay.yml`

```yaml
# The only hand-maintained file in this system. Keep additions here to
# "which services exist" facts only — anything compose can already state
# (ports, context, profiles) belongs in the compose files, not here.
roster:
  - crew-orchestrator
  - project-strategist
  - coder-agent
  - backend-specialist
  - database-architect
  - qa-engineer
  - devops-engineer
  - security-engineer
  - system-architect
  - frontend-specialist
  - hyper-split-agent
  - throttle-agent
  - super-hyper-broski-agent
  - session-snapshot
  - tips-tricks-writer
  - test-agent
  - business-agent
  - coderabbit-webhook
  - goal-keeper
  - brain-agent
  - agent-x
  - hyper-architect
  - hyper-observer
  - hyper-worker
  - fleet-controller

allowed_collisions:
  "8002": [coder-agent, ai-backend]
  "8099": [nemoclaw-agent, hyper-mission-ui]
```

25 roster names, zero ports — today's `EXPECTED_PORTS` dict pairs each of
these with a hand-typed port (one of which was already wrong). Ports come
from `build()` parsing compose instead.

### 3. Cross-validation inside `build()`

```
1. parse the 4 compose files -> ServiceInfo per service
2. load fleet_overlay.yml -> roster set, allowed_collisions dict
3. validate the overlay against reality:
   a. every roster name must exist in services -> else RegistryError
      ("roster entry {name} not found in any fleet compose file")
   b. every allowed_collisions port must have >=2 services actually
      sharing it, and the overlay's service names must be a subset of the
      real ones on that port -> else RegistryError
      ("allowed_collisions[{port}] names {overlay_names} but compose has
      {real_names}")
4. return FleetRegistry(services, roster, allowed_collisions)
```

Step 3 is the actual point of this design: the overlay is small (a name
list + a two-entry dict) specifically so it stays cheap to keep in sync,
and step 3 makes "out of sync" a loud build-time failure instead of a
silent pass — the same failure mode as tonight's stale `:8011`, just moved
from "reachable to the port-checker" to "reachable to the registry that
feeds the port-checker."

### 4. Consumer changes

`check_expected_ports.py` shrinks to:

```python
from fleet_registry import build, RegistryError

def main():
    try:
        registry = build()
    except RegistryError as e:
        print(f"FAIL: {e}")
        sys.exit(1)

    missing = [n for n in registry.roster if n not in registry.services]
    if missing:
        print("FAIL: roster names not found (should be impossible after build() validation):")
        for n in missing:
            print(f"  {n}")
        sys.exit(1)

    print(f"PASS: all {len(registry.roster)} roster agents confirmed in compose files.")
```

(The `missing` check after a successful `build()` is defensive, not
load-bearing — `build()`'s own step 3a already guarantees this can't
happen. Kept because a check that can never fail its own stated assertion
is a smell worth avoiding, not because it's expected to trigger.)

`check_duplicate_ports.py` shrinks similarly: iterate `registry.services`
grouped by `host_port`, flag any group of size >1 whose names aren't a
subset of `registry.allowed_collisions.get(port, frozenset())`.

## Error Handling

Same conventions as tonight's scripts, consolidated in one place instead of
repeated:

- Missing compose file -> skipped (`FileNotFoundError` caught), matches
  existing behavior — a fleet file genuinely might not exist in every
  checkout context.
- Malformed YAML in a compose file or the overlay -> `yaml.YAMLError`
  propagates unhandled; the script's own top-level failure message is
  self-explanatory enough (this matches how `validate_compose_yaml.py`
  already treats malformed compose YAML as a hard, visible failure rather
  than something to catch and re-wrap).
- Overlay contract violations (roster entry not in compose, collision
  allowlist stale) -> `RegistryError`, a small custom exception carrying a
  human-readable message identifying exactly which overlay line is wrong —
  this is the one new error type this design introduces, deliberately
  distinct from `yaml.YAMLError` so consumers can tell "the overlay is
  syntactically fine but semantically stale" apart from "the YAML itself is
  broken."

## Testing Plan

`agents/fleet-controller/tests/`-style layout:

```
.github/scripts/tests/
  test_fleet_registry.py
  fixtures/
    compose_minimal.yml       # 2-3 services, one with a BIND_IP:HOST:CONTAINER port
    overlay_valid.yml
    overlay_stale_roster.yml   # roster name not in the fixture compose
    overlay_stale_collision.yml # allowed_collisions naming a service not on that port
```

Cases:
- `build()` against the fixture compose + valid overlay returns the
  expected `ServiceInfo` set, including correct `host_port` extraction from
  a `"127.0.0.1:HOST:CONTAINER"` string (the exact bug fixed twice tonight
  in two independent copies of this same line).
- `build()` against `overlay_stale_roster.yml` raises `RegistryError`
  naming the specific missing service.
- `build()` against `overlay_stale_collision.yml` raises `RegistryError`
  naming the specific bad allowlist entry.
- `check_expected_ports.py`/`check_duplicate_ports.py` each get one
  integration-style test running against the real, live
  `fleet_overlay.yml` + real compose files (not fixtures) — this is the
  test that would have caught tonight's stale `:8011` before it shipped,
  and the one that keeps the fixture tests honest against reality.

No `conftest.py` needed — `fleet_registry.py` is synchronous, pure
file-parsing with no async fixtures to share (unlike `fleet-controller`'s
`client` fixture, which exists because that module is an HTTP service).

## Rollout Order

1. `fleet_registry.py` + `fleet_overlay.yml` + `tests/test_fleet_registry.py` — reviewed and passing standalone before anything else changes.
2. Migrate `check_expected_ports.py` to consume it; re-run against the live repo (same verification bar as tonight — parse the real workflow YAML, execute the real parsed `run:` command, confirm PASS).
3. Migrate `check_duplicate_ports.py` the same way.
4. Delete the now-dead duplicated `FILES`/`EXPECTED_PORTS`/`ALLOWED_COLLISIONS` definitions from both scripts.
5. Push, confirm via `gh run view` that `health-check.yml` still executes and passes both gates (blocked only by the known pre-existing billing lock, same as tonight).

## Out of Scope (future phases, not built here)

- Generating `AGENT-START.md`/`CLAUDE.md` fleet tables from the registry.
- Whole-ecosystem scope (all ~30 compose files, including the
  `hypercode-ollama`/`prometheus` port-reuse risk from item #8a).
- Any registry consumer outside `.github/scripts/`.
- `mission-director`, the mission evaluator, and the rest of the bigger
  autonomous-infrastructure roadmap this registry is a prerequisite for.
