from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api import deps
from app.observability import dlq

router = APIRouter()


class DLQReplayRequest(BaseModel):
    task_id: Optional[str] = None
    index: Optional[int] = Field(default=None, ge=0)
    queue: Optional[str] = None


@router.get("/dlq/stats")
def dlq_stats(
    _current_user=Depends(deps.get_current_active_superuser),
) -> dict[str, Any]:
    return dlq.stats()


@router.get("/dlq")
def dlq_list(
    limit: int = 50,
    offset: int = 0,
    _current_user=Depends(deps.get_current_active_superuser),
) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)
    items = dlq.list_envelopes(limit=safe_limit, offset=safe_offset)
    return {"items": items, "limit": safe_limit, "offset": safe_offset}


@router.post("/dlq/replay")
def dlq_replay(
    body: DLQReplayRequest,
    _current_user=Depends(deps.get_current_active_superuser),
) -> dict[str, Any]:
    return dlq.replay(task_id=body.task_id, index=body.index, queue=body.queue)


@router.delete("/dlq")
def dlq_purge_all(
    _current_user=Depends(deps.get_current_active_superuser),
) -> dict[str, Any]:
    removed = dlq.purge_all()
    return {"purged": removed}


@router.delete("/dlq/{task_id}")
def dlq_delete_task_id(
    task_id: str,
    _current_user=Depends(deps.get_current_active_superuser),
) -> dict[str, Any]:
    removed = dlq.remove_by_task_id(task_id)
    return {"removed": removed, "task_id": task_id}
