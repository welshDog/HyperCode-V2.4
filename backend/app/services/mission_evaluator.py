"""
Mission Evaluator v1 -- pure rule logic.

Scores one already-recorded MissionProposal (status + plan_response)
against deterministic checks. No DB access, no network call, no LLM
call -- a pure function, trivially unit-testable, kept separate from
persistence (mission_evaluation_store.py) and HTTP (mission_evaluations
endpoint) concerns. See
docs/superpowers/specs/2026-08-21-mission-evaluator-design.md §2-3.
"""
from __future__ import annotations

from typing import Any, Optional

TERMINAL_STATUSES = frozenset(
    {"rejected_malformed", "preview_unavailable", "approved", "rejected"}
)


def _safety_field(plan_response: Optional[dict[str, Any]], field: str) -> Any:
    if not plan_response:
        return None
    safety = plan_response.get("safety")
    if not isinstance(safety, dict):
        return None
    return safety.get(field)


def _human_decision(status: str) -> Optional[str]:
    if status == "approved":
        return "approved"
    if status == "rejected":
        return "rejected"
    return None


def _summary(checks: dict[str, Any]) -> str:
    if checks["anomaly_approved_despite_block"]:
        return "anomaly: approved despite a genuine Shepherd BLOCK verdict"
    if checks["anomaly_approved_despite_shepherd_down"]:
        return "anomaly: approved while Shepherd was unreachable (fail-closed BLOCK)"
    if checks["anomaly_rejected_despite_allow"]:
        return "anomaly: rejected despite an ALLOW verdict"
    return f"clean: {checks['status']}"


def evaluate_mission(status: str, plan_response: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Returns a dict with every key from the spec's §2 `checks` shape,
    plus `verdict` and `summary`. Never raises on a null or malformed
    plan_response -- degrades every safety-derived field to None instead."""
    plan_malformed = status == "rejected_malformed"
    preview_failed = status == "preview_unavailable"
    safety_decision = _safety_field(plan_response, "decision")
    shepherd_available = _safety_field(plan_response, "shepherd_available")
    human_decision = _human_decision(status)

    anomaly_approved_despite_block = (
        human_decision == "approved"
        and safety_decision == "BLOCK"
        and shepherd_available is True
    )
    anomaly_approved_despite_shepherd_down = (
        human_decision == "approved"
        and safety_decision == "BLOCK"
        and shepherd_available is False
    )
    anomaly_rejected_despite_allow = (
        human_decision == "rejected" and safety_decision == "ALLOW"
    )

    checks: dict[str, Any] = {
        "status": status,
        "plan_malformed": plan_malformed,
        "preview_failed": preview_failed,
        "safety_decision": safety_decision,
        "shepherd_available": shepherd_available,
        "human_decision": human_decision,
        "anomaly_approved_despite_block": anomaly_approved_despite_block,
        "anomaly_approved_despite_shepherd_down": anomaly_approved_despite_shepherd_down,
        "anomaly_rejected_despite_allow": anomaly_rejected_despite_allow,
    }

    verdict = (
        "anomaly"
        if (
            anomaly_approved_despite_block
            or anomaly_approved_despite_shepherd_down
            or anomaly_rejected_despite_allow
        )
        else "clean"
    )

    return {**checks, "verdict": verdict, "summary": _summary(checks)}
