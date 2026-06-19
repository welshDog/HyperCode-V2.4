"""HyperFlow schema — the declarative DSL for agent mission graphs.

A flow is a directed graph of typed nodes connected by edges. The runner
(``app.agents.hyperflow_runner.HyperFlowRunner``) walks it from ``entry``,
dispatching agent/tool nodes to the crew-orchestrator and pausing at
human-approval gates.

Node types
    agent_role          — dispatch to a named agent via the orchestrator
    tool                — dispatch a named tool action via the orchestrator
    human_approval_gate — suspend the run until a human resumes it

Edge controls (all optional)
    condition           — only traverse when the source node result matches
    retry               — re-run the source node up to ``max`` times on failure
    fallback            — alternate ``to`` node when the source node fails
    loop                — back-edge bounded by ``max_iterations``
"""

from __future__ import annotations

import enum
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, model_validator


class NodeType(str, enum.Enum):
    AGENT_ROLE = "agent_role"
    TOOL = "tool"
    HUMAN_APPROVAL_GATE = "human_approval_gate"


class RetryPolicy(BaseModel):
    max: int = Field(default=1, ge=0, description="Max re-runs on failure (0 = no retry).")
    backoff_seconds: float = Field(default=2.0, ge=0.0)


class LoopPolicy(BaseModel):
    max_iterations: int = Field(default=3, ge=1, description="Cap on back-edge traversals.")


class SafetyHint(BaseModel):
    """Declares the dangerous action a node represents, for Safety Shepherd.

    When present, the HyperFlowRunner consults Safety Shepherd /evaluate before
    dispatching the node (ALLOW proceeds, BLOCK fails it, ESCALATE waits for a
    human approval). Absent → the node is treated as a benign 'generic' action.
    """
    category: str = "generic"  # docker | http_external | file_write | stripe | discord | generic
    tool: Optional[str] = None
    target: Optional[str] = None
    domain: Optional[str] = None


class FlowNode(BaseModel):
    id: str
    type: NodeType
    # agent_role → agent name; tool → tool name. Ignored for approval gates.
    agent: Optional[str] = None
    tool: Optional[str] = None
    params: dict[str, Any] = Field(default_factory=dict)
    # When set, the node result is "green" only if result[success_key] is truthy.
    success_key: str = "ok"
    # Optional Safety Shepherd policy hint (see SafetyHint).
    safety: Optional[SafetyHint] = None

    @model_validator(mode="after")
    def _check_ref(self) -> "FlowNode":
        if self.type is NodeType.AGENT_ROLE and not self.agent:
            raise ValueError(f"node '{self.id}': agent_role requires 'agent'")
        if self.type is NodeType.TOOL and not self.tool:
            raise ValueError(f"node '{self.id}': tool requires 'tool'")
        return self


class FlowEdge(BaseModel):
    src: str = Field(alias="from")
    dst: str = Field(alias="to")
    # Traverse only when the source result's success matches this (None = always).
    condition: Optional[bool] = None
    retry: Optional[RetryPolicy] = None
    fallback: Optional[str] = None
    loop: Optional[LoopPolicy] = None

    model_config = {"populate_by_name": True}


class FlowDefinition(BaseModel):
    name: str
    version: int = 1
    entry: str
    nodes: list[FlowNode]
    edges: list[FlowEdge] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _check_graph(self) -> "FlowDefinition":
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate node ids")
        node_ids = set(ids)
        if self.entry not in node_ids:
            raise ValueError(f"entry '{self.entry}' is not a defined node")
        for e in self.edges:
            if e.src not in node_ids:
                raise ValueError(f"edge from unknown node '{e.src}'")
            if e.dst not in node_ids:
                raise ValueError(f"edge to unknown node '{e.dst}'")
            if e.fallback is not None and e.fallback not in node_ids:
                raise ValueError(f"edge fallback to unknown node '{e.fallback}'")
        return self

    def node(self, node_id: str) -> FlowNode:
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise KeyError(node_id)

    def edges_from(self, node_id: str) -> list[FlowEdge]:
        return [e for e in self.edges if e.src == node_id]


def load_flow(path: str | Path) -> FlowDefinition:
    """Load and validate a flow definition from a YAML file."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return FlowDefinition.model_validate(raw)
