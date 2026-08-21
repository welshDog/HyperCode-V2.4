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
