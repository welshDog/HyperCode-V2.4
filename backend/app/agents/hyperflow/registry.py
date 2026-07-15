"""HyperFlow registry — discovers flow definitions shipped under ``flows/``."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.agents.hyperflow.schema import FlowDefinition, load_flow

FLOWS_DIR = Path(__file__).parent / "flows"


def available_flows() -> dict[str, FlowDefinition]:
    """Load + validate every flow YAML, keyed by flow name."""
    flows: dict[str, FlowDefinition] = {}
    for path in sorted(FLOWS_DIR.glob("*.yml")):
        fd = load_flow(path)
        flows[fd.name] = fd
    return flows


def get_flow(name: str) -> Optional[FlowDefinition]:
    """Return a validated flow definition by name, or None if unknown."""
    return available_flows().get(name)
