"""The transition table — fixed code, never LLM-decided.

(mode x decision x kill_switch) -> Outcome. One place, exhaustive, one
test per row. Spec §7.
"""
from __future__ import annotations

from dataclasses import dataclass

_READ_ONLY = {"READ_ONLY"}


@dataclass(frozen=True)
class Outcome:
    mint: bool
    needs_approval: bool
    capability_mode: str | None
    reason: str


def resolve(*, mode: str, decision: str, kill_switch: bool, risk_class: str) -> Outcome:
    if kill_switch:
        if risk_class in _READ_ONLY and decision == "ALLOW":
            # Force DRY_RUN regardless of the requested mode -- CodeRabbit
            # follow-up. Passing the requested `mode` through here could
            # mint a LIVE-mode capability while the kill switch is engaged:
            # the system lease only *stops renewing* on kill (lease.py's
            # docstring), it isn't invalidated, so it can stay valid for up
            # to one lease period (300s) after a kill -- long enough that
            # main.py's `mode == "LIVE" and not lease valid` gate would not
            # catch it. The kill switch must mean "no LIVE capability,
            # period," not "no LIVE capability once the lease also expires."
            return Outcome(True, False, "DRY_RUN", "kill-switch ON; read-only preview permitted")
        return Outcome(False, False, None, "kill-switch ON; all mutation rejected")

    if decision == "BLOCK":
        return Outcome(False, False, None, "policy verdict BLOCK")
    if decision == "ESCALATE":
        return Outcome(False, True, None, "policy verdict ESCALATE; approval required")
    if decision == "ALLOW":
        return Outcome(True, False, mode, f"policy verdict ALLOW; {mode} capability")
    return Outcome(False, False, None, f"unknown decision {decision!r}")
