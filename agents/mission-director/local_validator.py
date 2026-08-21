# agents/mission-director/local_validator.py
"""
Fast, deterministic well-formedness gate -- NOT a safety decision. Every
actual safety judgment (dangerous categories, profile denials) stays
inside fleet-controller's boundary (plan_validator.py, Safety Shepherd's
policy.py), both untouched by this module. This exists only to avoid
spending a network round-trip on garbage before calling fleet-controller.
See docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md §3.
"""
from __future__ import annotations

from typing import Optional

from models import PlanRequest


class LocalValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def validate(plan: PlanRequest, truth_snapshot_ref: Optional[str]) -> None:
    if not plan.requested_actions:
        raise LocalValidationError("plan.requested_actions must be non-empty")
    if not truth_snapshot_ref:
        raise LocalValidationError("truth_snapshot_ref is required and must be non-empty")
