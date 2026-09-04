"""
Reject bad plans before Safety Shepherd is ever contacted.

Unknown `kind` values are already rejected by pydantic's Literal type at
the request-parsing layer (422) before this module runs at all — don't
duplicate that check here.
"""
from __future__ import annotations

from models import PlanRequest

HARD_DENIED_PROFILES = {"prod", "gpu"}


class PlanValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def validate_plan(plan: PlanRequest) -> None:
    if plan.schema_version != 1:
        raise PlanValidationError("unsupported schema_version")

    if not plan.requested_actions:
        raise PlanValidationError("requested_actions must not be empty")

    action_ids = [a.action_id for a in plan.requested_actions]
    if len(action_ids) != len(set(action_ids)):
        raise PlanValidationError("duplicate action_id")

    for action in plan.requested_actions:
        if action.profile is None:
            continue
        # Hard-denied regardless of what the caller's own constraints claim —
        # omitting deny_profiles must not be a way to bypass this.
        if action.profile in HARD_DENIED_PROFILES:
            raise PlanValidationError(f"profile '{action.profile}' is hard-denied")
        if action.profile in plan.constraints.deny_profiles:
            raise PlanValidationError(f"profile '{action.profile}' is denied by constraints")
        if plan.constraints.allow_profiles and action.profile not in plan.constraints.allow_profiles:
            raise PlanValidationError(f"profile '{action.profile}' not in allow_profiles")
