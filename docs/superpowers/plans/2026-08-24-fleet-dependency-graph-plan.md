# Fleet Dependency Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the fleet truth-registry with a dependency graph (explicit `depends_on` + curated shared-resource env-var matching, including core infra) and surface a purely-advisory "impact set" (upstream needs, downstream already-running dependents) on `mission-director`'s `MissionProposal`, so a human reviewing a mission has a real answer to "what does this actually affect?" instead of just a category label.

**Architecture:** The canonical `.github/scripts/fleet_registry.py` gains graph facts (edges) and a query (`impact_set()`), computed fresh at call time like everything else in that module — never cached. `mission-director` (which already has a read-only bind-mount of the compose files for `truth_snapshot_ref`) computes impact for whatever profile(s) its LLM-generated plan picked, attaches it to its own `MissionProposal` type, and the backend persists+returns it. `fleet-controller` and the shared `PlanRequest`/`PlanResponse` types are untouched — zero risk to the Safety Shepherd policy path.

**Tech Stack:** Python 3.11, pydantic v2, pytest (+pytest-asyncio), FastAPI/httpx, SQLAlchemy + Alembic, PyYAML.

**Spec:** `docs/superpowers/specs/2026-08-24-fleet-dependency-graph-design.md`

## Global Constraints

- No cross-agent Python package imports — shared types/logic are kept as byte-for-byte file copies (established convention; see `agents/mission-director/models.py`'s header comment and the existing `fleet_registry.py` duplication between `.github/scripts/` and `agents/mission-director/`).
- Never touch `fleet-controller` or the shared `RequestedAction`/`Constraints`/`PlanRequest`/`SafetyView`/`ExecutionView`/`PlanResponse`/`canonical_hash` section of `models.py` — impact data is `mission-director`-only.
- `fleet_registry.py`/`impact_snapshot.py` never write a generated snapshot to disk — always computed fresh per call.
- A registry failure while computing `truth_snapshot_ref` still aborts the propose call (`preview_unavailable`, unchanged). A registry failure while computing impact must NOT abort it — degrade to `available: false` instead.
- 4 spaces indent, never 3, never mixed (repo-wide Python rule).
- `git fetch` before any push; commit+push per task per this repo's standing convention.

---

### Task 1: Dependency graph in the canonical `fleet_registry.py`

**Files:**
- Modify: `.github/scripts/fleet_registry.py`
- Create: `.github/scripts/tests/fixtures/compose_with_deps.yml`
- Create: `.github/scripts/tests/fixtures/overlay_empty.yml`
- Modify: `.github/scripts/tests/test_fleet_registry.py`
- Modify: `.github/scripts/tests/test_live_repo_integration.py`

**Interfaces:**
- Produces (used by Task 2): `GRAPH_FILES: list[str]` (module constant — `FILES + ["docker-compose.core.yml"]`), `build_edges(registry: FleetRegistry) -> dict[str, frozenset[str]]`, `impact_set(registry: FleetRegistry, profile: str) -> ImpactResult`, `ImpactResult` (frozen dataclass: `profile: str`, `upstream: frozenset[str]`, `downstream_already_running: frozenset[str]`). `ServiceInfo` gains `depends_on: frozenset[str]` and `env_var_names: frozenset[str]` (both default to `frozenset()`).
- Consumes: nothing new — extends the existing `build()`/`ServiceInfo`/`FleetRegistry`/`RegistryError` from this same file.

- [ ] **Step 1: Create the dependency fixture**

Create `.github/scripts/tests/fixtures/compose_with_deps.yml`:

```yaml
services:
  postgres:
    ports:
      - "5432:5432"
  worker:
    profiles: ["agents"]
    ports:
      - "9010:8080"
    depends_on:
      - postgres
    environment:
      POSTGRES_HOST: postgres
  watcher:
    ports:
      - "9011:8080"
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/db
  always-on-consumer:
    ports:
      - "9012:8080"
    depends_on:
      - worker
```

This covers: explicit `depends_on` (`worker`→`postgres`, `always-on-consumer`→`worker`), env-var-only inference with no `depends_on` at all (`watcher`→`postgres` via `DATABASE_URL`), a profile-gated service (`worker`, profile `agents`) and an always-on downstream consumer of it (`always-on-consumer`, no profile).

- [ ] **Step 2: Create the empty overlay fixture**

Create `.github/scripts/tests/fixtures/overlay_empty.yml`:

```yaml
roster: []
allowed_collisions: {}
```

- [ ] **Step 3: Write the failing tests**

Append to `.github/scripts/tests/test_fleet_registry.py`:

```python
from fleet_registry import build_edges, impact_set

FIXTURE_WITH_DEPS = os.path.join(FIXTURES, "compose_with_deps.yml")
OVERLAY_EMPTY = os.path.join(FIXTURES, "overlay_empty.yml")


def test_service_info_parses_depends_on_list_form():
    registry = build(files=[FIXTURE_WITH_DEPS], overlay_path=OVERLAY_EMPTY)
    assert registry.services["worker"].depends_on == frozenset({"postgres"})
    assert registry.services["always-on-consumer"].depends_on == frozenset({"worker"})
    assert registry.services["postgres"].depends_on == frozenset()


def test_service_info_parses_env_var_names_from_dict_form():
    registry = build(files=[FIXTURE_WITH_DEPS], overlay_path=OVERLAY_EMPTY)
    assert registry.services["worker"].env_var_names == frozenset({"POSTGRES_HOST"})
    assert registry.services["watcher"].env_var_names == frozenset({"DATABASE_URL"})
    assert registry.services["postgres"].env_var_names == frozenset()


def test_build_edges_includes_depends_on_and_env_var_matches():
    registry = build(files=[FIXTURE_WITH_DEPS], overlay_path=OVERLAY_EMPTY)
    edges = build_edges(registry)
    assert edges["worker"] == frozenset({"postgres"})
    assert edges["watcher"] == frozenset({"postgres"})  # env-var-only, no depends_on
    assert edges["always-on-consumer"] == frozenset({"worker"})
    assert edges["postgres"] == frozenset()


def test_impact_set_computes_upstream_and_downstream():
    registry = build(files=[FIXTURE_WITH_DEPS], overlay_path=OVERLAY_EMPTY)
    result = impact_set(registry, "agents")
    assert result.profile == "agents"
    assert result.upstream == frozenset({"postgres"})
    assert result.downstream_already_running == frozenset({"always-on-consumer"})


def test_impact_set_returns_empty_for_unknown_profile():
    registry = build(files=[FIXTURE_WITH_DEPS], overlay_path=OVERLAY_EMPTY)
    result = impact_set(registry, "no-such-profile")
    assert result.upstream == frozenset()
    assert result.downstream_already_running == frozenset()
```

- [ ] **Step 4: Run tests, confirm they fail**

Run: `cd .github/scripts && python -m pytest tests/test_fleet_registry.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_edges'` (and `impact_set`), and the two new `ServiceInfo` field assertions fail with `AttributeError` once the import is fixed.

- [ ] **Step 5: Implement the extension**

In `.github/scripts/fleet_registry.py`, replace the `ServiceInfo` dataclass (currently lines 36-42):

```python
@dataclass(frozen=True)
class ServiceInfo:
    name: str
    host_port: str
    container_port: str
    source_file: str
    profiles: frozenset
    depends_on: frozenset = frozenset()
    env_var_names: frozenset = frozenset()
```

Add two new helper functions right after `_container_port` (currently ends at line 59), before `def _parse_compose_files(files):`:

```python
def _depends_on_names(cfg) -> frozenset:
    """compose `depends_on:` may be a list of names or a dict of
    name -> {condition: ...}; either way we only need the names."""
    dep = cfg.get("depends_on")
    if not dep:
        return frozenset()
    if isinstance(dep, dict):
        return frozenset(dep.keys())
    return frozenset(str(d) for d in dep)


def _env_var_names(cfg) -> frozenset:
    """compose `environment:` may be a dict ({KEY: value}) or a list
    ("KEY=value" or bare "KEY" strings); either way we only need the
    variable *names* being referenced, never their values."""
    env = cfg.get("environment")
    if not env:
        return frozenset()
    if isinstance(env, dict):
        return frozenset(env.keys())
    return frozenset(str(item).split("=", 1)[0] for item in env)
```

In `_parse_compose_files`, replace the `services[svc] = ServiceInfo(...)` construction (currently lines 83-89) with:

```python
            services[svc] = ServiceInfo(
                name=svc,
                host_port=host_port,
                container_port=container_port,
                source_file=fname,
                profiles=profiles,
                depends_on=_depends_on_names(cfg),
                env_var_names=_env_var_names(cfg),
            )
```

Append at the end of the file, after `build()`:

```python
CORE_FILE = "docker-compose.core.yml"
GRAPH_FILES = FILES + [CORE_FILE]

# Shared-resource env vars -> the service they imply a dependency on. Not
# general network/volume inference (too noisy — nearly everything shares
# agents-net for routing without depending on each other); this is a
# small, reviewable list of the exact variable names this repo's compose
# files use to reach shared infra, standardized in the
# POSTGRES_HOST/REDIS_HOST indirection work (2026-08-23).
_SHARED_RESOURCE_ENV_VARS = {
    "POSTGRES_HOST": "postgres",
    "DATABASE_URL": "postgres",
    "POSTGRES_URL": "postgres",
    "HYPERCODE_DB_URL": "postgres",
    "REDIS_HOST": "redis",
    "REDIS_URL": "redis",
    "CORE_URL": "hypercode-core",
}


def build_edges(registry: FleetRegistry) -> dict:
    """service name -> frozenset of service names it depends on (compose
    depends_on union env-var-inferred). Pure function of the registry;
    never cached, matching this module's own convention."""
    edges = {}
    for name, svc in registry.services.items():
        targets = set(svc.depends_on)
        for env_name in svc.env_var_names:
            target = _SHARED_RESOURCE_ENV_VARS.get(env_name)
            if target:
                targets.add(target)
        edges[name] = frozenset(targets)
    return edges


@dataclass(frozen=True)
class ImpactResult:
    profile: str
    upstream: frozenset
    downstream_already_running: frozenset


def impact_set(registry: FleetRegistry, profile: str) -> ImpactResult:
    """What a profile's services need upstream (transitive), and what
    already-running (no-profile) services depend on them downstream
    (direct). A profile matching zero services returns empty sets, not an
    error — that's a legitimate (if suspicious) result for the caller to
    display, not a registry failure."""
    edges = build_edges(registry)
    profile_services = {
        name for name, svc in registry.services.items() if profile in svc.profiles
    }

    upstream = set()
    frontier = set(profile_services)
    while frontier:
        next_frontier = set()
        for name in frontier:
            for dep in edges.get(name, frozenset()):
                if dep not in upstream and dep not in profile_services:
                    upstream.add(dep)
                    next_frontier.add(dep)
        frontier = next_frontier

    downstream_already_running = set()
    for name, svc in registry.services.items():
        if svc.profiles:
            continue
        if edges.get(name, frozenset()) & profile_services:
            downstream_already_running.add(name)

    return ImpactResult(
        profile=profile,
        upstream=frozenset(upstream),
        downstream_already_running=frozenset(downstream_already_running),
    )
```

- [ ] **Step 6: Run tests, confirm they pass**

Run: `cd .github/scripts && python -m pytest tests/test_fleet_registry.py -v`
Expected: PASS, all tests including the pre-existing ones (this file's existing 5 tests must still be green — the `ServiceInfo` field additions have defaults so no existing caller breaks).

- [ ] **Step 7: Add the live-repo integration test**

Append to `.github/scripts/tests/test_live_repo_integration.py`:

```python
def test_impact_set_succeeds_against_real_repo_core_infra():
    from fleet_registry import GRAPH_FILES, impact_set

    registry = build(files=GRAPH_FILES)
    assert "postgres" in registry.services, "docker-compose.core.yml should be parsed via GRAPH_FILES"
    assert "redis" in registry.services

    result = impact_set(registry, "agents")
    assert isinstance(result.upstream, frozenset)
    assert isinstance(result.downstream_already_running, frozenset)
```

Run: `cd .github/scripts && python -m pytest tests/test_live_repo_integration.py -v`
Expected: PASS — confirms `docker-compose.core.yml` parses cleanly alongside the 4 fleet files with no `RegistryError` (e.g. from an unexpected multi-port service or an overlay mismatch).

- [ ] **Step 8: Sync the byte-for-byte copy**

```bash
cp .github/scripts/fleet_registry.py agents/mission-director/fleet_registry.py
```

Run: `cd agents/mission-director && python -m pytest tests/ -v`
Expected: PASS — this repo's existing mission-director test suite (unaffected by this change, since `ServiceInfo`'s new fields default to empty) must still be fully green after the copy.

- [ ] **Step 9: Commit**

```bash
git add .github/scripts/fleet_registry.py .github/scripts/tests/test_fleet_registry.py \
  .github/scripts/tests/test_live_repo_integration.py \
  .github/scripts/tests/fixtures/compose_with_deps.yml \
  .github/scripts/tests/fixtures/overlay_empty.yml \
  agents/mission-director/fleet_registry.py
git commit -m "feat: add dependency graph + impact_set to fleet_registry.py"
```

---

### Task 2: `impact_snapshot.py` + `ImpactView` in mission-director

**Files:**
- Create: `agents/mission-director/impact_snapshot.py`
- Modify: `agents/mission-director/models.py`
- Create: `agents/mission-director/tests/test_impact_snapshot.py`
- Modify: `agents/mission-director/tests/test_models.py`

**Interfaces:**
- Consumes (from Task 1): `fleet_registry.GRAPH_FILES`, `fleet_registry.RegistryError`, `fleet_registry.build(files, overlay_path)`, `fleet_registry.impact_set(registry, profile)`.
- Produces (used by Task 3): `impact_snapshot.get_impact(profiles: list[str], files: list[str] | None = None, overlay_path: str | None = None) -> list[ImpactView]`; `models.ImpactView` (pydantic: `profile: str`, `upstream: list[str] = []`, `downstream_already_running: list[str] = []`, `available: bool = True`, `reason: Optional[str] = None`); `models.MissionProposal.impact: list[ImpactView] = []` (new field).

- [ ] **Step 1: Write the failing model test**

Append to `agents/mission-director/tests/test_models.py`:

```python
from models import ImpactView


def test_mission_proposal_impact_defaults_to_empty_list():
    proposal = MissionProposal(
        schema_version=1,
        mission_id="mission_abc123",
        goal="do the thing",
        status="proposed",
    )
    assert proposal.impact == []


def test_impact_view_degraded_shape():
    view = ImpactView(profile="agents", available=False, reason="registry unavailable")
    assert view.upstream == []
    assert view.downstream_already_running == []
    assert view.reason == "registry unavailable"
```

Run: `cd agents/mission-director && python -m pytest tests/test_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'ImpactView'`.

- [ ] **Step 2: Add `ImpactView` and `MissionProposal.impact` to models.py**

In `agents/mission-director/models.py`, replace the `# ---- Mission Director additions (Phase 1) ----` section (currently lines 71-90) with:

```python
# ---- Mission Director additions (Phase 1 + Phase 2) ----


class ImpactView(BaseModel):
    """Advisory only -- never validated as fact, never fed back into
    Safety Shepherd's policy. See
    docs/superpowers/specs/2026-08-24-fleet-dependency-graph-design.md."""

    profile: str
    upstream: list[str] = Field(default_factory=list)
    downstream_already_running: list[str] = Field(default_factory=list)
    available: bool = True
    reason: Optional[str] = None


class MissionProposal(BaseModel):
    schema_version: Literal[1]
    mission_id: str
    goal: str
    truth_snapshot_ref: Optional[str] = None
    rationale: Optional[str] = None
    plan: Optional[PlanRequest] = None
    plan_response: Optional[PlanResponse] = None
    impact: list[ImpactView] = Field(default_factory=list)
    status: Literal[
        "proposed",
        "previewed",
        "approved",
        "rejected",
        "preview_unavailable",
        "rejected_malformed",
    ]
    superseded_from: Optional[str] = None
```

(The `class ReviewDecision(BaseModel):` block immediately after is unchanged — leave it in place.)

- [ ] **Step 3: Run model tests, confirm they pass**

Run: `cd agents/mission-director && python -m pytest tests/test_models.py -v`
Expected: PASS, all tests (pre-existing + new).

- [ ] **Step 4: Write the failing impact_snapshot tests**

Create `agents/mission-director/tests/test_impact_snapshot.py`:

```python
# agents/mission-director/tests/test_impact_snapshot.py
from impact_snapshot import get_impact

COMPOSE = """
services:
  postgres:
    ports:
      - "5432:5432"
  worker:
    profiles: ["agents"]
    ports:
      - "9010:8080"
    depends_on:
      - postgres
  always-on-consumer:
    ports:
      - "9012:8080"
    depends_on:
      - worker
"""

OVERLAY_EMPTY = """
roster: []
allowed_collisions: {}
"""


def test_get_impact_happy_path(tmp_path):
    compose_file = tmp_path / "compose.yml"
    compose_file.write_text(COMPOSE)
    overlay_file = tmp_path / "overlay.yml"
    overlay_file.write_text(OVERLAY_EMPTY)

    views = get_impact(["agents"], files=[str(compose_file)], overlay_path=str(overlay_file))

    assert len(views) == 1
    view = views[0]
    assert view.profile == "agents"
    assert view.available is True
    assert view.upstream == ["postgres"]
    assert view.downstream_already_running == ["always-on-consumer"]


def test_get_impact_degrades_on_registry_error(tmp_path):
    compose_file = tmp_path / "compose.yml"
    compose_file.write_text(COMPOSE)
    overlay_file = tmp_path / "overlay.yml"
    overlay_file.write_text("roster:\n  - nonexistent-service\nallowed_collisions: {}\n")

    views = get_impact(["agents"], files=[str(compose_file)], overlay_path=str(overlay_file))

    assert len(views) == 1
    assert views[0].available is False
    assert views[0].reason is not None
    assert views[0].upstream == []


def test_get_impact_empty_profiles_returns_empty_list():
    assert get_impact([]) == []
```

Run: `cd agents/mission-director && python -m pytest tests/test_impact_snapshot.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'impact_snapshot'`.

- [ ] **Step 5: Implement impact_snapshot.py**

Create `agents/mission-director/impact_snapshot.py`:

```python
# agents/mission-director/impact_snapshot.py
"""
Computes the advisory ImpactView list attached to a MissionProposal --
what a proposed plan's profile(s) need upstream, and what already-running
(no-profile) services depend on them downstream. Purely advisory: unlike
truth_snapshot.py, a failure here never aborts the propose call -- it
degrades to one ImpactView(available=False, reason=...) entry per
requested profile. See
docs/superpowers/specs/2026-08-24-fleet-dependency-graph-design.md.

Same bind-mount, same "never cache, compute fresh" rule as truth_snapshot.py.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/app/truth")

from fleet_registry import GRAPH_FILES, RegistryError, build, impact_set  # noqa: E402

from models import ImpactView

_MOUNT_DIR = "/app/truth"
_OVERLAY = f"{_MOUNT_DIR}/fleet_overlay.yml"


def _graph_files() -> list[str]:
    return [f"{_MOUNT_DIR}/{f}" for f in GRAPH_FILES]


def get_impact(
    profiles: list[str],
    files: list[str] | None = None,
    overlay_path: str | None = None,
) -> list[ImpactView]:
    views: list[ImpactView] = []
    for profile in profiles:
        try:
            registry = build(
                files=files if files is not None else _graph_files(),
                overlay_path=overlay_path or _OVERLAY,
            )
            result = impact_set(registry, profile)
        except (RegistryError, FileNotFoundError) as exc:
            views.append(ImpactView(profile=profile, available=False, reason=str(exc)))
            continue
        views.append(
            ImpactView(
                profile=profile,
                upstream=sorted(result.upstream),
                downstream_already_running=sorted(result.downstream_already_running),
                available=True,
            )
        )
    return views
```

- [ ] **Step 6: Run tests, confirm they pass**

Run: `cd agents/mission-director && python -m pytest tests/test_impact_snapshot.py -v`
Expected: PASS, all 3 tests.

- [ ] **Step 7: Run the full mission-director suite**

Run: `cd agents/mission-director && python -m pytest tests/ -v`
Expected: PASS, every test (pre-existing + Task 2's new ones) — `main.py` isn't touched yet, so nothing here should regress.

- [ ] **Step 8: Commit**

```bash
git add agents/mission-director/impact_snapshot.py agents/mission-director/models.py \
  agents/mission-director/tests/test_impact_snapshot.py agents/mission-director/tests/test_models.py
git commit -m "feat: add impact_snapshot.py and ImpactView to mission-director"
```

---

### Task 3: Wire it end-to-end (main.py, container, backend)

**Files:**
- Modify: `agents/mission-director/main.py`
- Modify: `agents/mission-director/Dockerfile`
- Modify: `docker-compose.agents-full.yml`
- Modify: `agents/mission-director/tests/test_fleet_controller_unavailable.py`
- Modify: `backend/app/models/mission.py`
- Create: `backend/alembic/versions/022_add_mission_impact.py`
- Modify: `backend/app/services/mission_store.py`
- Modify: `backend/app/api/v1/endpoints/missions.py`
- Modify: `backend/tests/test_mission_store.py`
- Modify: `backend/tests/test_missions_endpoint.py`

**Interfaces:**
- Consumes (from Task 2): `impact_snapshot.get_impact(profiles) -> list[ImpactView]`, `models.ImpactView`.
- Produces: `MissionProposal.impact` flows end-to-end from mission-director's HTTP response through `backend/app/services/mission_store.create(..., impact=...)` into the `mission_proposals.impact` JSONB column and back out through `_serialize()`.

- [ ] **Step 1: Wire main.py**

In `agents/mission-director/main.py`, update the imports (currently lines 22-27):

```python
import fleet_client
import impact_snapshot
import ledger_client
import plan_generator
from local_validator import LocalValidationError, validate
from models import Constraints, ImpactView, MissionProposal, PlanRequest
from truth_snapshot import get_snapshot_ref
```

Replace `_terminal` (currently lines 55-74):

```python
def _terminal(
    mission_id: str,
    goal: str,
    truth_snapshot_ref: str | None,
    status: str,
    plan: PlanRequest | None = None,
    rationale: str | None = None,
    impact: list[ImpactView] | None = None,
) -> MissionProposal:
    proposal = MissionProposal(
        schema_version=1,
        mission_id=mission_id,
        goal=goal,
        truth_snapshot_ref=truth_snapshot_ref,
        rationale=rationale,
        plan=plan,
        plan_response=None,
        impact=impact or [],
        status=status,
    )
    ledger_client.record_proposal(proposal)  # fire-and-forget, not awaited
    return proposal
```

Replace `create_plan` (currently lines 77-126):

```python
@app.post("/v1/plan", response_model=MissionProposal)
async def create_plan(request: PlanGoalRequest) -> MissionProposal:
    mission_id = request.mission_id
    goal = request.goal

    try:
        snapshot_ref = get_snapshot_ref()
    except Exception:
        return _terminal(mission_id, goal, None, "preview_unavailable")

    try:
        llm_output = await plan_generator.generate(goal)
    except plan_generator.PlanGenerationError:
        return _terminal(mission_id, goal, snapshot_ref, "preview_unavailable")
    except plan_generator.PlanMalformedError:
        return _terminal(mission_id, goal, snapshot_ref, "rejected_malformed")

    plan_request = PlanRequest(
        schema_version=1,
        mission_id=mission_id,
        requested_actions=llm_output.requested_actions,
        constraints=Constraints(),
    )

    profiles = sorted(
        {a.profile for a in llm_output.requested_actions if a.profile is not None}
    )
    impact = impact_snapshot.get_impact(profiles)

    try:
        validate(plan_request, snapshot_ref)
    except LocalValidationError:
        return _terminal(
            mission_id, goal, snapshot_ref, "rejected_malformed",
            plan_request, llm_output.rationale, impact,
        )

    try:
        plan_response = await fleet_client.preview(plan_request)
    except fleet_client.FleetControllerUnavailable:
        return _terminal(
            mission_id, goal, snapshot_ref, "preview_unavailable",
            plan_request, llm_output.rationale, impact,
        )

    proposal = MissionProposal(
        schema_version=1,
        mission_id=mission_id,
        goal=goal,
        truth_snapshot_ref=snapshot_ref,
        rationale=llm_output.rationale,
        plan=plan_request,
        plan_response=plan_response,
        impact=impact,
        status="previewed",
    )
    ledger_client.record_proposal(proposal)
    return proposal
```

- [ ] **Step 2: Run the existing mission-director tests — confirm no regressions**

Run: `cd agents/mission-director && python -m pytest tests/ -v`
Expected: PASS, all pre-existing tests unchanged (every existing test uses `RequestedAction` without a `profile`, so `profiles` resolves to `[]` and `impact_snapshot.get_impact([])` returns `[]` without touching `/app/truth` at all — no new mocking needed for them to keep passing).

- [ ] **Step 3: Write the new impact-wiring test**

Append to `agents/mission-director/tests/test_fleet_controller_unavailable.py`:

```python
@pytest.mark.asyncio
async def test_create_plan_route_includes_impact_for_profile_actions(client, monkeypatch):
    import main
    from models import ExecutionView, ImpactView, PlanResponse, SafetyView

    async def _fake_generate(goal):
        return LLMPlanOutput(
            rationale="r",
            requested_actions=[
                RequestedAction(action_id="a1", kind="compose_profile.preview", profile="agents")
            ],
        )

    async def _fake_preview(plan):
        return PlanResponse(
            plan_id="plan_test6",
            plan_hash="sha256:testhash6",
            safety=SafetyView(decision="ESCALATE", reason="dangerous category", shepherd_available=True),
            execution=ExecutionView(performed=False, would_execute=[]),
        )

    def _fake_get_impact(profiles):
        assert profiles == ["agents"]
        return [
            ImpactView(
                profile="agents",
                upstream=["postgres"],
                downstream_already_running=[],
                available=True,
            )
        ]

    monkeypatch.setattr(main, "get_snapshot_ref", lambda: "sha256:test")
    monkeypatch.setattr(main.plan_generator, "generate", _fake_generate)
    monkeypatch.setattr(main.fleet_client, "preview", _fake_preview)
    monkeypatch.setattr(main.impact_snapshot, "get_impact", _fake_get_impact)

    resp = await client.post("/v1/plan", json={"mission_id": "mission_t6", "goal": "x"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "previewed"
    assert body["impact"] == [
        {
            "profile": "agents",
            "upstream": ["postgres"],
            "downstream_already_running": [],
            "available": True,
            "reason": None,
        }
    ]
```

Run: `cd agents/mission-director && python -m pytest tests/test_fleet_controller_unavailable.py -v`
Expected: PASS, all tests including the new one.

- [ ] **Step 4: Update the Dockerfile**

In `agents/mission-director/Dockerfile`, add one line after `COPY truth_snapshot.py .` (currently line 63):

```dockerfile
COPY truth_snapshot.py .
COPY impact_snapshot.py .
COPY fleet_registry.py .
```

- [ ] **Step 5: Add the core-infra bind mount**

In `docker-compose.agents-full.yml`, in `mission-director`'s `volumes:` block, add one line after the existing `docker-compose.brain.yml` mount (currently line 688):

```yaml
      - ./docker-compose.brain.yml:/app/truth/docker-compose.brain.yml:ro
      - ./docker-compose.core.yml:/app/truth/docker-compose.core.yml:ro
```

- [ ] **Step 6: Add the backend migration**

Create `backend/alembic/versions/022_add_mission_impact.py`:

```python
"""Add impact column to mission_proposals (Fleet Dependency Graph, Phase 2)

Revision ID: 022
Revises: 021
Create Date: 2026-08-24

Purely advisory data -- see
docs/superpowers/specs/2026-08-24-fleet-dependency-graph-design.md. Same
nullable-JSONB pattern as plan/plan_response (020).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mission_proposals",
        sa.Column("impact", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mission_proposals", "impact")
```

- [ ] **Step 7: Add the column to the SQLAlchemy model**

In `backend/app/models/mission.py`, add one field after `plan_response` (currently lines 31-33):

```python
    plan_response: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB().with_variant(SQLiteJSON(), "sqlite"), nullable=True
    )
    impact: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB().with_variant(SQLiteJSON(), "sqlite"), nullable=True
    )
```

- [ ] **Step 8: Write the failing mission_store test**

Append to `backend/tests/test_mission_store.py`:

```python
def test_impact_stored_and_retrieved(db: Session):
    row = mission_store.create(
        db,
        mission_id="mission_test004",
        status="previewed",
        goal="g3",
        truth_snapshot_ref="sha256:abc",
        plan=None,
        plan_response=None,
        impact=[{"profile": "agents", "upstream": ["postgres"], "downstream_already_running": [], "available": True, "reason": None}],
    )
    assert row.impact == [
        {"profile": "agents", "upstream": ["postgres"], "downstream_already_running": [], "available": True, "reason": None}
    ]

    fetched = mission_store.get_by_id(db, "mission_test004")
    assert fetched.impact == row.impact
```

Run: `cd backend && python -m pytest tests/test_mission_store.py -v`
Expected: FAIL — `TypeError: create() got an unexpected keyword argument 'impact'`.

- [ ] **Step 9: Add `impact` to mission_store.create()**

In `backend/app/services/mission_store.py`, replace `create()` (currently lines 16-39):

```python
def create(
    db: Session,
    *,
    mission_id: str,
    status: str,
    goal: str,
    truth_snapshot_ref: Optional[str],
    plan: Optional[dict[str, Any]],
    plan_response: Optional[dict[str, Any]],
    impact: Optional[list[dict[str, Any]]] = None,
    superseded_from: Optional[str] = None,
) -> MissionProposal:
    row = MissionProposal(
        mission_id=mission_id,
        status=status,
        goal=goal,
        truth_snapshot_ref=truth_snapshot_ref,
        plan=plan,
        plan_response=plan_response,
        impact=impact,
        superseded_from=superseded_from,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
```

- [ ] **Step 10: Run the mission_store tests, confirm they pass**

Run: `cd backend && python -m pytest tests/test_mission_store.py -v`
Expected: PASS, all tests (pre-existing + new).

- [ ] **Step 11: Write the failing endpoint test**

Append to `backend/tests/test_missions_endpoint.py`:

```python
def test_propose_persists_and_returns_impact(client, db):
    user = _make_user(db)
    mock_payload = {
        "schema_version": 1,
        "mission_id": "mission_mocked_impact",
        "goal": "do the thing",
        "truth_snapshot_ref": "sha256:abc",
        "rationale": "because",
        "plan": {"schema_version": 1, "mission_id": "mission_mocked_impact", "requested_actions": []},
        "plan_response": {
            "plan_id": "plan_x",
            "plan_hash": "sha256:x",
            "safety": {"decision": "ESCALATE", "reason": "r", "shepherd_available": True},
            "execution": {"performed": False, "would_execute": []},
        },
        "impact": [
            {"profile": "agents", "upstream": ["postgres"], "downstream_already_running": [], "available": True, "reason": None}
        ],
        "status": "previewed",
        "superseded_from": None,
    }
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_MockResponse(mock_payload))):
        resp = client.post(
            "/api/v1/missions/propose",
            json={"goal": "do the thing"},
            headers=_auth_headers(user),
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["impact"] == mock_payload["impact"]
```

Run: `cd backend && python -m pytest tests/test_missions_endpoint.py -v -k test_propose_persists_and_returns_impact`
Expected: FAIL — `body["impact"]` is missing (endpoint doesn't read or persist it yet).

- [ ] **Step 12: Wire the endpoint**

In `backend/app/api/v1/endpoints/missions.py`, add `"impact": row.impact or [],` to `_serialize()` (currently lines 69-80), after the `plan_response` line:

```python
def _serialize(row) -> dict[str, Any]:
    return {
        "mission_id": row.mission_id,
        "status": row.status,
        "goal": row.goal,
        "truth_snapshot_ref": row.truth_snapshot_ref,
        "plan": row.plan,
        "plan_response": row.plan_response,
        "impact": row.impact or [],
        "superseded_from": row.superseded_from,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
```

In the same file's `propose_mission()`, add `"impact": []` to the exception-fallback `proposal` dict (currently lines 108-118):

```python
    except Exception:
        proposal = {
            "schema_version": 1,
            "mission_id": mission_id,
            "goal": body.goal,
            "truth_snapshot_ref": None,
            "rationale": None,
            "plan": None,
            "plan_response": None,
            "impact": [],
            "status": "preview_unavailable",
            "superseded_from": None,
        }
```

And add `impact=proposal.get("impact")` to the `mission_store.create()` call (currently lines 123-132):

```python
    row = mission_store.create(
        db,
        mission_id=mission_id,
        status=proposal["status"],
        goal=proposal["goal"],
        truth_snapshot_ref=proposal.get("truth_snapshot_ref"),
        plan=proposal.get("plan"),
        plan_response=proposal.get("plan_response"),
        impact=proposal.get("impact"),
        superseded_from=proposal.get("superseded_from"),
    )
```

- [ ] **Step 13: Run the endpoint tests, confirm they pass**

Run: `cd backend && python -m pytest tests/test_missions_endpoint.py -v`
Expected: PASS, all tests (pre-existing + new) — the pre-existing tests' mock payloads don't include `"impact"`, so `proposal.get("impact")` returns `None`, stored as `impact=None`, serialized back as `"impact": []` — no breakage.

- [ ] **Step 14: Run the full backend test suite**

Run: `cd backend && python -m pytest tests/ -v`
Expected: PASS, no regressions anywhere else in the backend.

- [ ] **Step 15: Commit**

```bash
git add agents/mission-director/main.py agents/mission-director/Dockerfile \
  agents/mission-director/tests/test_fleet_controller_unavailable.py \
  docker-compose.agents-full.yml \
  backend/app/models/mission.py backend/alembic/versions/022_add_mission_impact.py \
  backend/app/services/mission_store.py backend/app/api/v1/endpoints/missions.py \
  backend/tests/test_mission_store.py backend/tests/test_missions_endpoint.py
git commit -m "feat: wire fleet-impact data through mission-director and backend"
```

---

### Task 4: Live verification + docs

**Files:**
- Modify: `WHATS_DONE.md`

- [ ] **Step 1: Rebuild and recreate mission-director**

```bash
docker build --no-cache -t hypercode-v24-mission-director:latest ./agents/mission-director
docker compose -f docker-compose.yml -f docker-compose.agents-full.yml \
  --profile fleet up -d --no-deps --force-recreate mission-director
```

Confirm the container's own compose service `image:` field (if any override exists — check `docker-compose.agents-full.yml`'s `mission-director` block for an `image:` line) matches the tag just built, per the exact gotcha already documented in this repo's 2026-08-23 afternoon `WHATS_DONE.md` entry (a mismatched tag silently keeps the stale image running even after `--force-recreate`).

- [ ] **Step 2: Rebuild and recreate hypercode-core (backend code + migration)**

```bash
docker compose -f docker-compose.core.yml build hypercode-core
docker compose -f docker-compose.yml -f docker-compose.core.yml up -d hypercode-core
```

Check the startup logs for the migration applying:

```bash
docker logs hypercode-core --tail 50 | grep -i "021 -> 022\|Running upgrade"
```

Expected: a line showing `021 -> 022, Add impact column to mission_proposals`.

- [ ] **Step 3: Full-fleet health sweep (before comparison already implicit — confirm after)**

```bash
docker ps --filter "health=unhealthy"
```

Expected: empty output — zero unhealthy containers.

- [ ] **Step 4: Live-verify a real propose call**

Mint a real JWT the same way prior sessions did (`create_access_token`, run inside the live `hypercode-core` container), then:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/missions/propose \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"goal": "preview turning on the agents profile"}' | python -m json.tool
```

Confirm the response's `"impact"` field is a non-empty list when the LLM's plan includes a `profile`, and that at least one entry's `"upstream"` includes `"postgres"` or `"redis"` for a profile that's known to contain DB-dependent agents (cross-check against `docker-compose.agents.yml`'s `depends_on`/env-var blocks for whichever profile the LLM actually picked — the real LLM output isn't scriptable in advance, so confirm post-hoc against the real compose file rather than asserting an exact expected profile name).

- [ ] **Step 5: Update WHATS_DONE.md**

Add a new dated entry at the top of `WHATS_DONE.md` (following this file's existing entry format — see the most recent entries for the exact header/prose style) summarizing: what was built (dependency graph + `impact_set()` in `fleet_registry.py`, `impact_snapshot.py` + `ImpactView` in mission-director, backend persistence), what was deliberately left untouched (Safety Shepherd's policy, fleet-controller, the shared `PlanRequest`/`PlanResponse` types), and the live verification result from Step 4 (exact response observed, not a paraphrase).

- [ ] **Step 6: Commit and push**

```bash
git add WHATS_DONE.md
git fetch origin
git commit -m "docs: fleet dependency graph live-verified, WHATS_DONE updated"
git push origin HEAD
```
