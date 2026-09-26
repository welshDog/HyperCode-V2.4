"""Pure mapping between HyperFlow run state and MCP-Tasks-shaped task state."""

from __future__ import annotations

from typing import Any, Optional

TERMINAL_RUN_STATUSES = frozenset({"completed", "failed", "cancelled"})

_STATUS_MAP = {
    "running": "working",
    "awaiting_approval": "input_required",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
}
_POLL_MS = {"working": 2000, "input_required": 5000}


def to_task_status(run_status: str) -> str:
    """Map a HyperFlow run status to a task status. Unknown → 'failed' (never poll forever)."""
    return _STATUS_MAP.get(run_status, "failed")


def poll_interval_ms(task_status: str) -> Optional[int]:
    return _POLL_MS.get(task_status)


def progress_percent(total_nodes: int, history: list[dict[str, Any]], run_status: str) -> int:
    """Share of distinct nodes completed. Only a completed run reports 100."""
    if run_status == "completed":
        return 100
    if total_nodes <= 0:
        return 0
    done = {e["node"] for e in history if e.get("status") == "completed" and e.get("node")}
    return min(99, int(100 * len(done) / total_nodes))


def build_result(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Final result: last node success, last tool report, ordered completed node ids."""
    success: Optional[bool] = None
    report: Optional[dict[str, Any]] = None
    nodes: list[str] = []
    for entry in history:
        if entry.get("status") != "completed" or not entry.get("node"):
            continue
        result = entry.get("result") or {}
        nodes.append(entry["node"])
        success = bool(result.get("success", True))
        if "data" in result:
            report = result["data"]
    return {"success": success, "report": report, "nodes": nodes}
