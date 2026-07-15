from typing import Any, List
import json
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.config import settings
from app.models import models
from app.api import deps
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Pydantic Models for Dashboard ---
class DashboardTask(BaseModel):
    id: str
    type: str
    description: str
    requires_approval: bool

class ExecuteRequest(BaseModel):
    task: DashboardTask

class LogEntry(BaseModel):
    id: int
    agent: str
    level: str
    msg: str
    time: str


class ApprovalRequestCreate(BaseModel):
    agent: str
    action_type: str
    details: dict = {}
    source: str = "dashboard"


class ApprovalRespond(BaseModel):
    status: str  # approved | rejected
    reason: str | None = None


# --- Approval Requests (Safety Shepherd escalations + dashboard) ---
# Backed by the shared `approval_requests` Redis channel + `approval:*` keys
# (DB 0) that Safety Shepherd and HyperFlow already publish to.

PENDING_SET = "approval:pending"


@router.get("/approval-requests")
async def list_approval_requests(
    current_user: Any | None = Depends(deps.get_optional_current_user),
) -> Any:
    """List pending human approval requests for the Mission Control dashboard."""
    if settings.ENVIRONMENT.lower() in {"production", "staging"} and current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    try:
        ids = await r.smembers(PENDING_SET)
        items = []
        for approval_id in ids:
            raw = await r.get(f"approval:{approval_id}")
            if raw:
                items.append(json.loads(raw))
            else:
                await r.srem(PENDING_SET, approval_id)  # expired — prune
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"count": len(items), "requests": items}
    finally:
        await r.aclose()


@router.post("/approval-requests")
async def create_approval_request(
    body: ApprovalRequestCreate,
    current_user: Any | None = Depends(deps.get_optional_current_user),
) -> Any:
    """Raise a human approval request (Safety Shepherd ESCALATE target)."""
    approval_id = str(uuid.uuid4())
    request = {
        "id": approval_id,
        "agent": body.agent,
        "action_type": body.action_type,
        "source": body.source,
        "details": body.details,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    try:
        payload = json.dumps(request)
        await r.set(f"approval:{approval_id}", payload, ex=900)
        await r.sadd(PENDING_SET, approval_id)
        await r.publish("approval_requests", payload)
    finally:
        await r.aclose()
    return {"id": approval_id, "status": "pending"}


@router.post("/approval-requests/{approval_id}/respond")
async def respond_approval_request(
    approval_id: str,
    body: ApprovalRespond,
    current_user: Any | None = Depends(deps.get_optional_current_user),
) -> Any:
    """Resolve a pending approval (human approve/reject)."""
    if settings.ENVIRONMENT.lower() in {"production", "staging"} and current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    try:
        raw = await r.get(f"approval:{approval_id}")
        if not raw:
            raise HTTPException(status_code=404, detail="Approval not found or expired")
        request = json.loads(raw)
        request["status"] = body.status
        await r.set(f"approval:{approval_id}", json.dumps(request), ex=3600)
        await r.set(
            f"approval:{approval_id}:response",
            json.dumps({"status": body.status, "reason": body.reason,
                        "responded_at": datetime.now(timezone.utc).isoformat()}),
            ex=3600,
        )
        await r.srem(PENDING_SET, approval_id)
        return {"id": approval_id, "status": body.status}
    finally:
        await r.aclose()


# --- Endpoints ---

@router.post("/execute")
def execute_command(
    request: ExecuteRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Executes a command from the Dashboard.
    Maps to the standard Task creation flow.
    """
    description = request.task.description

    # Resolve the user's own project — superusers may use any project
    if current_user.is_superuser:
        project = db.query(models.Project).first()
    else:
        project = db.query(models.Project).filter(
            models.Project.owner_id == current_user.id
        ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No project found for this user. Create a project first.",
        )

    # Simple logic to determine task type from description
    task_type = "general"
    if "research" in description.lower():
        task_type = "research"
    elif "translate" in description.lower():
        task_type = "translate"
    elif "health" in description.lower() or "status" in description.lower():
        task_type = "health"

    # Create Task in DB
    task = models.Task(
        title=f"Dashboard Command: {description[:30]}...",
        description=description,
        priority="high",
        project_id=project.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Push to Celery
    queue_payload = {
        "id": task.id,
        "title": task.title,
        "type": task_type,
        "description": task.description,
        "priority": "high",
        "status": "pending",
        "project_id": project.id,
    }
    
    from app.core.celery_app import celery_app
    celery_app.send_task("hypercode.tasks.process_agent_job", args=[queue_payload])
    
    logger.info(f"Dashboard command executed: {description} -> Task {task.id}")

    return {
        "status": "success", 
        "message": f"Command routed to {task_type.capitalize()} Agent (Task ID: {task.id})",
        "task_id": task.id
    }

@router.get("/logs", response_model=List[LogEntry])
def get_dashboard_logs(
    db: Session = Depends(get_db),
    skip: int = 0, 
    limit: int = 50,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Returns recent system events formatted for the Dashboard "Live Ops" feed.
    Currently pulls from the Tasks table as a proxy for logs.
    """
    capped_limit = min(limit, 200)
    query = db.query(models.Task).join(models.Project, models.Task.project_id == models.Project.id).order_by(models.Task.id.desc())
    if not current_user.is_superuser:
        query = query.filter(models.Project.owner_id == current_user.id)
    tasks = query.offset(skip).limit(capped_limit).all()
    
    logs = []
    for t in tasks:
        task_id = int(t.id) if t.id is not None else 0
        # Created Log
        logs.append({
            "id": task_id * 10, # Fake ID to avoid collision
            "agent": "Orchestrator",
            "level": "info",
            "msg": f"Task {task_id} queued: {t.title}",
            "time": t.created_at.strftime("%H:%M:%S") if t.created_at else "Now"
        })
        
        # If complete (we don't track completion time in DB yet, but let's mock it for 'done' tasks)
        # In a real system, we'd query a separate 'AuditLog' table.
        
    return logs
