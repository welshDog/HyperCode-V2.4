"""Tiny flow builders shared by the BROski operator tests."""

from app.agents.hyperflow.schema import FlowDefinition


def gate_flow(name: str = "g") -> FlowDefinition:
    """One human_approval_gate node called ``gate``."""
    return FlowDefinition.model_validate(
        {
            "name": name,
            "entry": "gate",
            "nodes": [{"id": "gate", "type": "human_approval_gate", "params": {"prompt": "ok?"}}],
        }
    )


def two_gate_flow() -> FlowDefinition:
    """Gate ``a`` then gate ``b``."""
    return FlowDefinition.model_validate(
        {
            "name": "two",
            "entry": "a",
            "nodes": [
                {"id": "a", "type": "human_approval_gate", "params": {"prompt": "a?"}},
                {"id": "b", "type": "human_approval_gate", "params": {"prompt": "b?"}},
            ],
            "edges": [{"from": "a", "to": "b"}],
        }
    )
