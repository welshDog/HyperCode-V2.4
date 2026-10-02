"""Map HyperFlow run history to AG-UI-shaped events (HyperCrew Day 5 — the output format).

AG-UI is used as the *edge* format only: this is a pure function of the persisted run, so there is
no new service, table or approval path. Replay is free — the sequence number is the event's index in
a deterministic walk of the history, and history is append-only, so ``after=<seq>`` always returns
exactly the events a client missed. Anything unfinished is reported in a separate ``state`` snapshot,
never as a sequenced event (so sequenced events never change once emitted).

Event/field names follow the AG-UI research doc (RUN_STARTED, STEP_*, TOOL_CALL_*, CUSTOM,
RUN_FINISHED, RUN_ERROR). They have NOT been checked against the current AG-UI spec.
Every value passes through :func:`app.crew.redaction.redact_value` and is length-capped.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from app.crew.redaction import redact_value

MAX_TEXT = 500
MAX_EVENTS_PER_CALL = 200

NODE_LABELS: dict[str, str] = {
    "plan": "Writing the plan",
    "approve": "Waiting for your approval",
    "seal": "Recording your approval",
    "build": "Builder is proposing a change",
    "verify": "Verifier is reviewing it",
    "guard": "Guardian is checking it",
    "settle": "Counting up your win",
}


def node_label(node: Optional[str]) -> str:
    if not node:
        return "Finishing up"
    return NODE_LABELS.get(node, f"Running {node}")


def _d(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _cap(value: Any, limit: int = MAX_TEXT) -> str:
    return str(value if value is not None else "")[:limit]


def _step(kind: str, node: str) -> dict[str, Any]:
    return {"type": kind, "stepName": node}


def _custom(name: str, value: dict[str, Any]) -> dict[str, Any]:
    return {"type": "CUSTOM", "name": f"hypercode.{name}", "value": value}


def _plan_events(data: dict[str, Any]) -> list[dict[str, Any]]:
    proposal = data.get("proposal")
    if not isinstance(proposal, dict) or not isinstance(proposal.get("plan"), dict):
        return []
    plan = proposal["plan"]
    stages = [s.get("id") for s in plan.get("stages", []) if isinstance(s, dict)]
    return [_custom("plan.created", {
        "summary": _cap(proposal.get("summary"), 160),
        "steps": [_cap(s, 40) for s in stages if s],
        "risk": _cap(plan.get("risk_hint", "unknown"), 20),
        "planHash": _cap(proposal.get("plan_hash"), 80),
    })]


def _completed_extras(entry: dict[str, Any], run_id: str) -> list[dict[str, Any]]:
    node, typ = str(entry.get("node")), entry.get("type")
    result = _d(entry.get("result"))
    data = _d(result.get("data"))
    out: list[dict[str, Any]] = []
    if typ == "human_approval_gate":
        out.append(_custom("approval.resolved", {"node": node, "approved": bool(result.get("approved", True))}))
    elif typ == "agent_dispatch":
        call_id = f"{run_id}:{node}"
        out.append({"type": "TOOL_CALL_START", "toolCallId": call_id, "toolCallName": _cap(data.get("agent"), 60)})
        out.append({"type": "TOOL_CALL_END", "toolCallId": call_id})
        out.append({"type": "TOOL_CALL_RESULT", "toolCallId": call_id, "content": json.dumps({
            "stage": _cap(data.get("stage"), 20), "role": _cap(data.get("role"), 20),
            "status": _cap(data.get("status"), 20), "summary": _cap(data.get("summary")),
            "summaryHash": _cap(data.get("summary_hash"), 80), "truncated": bool(data.get("truncated")),
            "slotWaitMs": data.get("slot_wait_ms") if isinstance(data.get("slot_wait_ms"), int) else None,
        })})
    elif "proposal" in data:
        out.extend(_plan_events(data))
    elif data.get("sealed") is True:
        out.append(_custom("plan.sealed", {"planHash": _cap(data.get("plan_hash"), 80), "performed": False}))
    elif "verdict" in data and isinstance(data.get("checks"), list):
        bundle = _d(data.get("evidence_bundle"))
        out.append(_custom("guard.verdict", {
            "verdict": _cap(data.get("verdict"), 10),
            "failedChecks": [_cap(c, 40) for c in data.get("failed_checks", [])][:10],
            "checks": [{"name": _cap(c.get("name"), 40), "passed": bool(c.get("passed"))}
                       for c in data["checks"] if isinstance(c, dict)][:12],
            "bundleHash": _cap(bundle.get("bundle_hash"), 80),
        }))
    elif node == "settle":
        # A quiet win, only when something was actually awarded. Never a "you got nothing" event.
        if data.get("status") == "awarded":
            out.append(_custom("quest.settled", {
                "xp": int(data.get("xp") or 0), "coins": int(data.get("coins") or 0),
                "achievements": [_cap(a, 120) for a in (data.get("achievements") or [])][:5],
            }))
    elif result.get("success") is False:
        notes = data.get("notes") if isinstance(data.get("notes"), list) else []
        out.append(_custom("step.unsuccessful", {"node": node, "reason": _cap(notes[0] if notes else "", 160)}))
    return out


def _entry_events(run_id: str, entry: dict[str, Any]) -> list[dict[str, Any]]:
    status, typ, node = entry.get("status"), entry.get("type"), entry.get("node")
    result = _d(entry.get("result"))
    if typ == "terminal":
        if status == "completed":
            return [{"type": "RUN_FINISHED", "threadId": run_id, "runId": run_id}]
        code = "CANCELLED" if status == "cancelled" else "RUN_FAILED"
        return [{"type": "RUN_ERROR", "message": _cap(result.get("error") or "The run stopped", 200), "code": code}]
    if typ == "control" and status in ("paused", "resumed"):
        return [_custom(f"run.{status}", {"next": _cap(result.get("next"), 40)})]
    if not node:
        return []
    node = str(node)
    if status == "awaiting_approval" and typ == "human_approval_gate":
        return [_step("STEP_STARTED", node), _custom("approval.required", {
            "approvalId": f"{run_id}:{node}", "node": node, "title": _cap(result.get("prompt"), 200),
            "action": "approve_plan", "planHash": _cap(result.get("plan_hash"), 80),
        })]
    if status == "completed":
        return [_step("STEP_STARTED", node), *_completed_extras(entry, run_id), _step("STEP_FINISHED", node)]
    if status == "failed":
        return [_custom("step.failed", {"node": node, "reason": _cap(result.get("reason") or result.get("error"), 200)})]
    if isinstance(status, str) and status.startswith("safety_"):
        return [_custom("safety.decision", {
            "node": node, "decision": status.removeprefix("safety_").upper(),
            "reason": _cap(result.get("reason"), 200),
        })]
    return []


def history_to_events(run_id: str, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """All events for the run so far, each wrapped as ``{"seq": n, "event": {...}}``."""
    events: list[dict[str, Any]] = [{"type": "RUN_STARTED", "threadId": run_id, "runId": run_id}]
    awaiting: set[str] = set()  # gates currently parked
    for entry in history:
        if not isinstance(entry, dict):
            continue
        node = entry.get("node")
        if entry.get("status") == "awaiting_approval" and node:
            # After a core restart the runner re-parks at the same gate and records the wait again.
            # That is the SAME wait, not a new one: emit it once.
            if node in awaiting:
                continue
            awaiting.add(str(node))
        elif node and entry.get("status") in ("completed", "failed"):
            awaiting.discard(str(node))
        events.extend(_entry_events(run_id, entry))
    safe = redact_value(events)
    return [{"seq": i, "event": ev} for i, ev in enumerate(safe)]


def events_after(all_events: list[dict[str, Any]], after: int) -> list[dict[str, Any]]:
    return [e for e in all_events if e["seq"] > after][:MAX_EVENTS_PER_CALL]
