"""BROski Identity Agent endpoints (P1-1).

Each user has a resident IdentityAgent. These routes expose it for the current
user. High-impact actions (token award) log_action() before executing, and
responses carry the X-BROSKI-IDENTITY header.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.identity_agent import IDENTITY_HEADER, IdentityAgent
from app.api import deps
from app.db.session import get_db
from app.models import models

router = APIRouter()


class AwardRequest(BaseModel):
    amount: int = Field(..., gt=0, le=100_000)
    reason: str = Field(..., min_length=1, max_length=255)
    source_id: str = Field(..., min_length=1, max_length=128, description="Stable id for ledger dedup")


class PermissionQuery(BaseModel):
    action: str


def _serialize(agent: IdentityAgent) -> dict[str, Any]:
    state = agent.state
    return {
        "user_id": agent.user_id,
        "discord_id": agent.discord_id,
        "tier": state.get("tier"),
        "permissions": state.get("permissions", {}),
        "recent_actions": state.get("recent_actions", []),
    }


@router.get("/me")
def get_my_identity(
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    agent = IdentityAgent.get_or_create(current_user.id, db)
    agent.touch()
    response.headers[IDENTITY_HEADER] = agent.discord_id or str(agent.user_id)
    return _serialize(agent)


@router.get("/me/actions")
def get_my_actions(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    agent = IdentityAgent.get_or_create(current_user.id, db)
    actions = agent.state.get("recent_actions", [])
    limit = max(1, min(50, limit))
    return {"count": len(actions), "actions": actions[-limit:][::-1]}


@router.post("/me/check-permission")
def check_my_permission(
    body: PermissionQuery,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    agent = IdentityAgent.get_or_create(current_user.id, db)
    return {"action": body.action, "allowed": agent.check_permission(body.action)}


@router.post("/me/award")
def award_my_tokens(
    body: AwardRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    agent = IdentityAgent.get_or_create(current_user.id, db)
    response.headers[IDENTITY_HEADER] = agent.discord_id or str(agent.user_id)
    try:
        result = agent.award_tokens(body.amount, body.reason, body.source_id, db=db)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return result
