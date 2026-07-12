"""Governance Ledger endpoints (P1-2 read + HS-P2c agent write).

GET /ledger  — user-JWT-authed read of the audit trail.
POST /ledger — internal agent-key-authed write path (X-Agent-Key) so services
like the Safety Shepherd can land ALLOW/BLOCK/ESCALATE verdicts in the ledger.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.db.session import get_db
from app.middleware.agent_auth import require_agent_key
from app.models import models
from app.models.governance import GovernanceLedger

router = APIRouter()


def _serialize(row: GovernanceLedger) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "user_id": row.user_id,
        "action": row.action,
        "tool_used": row.tool_used,
        "payload": row.payload,
        "decision": row.decision,
        "agent_name": row.agent_name,
        "approved_by": row.approved_by,
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
    }


@router.get("/ledger")
def get_ledger(
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Paginated governance-ledger rows, newest first. Filter by user_id / action."""
    q = db.query(GovernanceLedger)
    if user_id:
        q = q.filter(GovernanceLedger.user_id == user_id)
    if action:
        q = q.filter(GovernanceLedger.action == action)
    total = q.count()
    rows = q.order_by(GovernanceLedger.timestamp.desc()).offset(offset).limit(limit).all()
    return {"total": total, "count": len(rows), "rows": [_serialize(r) for r in rows]}


class LedgerWriteRequest(BaseModel):
    """A verdict/action another service wants recorded in the ledger."""

    agent: str = Field(..., min_length=1, max_length=128, description="Agent the verdict is about")
    action: str = Field(..., min_length=1, max_length=128, description="e.g. safety.docker")
    decision: str = Field(..., min_length=1, max_length=32, description="ALLOW|BLOCK|ESCALATE")
    tool: Optional[str] = Field(None, max_length=256)
    user_id: str = Field("system", min_length=1, max_length=128)
    payload: Optional[dict[str, Any]] = None
    approved_by: Optional[str] = Field(None, max_length=128)


@router.post("/ledger", status_code=201)
def write_ledger(
    body: LedgerWriteRequest,
    db: Session = Depends(get_db),
    agent_key: dict = Depends(require_agent_key),
) -> Any:
    """Agent-key-authed ledger write (HS-P2c). approved_by defaults to the caller."""
    row = GovernanceLedger(
        user_id=body.user_id,
        action=body.action,
        tool_used=body.tool,
        payload=body.payload,
        decision=body.decision,
        agent_name=body.agent,
        approved_by=body.approved_by or agent_key.get("agent_name") or "agent-key",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": str(row.id), "status": "recorded"}
