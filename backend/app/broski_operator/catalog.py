"""Allow-list of operator tools → HyperFlow flow names. Anything not listed cannot be started."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ValidationError

from app.crew.plan import CrewStartArgs

TOOL_FLOWS: dict[str, str] = {
    "hypercode.inspect": "operator-inspect",
    "hypercode.recover": "operator-recover",
    # Deterministic two-gate demo flow; used to prove approvals survive a restart.
    "hypercode.smoke": "hyperflow-smoke",
    # HyperCrew plan gate (Day 2): takes a goal, shows a hashed plan, seals on approval.
    "hypercode.crew": "hypercode-crew",
}

# Tools that accept arguments, with the model that validates them. Any tool NOT listed here
# accepts none: a non-empty ``arguments`` is rejected, never silently ignored.
TOOL_ARGUMENTS: dict[str, type[BaseModel]] = {
    "hypercode.crew": CrewStartArgs,
}


class ArgumentError(ValueError):
    """Arguments rejected. The message is safe to return to the caller (no echoed input)."""


def validate_arguments(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Return the cleaned arguments for ``tool`` or raise :class:`ArgumentError`."""
    model = TOOL_ARGUMENTS.get(tool)
    if model is None:
        if arguments:
            raise ArgumentError("This tool does not accept arguments yet")
        return {}
    try:
        return model.model_validate(arguments).model_dump()
    except ValidationError as exc:
        known = set(model.model_fields)
        # Only name fields the model defines; a caller-chosen key is never echoed back.
        fields = sorted(
            {str(e["loc"][0]) if e["loc"] and e["loc"][0] in known else "unexpected field" for e in exc.errors()}
        )
        raise ArgumentError(f"Invalid arguments: {', '.join(fields)}") from None


def tool_for_flow(flow_name: str) -> Optional[str]:
    for tool, flow in TOOL_FLOWS.items():
        if flow == flow_name:
            return tool
    return None
