"""Governance Ledger endpoint (P1-2) — read the audit trail of high-impact actions."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.db.session import get_db
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
