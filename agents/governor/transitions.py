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
            return Outcome(True, False, mode, "kill-switch ON; read-only preview permitted")
        return Outcome(False, False, None, "kill-switch ON; all mutation rejected")

    if decision == "BLOCK":
        return Outcome(False, False, None, "policy verdict BLOCK")
    if decision == "ESCALATE":
        return Outcome(False, True, None, "policy verdict ESCALATE; approval required")
    if decision == "ALLOW":
        return Outcome(True, False, mode, f"policy verdict ALLOW; {mode} capability")
    return Outcome(False, False, None, f"unknown decision {decision!r}")
