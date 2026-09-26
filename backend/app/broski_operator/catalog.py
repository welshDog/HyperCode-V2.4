"""Allow-list of operator tools → HyperFlow flow names. Anything not listed cannot be started."""

from __future__ import annotations

from typing import Optional

TOOL_FLOWS: dict[str, str] = {
    "hypercode.inspect": "operator-inspect",
    # Deterministic two-gate demo flow; used to prove approvals survive a restart.
    "hypercode.smoke": "hyperflow-smoke",
}


def tool_for_flow(flow_name: str) -> Optional[str]:
    for tool, flow in TOOL_FLOWS.items():
        if flow == flow_name:
            return tool
    return None
