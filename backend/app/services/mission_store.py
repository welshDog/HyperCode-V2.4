"""CRUD for mission_proposals -- Mission Director Phase 1's point-lookup
store. Every write here is paired with a Governance Ledger write at the
call site (missions.py endpoint); this module only owns current-state,
never the audit trail. See
docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md §6.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.mission import MissionProposal


def create(
    db: Session,
    *,
    mission_id: str,
    status: str,
    goal: str,
    truth_snapshot_ref: Optional[str],
    plan: Optional[dict[str, Any]],
    plan_response: Optional[dict[str, Any]],
    impact: Optional[list[dict[str, Any]]] = None,
    superseded_from: Optional[str] = None,
) -> MissionProposal:
    row = MissionProposal(
        mission_id=mission_id,
        status=status,
        goal=goal,
        truth_snapshot_ref=truth_snapshot_ref,
        plan=plan,
        plan_response=plan_response,
        impact=impact,
        superseded_from=superseded_from,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_by_id(db: Session, mission_id: str) -> Optional[MissionProposal]:
    return db.query(MissionProposal).filter(MissionProposal.mission_id == mission_id).first()


def update_status(db: Session, mission_id: str, new_status: str) -> Optional[MissionProposal]:
    row = get_by_id(db, mission_id)
    if row is None:
        return None
    row.status = new_status
    db.commit()
    db.refresh(row)
    return row
