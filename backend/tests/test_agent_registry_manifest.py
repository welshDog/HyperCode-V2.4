from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def registry_mod():
    return _load_module(
        "hc_agent_registry_mod",
        Path(__file__).resolve().parents[2] / "agents" / "agent-registry" / "agent_registry.py",
    )


def test_every_agent_has_manifest_fields(registry_mod):
    for name, meta in registry_mod.ROSTER.items():
        for key in ("capabilities", "tools_exposed", "events_subscribed"):
            assert key in meta, f"{name} missing {key}"
            value = meta[key]
            assert value is None or (
                isinstance(value, list) and all(isinstance(x, str) for x in value)
            ), f"{name}.{key} has an unexpected shape: {value!r}"
        assert "health_endpoint" in meta, f"{name} missing health_endpoint"
        assert meta["health_endpoint"] is None or isinstance(meta["health_endpoint"], str)
        assert isinstance(meta.get("mcp"), bool), f"{name}.mcp is not a bool"
        assert isinstance(meta.get("a2a"), bool), f"{name}.a2a is not a bool"


def test_health_endpoint_derived_from_documented_port(registry_mod):
    roster = registry_mod.ROSTER
    assert roster["crew-orchestrator"]["health_endpoint"] == "http://crew-orchestrator:8081/health"
    assert roster["broski-pets-bridge"]["health_endpoint"] == "http://broski-pets-bridge:8098/health"
    assert roster["nemoclaw-agent"]["health_endpoint"] == "http://nemoclaw-agent:8099/health"
    assert roster["agent-mcp-bridge"]["health_endpoint"] == "http://agent-mcp-bridge:3302/health"


def test_health_endpoint_none_when_no_port_documented(registry_mod):
    roster = registry_mod.ROSTER
    assert roster["healer-agent"]["health_endpoint"] is None
    assert roster["broski-bot"]["health_endpoint"] is None
    assert roster["hypercode-mcp-server"]["health_endpoint"] is None


def test_mcp_flag_true_only_for_mcp_named_or_described_agents(registry_mod):
    expected_mcp = {"hypercode-mcp-server", "mcp-gateway", "mcp-rest-adapter", "agent-mcp-bridge"}
    actual_mcp = {name for name, meta in registry_mod.ROSTER.items() if meta.get("mcp")}
    assert actual_mcp == expected_mcp


def test_a2a_flag_false_for_every_agent(registry_mod):
    assert all(meta.get("a2a") is False for meta in registry_mod.ROSTER.values())


def test_agent_status_model_accepts_manifest_fields(registry_mod):
    status = registry_mod.AgentStatus(
        name="crew-orchestrator",
        role="Multi-agent crew orchestration (/execute, port 8081)",
        source="agents.yml [agents]",
        status="healthy",
        capabilities=None,
        tools_exposed=None,
        events_subscribed=None,
        health_endpoint="http://crew-orchestrator:8081/health",
        mcp=False,
        a2a=False,
    )
    assert status.health_endpoint == "http://crew-orchestrator:8081/health"
    assert status.mcp is False
    assert status.a2a is False
