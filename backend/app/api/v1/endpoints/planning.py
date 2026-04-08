"""
planning.py — API endpoints for the HyperCode planning system.

Routes:
  POST /api/v1/planning/generate
  POST /api/v1/planning/generate-from-task/{task_id}
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.db.session import get_db
from app.models import models
from app.schemas.planning import CodingPlan, DocumentInput, DocumentType
from app.services.document_parser import document_parser
from app.services.plan_formatter import format_plan_json, format_plan_markdown
from app.services.plan_generator import plan_generator

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# POST /generate
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=CodingPlan)
async def generate_plan(
    *,
    db: Session = Depends(get_db),
    doc_input: DocumentInput,
    persist: bool = Query(
        default=False,
        description="When true, save the plan to the associated Task's output field.",
    ),
    task_id: Optional[int] = Query(
        default=None,
        description="Task ID to attach the plan to (required when persist=True).",
    ),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Parse a document and generate a structured coding plan.

    - Accepts any DocumentInput (issue, prd, design, generic).
    - Returns a CodingPlan.
    - If persist=True and task_id is supplied, saves the plan to Task.output.
    """
    logger.info(f"[PLANNING] /generate called by user {current_user.id}")

    try:
        parsed_doc = await document_parser.parse(doc_input)
    except Exception as exc:
        logger.error(f"[PLANNING] DocumentParser failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Document parsing failed: {exc}")

    try:
        plan = await plan_generator.generate_plan(
            parsed_doc,
            context={"user_id": current_user.id},
        )
    except Exception as exc:
        logger.error(f"[PLANNING] PlanGenerator failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {exc}")

    if persist and task_id is not None:
        _persist_plan_to_task(db, task_id, plan, current_user)

    return plan


# ---------------------------------------------------------------------------
# POST /generate-from-task/{task_id}
# ---------------------------------------------------------------------------

@router.post("/generate-from-task/{task_id}", response_model=CodingPlan)
async def generate_plan_from_task(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    persist: bool = Query(
        default=False,
        description="When true, save the generated plan to Task.output.",
    ),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Fetch an existing Task by ID, use its description as input,
    and generate a structured coding plan.

    - Enforces ownership: regular users can only plan their own tasks.
    - If persist=True, saves the plan back to Task.output.
    """
    query = (
        db.query(models.Task)
        .join(models.Project, models.Task.project_id == models.Project.id)
        .filter(models.Task.id == task_id)
    )
    if not current_user.is_superuser:
        query = query.filter(models.Project.owner_id == current_user.id)
    task = query.first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    content = task.description or task.title
    if not content:
        raise HTTPException(status_code=422, detail="Task has no description to plan from")

    doc_input = DocumentInput(
        content=content,
        document_type=DocumentType.GENERIC,
        metadata={"task_id": task_id, "project_id": task.project_id},
    )

    logger.info(
        f"[PLANNING] /generate-from-task/{task_id} called by user {current_user.id}"
    )

    try:
        parsed_doc = await document_parser.parse(doc_input)
    except Exception as exc:
        logger.error(f"[PLANNING] DocumentParser failed for task {task_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Document parsing failed: {exc}")

    try:
        plan = await plan_generator.generate_plan(
            parsed_doc,
            context={"task_id": task_id, "user_id": current_user.id},
        )
    except Exception as exc:
        logger.error(f"[PLANNING] PlanGenerator failed for task {task_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {exc}")

    if persist:
        _persist_plan_to_task(db, task_id, plan, current_user)

    return plan


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _persist_plan_to_task(
    db: Session,
    task_id: int,
    plan: CodingPlan,
    current_user: models.User,
) -> None:
    """Save the plan JSON to Task.output; silently logs errors (never raises)."""
    try:
        query = (
            db.query(models.Task)
            .join(models.Project, models.Task.project_id == models.Project.id)
            .filter(models.Task.id == task_id)
        )
        if not current_user.is_superuser:
            query = query.filter(models.Project.owner_id == current_user.id)
        task = query.first()
        if task:
            task.output = json.dumps(format_plan_json(plan))
            db.add(task)
            db.commit()
            logger.info(f"[PLANNING] Plan persisted to Task {task_id}.")
        else:
            logger.warning(
                f"[PLANNING] Could not persist plan — Task {task_id} not found."
            )
    except Exception as exc:
        logger.error(f"[PLANNING] Failed to persist plan to Task {task_id}: {exc}")
