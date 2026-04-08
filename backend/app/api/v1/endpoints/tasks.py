from typing import Any, List, Optional

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.Task])
def read_tasks(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve tasks.
    """
    query = db.query(models.Task).join(models.Project, models.Task.project_id == models.Project.id)
    if not current_user.is_superuser:
        query = query.filter(models.Project.owner_id == current_user.id)
    tasks = query.offset(skip).limit(limit).all()
    return tasks


@router.post("/", response_model=schemas.Task)
async def create_task(
    *,
    db: Session = Depends(get_db),
    task_in: schemas.TaskCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new task.

    If generate_plan=True is set on the TaskCreate payload, DocumentParser +
    PlanGenerator run before Celery dispatch and the resulting plan is stored
    in Task.output.  A plan_reference is also injected into the Celery payload
    so executing agents have full plan context during execution.
    """
    task_data = task_in.dict()
    task_type = task_data.pop("type", "general")
    generate_plan_flag: bool = task_data.pop("generate_plan", False)

    project = db.query(models.Project).filter(models.Project.id == task_in.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    task = models.Task(**task_data)
    db.add(task)
    db.commit()
    db.refresh(task)

    from app.services import broski_service
    broski_service.award_coins(current_user.id, 2, "Task created", db)

    plan_reference: Optional[str] = None

    # ---- Optional: run planning pipeline before dispatch ----
    if generate_plan_flag:
        try:
            from app.schemas.planning import DocumentInput, DocumentType
            from app.services.document_parser import document_parser
            from app.services.plan_generator import plan_generator
            from app.services.plan_formatter import format_plan_json
            import json

            content = task.description or task.title
            doc_input = DocumentInput(
                content=content,
                document_type=DocumentType.GENERIC,
                metadata={"task_id": task.id, "project_id": task.project_id},
            )
            parsed_doc = await document_parser.parse(doc_input)
            plan = await plan_generator.generate_plan(
                parsed_doc,
                context={"task_id": task.id, "user_id": current_user.id},
            )
            plan_json_str = json.dumps(format_plan_json(plan))
            task.output = plan_json_str
            db.add(task)
            db.commit()
            db.refresh(task)
            plan_reference = plan_json_str
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                f"[TASKS] generate_plan failed for task {task.id}: {exc}. "
                "Continuing without plan."
            )

    # ---- Push to Celery Task Queue ----
    queue_payload = {
        "id": task.id,
        "title": task.title,
        "type": task_type,
        "description": task.description or task.title,
        "priority": task.priority,
        "status": "pending",
        "project_id": task.project_id,
    }

    if plan_reference is not None:
        queue_payload["plan_reference"] = plan_reference

    from app.core.celery_app import celery_app
    from celery.exceptions import OperationalError as CeleryOperationalError
    try:
        celery_app.send_task("hypercode.tasks.process_agent_job", args=[queue_payload])
    except CeleryOperationalError as e:
        import logging as _logging
        _logging.getLogger(__name__).error(f"Celery broker unreachable: {e}")
        raise HTTPException(status_code=503, detail="Task queue unavailable. Retry in 30 seconds.")

    return task


@router.get("/{id}", response_model=schemas.Task)
def read_task(
    *,
    db: Session = Depends(get_db),
    id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get task by ID.
    """
    query = db.query(models.Task).join(models.Project, models.Task.project_id == models.Project.id).filter(models.Task.id == id)
    if not current_user.is_superuser:
        query = query.filter(models.Project.owner_id == current_user.id)
    task = query.first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{id}", response_model=schemas.Task)
def update_task(
    *,
    db: Session = Depends(get_db),
    id: int,
    task_in: schemas.TaskUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    task_data = task_in.dict(exclude_unset=True)
    query = db.query(models.Task).join(models.Project, models.Task.project_id == models.Project.id).filter(models.Task.id == id)
    if not current_user.is_superuser:
        query = query.filter(models.Project.owner_id == current_user.id)
    task = query.first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_status = task.status

    if "project_id" in task_data and task_data["project_id"] != task.project_id:
        project = db.query(models.Project).filter(models.Project.id == task_data["project_id"]).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if not current_user.is_superuser and project.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not enough privileges")

    for key, value in task_data.items():
        setattr(task, key, value)

    db.add(task)
    db.commit()
    db.refresh(task)

    if "status" in task_data and old_status != models.TaskStatus.DONE and task.status == models.TaskStatus.DONE:
        from app.services import broski_service
        broski_service.award_coins(current_user.id, 10, "Task completed", db)
        broski_service.award_xp(current_user.id, 25, "Task completed", db)
        wallet = broski_service.get_wallet(current_user.id, db)
        today = datetime.now(timezone.utc).date()
        last = wallet.last_first_task_date.astimezone(timezone.utc).date() if wallet.last_first_task_date else None
        if last is None or last < today:
            broski_service.award_xp(current_user.id, 15, "First task of the day bonus!", db)
            wallet.last_first_task_date = datetime.now(timezone.utc)
            db.commit()

    return task
