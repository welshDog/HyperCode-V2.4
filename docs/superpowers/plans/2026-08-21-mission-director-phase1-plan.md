# Mission Director Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship mission-director Phase 1 — a human-submitted goal becomes a
previewed, audited, human-reviewable plan, with zero possibility of live
mutation anywhere in the path.

**Architecture:** A new stateless container `agents/mission-director/`
(mirrors `agents/fleet-controller/`'s shape) turns a goal into a
`MissionProposal` via an LLM call, validates it, and previews it against
the real (unmodified) `agents/fleet-controller/` — but holds no DB
connection and no user-auth capability of its own. The two human-facing
routes (`propose`, `review`) live in the backend
(`backend/app/api/v1/endpoints/missions.py`) instead, reusing
`deps.get_current_active_user` literally, unmodified — backend calls
mission-director's unauthenticated internal `/v1/plan` route (trust
boundary = docker network, the same "containment via capability absence"
precedent `fleet-controller`'s own zero-auth route already established)
and persists the result into a new `mission_proposals` table it owns.

**Tech Stack:** FastAPI + Pydantic v2 + httpx (mission-director container);
FastAPI + SQLAlchemy + Alembic (backend, existing stack); `anthropic`
AsyncAnthropic tool-use for forced structured output.

**Spec:** `docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md`

## Deviations from the spec (ruled during planning, recorded — not silent)

The spec's §2/§4/§9 describe the two human-facing routes
(`POST /v1/missions/propose`, `POST /v1/missions/{id}/review`) as living
*inside* `agents/mission-director/main.py`, gated directly by
`Depends(deps.get_current_active_user)`. That dependency requires a live
SQLAlchemy `Session` and a real DB lookup + `is_active` check
(`backend/app/api/deps.py:22-54`) — it is not portable into a separate
container without dragging in the backend's full DB layer, and no agent
container in this repo does real JWT verification today (confirmed via
repo-wide grep before planning). Two structural changes follow, both
preserving every one of the spec's actual guarantees (human-authed only,
server-controlled state machine, zero live mutation, one ledger write per
terminal event):

1. **The two human-facing routes move to
   `backend/app/api/v1/endpoints/missions.py`.** They reuse
   `get_current_active_user` exactly as spec intended — same process, same
   DB session, zero reimplementation — just declared where that dependency
   actually lives. `agents/mission-director/main.py` keeps a single route,
   `POST /v1/plan`, unauthenticated — same trust model
   `fleet-controller`'s own `/v1/plans/preview` already uses (containment
   via capability absence, not access control).
2. **`mission_proposals` is a backend-owned table, not a table
   mission-director connects to directly.** mission-director stays fully
   stateless (matches fleet-controller's precedent of zero persistence);
   backend persists the row after calling mission-director, and owns the
   review endpoint's point-lookup + status transition entirely in-process
   (no second call to mission-director for review — spec §5 already says
   "approving performs nothing live," so there is nothing for
   mission-director to do at review time). mission-director keeps its own
   fire-and-forget Governance Ledger write for the `propose`-time terminal
   event (mirrors `fleet-controller/ledger_client.py` exactly); the
   `review`-time ledger write happens directly from backend, which already
   holds a DB session in every request (same pattern `governance.py`'s
   `write_ledger` already uses).

A consequence not covered by the spec's original error table: backend
calling mission-director can itself fail (network/timeout/non-200). This
is treated with the same philosophy the spec applies to
mission-director-calling-fleet-controller: `preview_unavailable`, an
infrastructure failure, not a plan-quality failure.

## Global Constraints

- Python indent: 4 spaces, never mixed (Sacred Rule).
- `.env` / secrets never committed to git.
- `git fetch` before any push (parallel auto-commit workflow this session
  has already used 5+ times).
- No cross-agent package imports — every schema/pattern used from another
  agent's code is copied by file, not imported across a container boundary
  (existing repo convention, named explicitly in the spec's §2).
- Every new agent's compose block gets `deploy.resources.limits: {memory:
  256m, cpus: "0.25"}` (repo-wide rule, `CLAUDE.md`).
- `execution.performed` must be `False` down every single code path in
  this feature — no exceptions, this is the whole point of Phase 1.
- Resolve worktree question the same way this session's truth-registry
  work did: skip an isolated git worktree, work directly on `main` with
  the existing fetch-before-push workflow (ruling already made and used
  this session, recorded in `WHATS_DONE.md`'s 2026-08-21 truth-registry
  entry).
- Alembic head going into this plan is `019` (`019_agent_policy_schema.py`)
  — verified via `backend/alembic/versions/` listing before writing this
  plan. The new migration is `020`, `down_revision = "019"`. Two
  migrations claiming the same revision id broke `upgrade head` once
  already (2026-08-15, `019`'s own docstring) — do not repeat it.

---

### Task 1: `mission_proposals` table — migration, model, store

**Files:**
- Create: `backend/alembic/versions/020_add_mission_proposals.py`
- Create: `backend/app/models/mission.py`
- Create: `backend/app/services/mission_store.py`
- Modify: `backend/app/db/base.py` (register the model, same pattern as
  every other model in that file)
- Test: `backend/tests/test_mission_store.py`

**Interfaces:**
- Produces: `app.models.mission.MissionProposal` (SQLAlchemy model, table
  `mission_proposals`); `app.services.mission_store.create(db, *,
  mission_id, status, goal, truth_snapshot_ref, plan, plan_response,
  superseded_from=None) -> MissionProposal`; `mission_store.get_by_id(db,
  mission_id) -> Optional[MissionProposal]`; `mission_store.update_status(db,
  mission_id, new_status) -> Optional[MissionProposal]`.
- Consumes: `backend/app/db/base_class.py`'s `Base`, `backend/tests/conftest.py`'s
  existing `db` fixture (in-memory SQLite, `Base.metadata.create_all()`
  per test).

- [ ] **Step 1: Write the migration**

```python
# backend/alembic/versions/020_add_mission_proposals.py
"""Add mission_proposals table (Mission Director Phase 1)

Revision ID: 020
Revises: 019
Create Date: 2026-08-21

Backend-owned point-lookup store for mission-director's propose/review
flow -- NOT the audit trail (that's governance_ledger, untouched here).
See docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md §6.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mission_proposals",
        sa.Column("mission_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("truth_snapshot_ref", sa.Text(), nullable=True),
        sa.Column("plan", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("plan_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("superseded_from", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_mission_proposals_status", "mission_proposals", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_mission_proposals_status", table_name="mission_proposals")
    op.drop_table("mission_proposals")
```

- [ ] **Step 2: Write the model**

```python
# backend/app/models/mission.py
"""MissionProposal model -- Mission Director Phase 1's own operational
current-state store (point-lookup for the review endpoint's precondition
check). NOT a replacement for the Governance Ledger, which stays the
permanent, append-only audit trail. See
docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md §6.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base_class import Base


class MissionProposal(Base):
    __tablename__ = "mission_proposals"

    mission_id: Mapped[str] = mapped_column(Text, primary_key=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    truth_snapshot_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB().with_variant(SQLiteJSON(), "sqlite"), nullable=True
    )
    plan_response: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB().with_variant(SQLiteJSON(), "sqlite"), nullable=True
    )
    superseded_from: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 3: Register the model in `app/db/base.py`**

Add, alphabetically-with-the-rest-of-the-file placement is fine (match
existing style — each import gets an inline comment naming its phase):

```python
from app.models.mission import MissionProposal  # Mission Director Phase 1
```

And add `"MissionProposal"` to the `__all__` list.

- [ ] **Step 4: Write the store**

```python
# backend/app/services/mission_store.py
"""CRUD for mission_proposals -- Mission Director Phase 1's point-lookup
store. Every write here is paired with a Governance Ledger write at the
call site (missions.py endpoint); this module only owns current-state,
never the audit trail. See
docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md §6.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.mission import MissionProposal


def create(
    db: Session,
    *,
    mission_id: str,
    status: str,
    goal: str,
    truth_snapshot_ref: Optional[str],
    plan: Optional[dict[str, Any]],
    plan_response: Optional[dict[str, Any]],
    superseded_from: Optional[str] = None,
) -> MissionProposal:
    row = MissionProposal(
        mission_id=mission_id,
        status=status,
        goal=goal,
        truth_snapshot_ref=truth_snapshot_ref,
        plan=plan,
        plan_response=plan_response,
        superseded_from=superseded_from,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_by_id(db: Session, mission_id: str) -> Optional[MissionProposal]:
    return db.query(MissionProposal).filter(MissionProposal.mission_id == mission_id).first()


def update_status(db: Session, mission_id: str, new_status: str) -> Optional[MissionProposal]:
    row = get_by_id(db, mission_id)
    if row is None:
        return None
    row.status = new_status
    db.commit()
    db.refresh(row)
    return row
```

- [ ] **Step 5: Write the tests**

```python
# backend/tests/test_mission_store.py
from sqlalchemy.orm import Session

from app.services import mission_store


def test_create_and_get_round_trip(db: Session):
    row = mission_store.create(
        db,
        mission_id="mission_test001",
        status="previewed",
        goal="test goal",
        truth_snapshot_ref="sha256:abc",
        plan={"schema_version": 1, "requested_actions": []},
        plan_response={"plan_id": "plan_x", "safety": {"decision": "ALLOW"}},
    )
    assert row.mission_id == "mission_test001"

    fetched = mission_store.get_by_id(db, "mission_test001")
    assert fetched is not None
    assert fetched.status == "previewed"
    assert fetched.goal == "test goal"
    assert fetched.plan == {"schema_version": 1, "requested_actions": []}


def test_get_by_id_missing_returns_none(db: Session):
    assert mission_store.get_by_id(db, "does-not-exist") is None


def test_update_status_transitions_and_persists(db: Session):
    mission_store.create(
        db,
        mission_id="mission_test002",
        status="previewed",
        goal="g",
        truth_snapshot_ref="sha256:abc",
        plan=None,
        plan_response=None,
    )
    updated = mission_store.update_status(db, "mission_test002", "approved")
    assert updated is not None
    assert updated.status == "approved"

    refetched = mission_store.get_by_id(db, "mission_test002")
    assert refetched.status == "approved"


def test_update_status_missing_returns_none(db: Session):
    assert mission_store.update_status(db, "nope", "approved") is None


def test_superseded_from_stored(db: Session):
    row = mission_store.create(
        db,
        mission_id="mission_test003",
        status="proposed",
        goal="g2",
        truth_snapshot_ref=None,
        plan=None,
        plan_response=None,
        superseded_from="mission_test001",
    )
    assert row.superseded_from == "mission_test001"
```

- [ ] **Step 6: Run the tests**

Run: `cd backend && python -m pytest tests/test_mission_store.py -v`
Expected: 5/5 PASS

- [ ] **Step 7: Commit**

```bash
git add backend/alembic/versions/020_add_mission_proposals.py backend/app/models/mission.py backend/app/services/mission_store.py backend/app/db/base.py backend/tests/test_mission_store.py
git commit -m "feat(mission-director): add mission_proposals table, model, store"
```

---

### Task 2: `agents/mission-director/` scaffold — models, local validator, truth snapshot

**Files:**
- Create: `agents/mission-director/models.py`
- Create: `agents/mission-director/local_validator.py`
- Create: `agents/mission-director/truth_snapshot.py`
- Create: `agents/mission-director/Dockerfile`
- Create: `agents/mission-director/requirements.txt`
- Create: `agents/mission-director/main.py` (health-only for this task —
  Task 3 adds the real route)
- Create: `agents/mission-director/tests/conftest.py`
- Test: `agents/mission-director/tests/test_models.py`
- Test: `agents/mission-director/tests/test_local_validator.py`
- Test: `agents/mission-director/tests/test_truth_snapshot.py`

**Interfaces:**
- Consumes: `agents/fleet-controller/models.py`'s `PlanRequest`,
  `RequestedAction`, `Constraints`, `PlanResponse`, `canonical_hash` — file
  copy, not import (repo convention). `.github/scripts/fleet_registry.py`'s
  `build(files, overlay_path) -> FleetRegistry` and `RegistryError` — also
  file copy, vendored into this container's image so it's importable at
  build/runtime; the actual compose files + overlay it reads are supplied
  at container runtime via bind mounts wired in Task 6, not baked into the
  image.
- Produces: `models.MissionProposal` (pydantic, includes `plan_response:
  Optional[PlanResponse] = None` — spec's §2 code sample doesn't list this
  field explicitly, but §4/§6 both require `plan_response` to travel with
  the proposal, and the `mission_proposals` table already has a column for
  it; treating the sample as illustrative, not exhaustive, per this plan's
  Global Constraints); `models.ReviewDecision` (pydantic: `decision:
  Literal["approve", "reject"]`); `local_validator.validate(plan:
  PlanRequest, truth_snapshot_ref: Optional[str]) -> None`, raises
  `local_validator.LocalValidationError(detail: str)`;
  `truth_snapshot.get_snapshot_ref() -> str`, raises on registry failure
  (never swallows — caller decides the terminal state).

- [ ] **Step 1: Vendor fleet-controller's models as this container's `models.py`**

Copy `agents/fleet-controller/models.py` verbatim as the starting point
(same file-copy convention the spec names), then extend it with the two
new types this phase adds:

```python
# agents/mission-director/models.py
"""
Plan schema for mission-director Phase 1.

RequestedAction/Constraints/PlanRequest/PlanResponse/canonical_hash are a
file copy of agents/fleet-controller/models.py, byte-for-byte on the
shared types -- no cross-agent package imports in this repo (see
docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md §2).
Keep these two files' shared types in sync by hand if fleet-controller's
schema ever changes.
"""
from __future__ import annotations

import hashlib
import json
from typing import Literal, Optional

from pydantic import BaseModel, Field


class RequestedAction(BaseModel):
    action_id: str
    kind: Literal["compose_profile.preview", "crew.workflow.preview"]
    profile: Optional[str] = None


class Constraints(BaseModel):
    max_services: int = 25
    allow_profiles: list[str] = Field(default_factory=list)
    deny_profiles: list[str] = Field(default_factory=list)


class PlanRequest(BaseModel):
    schema_version: Literal[1]
    mission_id: str
    requested_actions: list[RequestedAction]
    constraints: Constraints = Field(default_factory=Constraints)


class SafetyView(BaseModel):
    decision: str
    reason: str
    rule: Optional[str] = None
    category: Optional[str] = None
    shepherd_available: bool = True


class ExecutionView(BaseModel):
    performed: bool = False
    would_execute: list[str] = Field(default_factory=list)


class PlanResponse(BaseModel):
    plan_id: str
    plan_hash: str
    mode: Literal["DRY_RUN"] = "DRY_RUN"
    safety: SafetyView
    execution: ExecutionView
    capability: Optional[str] = None


def canonical_hash(plan: PlanRequest) -> str:
    """sha256 over canonical (sorted-key, whitespace-free) JSON. Identical
    convention to fleet-controller/models.py's canonical_hash -- kept
    dependency-free (stdlib only) so both copies stay trivially
    comparable."""
    canonical = json.dumps(plan.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


# ---- Mission Director additions (Phase 1) ----


class MissionProposal(BaseModel):
    schema_version: Literal[1]
    mission_id: str
    goal: str
    truth_snapshot_ref: Optional[str] = None
    rationale: Optional[str] = None
    plan: Optional[PlanRequest] = None
    plan_response: Optional[PlanResponse] = None
    status: Literal[
        "proposed",
        "previewed",
        "approved",
        "rejected",
        "preview_unavailable",
        "rejected_malformed",
    ]
    superseded_from: Optional[str] = None


class ReviewDecision(BaseModel):
    decision: Literal["approve", "reject"]
```

- [ ] **Step 2: Write `local_validator.py`**

```python
# agents/mission-director/local_validator.py
"""
Fast, deterministic well-formedness gate -- NOT a safety decision. Every
actual safety judgment (dangerous categories, profile denials) stays
inside fleet-controller's boundary (plan_validator.py, Safety Shepherd's
policy.py), both untouched by this module. This exists only to avoid
spending a network round-trip on garbage before calling fleet-controller.
See docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md §3.
"""
from __future__ import annotations

from typing import Optional

from models import PlanRequest


class LocalValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def validate(plan: PlanRequest, truth_snapshot_ref: Optional[str]) -> None:
    if not plan.requested_actions:
        raise LocalValidationError("plan.requested_actions must be non-empty")
    if not truth_snapshot_ref:
        raise LocalValidationError("truth_snapshot_ref is required and must be non-empty")
```

- [ ] **Step 3: Write `truth_snapshot.py`**

```python
# agents/mission-director/truth_snapshot.py
"""
Produces the truth_snapshot_ref a MissionProposal is grounded against --
a deterministic hash of the live fleet registry, same canonical-hash
convention as models.canonical_hash (sorted-key, whitespace-free JSON,
sha256: prefix). Never caches: computed fresh on every call, matching
fleet_registry.py's own "never writes a generated snapshot to disk"
design note.

fleet_registry.py + fleet_overlay.yml + the 4 fleet compose files are
bind-mounted read-only into this container at /app/truth/ (wired in
docker-compose.agents-full.yml, Task 6) -- they are NOT baked into the
image, so the snapshot always reflects the live repo state, not a
build-time copy.
"""
from __future__ import annotations

import hashlib
import json
import sys

sys.path.insert(0, "/app/truth")

from fleet_registry import FleetRegistry, RegistryError, build  # noqa: E402

_MOUNT_DIR = "/app/truth"
_FILES = [
    f"{_MOUNT_DIR}/docker-compose.agents.yml",
    f"{_MOUNT_DIR}/docker-compose.agents-full.yml",
    f"{_MOUNT_DIR}/docker-compose.bropets.yml",
    f"{_MOUNT_DIR}/docker-compose.brain.yml",
]
_OVERLAY = f"{_MOUNT_DIR}/fleet_overlay.yml"


def _canonical_dict(registry: FleetRegistry) -> dict:
    return {
        "services": {
            name: {
                "host_port": svc.host_port,
                "container_port": svc.container_port,
                "source_file": svc.source_file,
                "profiles": sorted(svc.profiles),
            }
            for name, svc in sorted(registry.services.items())
        },
        "roster": sorted(registry.roster),
        "allowed_collisions": {
            port: sorted(names) for port, names in sorted(registry.allowed_collisions.items())
        },
    }


def get_snapshot_ref(files: list[str] | None = None, overlay_path: str | None = None) -> str:
    """Raises RegistryError / FileNotFoundError on any registry failure --
    never swallowed here. The caller (main.py) decides the terminal state
    (preview_unavailable) before ever calling the LLM or fleet-controller."""
    registry = build(files=files or _FILES, overlay_path=overlay_path or _OVERLAY)
    canonical = json.dumps(_canonical_dict(registry), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
```

- [ ] **Step 4: Write `Dockerfile`**

```dockerfile
# agents/mission-director/Dockerfile
# Mission Director -- Phase 1. Turns a human goal into a previewed,
# reviewable plan. Holds no DB connection, no user-auth capability, no
# mutation authority anywhere in this image -- see
# docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md

# ========================================
# Stage 1: Builder
# ========================================
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update --allow-releaseinfo-change && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# ========================================
# Stage 2: Runtime
# ========================================
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update --allow-releaseinfo-change && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libexpat1 \
        openssl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN pip install --upgrade --no-cache-dir \
    "pip==26.0.1" \
    "setuptools>=80.0.0" \
    "wheel==0.46.2" \
    "jaraco.context>=6.0.0" \
    "jaraco.functools>=4.1.0" \
    "jaraco.text>=4.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AGENT_NAME=mission-director \
    AGENT_PORT=8080

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY main.py .
COPY models.py .
COPY local_validator.py .
COPY truth_snapshot.py .
COPY plan_generator.py .
COPY fleet_client.py .
COPY ledger_client.py .

# Non-root user -- security hardening
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:${AGENT_PORT}/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

Note: this `COPY`s `plan_generator.py`, `fleet_client.py`,
`ledger_client.py` too — they don't exist until Task 3, but writing the
Dockerfile once, complete, is simpler than editing it twice. Docker build
will fail on this task until Task 3 lands; **Step 6 below builds with a
temporary empty stub for each of those three files, deleted at the end of
this task's Step 7** so the image proves out `models.py` /
`local_validator.py` / `truth_snapshot.py` wiring now, without blocking
on Task 3.

- [ ] **Step 5: Write `requirements.txt`**

```
fastapi>=0.136.1
uvicorn[standard]>=0.27.0
pydantic>=2.11.9,<2.13.0
httpx>=0.28.1
anthropic>=0.25.0
pyyaml>=6.0
```

(`pyyaml` is new relative to fleet-controller's requirements — needed by
the vendored `fleet_registry.py`, which fleet-controller's image never
needed.)

- [ ] **Step 6: Write `main.py` (health-only) + vendor `fleet_registry.py`**

```python
# agents/mission-director/main.py
"""
mission-director -- Phase 1.

Health-only in this task; POST /v1/plan lands in Task 3. See
docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md
"""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="mission-director", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "agent": "mission-director"}
```

Copy `.github/scripts/fleet_registry.py` verbatim to
`agents/mission-director/fleet_registry.py` — this is the vendored copy
the Dockerfile needs to `COPY` and `truth_snapshot.py` needs to import
(via the `/app/truth` mount at runtime, but it also needs to exist as an
importable module in the image itself since `truth_snapshot.py`'s
`sys.path.insert(0, "/app/truth")` only helps once the compose bind mount
is live — Task 6). Add one more `COPY fleet_registry.py .` line to the
Dockerfile written in Step 4, right after `COPY truth_snapshot.py .`.

- [ ] **Step 7: Standalone docker build + health check verification**

```bash
cd agents/mission-director
# temporary stubs so the Dockerfile's COPY lines succeed before Task 3:
echo "" > plan_generator.py
echo "" > fleet_client.py
echo "" > ledger_client.py

docker build -t mission-director-test .
docker run -d --name mission-director-test -p 18097:8080 mission-director-test
sleep 3
curl -f http://localhost:18097/health
# Expected: {"status":"healthy","agent":"mission-director"}
docker stop mission-director-test && docker rm mission-director-test

# remove the temporary stubs -- Task 3 creates the real files
rm plan_generator.py fleet_client.py ledger_client.py
cd ../..
```

- [ ] **Step 8: Write `tests/conftest.py`**

```python
# agents/mission-director/tests/conftest.py
import os
import sys

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest_asyncio.fixture
async def client():
    import main

    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 9: Write `tests/test_models.py`**

```python
# agents/mission-director/tests/test_models.py
import pytest
from pydantic import ValidationError

from models import MissionProposal, PlanRequest, ReviewDecision


def test_mission_proposal_minimal_valid():
    proposal = MissionProposal(
        schema_version=1,
        mission_id="mission_abc123",
        goal="do the thing",
        status="proposed",
    )
    assert proposal.status == "proposed"
    assert proposal.plan is None


def test_mission_proposal_rejects_unknown_status():
    with pytest.raises(ValidationError):
        MissionProposal(
            schema_version=1,
            mission_id="mission_abc123",
            goal="do the thing",
            status="not_a_real_status",
        )


def test_mission_proposal_full_shape():
    plan = PlanRequest(schema_version=1, mission_id="mission_abc123", requested_actions=[])
    proposal = MissionProposal(
        schema_version=1,
        mission_id="mission_abc123",
        goal="do the thing",
        truth_snapshot_ref="sha256:abc",
        rationale="because",
        plan=plan,
        status="previewed",
    )
    assert proposal.plan.mission_id == "mission_abc123"


def test_review_decision_accepts_approve_and_reject():
    assert ReviewDecision(decision="approve").decision == "approve"
    assert ReviewDecision(decision="reject").decision == "reject"


def test_review_decision_rejects_other_values():
    with pytest.raises(ValidationError):
        ReviewDecision(decision="maybe")
```

- [ ] **Step 10: Write `tests/test_local_validator.py`**

```python
# agents/mission-director/tests/test_local_validator.py
import pytest

from local_validator import LocalValidationError, validate
from models import PlanRequest, RequestedAction


def _plan(actions):
    return PlanRequest(schema_version=1, mission_id="mission_x", requested_actions=actions)


def test_validate_passes_with_actions_and_snapshot_ref():
    plan = _plan([RequestedAction(action_id="a1", kind="compose_profile.preview")])
    validate(plan, "sha256:abc")  # no raise


def test_validate_rejects_empty_actions():
    plan = _plan([])
    with pytest.raises(LocalValidationError, match="requested_actions"):
        validate(plan, "sha256:abc")


def test_validate_rejects_missing_snapshot_ref():
    plan = _plan([RequestedAction(action_id="a1", kind="compose_profile.preview")])
    with pytest.raises(LocalValidationError, match="truth_snapshot_ref"):
        validate(plan, None)


def test_validate_rejects_empty_snapshot_ref():
    plan = _plan([RequestedAction(action_id="a1", kind="compose_profile.preview")])
    with pytest.raises(LocalValidationError, match="truth_snapshot_ref"):
        validate(plan, "")
```

- [ ] **Step 11: Write `tests/test_truth_snapshot.py`**

Use temp fixture files (not the runtime `/app/truth` mount) — mirrors
`.github/scripts/tests/test_fleet_registry.py`'s own fixture pattern.

```python
# agents/mission-director/tests/test_truth_snapshot.py
import pytest

from fleet_registry import RegistryError
from truth_snapshot import get_snapshot_ref


COMPOSE = """
services:
  service-a:
    ports:
      - "9001:8080"
"""

OVERLAY_VALID = """
roster:
  - service-a
allowed_collisions: {}
"""

OVERLAY_STALE = """
roster:
  - service-does-not-exist
allowed_collisions: {}
"""


def test_snapshot_ref_is_deterministic(tmp_path):
    compose_file = tmp_path / "compose.yml"
    compose_file.write_text(COMPOSE)
    overlay_file = tmp_path / "overlay.yml"
    overlay_file.write_text(OVERLAY_VALID)

    ref1 = get_snapshot_ref(files=[str(compose_file)], overlay_path=str(overlay_file))
    ref2 = get_snapshot_ref(files=[str(compose_file)], overlay_path=str(overlay_file))
    assert ref1 == ref2
    assert ref1.startswith("sha256:")


def test_snapshot_ref_changes_when_registry_changes(tmp_path):
    compose_file = tmp_path / "compose.yml"
    compose_file.write_text(COMPOSE)
    overlay_file = tmp_path / "overlay.yml"
    overlay_file.write_text(OVERLAY_VALID)
    ref_before = get_snapshot_ref(files=[str(compose_file)], overlay_path=str(overlay_file))

    compose_file.write_text(COMPOSE + "\n  service-b:\n    ports:\n      - \"9002:8080\"\n")
    ref_after = get_snapshot_ref(files=[str(compose_file)], overlay_path=str(overlay_file))
    assert ref_before != ref_after


def test_snapshot_ref_raises_on_stale_overlay(tmp_path):
    compose_file = tmp_path / "compose.yml"
    compose_file.write_text(COMPOSE)
    overlay_file = tmp_path / "overlay.yml"
    overlay_file.write_text(OVERLAY_STALE)

    with pytest.raises(RegistryError):
        get_snapshot_ref(files=[str(compose_file)], overlay_path=str(overlay_file))
```

- [ ] **Step 12: Run all tests**

Run: `cd agents/mission-director && python -m pytest tests/ -v`
Expected: 12/12 PASS (5 models + 4 local_validator + 3 truth_snapshot)

- [ ] **Step 13: Commit**

```bash
git add agents/mission-director/
git commit -m "feat(mission-director): scaffold models, local validator, truth snapshot"
```

---

### Task 3: LLM plan generation + fleet-controller preview + ledger write

**Files:**
- Create: `agents/mission-director/plan_generator.py`
- Create: `agents/mission-director/fleet_client.py`
- Create: `agents/mission-director/ledger_client.py`
- Modify: `agents/mission-director/main.py` (add `POST /v1/plan`, lifespan)
- Test: `agents/mission-director/tests/test_llm_malformed_output.py`
- Test: `agents/mission-director/tests/test_fleet_controller_unavailable.py`
- Test: `agents/mission-director/tests/test_no_execution.py`

**Interfaces:**
- Consumes: Task 2's `models.MissionProposal`, `models.PlanRequest`,
  `models.Constraints`, `models.canonical_hash`,
  `local_validator.validate`/`LocalValidationError`,
  `truth_snapshot.get_snapshot_ref`.
- Produces: `plan_generator.generate(goal: str) -> LLMPlanOutput` (pydantic:
  `rationale: str`, `requested_actions: list[RequestedAction]`), raises
  `plan_generator.PlanGenerationError` (infra failure) or
  `plan_generator.PlanMalformedError` (bad LLM output);
  `plan_generator.init()`/`aclose()` (lifespan hooks, mirrors
  `ledger_client.init()`'s pattern below); `fleet_client.preview(plan:
  PlanRequest) -> PlanResponse`, raises
  `fleet_client.FleetControllerUnavailable`; `ledger_client.init()`,
  `ledger_client.aclose()`, `ledger_client.record_proposal(proposal:
  MissionProposal) -> None` (fire-and-forget, never awaited from the
  request path).

- [ ] **Step 1: Write `plan_generator.py`**

```python
# agents/mission-director/plan_generator.py
"""
LLM call -> forced structured output -> MissionProposal's plan-generation
inputs. Uses Anthropic tool-use with tool_choice pinned to a single tool,
so a well-formed response is either exactly the shape we asked for or the
call fails outright -- never a free-text response to parse. Same
Anthropic->client pattern as agents/09-tips-tricks-writer/base_agent.py's
_build_llm_client, scoped down: this agent has no Ollama fallback, because
a plan proposal with no real reasoning behind it is worse than a clear
"LLM unavailable" (PlanGenerationError -> preview_unavailable) --
Ollama-fallback silence would look like a considered plan.
"""
from __future__ import annotations

import os
from typing import Optional

from pydantic import BaseModel, ValidationError

from models import RequestedAction

_TOOL_NAME = "submit_plan"

_TOOL_SCHEMA = {
    "name": _TOOL_NAME,
    "description": "Submit a proposed DRY-RUN infrastructure-change plan for the given goal.",
    "input_schema": {
        "type": "object",
        "properties": {
            "rationale": {
                "type": "string",
                "description": "Why this plan addresses the goal. Advisory reasoning only, never validated as fact.",
            },
            "requested_actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action_id": {"type": "string"},
                        "kind": {
                            "type": "string",
                            "enum": ["compose_profile.preview", "crew.workflow.preview"],
                        },
                        "profile": {"type": ["string", "null"]},
                    },
                    "required": ["action_id", "kind"],
                },
            },
        },
        "required": ["rationale", "requested_actions"],
    },
}

_SYSTEM_PROMPT = (
    "You are mission-director's planner. Given a human goal, propose a "
    "DRY-RUN infrastructure-change plan using only the action kinds "
    "'compose_profile.preview' or 'crew.workflow.preview'. You have zero "
    "execution authority -- this produces a preview proposal only, "
    "reviewed by a human before anything else can ever happen. Always "
    "call submit_plan with your answer."
)


class LLMPlanOutput(BaseModel):
    rationale: str
    requested_actions: list[RequestedAction]


class PlanGenerationError(Exception):
    """The LLM call failed outright (timeout, API error, no client
    configured) -- an infrastructure failure, not a plan-quality failure.
    Caller maps this to status=preview_unavailable."""


class PlanMalformedError(Exception):
    """The LLM responded but its output didn't validate against
    LLMPlanOutput. Caller maps this to status=rejected_malformed -- never
    coerced, never auto-retried."""


_client = None


def init() -> None:
    """Create the Anthropic client if ANTHROPIC_API_KEY is configured.
    Call from lifespan startup. Leaves _client None otherwise -- generate()
    then always raises PlanGenerationError, fail-closed by omission."""
    global _client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return
    from anthropic import AsyncAnthropic

    _client = AsyncAnthropic(api_key=api_key)


async def aclose() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def generate(goal: str) -> LLMPlanOutput:
    if _client is None:
        raise PlanGenerationError("no LLM client configured (set ANTHROPIC_API_KEY)")

    try:
        resp = await _client.messages.create(
            model=os.getenv("AGENT_MODEL", "claude-sonnet-4-6"),
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": goal}],
            tools=[_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
        )
    except Exception as exc:
        raise PlanGenerationError(str(exc)) from exc

    tool_use = next((b for b in resp.content if getattr(b, "type", None) == "tool_use"), None)
    if tool_use is None:
        raise PlanMalformedError("no tool_use block in LLM response")

    try:
        return LLMPlanOutput(**tool_use.input)
    except ValidationError as exc:
        raise PlanMalformedError(str(exc)) from exc
```

- [ ] **Step 2: Write `fleet_client.py`**

```python
# agents/mission-director/fleet_client.py
"""
Thin httpx client for fleet-controller's existing, unmodified
POST /v1/plans/preview. Fails closed the same way safety_client.py in
agents/fleet-controller does -- any network/parse failure raises
FleetControllerUnavailable, caller maps that to preview_unavailable.
Deliberately no retry logic: a flaky preview call is exactly the kind of
"infrastructure failure, not a plan-quality failure" the spec's error
table already names.
"""
from __future__ import annotations

import os
from typing import Optional

import httpx

from models import PlanRequest, PlanResponse

_client: Optional[httpx.AsyncClient] = None


class FleetControllerUnavailable(Exception):
    pass


def _url() -> str:
    return (os.getenv("FLEET_CONTROLLER_URL") or "http://fleet-controller:8080").rstrip("/")


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=5.0)
    return _client


async def aclose() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def preview(plan: PlanRequest) -> PlanResponse:
    try:
        resp = await _get_client().post(
            f"{_url()}/v1/plans/preview", json=plan.model_dump(mode="json")
        )
    except Exception as exc:
        raise FleetControllerUnavailable(str(exc)) from exc

    if resp.status_code != 200:
        raise FleetControllerUnavailable(f"fleet-controller returned {resp.status_code}")

    try:
        return PlanResponse(**resp.json())
    except Exception as exc:
        raise FleetControllerUnavailable(f"malformed PlanResponse: {exc}") from exc
```

- [ ] **Step 3: Write `ledger_client.py`**

Byte-for-byte the same pattern as `agents/fleet-controller/ledger_client.py`,
retargeted to `MissionProposal`:

```python
# agents/mission-director/ledger_client.py
"""
Fire-and-forget Governance Ledger write, mirroring
agents/fleet-controller/ledger_client.py exactly: never awaited from the
request path, never raises, never affects status or execution.performed.
A slow or down hypercode-core must not add latency or a failure mode to
mission-director's response path.

Silently disabled (no-op) if CORE_AGENT_KEY isn't configured -- expected
until this agent's scoped key is provisioned (Task 5).
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx

from models import MissionProposal

LEDGER_PATH = "/api/v1/governance/ledger"

_client: Optional[httpx.AsyncClient] = None
_tasks: set[asyncio.Task] = set()


def init() -> None:
    global _client
    key = (os.getenv("CORE_AGENT_KEY") or "").strip()
    if not key:
        return
    core_url = (os.getenv("CORE_URL") or "http://hypercode-core:8000").rstrip("/")
    _client = httpx.AsyncClient(base_url=core_url, timeout=3.0, headers={"X-Agent-Key": key})


async def aclose() -> None:
    global _client
    for task in list(_tasks):
        task.cancel()
    if _client is not None:
        await _client.aclose()
        _client = None


async def _write(proposal: MissionProposal) -> None:
    client = _client
    if client is None:
        return
    body = {
        "agent": "mission-director",
        "action": "mission.propose",
        "decision": proposal.status,
        "user_id": "system",
        "payload": proposal.model_dump(mode="json"),
    }
    try:
        await client.post(LEDGER_PATH, json=body)
    except Exception:
        pass  # fail-soft by design


def record_proposal(proposal: MissionProposal) -> None:
    """Fire-and-forget. Never call `await` on this."""
    if _client is None:
        return
    task = asyncio.create_task(_write(proposal))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
```

- [ ] **Step 4: Wire `main.py`'s `POST /v1/plan`**

```python
# agents/mission-director/main.py
"""
mission-director -- Phase 1.

POST /v1/plan turns a goal into a previewed (or terminally-failed)
MissionProposal. Unauthenticated by design -- same trust model
fleet-controller's own /v1/plans/preview uses (containment via capability
absence, not access control); the human-auth boundary lives in
backend/app/api/v1/endpoints/missions.py (Task 4), the only sanctioned
caller. See
docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md
and this plan's "Deviations from the spec" section.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from pydantic import BaseModel

import fleet_client
import ledger_client
import plan_generator
from local_validator import LocalValidationError, validate
from models import Constraints, MissionProposal, PlanRequest
from truth_snapshot import get_snapshot_ref


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    plan_generator.init()
    ledger_client.init()
    try:
        yield
    finally:
        await plan_generator.aclose()
        await fleet_client.aclose()
        await ledger_client.aclose()


app = FastAPI(title="mission-director", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "agent": "mission-director"}


class PlanGoalRequest(BaseModel):
    mission_id: str
    goal: str


def _terminal(
    mission_id: str,
    goal: str,
    truth_snapshot_ref: str | None,
    status: str,
    plan: PlanRequest | None = None,
    rationale: str | None = None,
) -> MissionProposal:
    proposal = MissionProposal(
        schema_version=1,
        mission_id=mission_id,
        goal=goal,
        truth_snapshot_ref=truth_snapshot_ref,
        rationale=rationale,
        plan=plan,
        plan_response=None,
        status=status,
    )
    ledger_client.record_proposal(proposal)  # fire-and-forget, not awaited
    return proposal


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

    try:
        validate(plan_request, snapshot_ref)
    except LocalValidationError:
        return _terminal(
            mission_id, goal, snapshot_ref, "rejected_malformed", plan_request, llm_output.rationale
        )

    try:
        plan_response = await fleet_client.preview(plan_request)
    except fleet_client.FleetControllerUnavailable:
        return _terminal(
            mission_id, goal, snapshot_ref, "preview_unavailable", plan_request, llm_output.rationale
        )

    proposal = MissionProposal(
        schema_version=1,
        mission_id=mission_id,
        goal=goal,
        truth_snapshot_ref=snapshot_ref,
        rationale=llm_output.rationale,
        plan=plan_request,
        plan_response=plan_response,
        status="previewed",
    )
    ledger_client.record_proposal(proposal)
    return proposal
```

- [ ] **Step 5: Write `tests/test_llm_malformed_output.py`**

```python
# agents/mission-director/tests/test_llm_malformed_output.py
import pytest

import plan_generator


class _BadToolUse:
    type = "tool_use"
    input = {"rationale": "ok"}  # missing required requested_actions


class _BadResp:
    content = [_BadToolUse()]


class _MockAnthropic:
    class messages:
        @staticmethod
        async def create(**kwargs):
            return _BadResp()


@pytest.mark.asyncio
async def test_generate_raises_malformed_on_schema_violation(monkeypatch):
    plan_generator._client = _MockAnthropic()
    with pytest.raises(plan_generator.PlanMalformedError):
        await plan_generator.generate("do the thing")
    plan_generator._client = None


@pytest.mark.asyncio
async def test_generate_raises_generation_error_when_no_client_configured():
    plan_generator._client = None
    with pytest.raises(plan_generator.PlanGenerationError):
        await plan_generator.generate("do the thing")


@pytest.mark.asyncio
async def test_create_plan_route_returns_rejected_malformed(client, monkeypatch):
    import main

    async def _raise_malformed(goal):
        raise plan_generator.PlanMalformedError("bad output")

    async def _fake_snapshot():
        return "sha256:test"

    monkeypatch.setattr(main.plan_generator, "generate", _raise_malformed)
    monkeypatch.setattr(main, "get_snapshot_ref", lambda: "sha256:test")

    resp = await client.post("/v1/plan", json={"mission_id": "mission_t1", "goal": "x"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "rejected_malformed"
    assert body["plan_response"] is None
```

- [ ] **Step 6: Write `tests/test_fleet_controller_unavailable.py`**

```python
# agents/mission-director/tests/test_fleet_controller_unavailable.py
import pytest

import fleet_client
import plan_generator
from plan_generator import LLMPlanOutput
from models import RequestedAction


@pytest.mark.asyncio
async def test_create_plan_route_returns_preview_unavailable_on_fleet_controller_down(
    client, monkeypatch
):
    import main

    async def _fake_generate(goal):
        return LLMPlanOutput(
            rationale="r",
            requested_actions=[RequestedAction(action_id="a1", kind="compose_profile.preview")],
        )

    async def _fake_preview(plan):
        raise fleet_client.FleetControllerUnavailable("connection refused")

    monkeypatch.setattr(main, "get_snapshot_ref", lambda: "sha256:test")
    monkeypatch.setattr(main.plan_generator, "generate", _fake_generate)
    monkeypatch.setattr(main.fleet_client, "preview", _fake_preview)

    resp = await client.post("/v1/plan", json={"mission_id": "mission_t2", "goal": "x"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "preview_unavailable"
    assert body["plan"] is not None  # plan was built before the failed call
    assert body["plan_response"] is None


@pytest.mark.asyncio
async def test_create_plan_route_returns_preview_unavailable_when_truth_registry_fails(
    client, monkeypatch
):
    import main

    def _raise_registry_error():
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr(main, "get_snapshot_ref", _raise_registry_error)

    resp = await client.post("/v1/plan", json={"mission_id": "mission_t3", "goal": "x"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "preview_unavailable"
    assert body["plan"] is None  # never reached the LLM or fleet-controller
```

- [ ] **Step 7: Write `tests/test_no_execution.py`**

```python
# agents/mission-director/tests/test_no_execution.py
"""Asserts no code path in this module can ever set an
execution/mutation flag True. main.py never constructs an ExecutionView
itself -- execution always comes verbatim from fleet-controller's own
PlanResponse, which fleet-controller's own Phase 0 already proves can
never be True. This test guards against a future regression introducing
a local override."""
import inspect

import main


def test_main_module_never_hardcodes_performed_true():
    source = inspect.getsource(main)
    assert "performed=True" not in source
    assert "performed = True" not in source


def test_terminal_helper_never_sets_plan_response():
    """_terminal() is used for every failure path -- plan_response must
    always be None there, since fleet-controller was never successfully
    reached (or never called) on any path that uses it."""
    source = inspect.getsource(main._terminal)
    assert "plan_response=None" in source
```

- [ ] **Step 8: Run all tests**

Run: `cd agents/mission-director && python -m pytest tests/ -v`
Expected: 19/19 PASS (12 from Task 2 + 3 malformed + 2 unavailable + 2 no-execution)

- [ ] **Step 9: Docker build + standalone smoke test**

```bash
cd agents/mission-director
docker build -t mission-director-test .
docker run -d --name mission-director-test -p 18097:8080 \
  -e ANTHROPIC_API_KEY="" \
  mission-director-test
sleep 3
curl -f http://localhost:18097/health
# Expected: {"status":"healthy","agent":"mission-director"}
curl -s -X POST http://localhost:18097/v1/plan \
  -H "Content-Type: application/json" \
  -d '{"mission_id":"mission_smoke1","goal":"smoke test"}'
# Expected: 200, status "preview_unavailable" (no ANTHROPIC_API_KEY set,
# so plan_generator.generate raises PlanGenerationError -- but first it
# needs the truth mount, which isn't wired until Task 6, so this call is
# actually expected to fail at get_snapshot_ref() instead, same terminal
# status either way; this proves the route doesn't 500).
docker stop mission-director-test && docker rm mission-director-test
cd ../..
```

- [ ] **Step 10: Commit**

```bash
git add agents/mission-director/
git commit -m "feat(mission-director): LLM plan generation, fleet-controller preview, ledger write"
```

---

### Task 4: Backend endpoints — propose + review

**Files:**
- Create: `backend/app/api/v1/endpoints/missions.py`
- Modify: `backend/app/api/api.py` (register the router, same graceful
  try/except pattern as `governance`)
- Modify: `backend/requirements.txt` (confirm `httpx` present — it already
  is at `httpx==0.28.1`, no change needed, verify only)
- Test: `backend/tests/test_missions_endpoint.py`

**Interfaces:**
- Consumes: Task 1's `app.services.mission_store` (`create`, `get_by_id`,
  `update_status`), Task 1's `app.models.mission.MissionProposal`,
  `app.api.deps.get_current_active_user` (unmodified), `app.db.session.get_db`
  (unmodified), `app.models.governance.GovernanceLedger` (direct insert for
  the review-time ledger write).
- Produces: `POST /api/v1/missions/propose` (body `{"goal": str}`, 200 on
  every outcome including terminal-failure states — the failure itself is
  the payload, not an HTTP error; auth failures still 401/403 via the
  existing dependency); `POST /api/v1/missions/{mission_id}/review` (body
  `{"decision": "approve"|"reject"}`, 200 on success, 404 if
  `mission_id` unknown, 409 if `status != "previewed"`).

- [ ] **Step 1: Write the endpoint module**

```python
# backend/app/api/v1/endpoints/missions.py
"""
Mission Director Phase 1 -- human-facing surface.

Both routes here are the ONLY sanctioned way to reach mission-director's
propose/review flow: they reuse deps.get_current_active_user literally,
unmodified, which is what makes "human-submitted only, no self-triggering"
a structural fact rather than a documented convention -- no agent identity
in this repo can authenticate as a user. mission-director itself
(agents/mission-director/) holds no auth of its own; its /v1/plan route is
reachable only inside the docker network, mirroring fleet-controller's own
zero-auth /v1/plans/preview precedent. See
docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md and
docs/superpowers/plans/2026-08-21-mission-director-phase1-plan.md's
"Deviations from the spec" section for why the routes live here instead
of inside the mission-director container as the spec originally sketched.
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.db.session import get_db
from app.models import models
from app.models.governance import GovernanceLedger
from app.services import mission_store

router = APIRouter()


def _mission_director_url() -> str:
    return (os.getenv("MISSION_DIRECTOR_URL") or "http://mission-director:8080").rstrip("/")


class ProposeRequest(BaseModel):
    goal: str


class ReviewRequest(BaseModel):
    decision: Literal["approve", "reject"]


def _serialize(row) -> dict[str, Any]:
    return {
        "mission_id": row.mission_id,
        "status": row.status,
        "goal": row.goal,
        "truth_snapshot_ref": row.truth_snapshot_ref,
        "plan": row.plan,
        "plan_response": row.plan_response,
        "superseded_from": row.superseded_from,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.post("/propose", status_code=200)
async def propose_mission(
    body: ProposeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    mission_id = f"mission_{uuid.uuid4().hex[:12]}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            resp = await http_client.post(
                f"{_mission_director_url()}/v1/plan",
                json={"mission_id": mission_id, "goal": body.goal},
            )
        resp.raise_for_status()
        proposal = resp.json()
    except Exception:
        proposal = {
            "schema_version": 1,
            "mission_id": mission_id,
            "goal": body.goal,
            "truth_snapshot_ref": None,
            "rationale": None,
            "plan": None,
            "plan_response": None,
            "status": "preview_unavailable",
            "superseded_from": None,
        }

    row = mission_store.create(
        db,
        mission_id=proposal["mission_id"],
        status=proposal["status"],
        goal=proposal["goal"],
        truth_snapshot_ref=proposal.get("truth_snapshot_ref"),
        plan=proposal.get("plan"),
        plan_response=proposal.get("plan_response"),
        superseded_from=proposal.get("superseded_from"),
    )
    return _serialize(row)


@router.post("/{mission_id}/review", status_code=200)
def review_mission(
    mission_id: str,
    body: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    row = mission_store.get_by_id(db, mission_id)
    if row is None:
        raise HTTPException(status_code=404, detail="mission not found")
    if row.status != "previewed":
        raise HTTPException(
            status_code=409,
            detail=f"mission status is {row.status!r}, must be 'previewed' to review",
        )

    new_status = "approved" if body.decision == "approve" else "rejected"
    updated = mission_store.update_status(db, mission_id, new_status)

    ledger_row = GovernanceLedger(
        user_id=str(current_user.id),
        action="mission.review",
        tool_used=None,
        payload={"mission_id": mission_id, "decision": body.decision},
        decision=new_status,
        agent_name="mission-director",
        approved_by=str(current_user.id),
    )
    db.add(ledger_row)
    db.commit()

    return _serialize(updated)
```

- [ ] **Step 2: Register the router in `api.py`**

Add near the other conditionally-guarded routers (same pattern as
`governance`, since this needs the new `mission.py` model):

```python
# P1-3 Mission Director Phase 1 (requires the mission_proposals model/migration)
try:
    from app.api.v1.endpoints import missions
    _HAS_MISSIONS = True
except Exception as _e:
    import logging as _log
    _log.getLogger(__name__).warning("Mission Director endpoints unavailable (old image): %s", _e)
    _HAS_MISSIONS = False
```

And, alongside the other conditional `include_router` calls (near
`governance`'s):

```python
    api_router.include_router(missions.router, prefix="/missions", tags=["missions"])  # P1-3: Mission Director
```

- [ ] **Step 3: Write the tests**

```python
# backend/tests/test_missions_endpoint.py
import pytest
from unittest.mock import AsyncMock, patch

from app.core import security
from app.core.config import settings
from app.models import models


def _make_user(db):
    user = models.User(
        email="mission-tester@example.com",
        hashed_password="x",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_headers(user):
    from jose import jwt

    token = jwt.encode(
        {"sub": str(user.id), "aud": settings.JWT_AUDIENCE, "iss": settings.JWT_ISSUER},
        settings.JWT_SECRET,
        algorithm=security.ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


class _MockResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self._payload


def test_propose_requires_auth(client):
    resp = client.post("/api/v1/missions/propose", json={"goal": "do the thing"})
    assert resp.status_code in (401, 403)


def test_propose_persists_and_returns_previewed(client, db):
    user = _make_user(db)
    mock_payload = {
        "schema_version": 1,
        "mission_id": "mission_mocked01",
        "goal": "do the thing",
        "truth_snapshot_ref": "sha256:abc",
        "rationale": "because",
        "plan": {"schema_version": 1, "mission_id": "mission_mocked01", "requested_actions": []},
        "plan_response": {
            "plan_id": "plan_x",
            "plan_hash": "sha256:x",
            "safety": {"decision": "ESCALATE", "reason": "r", "shepherd_available": True},
            "execution": {"performed": False, "would_execute": []},
        },
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
    assert body["status"] == "previewed"
    assert body["plan_response"]["execution"]["performed"] is False


def test_propose_returns_preview_unavailable_when_mission_director_unreachable(client, db):
    user = _make_user(db)
    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=RuntimeError("connection refused"))):
        resp = client.post(
            "/api/v1/missions/propose",
            json={"goal": "do the thing"},
            headers=_auth_headers(user),
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "preview_unavailable"


def test_review_requires_auth(client):
    resp = client.post("/api/v1/missions/mission_x/review", json={"decision": "approve"})
    assert resp.status_code in (401, 403)


def test_review_404_on_unknown_mission(client, db):
    user = _make_user(db)
    resp = client.post(
        "/api/v1/missions/does-not-exist/review",
        json={"decision": "approve"},
        headers=_auth_headers(user),
    )
    assert resp.status_code == 404


def test_review_409_when_status_not_previewed(client, db):
    user = _make_user(db)
    from app.services import mission_store

    mission_store.create(
        db,
        mission_id="mission_notprevd",
        status="rejected_malformed",
        goal="g",
        truth_snapshot_ref=None,
        plan=None,
        plan_response=None,
    )
    resp = client.post(
        "/api/v1/missions/mission_notprevd/review",
        json={"decision": "approve"},
        headers=_auth_headers(user),
    )
    assert resp.status_code == 409


def test_review_approve_transitions_and_writes_ledger(client, db):
    user = _make_user(db)
    from app.services import mission_store

    mission_store.create(
        db,
        mission_id="mission_toreview",
        status="previewed",
        goal="g",
        truth_snapshot_ref="sha256:abc",
        plan=None,
        plan_response=None,
    )
    resp = client.post(
        "/api/v1/missions/mission_toreview/review",
        json={"decision": "approve"},
        headers=_auth_headers(user),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    from app.models.governance import GovernanceLedger

    ledger_rows = (
        db.query(GovernanceLedger).filter(GovernanceLedger.action == "mission.review").all()
    )
    assert len(ledger_rows) == 1
    assert ledger_rows[0].decision == "approved"
```

- [ ] **Step 4: Run the tests**

Run: `cd backend && python -m pytest tests/test_missions_endpoint.py -v`
Expected: 7/7 PASS

(If `_auth_headers`'s JWT shape doesn't match this repo's actual
`TokenPayload`/`settings.JWT_AUDIENCE`/`JWT_ISSUER` fields exactly, fix by
reading `backend/tests/unit/test_deps.py`'s own token-minting helper and
matching it — that file already solves this exact problem for
`get_current_active_user`-gated tests elsewhere in this repo.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/missions.py backend/app/api/api.py backend/tests/test_missions_endpoint.py
git commit -m "feat(mission-director): backend propose/review endpoints, auth-gated"
```

---

### Task 5: Governance Ledger key for mission-director

**Files:**
- Modify: `scripts/seed_agent_api_keys.py` (add `mission-director` to
  `SERVICES` — documentation of intent, NOT re-run in this task)
- Create (git-ignored, not committed): `secrets/agent_api_key_mission-director.txt`

**Interfaces:**
- Produces: one row in the live `agent_api_keys` table (`agent_name =
  'mission-director'`), matching the schema `007_add_agent_api_keys.py`
  already created and `agent_auth.py`'s `hash_agent_key` already reads
  (SHA-256 hex of the raw key).

- [ ] **Step 1: Add `mission-director` to the SERVICES list (doc-of-intent only)**

In `scripts/seed_agent_api_keys.py`, add one line to the `SERVICES` list
(after the existing `("fleet-controller", 200),` entry):

```python
    ("mission-director",         200),
```

This documents that `mission-director` is now a known agent for future
full reseeds — **do not run the full script**, per the same reasoning
`fleet-controller`'s own provisioning used: `seed_agent_api_keys.py`
regenerates every listed agent's key in one pass, which would silently
invalidate the 15 other live agents' keys while their running containers
still hold the old ones.

- [ ] **Step 2: Generate one scoped key + hash, write the raw key to `secrets/`**

```bash
python -c "
import hashlib, secrets
raw = 'hc_' + secrets.token_urlsafe(32)
digest = hashlib.sha256(raw.encode()).hexdigest()
with open('secrets/agent_api_key_mission-director.txt', 'w') as f:
    f.write(raw)
print('digest:', digest)
"
```

Copy the printed `digest:` value — it's the only thing that goes into the
next step's SQL. The raw key never leaves this local step (file is
git-ignored, matching every other `secrets/agent_api_key_*.txt`).

- [ ] **Step 3: Insert the single row**

```bash
docker exec -i postgres psql -U postgres -d hypercode -c "
INSERT INTO agent_api_keys (agent_name, key_hash, rate_limit_rpm, is_active, created_at)
VALUES ('mission-director', '<PASTE_DIGEST_HERE>', 200, true, now())
ON CONFLICT (agent_name) DO NOTHING;
"
```

If the live `postgres` container uses a different name/credentials than
this template assumes, check `docker compose config postgres | grep -E
'container_name|POSTGRES_USER|POSTGRES_DB'` first and adjust — don't
guess against a running database.

- [ ] **Step 4: Verify the row exists and no other agent's row changed**

```bash
docker exec -i postgres psql -U postgres -d hypercode -c \
  "SELECT agent_name, is_active, rate_limit_rpm FROM agent_api_keys ORDER BY agent_name;"
```

Expected: 16 rows total (15 pre-existing + `mission-director`), every
pre-existing row's `agent_name` unchanged from before this step.

- [ ] **Step 5: Commit (script change only — never the secrets/ file)**

```bash
git status  # confirm secrets/agent_api_key_mission-director.txt shows as untracked, NOT staged
git add scripts/seed_agent_api_keys.py
git commit -m "chore(mission-director): document mission-director in seed_agent_api_keys.py roster"
```

---

### Task 6: Compose wiring + live verification

**Files:**
- Modify: `docker-compose.agents-full.yml` (new `mission-director` service
  block)
- Modify: `.github/scripts/fleet_overlay.yml` (add `mission-director` to
  `roster` — it's now a real fleet member; the truth registry itself would
  otherwise flag it as unaccounted-for the next time anyone runs the port
  checks)
- Modify: `CLAUDE.md`, `AGENT-START.md`, `WHATS_DONE.md` (fleet
  tables + roster counts + done-log entry)

**Interfaces:**
- Consumes: everything from Tasks 1-5. This task's job is wiring +
  verification only — no new application code.

- [ ] **Step 1: Re-verify `:8097` is still free**

```bash
grep -r "8097" docker-compose*.yml
```

Expected: no matches. (The spec's own grep for this was earlier the same
day; two unrelated docs-only commits landed on `main` since — re-verify
port state, don't trust the spec's timestamp.)

- [ ] **Step 2: Add the compose service block**

In `docker-compose.agents-full.yml`, add a new block (place it near
`fleet-controller`'s, same file, same `["fleet"]` profile — matched pair,
no reason to fragment the opt-in boundary):

```yaml
  # ══════════════════════════════════════════════════════════════════════════════
  # mission-director — Phase 1. Turns a human goal into a previewed,
  # reviewable plan via the real (unmodified) fleet-controller. Holds no DB
  # connection and no user-auth capability of its own — the human-facing
  # propose/review endpoints live in hypercode-core
  # (backend/app/api/v1/endpoints/missions.py), which is the only
  # sanctioned caller of this service's /v1/plan route. See
  # docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md and
  # docs/superpowers/plans/2026-08-21-mission-director-phase1-plan.md.
  # No depends_on: crew-orchestrator (same named exception fleet-controller
  # already has — no crew-orchestrator credential, no dispatch path
  # through it) and no depends_on: safety-shepherd either — unlike
  # fleet-controller, mission-director never talks to Shepherd directly,
  # only transitively through fleet-controller.
  # ══════════════════════════════════════════════════════════════════════════════
  mission-director:
    profiles: ["fleet"]
    image: hypercode-mission-director:latest
    build:
      context: ./agents/mission-director
      dockerfile: Dockerfile
    container_name: mission-director
    ports:
      - "127.0.0.1:8097:8080"
    environment:
      - AGENT_NAME=mission-director
      - LOG_LEVEL=INFO
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - AGENT_MODEL=${AGENT_MODEL:-claude-sonnet-4-6}
      - FLEET_CONTROLLER_URL=http://fleet-controller:8080
      - CORE_URL=${CORE_URL:-http://hypercode-core:8000}
      - CORE_AGENT_KEY=${MISSION_DIRECTOR_CORE_AGENT_KEY:-}
    volumes:
      - ./.github/scripts/fleet_registry.py:/app/truth/fleet_registry.py:ro
      - ./.github/scripts/fleet_overlay.yml:/app/truth/fleet_overlay.yml:ro
      - ./docker-compose.agents.yml:/app/truth/docker-compose.agents.yml:ro
      - ./docker-compose.agents-full.yml:/app/truth/docker-compose.agents-full.yml:ro
      - ./docker-compose.bropets.yml:/app/truth/docker-compose.bropets.yml:ro
      - ./docker-compose.brain.yml:/app/truth/docker-compose.brain.yml:ro
    networks:
      - agents-net
    deploy:
      resources:
        limits:
          cpus: "0.25"
          memory: 256MB
        reservations:
          cpus: "0.1"
          memory: 128MB
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    labels:
      - "com.hypercode.tier=infrastructure"
      - "com.hypercode.role=mission-planning"
```

- [ ] **Step 3: Add `MISSION_DIRECTOR_URL` for the backend container**

Find `hypercode-core`'s service block (whichever compose file defines it —
`docker-compose.core.yml` per this repo's file layout) and add one env var
alongside its existing `CORE_URL`-style entries:

```yaml
      - MISSION_DIRECTOR_URL=${MISSION_DIRECTOR_URL:-http://mission-director:8080}
```

- [ ] **Step 4: Add `mission-director` to the truth registry's overlay roster**

In `.github/scripts/fleet_overlay.yml`, add `- mission-director` to the
`roster:` list (alongside `fleet-controller`, if it's already there — if
not, this is the first time either boundary-proving service joined the
roster; add both if `fleet-controller` was previously left out
intentionally, matching whatever the current file actually shows).

- [ ] **Step 5: Run the migration against the live DB**

```bash
cd backend
alembic upgrade head
```

Expected: applies `020_add_mission_proposals`, no errors. Verify:

```bash
docker exec -i postgres psql -U postgres -d hypercode -c "\d mission_proposals"
```

- [ ] **Step 6: Build and launch mission-director**

```bash
docker compose -f docker-compose.yml -f docker-compose.agents-full.yml \
  --profile fleet build mission-director
docker compose -f docker-compose.yml -f docker-compose.agents-full.yml \
  --profile fleet up -d mission-director
sleep 5
curl -f http://127.0.0.1:8097/health
# Expected: {"status":"healthy","agent":"mission-director"}
```

- [ ] **Step 7: Real end-to-end propose call against the real, running fleet-controller**

Confirm fleet-controller is already up (`docker ps | grep fleet-controller`;
if not, `docker compose ... --profile fleet up -d fleet-controller` first —
mission-director's `/v1/plan` needs it live for this step). Then, using a
real user JWT (mint one via the backend's existing login flow, or reuse
whatever this repo's own manual-testing convention already is for
`get_current_active_user`-gated routes):

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/missions/propose \
  -H "Authorization: Bearer <REAL_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"goal": "preview enabling the gpu profile"}' | python -m json.tool
```

Expected: `status: "previewed"` (or `"rejected_malformed"`/`"preview_unavailable"`
if `ANTHROPIC_API_KEY` isn't configured in this environment — acceptable,
document which one actually happened), and if `previewed`,
`plan_response.safety.decision` shows a real Shepherd verdict (`ESCALATE`
for the `docker` category, per fleet-controller's own Phase 0
verification) — **this is the spec's explicit requirement to prove a real
ESCALATE/BLOCK round-trip, not just a mocked happy path.**
`plan_response.execution.performed` must be `false`.

- [ ] **Step 8: Real review call**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/missions/<MISSION_ID_FROM_STEP_7>/review \
  -H "Authorization: Bearer <REAL_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve"}' | python -m json.tool
```

Expected: `status: "approved"` (only if step 7 actually reached
`previewed` — if it landed on a terminal-failure status instead, expect
`409` here instead, and note that as the actual observed behavior, not a
bug).

- [ ] **Step 9: Full-box sweep**

```bash
docker ps --filter "health=unhealthy" --format "table {{.Names}}\t{{.Status}}"
```

Expected: empty output — zero unhealthy containers anywhere on the box,
same bar every prior fleet change this session has held itself to.

- [ ] **Step 10: Update docs**

- `WHATS_DONE.md`: new top entry, "Mission Director Phase 1 live" —
  what was built, the auth/persistence deviation from the spec and why,
  the real ESCALATE round-trip proof from Step 7, zero-unhealthy sweep
  result.
- `CLAUDE.md`: add `mission-director` to the "Phase 0: Fleet Controller"
  section's table (rename section heading to cover both, e.g. "Phase 0-1:
  Fleet Controller + Mission Director"), same `--profile fleet` note.
- `AGENT-START.md`: same table addition, mirrored.

- [ ] **Step 11: Commit**

```bash
git add docker-compose.agents-full.yml .github/scripts/fleet_overlay.yml WHATS_DONE.md CLAUDE.md AGENT-START.md
# (backend's compose file with MISSION_DIRECTOR_URL — add whichever file Step 3 actually touched)
git commit -m "feat(mission-director): compose wiring, profile fleet, live end-to-end verification"
git fetch origin main
git rebase origin/main
git push
```

---

## Self-Review Notes (completed during plan authoring)

- **Spec coverage:** §1 (service layout) → Tasks 2-3. §2 (schema) → Task 2
  Step 1. §3 (local validation) → Task 2 Step 2. §4 (`propose`) → Task 3
  Step 4 (mission-director side) + Task 4 (backend side). §5 (`review`) →
  Task 4 only (mission-director has no role at review time, per this
  plan's ruled deviation). §6 (durable record) → Task 1. §7 (ledger
  shape) → Task 3 Step 3 + Task 4 Step 1's review-time insert. §8
  (compose) → Task 6. §9 (no Shepherd client) → Task 6's `depends_on`
  omission, unchanged from spec. Testing Plan's 4 named test files →
  Task 2/3's `tests/test_models.py` (schema), `test_llm_malformed_output.py`,
  `test_fleet_controller_unavailable.py`, `test_no_execution.py`. Rollout
  Order 1-6 → Tasks 1-6 in the same order, split further where each step
  needed its own test cycle.
- **Type consistency checked:** `MissionProposal.plan_response` (added,
  not in spec's literal code sample) is used consistently across Task 2's
  model, Task 3's `main.py`, Task 4's serializer, and Task 1's table
  column — no drift.
- **No placeholders:** every step above has literal, runnable code or an
  exact shell command; the one deliberately-deferred item (Task 2's
  `plan_generator.py`/`fleet_client.py`/`ledger_client.py` stubs) is
  explicitly scoped, timed, and reversed within the same task.
