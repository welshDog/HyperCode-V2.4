"""Unit tests for HyperFlow P0-1 — schema validation + runner graph walk.

These tests are DB/Redis-independent: the runner's persistence and pub/sub IO
is monkeypatched so we exercise pure graph logic (routing, retry, loop,
approval, fallback) without standing up Postgres or Redis.
"""

import asyncio
from pathlib import Path

import pytest

from app.agents.hyperflow.registry import FLOWS_DIR, available_flows, get_flow
from app.agents.hyperflow.schema import FlowDefinition, NodeType, load_flow
from app.agents.hyperflow_runner import HyperFlowRunner
from app.models.hyperflow import HyperFlowRunStatus


@pytest.fixture(autouse=True)
def _safety_off_by_default(monkeypatch):
    """Default Safety Shepherd to off so tests never hit the network.
    Safety-specific tests override SAFETY_SHEPHERD_MODE in their own body."""
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "off")


def _one_node_flow(safety=None):
    node = {"id": "act", "type": "agent_role", "agent": "qa_engineer", "params": {"task": "x"}}
    if safety is not None:
        node["safety"] = safety
    return FlowDefinition.model_validate({"name": "sf", "entry": "act", "nodes": [node]})


def _runner_with_io(flow, run_id, monkeypatch):
    runner = HyperFlowRunner(flow, run_id)

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(runner, "_persist", _noop)
    monkeypatch.setattr(runner, "_publish", _noop)
    monkeypatch.setattr(runner, "_publish_approval_request", _noop)

    final = {}

    async def _finish(status, error=None):
        final["status"] = status
        final["error"] = error

    async def _green(node):
        return {"ok": True, "green": True}

    monkeypatch.setattr(runner, "_finish", _finish)
    monkeypatch.setattr(runner, "_dispatch", _green)
    return runner, final


# ── schema ────────────────────────────────────────────────────────────────────

def test_example_flow_validates():
    fd = load_flow(FLOWS_DIR / "implement_new_agent.yml")
    assert fd.name == "implement-new-agent"
    assert fd.entry == "design_spec"
    # entry resolves, every edge endpoint resolves (validated by the model)
    node_ids = {n.id for n in fd.nodes}
    for e in fd.edges:
        assert e.src in node_ids and e.dst in node_ids
    assert get_flow("implement-new-agent") is not None


def test_registry_loads_example():
    assert (FLOWS_DIR / "implement_new_agent.yml").exists()
    assert get_flow("does-not-exist") is None


def available_flows_for_test():
    return available_flows()


def test_all_registered_flows_declare_intent():
    for name, fd in available_flows_for_test().items():
        assert fd.intent, f"flow '{name}' has no intent — needed for goal matching"


def test_schema_rejects_bad_entry():
    with pytest.raises(Exception):
        FlowDefinition.model_validate(
            {"name": "x", "entry": "ghost", "nodes": [{"id": "a", "type": "tool", "tool": "t"}]}
        )


def test_schema_rejects_dangling_edge():
    with pytest.raises(Exception):
        FlowDefinition.model_validate(
            {
                "name": "x",
                "entry": "a",
                "nodes": [{"id": "a", "type": "tool", "tool": "t"}],
                "edges": [{"from": "a", "to": "ghost"}],
            }
        )


def test_agent_role_requires_agent():
    with pytest.raises(Exception):
        FlowDefinition.model_validate(
            {"name": "x", "entry": "a", "nodes": [{"id": "a", "type": "agent_role"}]}
        )


# ── runner ──────────────────────────────────────────────────────────────────

def _patch_io(runner, monkeypatch):
    """Replace DB + Redis IO with no-ops; capture the final status."""
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(runner, "_persist", _noop)
    monkeypatch.setattr(runner, "_publish", _noop)
    monkeypatch.setattr(runner, "_publish_approval_request", _noop)


def test_full_walk_reaches_completed(monkeypatch):
    fd = get_flow("implement-new-agent")
    runner = HyperFlowRunner(fd, "test-run-1")
    _patch_io(runner, monkeypatch)

    # Orchestrator mocked green; approval auto-granted.
    async def _green(node):
        return {"ok": True, "green": True}

    async def _approve(node):
        return {"ok": True, "approved": True}

    final = {}

    async def _finish(status, error=None):
        final["status"] = status
        final["error"] = error

    monkeypatch.setattr(runner, "_dispatch", _green)
    monkeypatch.setattr(runner, "_await_approval", _approve)
    monkeypatch.setattr(runner, "_finish", _finish)

    asyncio.run(runner._run())

    assert final["status"] is HyperFlowRunStatus.COMPLETED
    visited = [h["node"] for h in runner._history if h["status"] == "completed"]
    # spec → approval → scaffold → health-probe (green) all recorded
    assert "design_spec" in visited
    assert "scaffold_agent" in visited
    assert "health_probe" in visited


def test_rejected_approval_fails_run(monkeypatch):
    fd = get_flow("implement-new-agent")
    runner = HyperFlowRunner(fd, "test-run-2")
    _patch_io(runner, monkeypatch)

    async def _green(node):
        return {"ok": True, "green": True}

    final = {}

    async def _finish(status, error=None):
        final["status"] = status
        final["error"] = error

    monkeypatch.setattr(runner, "_dispatch", _green)
    monkeypatch.setattr(runner, "_finish", _finish)

    # Start the run, then reject the approval gate it lands on.
    async def drive():
        task = asyncio.create_task(runner._run())
        # Wait until the run is actually parked on the approval gate before resuming —
        # resume() only counts once the gate is active (the runner clears stale signals).
        for _ in range(200):
            await asyncio.sleep(0.02)
            if any(h["status"] == "awaiting_approval" for h in runner._history):
                break
        else:
            task.cancel()
            raise AssertionError("run never reached the approval gate")
        runner.resume(False)
        await asyncio.wait_for(task, timeout=5)

    asyncio.run(drive())
    assert final["status"] is HyperFlowRunStatus.FAILED


def test_safety_block_enforce_fails_node(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "enforce")
    runner, final = _runner_with_io(_one_node_flow({"category": "file_write", "target": "/etc/passwd"}), "sf-block", monkeypatch)

    async def _block(req):
        return {"decision": "BLOCK", "reason": "hard-blocked", "rule": "blocked_path"}

    monkeypatch.setattr(runner, "_safety_evaluate", _block)
    asyncio.run(runner._run())
    assert final["status"] is HyperFlowRunStatus.FAILED


def test_safety_monitor_proceeds_despite_block(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "monitor")
    runner, final = _runner_with_io(_one_node_flow({"category": "docker"}), "sf-monitor", monkeypatch)

    async def _block(req):
        return {"decision": "BLOCK", "reason": "x", "rule": "y"}

    monkeypatch.setattr(runner, "_safety_evaluate", _block)
    asyncio.run(runner._run())
    # monitor never blocks — the node still dispatched and the run completed.
    assert final["status"] is HyperFlowRunStatus.COMPLETED


def test_safety_off_skips_call(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "off")
    runner, final = _runner_with_io(_one_node_flow(), "sf-off", monkeypatch)
    called = []

    async def _spy(req):
        called.append(req)
        return {"decision": "BLOCK"}

    monkeypatch.setattr(runner, "_safety_evaluate", _spy)
    asyncio.run(runner._run())
    assert called == []  # never consulted
    assert final["status"] is HyperFlowRunStatus.COMPLETED


def test_safety_escalate_enforce_approved_proceeds(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "enforce")
    runner, final = _runner_with_io(_one_node_flow({"category": "docker"}), "sf-esc-ok", monkeypatch)

    async def _escalate(req):
        return {"decision": "ESCALATE", "approval_id": "appr-1", "reason": "needs ok"}

    async def _approve(node, approval_id, timeout=None):
        return True

    monkeypatch.setattr(runner, "_safety_evaluate", _escalate)
    monkeypatch.setattr(runner, "_wait_safety_approval", _approve)
    asyncio.run(runner._run())
    assert final["status"] is HyperFlowRunStatus.COMPLETED


def test_safety_escalate_enforce_denied_fails(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "enforce")
    runner, final = _runner_with_io(_one_node_flow({"category": "docker"}), "sf-esc-no", monkeypatch)

    async def _escalate(req):
        return {"decision": "ESCALATE", "approval_id": "appr-2", "reason": "needs ok"}

    async def _deny(node, approval_id, timeout=None):
        return False

    monkeypatch.setattr(runner, "_safety_evaluate", _escalate)
    monkeypatch.setattr(runner, "_wait_safety_approval", _deny)
    asyncio.run(runner._run())
    assert final["status"] is HyperFlowRunStatus.FAILED


def test_safety_fail_open_when_shepherd_unreachable(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "enforce")
    runner, final = _runner_with_io(_one_node_flow({"category": "docker"}), "sf-open", monkeypatch)

    async def _down(req):
        return None  # unreachable

    monkeypatch.setattr(runner, "_safety_evaluate", _down)
    asyncio.run(runner._run())
    # fail-open: an unreachable Shepherd must not break the flow.
    assert final["status"] is HyperFlowRunStatus.COMPLETED


def test_loop_then_fallback_when_never_green(monkeypatch):
    fd = get_flow("implement-new-agent")
    runner = HyperFlowRunner(fd, "test-run-3")
    _patch_io(runner, monkeypatch)

    async def _never_green(node):
        # health_probe never goes green → loop until exhausted → fallback to escalate
        return {"ok": True, "green": False}

    async def _approve(node):
        return {"ok": True, "approved": True}

    final = {}

    async def _finish(status, error=None):
        final["status"] = status

    monkeypatch.setattr(runner, "_dispatch", _never_green)
    monkeypatch.setattr(runner, "_await_approval", _approve)
    monkeypatch.setattr(runner, "_finish", _finish)

    asyncio.run(runner._run())

    # Reaches the escalate gate (auto-approved here) → completes, having looped.
    probe_completions = [
        h for h in runner._history if h["node"] == "health_probe" and h["status"] == "completed"
    ]
    assert len(probe_completions) >= 2  # looped at least once
    assert final["status"] is HyperFlowRunStatus.COMPLETED
