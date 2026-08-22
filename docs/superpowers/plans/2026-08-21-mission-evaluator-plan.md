# Mission Evaluator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing `mission_proposals` audit trail into structured,
queryable "lessons" about how well the propose→review pipeline is
performing — without executing anything, without an LLM call, and with
zero new mutation capability anywhere in the system.

**Architecture:** A pure rule-based observer, entirely inside the
existing `backend/` FastAPI app (no new container, unlike mission-director
itself) — a new `mission_evaluations` table, a pure function that scores
one `MissionProposal` row against deterministic checks, a store, and 3
read-mostly HTTP endpoints. On-demand trigger only (`POST .../run`), no
scheduling.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (existing backend stack,
no new dependencies).

**Spec:** `docs/superpowers/specs/2026-08-21-mission-evaluator-design.md`

## Global Constraints

- Python indent: 4 spaces, never mixed.
- `from app.X import Y` — NEVER `from backend.app.X` (this repo's Sacred
  Rule; a reviewed second-opinion sketch of this exact feature got this
  wrong during brainstorming — worth double-checking every import in
  every task).
- No new mutation capability anywhere — `mission_evaluator.py` and every
  new endpoint are read-only against `mission_proposals`, writing only
  to the new `mission_evaluations` table. No execution code path,
  disabled or otherwise.
- Alembic head going into this plan is `020`
  (`020_add_mission_proposals.py`) — verified via `backend/alembic/versions/`
  listing before writing this plan. The new migration is `021`,
  `down_revision = "020"`.
- `.env`/secrets never committed to git.
- `git fetch` before any push (this session's established direct-to-main
  workflow — used throughout Mission Director Phase 1 the same day).
- Worktree: same ruling as every prior plan this session — skip an
  isolated git worktree, work directly on `main` with fetch-before-push.

---

### Task 1: `mission_evaluations` table — migration + model

**Files:**
- Create: `backend/alembic/versions/021_add_mission_evaluations.py`
- Create: `backend/app/models/mission_evaluation.py`
- Modify: `backend/app/db/base.py` (register the model, same one-line
  pattern as every other model in that file)
- Test: `backend/tests/test_mission_evaluation_model.py`

**Interfaces:**
- Produces: `app.models.mission_evaluation.MissionEvaluation` (SQLAlchemy
  model, table `mission_evaluations`, PK `mission_id: str`).
- Consumes: `backend/app/db/base_class.py`'s `Base`, `backend/tests/conftest.py`'s
  existing `db` fixture (in-memory SQLite, `Base.metadata.create_all()`
  per test).

- [ ] **Step 1: Write the migration**

```python
# backend/alembic/versions/021_add_mission_evaluations.py
"""Add mission_evaluations table (Mission Evaluator v1)

Revision ID: 021
Revises: 020
Create Date: 2026-08-21

Read-only observer over mission_proposals -- one row per evaluated
mission, never updated after insert. NOT the audit trail (that's
governance_ledger, untouched here); NOT mission_proposals' own
current-state store either. See
docs/superpowers/specs/2026-08-21-mission-evaluator-design.md §1.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mission_evaluations",
        sa.Column("mission_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("verdict", sa.Text(), nullable=False),
        sa.Column("checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_mission_evaluations_verdict", "mission_evaluations", ["verdict"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_mission_evaluations_verdict", table_name="mission_evaluations")
    op.drop_table("mission_evaluations")
```

- [ ] **Step 2: Write the model**

```python
# backend/app/models/mission_evaluation.py
"""MissionEvaluation model -- Mission Evaluator v1's own table. One row
per evaluated mission, written once and never updated (an evaluation is
a point-in-time judgment of a terminal mission, not a live-updating
record). NOT the audit trail (governance_ledger) and NOT
mission_proposals' own current-state store -- a third, narrower table
purpose-built for this observer. See
docs/superpowers/specs/2026-08-21-mission-evaluator-design.md §1.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base_class import Base


class MissionEvaluation(Base):
    __tablename__ = "mission_evaluations"

    mission_id: Mapped[str] = mapped_column(Text, primary_key=True)
    verdict: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    checks: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(SQLiteJSON(), "sqlite"), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 3: Register the model in `app/db/base.py`**

Add, matching the existing style (each import gets an inline comment
naming its phase):

```python
from app.models.mission_evaluation import MissionEvaluation  # Mission Evaluator v1
```

And add `"MissionEvaluation"` to the `__all__` list.

- [ ] **Step 4: Write the test**

```python
# backend/tests/test_mission_evaluation_model.py
from sqlalchemy.orm import Session

from app.models.mission_evaluation import MissionEvaluation


def test_create_and_query_mission_evaluation(db: Session):
    row = MissionEvaluation(
        mission_id="mission_eval_test001",
        verdict="anomaly",
        checks={
            "status": "approved",
            "plan_malformed": False,
            "preview_failed": False,
            "safety_decision": "BLOCK",
            "shepherd_available": True,
            "human_decision": "approved",
            "anomaly_approved_despite_block": True,
            "anomaly_approved_despite_shepherd_down": False,
            "anomaly_rejected_despite_allow": False,
        },
        summary="approved despite BLOCK verdict",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    assert row.mission_id == "mission_eval_test001"
    assert row.verdict == "anomaly"
    assert row.checks["anomaly_approved_despite_block"] is True
    assert row.evaluated_at is not None


def test_verdict_index_query(db: Session):
    db.add(
        MissionEvaluation(
            mission_id="mission_eval_test002",
            verdict="clean",
            checks={"status": "rejected_malformed"},
            summary="clean: rejected_malformed",
        )
    )
    db.commit()

    rows = db.query(MissionEvaluation).filter(MissionEvaluation.verdict == "clean").all()
    assert len(rows) == 1
    assert rows[0].mission_id == "mission_eval_test002"
```

- [ ] **Step 5: Run the tests**

Run: `cd backend && python -m pytest tests/test_mission_evaluation_model.py -v`
Expected: 2/2 PASS

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/versions/021_add_mission_evaluations.py backend/app/models/mission_evaluation.py backend/app/db/base.py backend/tests/test_mission_evaluation_model.py
git commit -m "feat(mission-evaluator): add mission_evaluations table + model"
```

---

### Task 2: Pure rule logic — `evaluate_mission()`

**Files:**
- Create: `backend/app/services/mission_evaluator.py`
- Test: `backend/tests/test_mission_evaluator.py`

**Interfaces:**
- Consumes: `app.models.mission.MissionProposal` (Mission Director Phase
  1's model — `status: str`, `plan_response: Optional[dict]`) — read-only,
  never modified.
- Produces: `mission_evaluator.evaluate_mission(status: str, plan_response:
  Optional[dict]) -> dict` — a pure function (no DB, no I/O) returning
  the `checks` dict plus `verdict` and `summary` keys, per spec §2.
  Deliberately typed on the two raw fields (`status`, `plan_response`),
  not the ORM object itself, so it's testable with plain Python values
  and has zero coupling to SQLAlchemy.
- `mission_evaluator.TERMINAL_STATUSES: frozenset[str]` — the 4 statuses
  eligible for evaluation (`rejected_malformed`, `preview_unavailable`,
  `approved`, `rejected`). Consumed by Task 3's store to filter which
  `mission_proposals` rows are evaluable.

- [ ] **Step 1: Write `mission_evaluator.py`**

```python
# backend/app/services/mission_evaluator.py
"""
Mission Evaluator v1 -- pure rule logic.

Scores one already-recorded MissionProposal (status + plan_response)
against deterministic checks. No DB access, no network call, no LLM
call -- a pure function, trivially unit-testable, kept separate from
persistence (mission_evaluation_store.py) and HTTP (mission_evaluations
endpoint) concerns. See
docs/superpowers/specs/2026-08-21-mission-evaluator-design.md §2-3.
"""
from __future__ import annotations

from typing import Any, Optional

TERMINAL_STATUSES = frozenset(
    {"rejected_malformed", "preview_unavailable", "approved", "rejected"}
)


def _safety_field(plan_response: Optional[dict[str, Any]], field: str) -> Any:
    if not plan_response:
        return None
    safety = plan_response.get("safety")
    if not isinstance(safety, dict):
        return None
    return safety.get(field)


def _human_decision(status: str) -> Optional[str]:
    if status == "approved":
        return "approved"
    if status == "rejected":
        return "rejected"
    return None


def _summary(checks: dict[str, Any]) -> str:
    if checks["anomaly_approved_despite_block"]:
        return "anomaly: approved despite a genuine Shepherd BLOCK verdict"
    if checks["anomaly_approved_despite_shepherd_down"]:
        return "anomaly: approved while Shepherd was unreachable (fail-closed BLOCK)"
    if checks["anomaly_rejected_despite_allow"]:
        return "anomaly: rejected despite an ALLOW verdict"
    return f"clean: {checks['status']}"


def evaluate_mission(status: str, plan_response: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Returns a dict with every key from the spec's §2 `checks` shape,
    plus `verdict` and `summary`. Never raises on a null or malformed
    plan_response -- degrades every safety-derived field to None instead."""
    plan_malformed = status == "rejected_malformed"
    preview_failed = status == "preview_unavailable"
    safety_decision = _safety_field(plan_response, "decision")
    shepherd_available = _safety_field(plan_response, "shepherd_available")
    human_decision = _human_decision(status)

    anomaly_approved_despite_block = (
        human_decision == "approved"
        and safety_decision == "BLOCK"
        and shepherd_available is True
    )
    anomaly_approved_despite_shepherd_down = (
        human_decision == "approved"
        and safety_decision == "BLOCK"
        and shepherd_available is False
    )
    anomaly_rejected_despite_allow = (
        human_decision == "rejected" and safety_decision == "ALLOW"
    )

    checks: dict[str, Any] = {
        "status": status,
        "plan_malformed": plan_malformed,
        "preview_failed": preview_failed,
        "safety_decision": safety_decision,
        "shepherd_available": shepherd_available,
        "human_decision": human_decision,
        "anomaly_approved_despite_block": anomaly_approved_despite_block,
        "anomaly_approved_despite_shepherd_down": anomaly_approved_despite_shepherd_down,
        "anomaly_rejected_despite_allow": anomaly_rejected_despite_allow,
    }

    verdict = (
        "anomaly"
        if (
            anomaly_approved_despite_block
            or anomaly_approved_despite_shepherd_down
            or anomaly_rejected_despite_allow
        )
        else "clean"
    )

    return {**checks, "verdict": verdict, "summary": _summary(checks)}
```

- [ ] **Step 2: Write the tests**

```python
# backend/tests/test_mission_evaluator.py
from app.services.mission_evaluator import TERMINAL_STATUSES, evaluate_mission


def _plan_response(decision, shepherd_available=True):
    return {
        "plan_id": "plan_x",
        "plan_hash": "sha256:x",
        "safety": {"decision": decision, "reason": "r", "shepherd_available": shepherd_available},
        "execution": {"performed": False, "would_execute": []},
    }


def test_terminal_statuses_are_exactly_the_four_expected():
    assert TERMINAL_STATUSES == frozenset(
        {"rejected_malformed", "preview_unavailable", "approved", "rejected"}
    )


def test_rejected_malformed_has_no_safety_or_human_decision():
    result = evaluate_mission("rejected_malformed", None)
    assert result["plan_malformed"] is True
    assert result["preview_failed"] is False
    assert result["safety_decision"] is None
    assert result["shepherd_available"] is None
    assert result["human_decision"] is None
    assert result["verdict"] == "clean"
    assert result["summary"] == "clean: rejected_malformed"


def test_preview_unavailable_has_no_safety_or_human_decision():
    result = evaluate_mission("preview_unavailable", None)
    assert result["preview_failed"] is True
    assert result["plan_malformed"] is False
    assert result["human_decision"] is None
    assert result["verdict"] == "clean"


def test_approved_with_allow_is_clean():
    result = evaluate_mission("approved", _plan_response("ALLOW"))
    assert result["human_decision"] == "approved"
    assert result["safety_decision"] == "ALLOW"
    assert result["anomaly_approved_despite_block"] is False
    assert result["anomaly_approved_despite_shepherd_down"] is False
    assert result["verdict"] == "clean"


def test_approved_despite_real_block_is_the_flagship_anomaly():
    result = evaluate_mission("approved", _plan_response("BLOCK", shepherd_available=True))
    assert result["anomaly_approved_despite_block"] is True
    assert result["anomaly_approved_despite_shepherd_down"] is False
    assert result["verdict"] == "anomaly"
    assert result["summary"] == "anomaly: approved despite a genuine Shepherd BLOCK verdict"


def test_approved_despite_shepherd_down_is_a_distinct_anomaly():
    result = evaluate_mission("approved", _plan_response("BLOCK", shepherd_available=False))
    assert result["anomaly_approved_despite_block"] is False
    assert result["anomaly_approved_despite_shepherd_down"] is True
    assert result["verdict"] == "anomaly"
    assert result["summary"] == "anomaly: approved while Shepherd was unreachable (fail-closed BLOCK)"


def test_rejected_despite_allow_is_a_secondary_anomaly():
    result = evaluate_mission("rejected", _plan_response("ALLOW"))
    assert result["anomaly_rejected_despite_allow"] is True
    assert result["verdict"] == "anomaly"


def test_rejected_with_escalate_is_clean():
    result = evaluate_mission("rejected", _plan_response("ESCALATE"))
    assert result["anomaly_rejected_despite_allow"] is False
    assert result["verdict"] == "clean"


def test_malformed_plan_response_degrades_to_none_never_raises():
    result = evaluate_mission("approved", {"safety": "not-a-dict"})
    assert result["safety_decision"] is None
    assert result["shepherd_available"] is None
    # human_decision is still "approved" (derived from status, not plan_response)
    assert result["human_decision"] == "approved"
    assert result["anomaly_approved_despite_block"] is False
```

- [ ] **Step 3: Run the tests**

Run: `cd backend && python -m pytest tests/test_mission_evaluator.py -v`
Expected: 9/9 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/mission_evaluator.py backend/tests/test_mission_evaluator.py
git commit -m "feat(mission-evaluator): pure rule logic for evaluate_mission()"
```

---

### Task 3: Persistence — `mission_evaluation_store.py`

**Files:**
- Create: `backend/app/services/mission_evaluation_store.py`
- Test: `backend/tests/test_mission_evaluation_store.py`

**Interfaces:**
- Consumes: Task 1's `MissionEvaluation` model, Task 2's
  `evaluate_mission()`/`TERMINAL_STATUSES`, `app.models.mission.MissionProposal`
  (Mission Director Phase 1 — queried, never modified).
- Produces:
  - `mission_evaluation_store.run_evaluation(db: Session) -> dict` —
    queries `mission_proposals` for terminal-status rows with no
    existing `mission_evaluations` row, evaluates + inserts one row per
    mission (one commit per mission, not a single batch transaction —
    per spec §4, so a mid-batch failure doesn't roll back earlier
    successes), returns `{"evaluated_count": int, "anomaly_count": int,
    "already_evaluated_skipped": int}`.
  - `mission_evaluation_store.list_evaluations(db: Session, *, verdict:
    Optional[str] = None, limit: int = 50, offset: int = 0) -> tuple[int,
    list[MissionEvaluation]]` — returns `(total_matching, rows)`.
  - `mission_evaluation_store.summary(db: Session) -> dict` — the
    aggregate rollup from spec §6, all rates `0.0` when
    `total_evaluated == 0`.

- [ ] **Step 1: Write `mission_evaluation_store.py`**

```python
# backend/app/services/mission_evaluation_store.py
"""
CRUD + the actual evaluation run for Mission Evaluator v1. Queries
mission_proposals (Mission Director Phase 1's table) read-only; writes
only to this feature's own mission_evaluations table. See
docs/superpowers/specs/2026-08-21-mission-evaluator-design.md §4-6.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.mission import MissionProposal
from app.models.mission_evaluation import MissionEvaluation
from app.services.mission_evaluator import TERMINAL_STATUSES, evaluate_mission


def run_evaluation(db: Session) -> dict[str, int]:
    already_evaluated_ids = {
        row.mission_id for row in db.query(MissionEvaluation.mission_id).all()
    }

    candidates = (
        db.query(MissionProposal)
        .filter(MissionProposal.status.in_(TERMINAL_STATUSES))
        .all()
    )

    evaluated_count = 0
    anomaly_count = 0
    already_evaluated_skipped = 0

    for proposal in candidates:
        if proposal.mission_id in already_evaluated_ids:
            already_evaluated_skipped += 1
            continue

        result = evaluate_mission(proposal.status, proposal.plan_response)
        verdict = result.pop("verdict")
        summary = result.pop("summary")

        row = MissionEvaluation(
            mission_id=proposal.mission_id,
            verdict=verdict,
            checks=result,
            summary=summary,
        )
        db.add(row)
        db.commit()

        evaluated_count += 1
        if verdict == "anomaly":
            anomaly_count += 1

    return {
        "evaluated_count": evaluated_count,
        "anomaly_count": anomaly_count,
        "already_evaluated_skipped": already_evaluated_skipped,
    }


def list_evaluations(
    db: Session,
    *,
    verdict: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[MissionEvaluation]]:
    q = db.query(MissionEvaluation)
    if verdict:
        q = q.filter(MissionEvaluation.verdict == verdict)
    total = q.count()
    rows = q.order_by(MissionEvaluation.evaluated_at.desc()).offset(offset).limit(limit).all()
    return total, rows


def summary(db: Session) -> dict[str, Any]:
    rows = db.query(MissionEvaluation).all()
    total = len(rows)
    if total == 0:
        return {
            "total_evaluated": 0,
            "plan_malformed_rate": 0.0,
            "preview_failed_rate": 0.0,
            "human_approved_count": 0,
            "human_rejected_count": 0,
            "anomaly_approved_despite_block_count": 0,
            "anomaly_approved_despite_shepherd_down_count": 0,
            "anomaly_rejected_despite_allow_count": 0,
        }

    plan_malformed = sum(1 for r in rows if r.checks.get("plan_malformed"))
    preview_failed = sum(1 for r in rows if r.checks.get("preview_failed"))
    human_approved = sum(1 for r in rows if r.checks.get("human_decision") == "approved")
    human_rejected = sum(1 for r in rows if r.checks.get("human_decision") == "rejected")
    anomaly_block = sum(1 for r in rows if r.checks.get("anomaly_approved_despite_block"))
    anomaly_shepherd_down = sum(
        1 for r in rows if r.checks.get("anomaly_approved_despite_shepherd_down")
    )
    anomaly_allow = sum(1 for r in rows if r.checks.get("anomaly_rejected_despite_allow"))

    return {
        "total_evaluated": total,
        "plan_malformed_rate": plan_malformed / total,
        "preview_failed_rate": preview_failed / total,
        "human_approved_count": human_approved,
        "human_rejected_count": human_rejected,
        "anomaly_approved_despite_block_count": anomaly_block,
        "anomaly_approved_despite_shepherd_down_count": anomaly_shepherd_down,
        "anomaly_rejected_despite_allow_count": anomaly_allow,
    }
```

- [ ] **Step 2: Write the tests**

```python
# backend/tests/test_mission_evaluation_store.py
from sqlalchemy.orm import Session

from app.models.mission import MissionProposal
from app.services import mission_evaluation_store


def _seed_proposal(db: Session, mission_id: str, status: str, plan_response=None):
    db.add(
        MissionProposal(
            mission_id=mission_id,
            status=status,
            goal="g",
            truth_snapshot_ref="sha256:abc",
            plan=None,
            plan_response=plan_response,
        )
    )
    db.commit()


def test_run_evaluation_evaluates_terminal_missions_only(db: Session):
    _seed_proposal(db, "mission_e1", "rejected_malformed")
    _seed_proposal(db, "mission_e2", "previewed")  # not terminal, must be skipped

    result = mission_evaluation_store.run_evaluation(db)
    assert result["evaluated_count"] == 1
    assert result["already_evaluated_skipped"] == 0


def test_run_evaluation_is_idempotent(db: Session):
    _seed_proposal(db, "mission_e3", "preview_unavailable")

    first = mission_evaluation_store.run_evaluation(db)
    assert first["evaluated_count"] == 1

    second = mission_evaluation_store.run_evaluation(db)
    assert second["evaluated_count"] == 0
    assert second["already_evaluated_skipped"] == 1


def test_run_evaluation_flags_the_flagship_anomaly(db: Session):
    _seed_proposal(
        db,
        "mission_e4",
        "approved",
        plan_response={"safety": {"decision": "BLOCK", "shepherd_available": True}},
    )

    result = mission_evaluation_store.run_evaluation(db)
    assert result["evaluated_count"] == 1
    assert result["anomaly_count"] == 1


def test_list_evaluations_filters_by_verdict(db: Session):
    _seed_proposal(db, "mission_e5", "rejected_malformed")
    _seed_proposal(
        db,
        "mission_e6",
        "approved",
        plan_response={"safety": {"decision": "BLOCK", "shepherd_available": True}},
    )
    mission_evaluation_store.run_evaluation(db)

    total, anomalies = mission_evaluation_store.list_evaluations(db, verdict="anomaly")
    assert total == 1
    assert anomalies[0].mission_id == "mission_e6"

    total_clean, clean_rows = mission_evaluation_store.list_evaluations(db, verdict="clean")
    assert total_clean == 1
    assert clean_rows[0].mission_id == "mission_e5"


def test_summary_with_zero_evaluations(db: Session):
    result = mission_evaluation_store.summary(db)
    assert result["total_evaluated"] == 0
    assert result["plan_malformed_rate"] == 0.0
    assert result["anomaly_approved_despite_block_count"] == 0


def test_summary_computes_rates_correctly(db: Session):
    _seed_proposal(db, "mission_e7", "rejected_malformed")
    _seed_proposal(db, "mission_e8", "approved", plan_response={"safety": {"decision": "ALLOW", "shepherd_available": True}})
    mission_evaluation_store.run_evaluation(db)

    result = mission_evaluation_store.summary(db)
    assert result["total_evaluated"] == 2
    assert result["plan_malformed_rate"] == 0.5
    assert result["human_approved_count"] == 1
```

- [ ] **Step 3: Run the tests**

Run: `cd backend && python -m pytest tests/test_mission_evaluation_store.py -v`
Expected: 6/6 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/mission_evaluation_store.py backend/tests/test_mission_evaluation_store.py
git commit -m "feat(mission-evaluator): evaluation run + list/summary store"
```

---

### Task 4: HTTP endpoints + router registration + live verification

**Files:**
- Create: `backend/app/api/v1/endpoints/mission_evaluations.py`
- Modify: `backend/app/api/api.py` (register the router, mirroring the
  `missions`/`_HAS_MISSIONS` conditional-import pattern exactly)
- Test: `backend/tests/test_mission_evaluations_endpoint.py`

**Interfaces:**
- Consumes: Task 3's `mission_evaluation_store.run_evaluation/list_evaluations/summary`,
  `app.api.deps.get_current_active_user` (unmodified), `app.db.session.get_db`
  (unmodified).
- Produces: `POST /api/v1/mission-evaluations/run`, `GET /api/v1/mission-evaluations`,
  `GET /api/v1/mission-evaluations/summary` — all authed, all 200 on
  success (this endpoint has no terminal-failure states to encode the
  way `missions.py`'s `propose` does — a run either evaluates zero-or-more
  missions successfully or the request itself errors, there's no
  partial-success status field to report).

- [ ] **Step 1: Write the endpoint module**

```python
# backend/app/api/v1/endpoints/mission_evaluations.py
"""
Mission Evaluator v1 -- HTTP surface.

Read-only observer over mission_proposals: POST /run scores every
terminal mission not yet evaluated, GET / lists results, GET /summary
gives the aggregate rollup. All three routes reuse
deps.get_current_active_user unmodified -- same auth convention as every
other human-facing backend endpoint in this repo (missions.py,
governance.py). See
docs/superpowers/specs/2026-08-21-mission-evaluator-design.md §4-6.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.db.session import get_db
from app.models import models
from app.models.mission_evaluation import MissionEvaluation
from app.services import mission_evaluation_store

router = APIRouter()


def _serialize(row: MissionEvaluation) -> dict[str, Any]:
    return {
        "mission_id": row.mission_id,
        "verdict": row.verdict,
        "checks": row.checks,
        "summary": row.summary,
        "evaluated_at": row.evaluated_at.isoformat() if row.evaluated_at else None,
    }


@router.post("/run", status_code=200)
def run(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    return mission_evaluation_store.run_evaluation(db)


@router.get("")
def list_evaluations(
    verdict: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    total, rows = mission_evaluation_store.list_evaluations(
        db, verdict=verdict, limit=limit, offset=offset
    )
    return {"total": total, "count": len(rows), "rows": [_serialize(r) for r in rows]}


@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    return mission_evaluation_store.summary(db)
```

- [ ] **Step 2: Register the router in `api.py`**

Add near the `missions`/`_HAS_MISSIONS` block (same pattern):

```python
# Mission Evaluator v1 (requires the mission_evaluations model/migration)
try:
    from app.api.v1.endpoints import mission_evaluations
    _HAS_MISSION_EVALUATIONS = True
except Exception as _e:
    import logging as _log
    _log.getLogger(__name__).warning("Mission Evaluator endpoints unavailable (old image): %s", _e)
    _HAS_MISSION_EVALUATIONS = False
```

And, alongside the other conditional `include_router` calls:

```python
if _HAS_MISSION_EVALUATIONS:
    api_router.include_router(mission_evaluations.router, prefix="/mission-evaluations", tags=["mission-evaluator"])  # Mission Evaluator v1
```

**Route ordering note**: FastAPI matches routes in registration order
within a single `APIRouter`. This router only has 3 routes
(`POST /run`, `GET ""`, `GET /summary`) with no path-parameter route
(unlike `missions.py`'s `/{mission_id}/review`), so there's no
literal-vs-parameter collision risk here — but keep `/run` and
`/summary` defined before any future path-parameter route is ever added
to this router, to avoid the same class of ordering bug other FastAPI
apps commonly hit.

- [ ] **Step 3: Write the tests**

```python
# backend/tests/test_mission_evaluations_endpoint.py
from jose import jwt

from app.core import security
from app.core.config import settings
from app.models import models
from app.models.mission import MissionProposal


def _make_user(db):
    user = models.User(
        email="evaluator-tester@example.com",
        hashed_password="x",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_headers(user):
    token = jwt.encode({"sub": str(user.id)}, settings.JWT_SECRET, algorithm=security.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def _seed_proposal(db, mission_id, status, plan_response=None):
    db.add(
        MissionProposal(
            mission_id=mission_id,
            status=status,
            goal="g",
            truth_snapshot_ref="sha256:abc",
            plan=None,
            plan_response=plan_response,
        )
    )
    db.commit()


def test_run_requires_auth(client):
    resp = client.post("/api/v1/mission-evaluations/run")
    assert resp.status_code in (401, 403)


def test_list_requires_auth(client):
    resp = client.get("/api/v1/mission-evaluations")
    assert resp.status_code in (401, 403)


def test_summary_requires_auth(client):
    resp = client.get("/api/v1/mission-evaluations/summary")
    assert resp.status_code in (401, 403)


def test_run_evaluates_seeded_terminal_mission(client, db):
    user = _make_user(db)
    _seed_proposal(db, "mission_ep1", "rejected_malformed")

    resp = client.post("/api/v1/mission-evaluations/run", headers=_auth_headers(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["evaluated_count"] == 1
    assert body["anomaly_count"] == 0


def test_run_flags_flagship_anomaly_end_to_end(client, db):
    user = _make_user(db)
    _seed_proposal(
        db,
        "mission_ep2",
        "approved",
        plan_response={"safety": {"decision": "BLOCK", "shepherd_available": True}},
    )

    resp = client.post("/api/v1/mission-evaluations/run", headers=_auth_headers(user))
    assert resp.status_code == 200
    assert resp.json()["anomaly_count"] == 1

    list_resp = client.get(
        "/api/v1/mission-evaluations?verdict=anomaly", headers=_auth_headers(user)
    )
    assert list_resp.status_code == 200
    rows = list_resp.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["mission_id"] == "mission_ep2"
    assert rows[0]["checks"]["anomaly_approved_despite_block"] is True


def test_summary_endpoint_returns_rollup(client, db):
    user = _make_user(db)
    _seed_proposal(db, "mission_ep3", "preview_unavailable")
    client.post("/api/v1/mission-evaluations/run", headers=_auth_headers(user))

    resp = client.get("/api/v1/mission-evaluations/summary", headers=_auth_headers(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_evaluated"] == 1
    assert body["preview_failed_rate"] == 1.0
```

- [ ] **Step 4: Run the tests**

Run: `cd backend && python -m pytest tests/test_mission_evaluations_endpoint.py -v`
Expected: 6/6 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/mission_evaluations.py backend/app/api/api.py backend/tests/test_mission_evaluations_endpoint.py
git commit -m "feat(mission-evaluator): HTTP endpoints, auth-gated, registered"
```

- [ ] **Step 6: Run the migration against the live DB**

```bash
cd backend
alembic upgrade head
```

Expected: applies `021_add_mission_evaluations`, no errors. Verify:

```bash
docker exec -i postgres psql -U postgres -d hypercode -c "\d mission_evaluations"
```

- [ ] **Step 7: Rebuild + recreate `hypercode-core`**

Mission Director Phase 1's own live verification found `hypercode-core`
doesn't auto-pick-up new backend code (no volume mount for `backend/app`,
only `alembic`/`alembic.ini`). Rebuild explicitly:

```bash
docker compose -f docker-compose.core.yml build hypercode-core
docker compose -f docker-compose.core.yml up -d hypercode-core
```

(If the full multi-file `docker compose` command is still blocked by the
pre-existing, unrelated `broski-bot` duplicate-`security_opt` YAML merge
error — a known issue flagged during Mission Director Phase 1's own Task
6, not something to fix here — use `docker-compose.core.yml` alone, same
workaround.)

Verify the new code is live before testing further:

```bash
docker exec hypercode-core python -c "import app.api.api as api; print(getattr(api, '_HAS_MISSION_EVALUATIONS', 'ATTR_MISSING'))"
```

Expected: `True`.

- [ ] **Step 8: Real end-to-end verification against the live stack**

Mission Director Phase 1's own live verification already created at
least one real `mission_proposals` row (`mission_ae0fea4b4dc6`, status
`preview_unavailable`) — this plan's `run` call will pick that up too,
alongside anything else already in the table.

Mint a real JWT the same way Mission Director Phase 1's live
verification did (a real user id from the DB, tokenized via
`app.core.security.create_access_token` run inside the `hypercode-core`
container):

```bash
docker exec -i hypercode-core python -c "
from app.core import security
from datetime import timedelta
print(security.create_access_token(1, expires_delta=timedelta(minutes=60)))
"
```

Then:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/mission-evaluations/run \
  -H "Authorization: Bearer <TOKEN>" | python -m json.tool

curl -s http://127.0.0.1:8000/api/v1/mission-evaluations/summary \
  -H "Authorization: Bearer <TOKEN>" | python -m json.tool

curl -s -w "\nHTTP_STATUS:%{http_code}\n" http://127.0.0.1:8000/api/v1/mission-evaluations/run
```

Expected: the first call returns `evaluated_count >= 1` (picking up the
real pre-existing `preview_unavailable` mission at minimum), `summary`
shows a non-zero `total_evaluated` with `preview_failed_rate` reflecting
it, and the unauthenticated call at the end returns `401`.

- [ ] **Step 9: Full-box sweep**

```bash
docker ps --filter "health=unhealthy" --format "{{.Names}}\t{{.Status}}"
```

Expected: empty output.

- [ ] **Step 10: Update `WHATS_DONE.md`**

New top entry: what was built, the scope-narrowing decision made during
brainstorming (v1 evaluates proposal/review quality, not real execution
outcomes — those need Phase 3), the flagship anomaly finding (confirmed
live: `review_mission` never re-checks the safety verdict before
allowing approval — still true after this plan, since this plan
deliberately does not touch `review_mission`, only observes it), and the
real `run`/`summary` verification results from Step 8.

- [ ] **Step 11: Commit + push**

```bash
git add WHATS_DONE.md
git commit -m "docs: mission evaluator v1 live"
git fetch origin main
git rebase origin/main
git push
```

---

## Self-Review Notes (completed during plan authoring)

- **Spec coverage:** §1 (table) → Task 1. §2 (checks shape, including
  the `shepherd_available` refinement added after the second-opinion
  review) → Task 2. §3 (evaluable missions) → Task 2's `TERMINAL_STATUSES`.
  §4 (`POST /run`) → Task 3's `run_evaluation` + Task 4's route. §5
  (`GET /`) → Task 3's `list_evaluations` + Task 4's route. §6 (`GET
  /summary`) → Task 3's `summary` + Task 4's route. §7 (file list) →
  matches Tasks 1-4's file lists exactly. Testing Plan's 3 named test
  files → Tasks 2/3/4's test files (renamed slightly for clarity but
  covering the same scope: unit/store/endpoint). Rollout Order 1-5 →
  Tasks 1-4 plus Task 4's Steps 6-9 for live verification.
- **Type consistency checked:** `evaluate_mission`'s return dict keys
  match `MissionEvaluation.checks`'s expected shape exactly across
  Task 2 (producer), Task 3 (consumer — pops `verdict`/`summary` before
  storing the rest as `checks`), and Task 4 (serializer, reads
  `row.checks` as-is). No drift.
- **No placeholders:** every step has literal, runnable code or an exact
  shell command.
- **Import path check** (this plan's own Global Constraints item, driven
  by a real mistake in a reviewed second-opinion sketch of this same
  feature): every new file uses `from app.X import Y`, never `from
  backend.app.X` — verified by writing every import above directly
  against this repo's real, existing `missions.py`/`mission.py` import
  style, not from memory.
