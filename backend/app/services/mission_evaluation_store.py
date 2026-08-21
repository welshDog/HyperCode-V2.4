# backend/app/services/mission_evaluation_store.py
"""
CRUD + the actual evaluation run for Mission Evaluator v1. Queries
mission_proposals (Mission Director Phase 1's table) read-only; writes
only to this feature's own mission_evaluations table. See
docs/superpowers/specs/2026-08-21-mission-evaluator-design.md §4-6.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.mission import MissionProposal
from app.models.mission_evaluation import MissionEvaluation
from app.services.mission_evaluator import TERMINAL_STATUSES, evaluate_mission


def run_evaluation(db: Session) -> dict[str, int]:
    already_evaluated_ids = {
        row.mission_id for row in db.query(MissionEvaluation.mission_id).all()
    }

    candidates = (
        db.query(MissionProposal)
        .filter(MissionProposal.status.in_(TERMINAL_STATUSES))
        .all()
    )

    evaluated_count = 0
    anomaly_count = 0
    already_evaluated_skipped = 0

    for proposal in candidates:
        if proposal.mission_id in already_evaluated_ids:
            already_evaluated_skipped += 1
            continue

        result = evaluate_mission(proposal.status, proposal.plan_response)
        verdict = result.pop("verdict")
        summary = result.pop("summary")

        row = MissionEvaluation(
            mission_id=proposal.mission_id,
            verdict=verdict,
            checks=result,
            summary=summary,
        )
        db.add(row)
        db.commit()

        evaluated_count += 1
        if verdict == "anomaly":
            anomaly_count += 1

    return {
        "evaluated_count": evaluated_count,
        "anomaly_count": anomaly_count,
        "already_evaluated_skipped": already_evaluated_skipped,
    }


def list_evaluations(
    db: Session,
    *,
    verdict: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[MissionEvaluation]]:
    q = db.query(MissionEvaluation)
    if verdict:
        q = q.filter(MissionEvaluation.verdict == verdict)
    total = q.count()
    rows = q.order_by(MissionEvaluation.evaluated_at.desc()).offset(offset).limit(limit).all()
    return total, rows


def summary(db: Session) -> dict[str, Any]:
    rows = db.query(MissionEvaluation).all()
    total = len(rows)
    if total == 0:
        return {
            "total_evaluated": 0,
            "plan_malformed_rate": 0.0,
            "preview_failed_rate": 0.0,
            "human_approved_count": 0,
            "human_rejected_count": 0,
            "anomaly_approved_despite_block_count": 0,
            "anomaly_approved_despite_shepherd_down_count": 0,
            "anomaly_rejected_despite_allow_count": 0,
        }

    plan_malformed = sum(1 for r in rows if r.checks.get("plan_malformed"))
    preview_failed = sum(1 for r in rows if r.checks.get("preview_failed"))
    human_approved = sum(1 for r in rows if r.checks.get("human_decision") == "approved")
    human_rejected = sum(1 for r in rows if r.checks.get("human_decision") == "rejected")
    anomaly_block = sum(1 for r in rows if r.checks.get("anomaly_approved_despite_block"))
    anomaly_shepherd_down = sum(
        1 for r in rows if r.checks.get("anomaly_approved_despite_shepherd_down")
    )
    anomaly_allow = sum(1 for r in rows if r.checks.get("anomaly_rejected_despite_allow"))

    return {
        "total_evaluated": total,
        "plan_malformed_rate": plan_malformed / total,
        "preview_failed_rate": preview_failed / total,
        "human_approved_count": human_approved,
        "human_rejected_count": human_rejected,
        "anomaly_approved_despite_block_count": anomaly_block,
        "anomaly_approved_despite_shepherd_down_count": anomaly_shepherd_down,
        "anomaly_rejected_despite_allow_count": anomaly_allow,
    }
