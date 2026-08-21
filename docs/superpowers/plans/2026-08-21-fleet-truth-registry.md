# Fleet Truth Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two hand-maintained sources of fleet-port truth (`EXPECTED_PORTS` in `check_expected_ports.py`, the `FILES`/`ALLOWED_COLLISIONS` in `check_duplicate_ports.py`) with one shared module that derives service facts from the real compose files and merges in a thin, self-validating overlay for the handful of facts compose can't express.

**Architecture:** A new `.github/scripts/fleet_registry.py` parses 4 compose files into a `FleetRegistry` (services keyed by name, each with host/container port + profiles), loads `.github/scripts/fleet_overlay.yml` (roster names + allowed-collision pairs), and cross-validates the overlay against the parsed reality at every `build()` call — a stale overlay entry raises `RegistryError` naming exactly what's wrong, rather than silently passing. Both existing check scripts shrink to call `build()` and assert against its result.

**Tech Stack:** Python 3, PyYAML (already a dependency of the sibling scripts), pytest (new dev dependency for this directory only — no existing `.github/scripts` tests to conflict with).

**Spec:** `docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md`

## Global Constraints

- No committed generated artifact — `fleet_registry.py` computes the registry at call time from the live compose files; never write a JSON/YAML snapshot to disk.
- Scope is exactly 4 files: `docker-compose.agents.yml`, `docker-compose.agents-full.yml`, `docker-compose.bropets.yml`, `docker-compose.brain.yml`. No others.
- Collision allowlist is keyed by host port (string), not by service-pair.
- `build()` must never return a partial/silently-wrong registry — every overlay contract violation raises `RegistryError` with a message naming the exact offending entry.
- Tests live in `.github/scripts/tests/`, plain pytest, no unittest classes.
- Every host-port string must be parsed via `parts[-2] if len(parts) >= 2 else parts[0]` on `str(mapping).split(":")` — the exact fix for the `"BIND_IP:HOST:CONTAINER"` bug found twice on 2026-08-21. Never reintroduce `.split('127.0.0.1:')` or any IP-literal-specific parsing.

---

## Task 1: `fleet_registry.py` core module + fixture-based unit tests

**Files:**
- Create: `.github/scripts/fleet_registry.py`
- Create: `.github/scripts/tests/conftest.py`
- Create: `.github/scripts/tests/fixtures/compose_minimal.yml`
- Create: `.github/scripts/tests/fixtures/overlay_valid.yml`
- Create: `.github/scripts/tests/fixtures/overlay_stale_roster.yml`
- Create: `.github/scripts/tests/fixtures/overlay_stale_collision.yml`
- Test: `.github/scripts/tests/test_fleet_registry.py`

**Interfaces:**
- Produces (used by Tasks 2, 3, 4):
  - `fleet_registry.RegistryError(Exception)`
  - `fleet_registry.ServiceInfo` — frozen dataclass: `name: str`, `host_port: str`, `container_port: str`, `source_file: str`, `profiles: frozenset[str]`
  - `fleet_registry.FleetRegistry` — frozen dataclass: `services: dict[str, ServiceInfo]`, `roster: frozenset[str]`, `allowed_collisions: dict[str, frozenset[str]]`
  - `fleet_registry.build(files: list[str] | None = None, overlay_path: str | None = None) -> FleetRegistry` — defaults to the real 4 fleet files and the real `fleet_overlay.yml` next to the module; accepts overrides for testing.
  - `fleet_registry.FILES` — `list[str]`, the 4 real compose file paths (module-level constant, importable so consumer scripts don't redefine it).

- [ ] **Step 1: Create the fixture compose file**

Create `.github/scripts/tests/fixtures/compose_minimal.yml`:

```yaml
services:
  service-a:
    profiles: ["agents"]
    ports:
      - "127.0.0.1:9001:8080"
  service-b:
    profiles: ["agents"]
    ports:
      - "9002:8080"
  service-c:
    profiles: ["other"]
    ports:
      - "127.0.0.1:9001:8080"
```

`service-a` uses the 3-part `BIND_IP:HOST:CONTAINER` form, `service-b` uses the
2-part `HOST:CONTAINER` form — covers both real formats in one small fixture.
`service-a` and `service-c` intentionally share host port `9001`.

- [ ] **Step 2: Create the fixture overlay files**

Create `.github/scripts/tests/fixtures/overlay_valid.yml`:

```yaml
roster:
  - service-a
  - service-b
allowed_collisions:
  "9001": [service-a, service-c]
```

Create `.github/scripts/tests/fixtures/overlay_stale_roster.yml`:

```yaml
roster:
  - service-a
  - service-does-not-exist
allowed_collisions: {}
```

Create `.github/scripts/tests/fixtures/overlay_stale_collision.yml`:

```yaml
roster:
  - service-a
allowed_collisions:
  "9001": [service-a, service-that-does-not-exist]
```

- [ ] **Step 3: Create `conftest.py` for import path resolution**

The spec says no `conftest.py` is needed for fixtures — that's still true. But
`.github/scripts/tests/` is a subdirectory of `.github/scripts/`, and pytest
does not automatically add the parent directory to `sys.path`, so `import
fleet_registry` would fail without this. Same mechanism
`agents/fleet-controller/tests/conftest.py` already uses for the same reason.

Create `.github/scripts/tests/conftest.py`:

```python
import os
import sys

# Make fleet_registry.py (one directory up) importable from this tests/
# directory — pytest does not do this automatically, same reason
# agents/fleet-controller/tests/conftest.py needs the equivalent line.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

- [ ] **Step 4: Write the failing test**

Create `.github/scripts/tests/test_fleet_registry.py`:

```python
import os

import pytest

from fleet_registry import RegistryError, build

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
COMPOSE = os.path.join(FIXTURES, "compose_minimal.yml")


def test_build_parses_both_port_string_formats():
    registry = build(
        files=[COMPOSE],
        overlay_path=os.path.join(FIXTURES, "overlay_valid.yml"),
    )
    assert registry.services["service-a"].host_port == "9001"
    assert registry.services["service-a"].container_port == "8080"
    assert registry.services["service-b"].host_port == "9002"
    assert registry.services["service-b"].container_port == "8080"


def test_build_loads_roster_and_allowed_collisions():
    registry = build(
        files=[COMPOSE],
        overlay_path=os.path.join(FIXTURES, "overlay_valid.yml"),
    )
    assert registry.roster == frozenset({"service-a", "service-b"})
    assert registry.allowed_collisions == {
        "9001": frozenset({"service-a", "service-c"})
    }


def test_build_raises_on_stale_roster_entry():
    with pytest.raises(RegistryError, match="service-does-not-exist"):
        build(
            files=[COMPOSE],
            overlay_path=os.path.join(FIXTURES, "overlay_stale_roster.yml"),
        )


def test_build_raises_on_stale_allowed_collision():
    with pytest.raises(RegistryError, match="9001"):
        build(
            files=[COMPOSE],
            overlay_path=os.path.join(FIXTURES, "overlay_stale_collision.yml"),
        )


def test_build_raises_on_multi_port_service(tmp_path):
    multi_port_compose = tmp_path / "compose_multiport.yml"
    multi_port_compose.write_text(
        "services:\n"
        "  weird-service:\n"
        "    ports:\n"
        "      - \"9001:8080\"\n"
        "      - \"9002:8081\"\n"
    )
    overlay = tmp_path / "overlay_empty.yml"
    overlay.write_text("roster: []\nallowed_collisions: {}\n")
    with pytest.raises(RegistryError, match="weird-service"):
        build(files=[str(multi_port_compose)], overlay_path=str(overlay))
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `python3 -m pytest .github/scripts/tests/test_fleet_registry.py -v` (from repo root)
Expected: FAIL/ERROR — `ModuleNotFoundError: No module named 'fleet_registry'` (the module doesn't exist yet)

- [ ] **Step 6: Implement `fleet_registry.py`**

Create `.github/scripts/fleet_registry.py`:

```python
#!/usr/bin/env python3
"""Single source of truth for the 26-agent fleet.

Parses ports/context/profiles live from the real compose files and merges
in a thin overlay (fleet_overlay.yml) for the handful of facts compose
can't express: which services count as "the fleet roster", and which port
collisions are genuinely intentional. Never writes a generated snapshot to
disk — always computed fresh from the compose files at call time.

See docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import yaml

FILES = [
    "docker-compose.agents.yml",
    "docker-compose.agents-full.yml",
    "docker-compose.bropets.yml",
    "docker-compose.brain.yml",
]

_OVERLAY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fleet_overlay.yml")


class RegistryError(Exception):
    """The overlay is syntactically fine but semantically stale: a roster
    entry or allowed-collision pair no longer matches the real compose
    files."""


@dataclass(frozen=True)
class ServiceInfo:
    name: str
    host_port: str
    container_port: str
    source_file: str
    profiles: frozenset


@dataclass(frozen=True)
class FleetRegistry:
    services: dict
    roster: frozenset
    allowed_collisions: dict


def _host_port(mapping) -> str:
    """'HOST:CONTAINER' or 'BIND_IP:HOST:CONTAINER' -> the host port field."""
    parts = str(mapping).split(":")
    return parts[-2] if len(parts) >= 2 else parts[0]


def _container_port(mapping) -> str:
    return str(mapping).split(":")[-1]


def _parse_compose_files(files):
    services = {}
    for fname in files:
        try:
            with open(fname, encoding="utf-8") as f:
                doc = yaml.safe_load(f)
        except FileNotFoundError:
            continue
        for svc, cfg in (doc.get("services") or {}).items():
            cfg = cfg or {}
            ports = cfg.get("ports") or []
            profiles = frozenset(cfg.get("profiles") or [])
            if len(ports) > 1:
                raise RegistryError(
                    f"service {svc!r} in {fname} publishes {len(ports)} ports "
                    f"({ports}) — fleet_registry.py only tracks one port per "
                    f"service; extend ServiceInfo before adding a multi-port "
                    f"fleet service"
                )
            host_port = _host_port(ports[0]) if ports else ""
            container_port = _container_port(ports[0]) if ports else ""
            services[svc] = ServiceInfo(
                name=svc,
                host_port=host_port,
                container_port=container_port,
                source_file=fname,
                profiles=profiles,
            )
    return services


def _load_overlay(path):
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    roster = frozenset(doc.get("roster") or [])
    allowed_collisions = {
        str(port): frozenset(names)
        for port, names in (doc.get("allowed_collisions") or {}).items()
    }
    return roster, allowed_collisions


def build(files: Optional[list] = None, overlay_path: Optional[str] = None) -> FleetRegistry:
    """Parse the fleet compose files + the overlay, cross-validate, return
    the merged model. Raises RegistryError on any contract violation —
    never returns a silently-partial registry."""
    files = FILES if files is None else files
    overlay_path = _OVERLAY_FILE if overlay_path is None else overlay_path

    services = _parse_compose_files(files)
    roster, allowed_collisions = _load_overlay(overlay_path)

    missing_roster = sorted(name for name in roster if name not in services)
    if missing_roster:
        raise RegistryError(
            f"roster entry {missing_roster[0]!r} not found in any fleet "
            f"compose file (checked: {', '.join(files)})"
        )

    ports_by_host = {}
    for svc in services.values():
        if svc.host_port:
            ports_by_host.setdefault(svc.host_port, set()).add(svc.name)

    for port, overlay_names in allowed_collisions.items():
        real_names = ports_by_host.get(port, set())
        if len(real_names) < 2 or not overlay_names <= real_names:
            raise RegistryError(
                f"allowed_collisions[{port!r}] names {sorted(overlay_names)} "
                f"but compose has {sorted(real_names)} service(s) on that port"
            )

    return FleetRegistry(services=services, roster=roster, allowed_collisions=allowed_collisions)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python3 -m pytest .github/scripts/tests/test_fleet_registry.py -v` (from repo root)
Expected: 5 passed

- [ ] **Step 8: Commit**

```bash
git add .github/scripts/fleet_registry.py .github/scripts/tests/
git commit -m "feat: add fleet_registry.py core module with fixture tests"
```

---

## Task 2: Real `fleet_overlay.yml` + integration tests against the live repo

**Files:**
- Create: `.github/scripts/fleet_overlay.yml`
- Test: `.github/scripts/tests/test_live_repo_integration.py`

**Interfaces:**
- Consumes: `fleet_registry.build()` (Task 1), called with no arguments so it
  reads the real files and the real overlay this task creates.

- [ ] **Step 1: Create the real overlay**

Create `.github/scripts/fleet_overlay.yml` — roster copied from the current
`EXPECTED_PORTS` dict in `check_expected_ports.py` (names only, no ports —
ports now come from `build()` parsing compose), collisions copied from
`check_duplicate_ports.py`'s current `ALLOWED_COLLISIONS`:

```yaml
# The only hand-maintained file in this system. Keep additions here to
# "which services exist" facts only — anything compose can already state
# (ports, context, profiles) belongs in the compose files, not here.
# See docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md.
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

- [ ] **Step 2: Write the integration test**

Create `.github/scripts/tests/test_live_repo_integration.py`:

```python
"""Integration tests against the REAL, live compose files + overlay — not
fixtures. This is the test that would have caught the stale :8011 bug
(frontend-specialist) before it shipped, and keeps the fixture tests honest
against reality. Must run with the repo root as the working directory —
fleet_registry.build()'s default file list is relative to CWD, matching how
the CI workflows invoke the consumer scripts."""
from fleet_registry import build


def test_build_succeeds_against_real_repo_state():
    registry = build()
    assert registry.roster, "roster should not be empty"
    assert all(name in registry.services for name in registry.roster)


def test_no_unexpected_duplicate_ports_in_real_repo_state():
    registry = build()
    ports_to_services = {}
    for svc in registry.services.values():
        if svc.host_port:
            ports_to_services.setdefault(svc.host_port, set()).add(svc.name)

    for port, names in ports_to_services.items():
        if len(names) <= 1:
            continue
        allowed = registry.allowed_collisions.get(port)
        assert allowed and names <= allowed, (
            f"unexpected duplicate port {port}: {sorted(names)} — either a "
            f"real collision needing a compose fix, or a new intentional "
            f"pair missing from fleet_overlay.yml's allowed_collisions"
        )
```

- [ ] **Step 3: Run the test — from repo root**

Run: `cd "H:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4" && python3 -m pytest .github/scripts/tests/test_live_repo_integration.py -v`
Expected: 2 passed. If either fails, the overlay copied in Step 1 has a typo
or a real port has drifted since the spec was written — fix the overlay, not
the test.

- [ ] **Step 4: Commit**

```bash
git add .github/scripts/fleet_overlay.yml .github/scripts/tests/test_live_repo_integration.py
git commit -m "feat: add real fleet_overlay.yml + live-repo integration tests"
```

---

## Task 3: Migrate `check_expected_ports.py`

**Files:**
- Modify: `.github/scripts/check_expected_ports.py`

**Interfaces:**
- Consumes: `fleet_registry.build`, `fleet_registry.RegistryError` (Task 1)

- [ ] **Step 1: Replace the file's contents**

Replace all of `.github/scripts/check_expected_ports.py` with:

```python
#!/usr/bin/env python3
"""Fail if any fleet-roster agent isn't declared in compose.

Ports, contexts, and profiles are derived live from the real compose files
by fleet_registry.py — this script only asserts every roster name from
.github/scripts/fleet_overlay.yml resolves to a real service.
See docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md.
"""
import sys

from fleet_registry import RegistryError, build


def main():
    try:
        registry = build()
    except RegistryError as e:
        print(f"FAIL: {e}")
        sys.exit(1)

    missing = [n for n in sorted(registry.roster) if n not in registry.services]
    if missing:
        print("FAIL: roster names not found (should be impossible after build() validation):")
        for n in missing:
            print(f"  {n}")
        sys.exit(1)

    print(f"PASS: all {len(registry.roster)} roster agents confirmed in compose files.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it directly to verify it still passes**

Run: `cd "H:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4" && python3 .github/scripts/check_expected_ports.py`
Expected: `PASS: all 25 roster agents confirmed in compose files.`

- [ ] **Step 3: Add the regression test for this exact script**

Add to `.github/scripts/tests/test_live_repo_integration.py`:

```python
def test_check_expected_ports_script_passes():
    import check_expected_ports

    try:
        check_expected_ports.main()
    except SystemExit as e:
        raise AssertionError(f"check_expected_ports.py failed: exit code {e.code}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "H:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4" && python3 -m pytest .github/scripts/tests/ -v`
Expected: all tests pass (8 total so far)

- [ ] **Step 5: Commit**

```bash
git add .github/scripts/check_expected_ports.py .github/scripts/tests/test_live_repo_integration.py
git commit -m "refactor: migrate check_expected_ports.py to fleet_registry"
```

---

## Task 4: Migrate `check_duplicate_ports.py`

**Files:**
- Modify: `.github/scripts/check_duplicate_ports.py`

**Interfaces:**
- Consumes: `fleet_registry.build`, `fleet_registry.RegistryError` (Task 1)

- [ ] **Step 1: Replace the file's contents**

Replace all of `.github/scripts/check_duplicate_ports.py` with:

```python
#!/usr/bin/env python3
"""Fail if two fleet services publish the same host port without an
explicit, reviewed exception.

Collisions are derived live from the real compose files by
fleet_registry.py; the intentional-collision allowlist lives in
.github/scripts/fleet_overlay.yml.
See docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md.

Used by both .github/workflows/health-check.yml and
.github/workflows/ghost-agents-build.yml — single source of truth so the
two gates can't drift out of sync with each other.
"""
import sys

from fleet_registry import RegistryError, build


def main():
    try:
        registry = build()
    except RegistryError as e:
        print(f"FAIL: {e}")
        sys.exit(1)

    ports_to_services = {}
    for svc in registry.services.values():
        if svc.host_port:
            ports_to_services.setdefault(svc.host_port, []).append(svc.name)

    errors = []
    for port, names in sorted(ports_to_services.items()):
        if len(names) <= 1:
            continue
        allowed = registry.allowed_collisions.get(port)
        if allowed and set(names) <= allowed:
            continue
        for name in sorted(names):
            source = registry.services[name].source_file
            errors.append(f"{port}: {name} ({source})")

    if errors:
        print("DUPLICATE HOST PORTS FOUND:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    total = sum(len(v) for v in ports_to_services.values())
    print(
        f"PASS: no unexpected duplicate host ports across {total} port "
        f"mappings ({len(ports_to_services)} distinct ports)."
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it directly to verify it still passes**

Run: `cd "H:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4" && python3 .github/scripts/check_duplicate_ports.py`
Expected: `PASS: no unexpected duplicate host ports across N port mappings (M distinct ports).`

- [ ] **Step 3: Add the regression test for this exact script**

Add to `.github/scripts/tests/test_live_repo_integration.py`:

```python
def test_check_duplicate_ports_script_passes():
    import check_duplicate_ports

    try:
        check_duplicate_ports.main()
    except SystemExit as e:
        raise AssertionError(f"check_duplicate_ports.py failed: exit code {e.code}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "H:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4" && python3 -m pytest .github/scripts/tests/ -v`
Expected: all tests pass (9 total)

- [ ] **Step 5: Commit**

```bash
git add .github/scripts/check_duplicate_ports.py .github/scripts/tests/test_live_repo_integration.py
git commit -m "refactor: migrate check_duplicate_ports.py to fleet_registry"
```

---

## Task 5: Final live verification against the real workflows + push

**Files:** none new — verification only.

- [ ] **Step 1: Confirm both workflow YAML files still parse cleanly**

Run:
```bash
cd "H:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4" && python3 -c "
import yaml, io
for f in ['.github/workflows/health-check.yml', '.github/workflows/ghost-agents-build.yml']:
    with io.open(f, encoding='utf-8') as fh:
        yaml.safe_load(fh)
        print(f'OK: {f}')
"
```
Expected: `OK:` for both files (neither workflow file's YAML changed this
session, but this re-confirms the 2026-08-21 CI-repair fix — see
`WHATS_DONE.md` — still holds).

- [ ] **Step 2: Run the full test suite one more time**

Run: `cd "H:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4" && python3 -m pytest .github/scripts/tests/ -v`
Expected: all 9 tests pass, 0 failures.

- [ ] **Step 3: Run both consumer scripts standalone one more time**

Run:
```bash
cd "H:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4" && \
  python3 .github/scripts/check_expected_ports.py && \
  python3 .github/scripts/check_duplicate_ports.py
```
Expected: both print `PASS:` and exit 0.

- [ ] **Step 4: Fetch, then push**

```bash
cd "H:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4"
git fetch origin
git status -sb
git push origin main
```

- [ ] **Step 5: Confirm the live workflow run on GitHub**

Run: `gh run list --workflow=health-check.yml --limit 1`
Then: `gh run view <run-id>` on that run's ID.
Expected: the run either passes fully, or fails only at the known
pre-existing GitHub Actions billing lock (`docs/NEXT_TASKS.md` "This Week"
list) — not at a workflow-file-parse error and not at either port-check
step.

- [ ] **Step 6: Update `WHATS_DONE.md`**

Add a dated entry (same voice/format as the 2026-08-21 CI-repair entry
already in the file) noting: `fleet_registry.py` built and live, both
`check_expected_ports.py`/`check_duplicate_ports.py` migrated, 9 tests
passing, `EXPECTED_PORTS`/duplicated `FILES`/`ALLOWED_COLLISIONS`
definitions deleted for good. Commit and push this too (`git add
WHATS_DONE.md && git commit -m "docs: fleet truth registry live" && git
push`).
