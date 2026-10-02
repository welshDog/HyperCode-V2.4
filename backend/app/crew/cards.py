"""Calm Card for a HyperFlow run: what happened, and the ONE thing a person should do next.

Pure and deterministic. The wording is literal and short on purpose (Calm Mode / neurodivergent-first):
at most five summary lines, exactly one next action, details collapsed.
"""

from __future__ import annotations

from typing import Any, Optional

from app.crew.agui import node_label
from app.crew.calm_card import MAX_LINE, MAX_TLDR_LINES, CalmCard, CardStatus
from app.crew.redaction import redact_text

DONE_LABELS: dict[str, str] = {
    "plan": "Plan written",
    "approve": "You approved the plan",
    "seal": "Approval recorded",
    "build": "Builder proposed a change",
    "verify": "Verifier reviewed it",
}


def _fit(text: str, limit: int = MAX_LINE) -> str:
    one_line = " ".join(redact_text(text).split())
    return one_line if len(one_line) <= limit else one_line[: limit - 1] + "…"


def _guard_data(history: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    for entry in reversed(history):
        if not isinstance(entry, dict):
            continue
        data = (entry.get("result") or {}).get("data")
        if entry.get("node") == "guard" and entry.get("status") == "completed" and isinstance(data, dict):
            return data
    return None


def _done_lines(history: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for entry in history:
        if not isinstance(entry, dict) or entry.get("status") != "completed" or not entry.get("node"):
            continue
        node = str(entry["node"])
        if node == "guard":
            data = _guard_data([entry]) or {}
            if data.get("verdict") == "ALLOW":
                lines.append("Guardian allowed it")
            else:
                failed = ", ".join(str(c) for c in data.get("failed_checks", [])[:3]) or "a check failed"
                lines.append(f"Guardian blocked it: {failed}")
        else:
            lines.append(DONE_LABELS.get(node, f"Finished {node}"))
    return lines


def calm_card_for_run(
    *,
    run_id: str,
    run_status: str,
    history: list[dict[str, Any]],
    current_node: Optional[str],
    error: Optional[str],
    at_gate: bool,
    paused: bool = False,
) -> CalmCard:
    lines = _done_lines(history)
    status: CardStatus
    if paused and run_status not in ("completed", "failed", "cancelled"):
        # Held by Panic. "Nothing is running" is only true once the runner has stopped between steps
        # (it records a control entry) or the run is parked at your gate; before that, say so honestly.
        last = history[-1] if history and isinstance(history[-1], dict) else {}
        stopped = at_gate or (last.get("type") == "control" and last.get("status") == "paused")
        lines.append("Paused. Nothing is running." if stopped else "Pausing: the step in progress finishes first.")
        status, nxt = "paused", "Resume when you are ready"
    elif run_status == "completed":
        guard = _guard_data(history)
        if guard is not None and guard.get("verdict") != "ALLOW":
            status, nxt = "blocked", "Read why the guard blocked it"
        elif guard is not None:
            status, nxt = "done", "Review the evidence and the proposed change"
        else:
            status, nxt = "done", "Check the result"
    elif run_status == "failed":
        status, nxt = "blocked", "Read why it stopped"
        lines.append(f"Stopped: {error or 'unknown reason'}")
    elif run_status == "cancelled":
        status, nxt = "paused", "Start it again when you are ready"
        lines.append("Cancelled")
    elif run_status == "awaiting_approval":
        status = "waiting_on_you"
        nxt = "Read the plan, then approve or reject it" if at_gate else "A safety decision is waiting on you"
    else:
        status, nxt = "running", f"Nothing needed. Now: {node_label(current_node).lower()}"
    tldr = [_fit(line) for line in lines[-MAX_TLDR_LINES:]] or ["Starting up"]
    return CalmCard(status=status, tldr=tldr, next_action=_fit(nxt), details=[f"Run: {run_id}"])
