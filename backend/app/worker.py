from app.core.celery_app import celery_app
from celery import Task as CeleryTask
from celery.signals import worker_ready
from app.agents.router import router
from app.db.session import SessionLocal
from app.models.models import Task, TaskStatus
import asyncio
from datetime import datetime, timezone
import logging
import os
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_HEARTBEAT_KEY = "agents:heartbeat:celery-worker"
_REDIS_URL     = os.getenv("HYPERCODE_REDIS_URL", "redis://redis:6379/0")


def _celery_heartbeat_thread() -> None:
    """
    Daemon thread: publishes a Redis heartbeat every 10s so the dashboard
    shows celery-worker as an active agent.
    Uses the synchronous redis client — safe inside a Celery worker process.
    """
    import redis as _redis_sync
    r = _redis_sync.Redis.from_url(_REDIS_URL, decode_responses=True, socket_connect_timeout=3)
    while True:
        try:
            r.hset(
                _HEARTBEAT_KEY,
                mapping={
                    "name": "celery-worker",
                    "status": "online",
                    "last_seen": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            )
            r.expire(_HEARTBEAT_KEY, 30)
        except Exception as exc:
            logger.warning(f"Celery heartbeat failed (non-fatal): {exc}")
        time.sleep(10)


@worker_ready.connect
def _on_worker_ready(sender, **kwargs) -> None:
    t = threading.Thread(target=_celery_heartbeat_thread, name="celery-heartbeat", daemon=True)
    t.start()
    logger.info("Celery worker heartbeat thread started — publishing to Redis every 10s")

class AgentTask(CeleryTask):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"[Worker] Task {task_id} failed: {exc}")

@celery_app.task(name="hypercode.tasks.process_agent_job")
def process_agent_job(task_payload: dict):
    """
    Main worker entrypoint for processing agent tasks.
    """
    logger.info(f"[Worker] Received task: {task_payload}")
    
    task_id = task_payload.get("id")
    task_type = task_payload.get("type", "general")
    description = task_payload.get("description", "")
    output_dir = "/app/outputs" # Internal Docker path

    try:
        # Pass context with task_id to router
        context = {"task_id": task_id, "conversation_id": f"task-{task_id}"}
        
        # Run the Router asynchronously
        plan: Any = asyncio.run(router.route_task(task_type, description, context=context))
        if not isinstance(plan, str) or not plan.strip():
            raise RuntimeError(f"Agent returned invalid output type={type(plan).__name__}")
        
        logger.info(f"[INFO] Agent Output Preview: {plan[:100]}...")
        
        # Update Task in DB
        db = SessionLocal()
        try:
            task_record = db.query(Task).filter(Task.id == task_id).first()
            if task_record:
                old_status = task_record.status
                task_record.output = plan
                task_record.status = TaskStatus.DONE
                db.commit()
                logger.info(f"[Worker] Updated Task {task_id} status to DONE")
                if old_status != TaskStatus.DONE:
                    from app.services import broski_service
                    user_id = task_record.assignee_id or task_record.project.owner_id
                    broski_service.award_coins(user_id, 10, "Task completed", db)
                    broski_service.award_xp(user_id, 25, "Task completed", db)
                    wallet = broski_service.get_wallet(user_id, db)
                    today = datetime.now(timezone.utc).date()
                    last = wallet.last_first_task_date.astimezone(timezone.utc).date() if wallet.last_first_task_date else None
                    if last is None or last < today:
                        broski_service.award_xp(user_id, 15, "First task of the day bonus!", db)
                        wallet.last_first_task_date = datetime.now(timezone.utc)
                        db.commit()
            else:
                logger.warning(f"[Worker] Task {task_id} not found in DB")
        except Exception as db_e:
            logger.error(f"[Worker] DB Error: {db_e}")
            db.rollback()
        finally:
            db.close()
        
        # Save output to disk (Legacy/Backup)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        file_path = f"{output_dir}/{task_type}_{task_id}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# 🧠 HyperCode Output: {task_type.upper()}\n\n")
            f.write(plan)
            
        logger.info(f"[Worker] Saved output to {file_path}")
        
        return {"status": "completed", "output_file": file_path, "preview": plan[:200]}

    except Exception as e:
        logger.error(f"[Worker] Error processing task {task_id}: {e}")
        return {"status": "failed", "error": str(e)}
