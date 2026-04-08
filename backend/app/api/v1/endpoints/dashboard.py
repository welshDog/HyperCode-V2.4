from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
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
        project_id=1, # Default project
        # status="pending" # Default
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
        "project_id": 1
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
