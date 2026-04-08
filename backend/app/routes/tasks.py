"""
Task 9 — Public Dashboard Task CRUD
Provides:
  GET    /api/tasks       — list dashboard tasks (no auth)
  POST   /api/tasks       — create dashboard task (no auth)
  GET    /api/tasks/{id}  — get single task
  PUT    /api/tasks/{id}  — update task status/priority
  DELETE /api/tasks/{id}  — soft-delete (sets status=cancelled)

Auto-task logic:
  POST /api/tasks/check-errors  — checks current error rate; if > 5% creates an
  auto task and publishes to Redis events channel (called by healer or cron).

No authentication required — designed for the live dashboard panel.
"""

import datetime
import json
import logging
import uuid
from typing import List, Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.dashboard_task import DashboardTask, DashboardTaskSource, DashboardTaskStatus

router = APIRouter()
logger = logging.getLogger(__name__)

# Import the event publish helper lazily to avoid circular imports
EVENTS_CHANNEL = "hypercode:events:channel"
EVENTS_LIST    = "hypercode:events"


# ── Pydantic models ────────────────────────────────────────────────────────────

class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    source: str
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    source: str = "manual"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None


class TaskListResponse(BaseModel):
    tasks: List[TaskOut]
    total: int


def _to_out(task: DashboardTask) -> TaskOut:
    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status.value if task.status else "todo",
        priority=task.priority or "medium",
        source=task.source.value if task.source else "manual",
        created_at=task.created_at.isoformat() if task.created_at else "",
        updated_at=task.updated_at.isoformat() if task.updated_at else None,
    )


async def _publish_event(event_data: dict) -> None:
    """Publish a task event to Redis for the live event stream."""
    r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    try:
        payload = json.dumps({
            "id": str(uuid.uuid4()),
            "channel": "ws_tasks",
            "agentId": "system",
            "taskId": str(event_data.get("id", "")),
            "status": event_data.get("status", "created"),
            "payload": event_data,
            "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        async with r.pipeline(transaction=False) as pipe:
            pipe.rpush(EVENTS_LIST, payload)
            pipe.ltrim(EVENTS_LIST, -500, -1)
            pipe.publish(EVENTS_CHANNEL, payload)
            await pipe.execute()
    except Exception:
        logger.warning("Failed to publish task event to Redis")
    finally:
        await r.aclose()


# ── CRUD endpoints ─────────────────────────────────────────────────────────────

@router.get("/tasks", response_model=TaskListResponse)
@router.get("/tasks/", response_model=TaskListResponse, include_in_schema=False)
def list_tasks(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> TaskListResponse:
    """List dashboard tasks. Optionally filter by status."""
    query = db.query(DashboardTask).order_by(DashboardTask.created_at.desc())
    if status:
        try:
            query = query.filter(DashboardTask.status == DashboardTaskStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    total = query.count()
    tasks = query.offset(skip).limit(limit).all()
    return TaskListResponse(tasks=[_to_out(t) for t in tasks], total=total)


@router.post("/tasks", response_model=TaskOut, status_code=201)
async def create_task(body: TaskCreate, db: Session = Depends(get_db)) -> TaskOut:
    """Create a dashboard task (no auth required)."""
    try:
        source = DashboardTaskSource(body.source)
    except ValueError:
        source = DashboardTaskSource.MANUAL

    task = DashboardTask(
        title=body.title,
        description=body.description,
        priority=body.priority,
        source=source,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    out = _to_out(task)
    await _publish_event({"id": task.id, "title": task.title, "status": "created"})
    return out


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)) -> TaskOut:
    task = db.query(DashboardTask).filter(DashboardTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _to_out(task)


@router.put("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    body: TaskUpdate,
    db: Session = Depends(get_db),
) -> TaskOut:
    task = db.query(DashboardTask).filter(DashboardTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if body.title is not None:
        task.title = body.title
    if body.description is not None:
        task.description = body.description
    if body.priority is not None:
        task.priority = body.priority
    if body.status is not None:
        try:
            task.status = DashboardTaskStatus(body.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")

    db.add(task)
    db.commit()
    db.refresh(task)
    out = _to_out(task)
    await _publish_event({"id": task.id, "title": task.title, "status": task.status.value})
    return out


@router.delete("/tasks/{task_id}", response_model=TaskOut)
def cancel_task(task_id: int, db: Session = Depends(get_db)) -> TaskOut:
    """Soft-delete: sets status to 'cancelled'."""
    task = db.query(DashboardTask).filter(DashboardTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = DashboardTaskStatus.CANCELLED
    db.add(task)
    db.commit()
    db.refresh(task)
    return _to_out(task)


# ── Auto-task: trigger when error rate > 5% ───────────────────────────────────

class AutoTaskResult(BaseModel):
    triggered: bool
    task: Optional[TaskOut] = None
    reason: str


@router.post("/tasks/check-errors", response_model=AutoTaskResult)
async def check_and_create_error_task(db: Session = Depends(get_db)) -> AutoTaskResult:
    """
    Called by healer-agent or cron.
    If the current error rate exceeds 5%, auto-creates an incident task
    (only once per 10 minutes to avoid spam).
    """
    # Import here to avoid circular dependency with reliability module
    from app.routes.reliability import get_error_budget

    budget = await get_error_budget()

    if budget.actualErrorPct <= 5.0:
        return AutoTaskResult(
            triggered=False,
            reason=f"Error rate {budget.actualErrorPct:.2f}% is within threshold",
        )

    # Check if an auto task was recently created (within 10 minutes)
    ten_min_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
    recent = (
        db.query(DashboardTask)
        .filter(
            DashboardTask.source == DashboardTaskSource.AUTO,
            DashboardTask.created_at >= ten_min_ago,
        )
        .first()
    )
    if recent:
        return AutoTaskResult(
            triggered=False,
            reason=f"Auto-task already created {recent.created_at.isoformat()} (throttle: 10min)",
        )

    task = DashboardTask(
        title=f"ALERT: Error rate {budget.actualErrorPct:.1f}% exceeds 5% SLO",
        description=(
            f"Auto-created by error rate monitor.\n"
            f"Error rate: {budget.actualErrorPct:.2f}% over last {budget.windowMinutes} minutes.\n"
            f"Total errors: {budget.errorTotal} / {budget.requestTotal} requests.\n"
            f"Error budget remaining: {budget.budgetPct:.1f}%."
        ),
        priority="critical",
        source=DashboardTaskSource.AUTO,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    out = _to_out(task)
    await _publish_event({
        "id": task.id,
        "title": task.title,
        "status": "created",
        "errorRatePct": budget.actualErrorPct,
    })
    logger.warning(f"Auto-task created: error rate {budget.actualErrorPct:.2f}% (task id={task.id})")
    return AutoTaskResult(triggered=True, task=out, reason="Error rate exceeded 5% SLO threshold")
