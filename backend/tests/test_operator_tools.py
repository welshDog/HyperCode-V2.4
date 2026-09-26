"""BROski operator — local tools, inspect, and runner integration."""

import asyncio

import httpx
import pytest

from app.agents.hyperflow.registry import get_flow
from app.agents.hyperflow.schema import FlowDefinition
from app.broski_operator import tools
from app.models.hyperflow import HyperFlowRunStatus
from tests.test_hyperflow import _runner_with_io


@pytest.fixture(autouse=True)
def _safety_off(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "off")


def _patch_sections(monkeypatch, **overrides):
    async def _ok():
        return {"ok": True}

    for name in ("containers", "redis", "postgres", "queues", "disk", "models"):
        fn = overrides.get(name, _ok)
        monkeypatch.setattr(tools, f"_{name}_section" if name != "containers" else "_docker_section", fn)


def test_inspect_all_ok(monkeypatch):
    _patch_sections(monkeypatch)
    report = asyncio.run(tools.inspect_stack({}))
    assert report["ok"] is True
    assert report["attention"] == []
    assert set(report) >= {"containers", "redis", "postgres", "queues", "disk", "models", "checked_at"}


def test_inspect_fail_soft_when_postgres_down(monkeypatch):
    async def _boom():
        raise RuntimeError("connection refused")

    _patch_sections(monkeypatch, postgres=_boom)
    report = asyncio.run(tools.inspect_stack({}))
    assert report["ok"] is False
    assert report["postgres"]["ok"] is False
    assert "RuntimeError" in report["postgres"]["error"]
    assert any(a.startswith("postgres") for a in report["attention"])


def test_inspect_hung_section_times_out(monkeypatch):
    async def _hang():
        await asyncio.sleep(5)
        return {"ok": True}

    monkeypatch.setattr(tools, "SECTION_TIMEOUT_SECONDS", 0.05)
    _patch_sections(monkeypatch, containers=_hang)
    report = asyncio.run(tools.inspect_stack({}))
    assert report["containers"]["ok"] is False
    assert report["ok"] is False


def test_inspect_flags_unhealthy_containers_and_dlq(monkeypatch):
    async def _docker():
        return {"ok": True, "total": 3, "running": 2, "exited": [], "unhealthy": ["bad-one"]}

    async def _queues():
        return {"ok": True, "depths": {"hypercode-dlq": 4}}

    _patch_sections(monkeypatch, containers=_docker, queues=_queues)
    report = asyncio.run(tools.inspect_stack({}))
    assert report["ok"] is True  # informational, not a core failure
    assert any("unhealthy" in a and "bad-one" in a for a in report["attention"])
    assert any("dead-letter" in a for a in report["attention"])


def test_docker_section_summarises_containers(monkeypatch):
    payload = [
        {"Names": ["/hypercode-core"], "State": "running", "Status": "Up 2 hours (healthy)"},
        {"Names": ["/bad-one"], "State": "running", "Status": "Up 1 hour (unhealthy)"},
        {"Names": ["/old"], "State": "exited", "Status": "Exited (0) 3 days ago"},
    ]
    real = httpx.AsyncClient
    monkeypatch.setattr(
        tools.httpx,
        "AsyncClient",
        lambda **kw: real(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload)), **kw
        ),
    )
    out = asyncio.run(tools._docker_section())
    assert out == {"ok": True, "total": 3, "running": 2, "exited": ["old"], "unhealthy": ["bad-one"]}


def test_local_tools_registry():
    assert "local.inspect" in tools.LOCAL_TOOLS


def _local_flow():
    return FlowDefinition.model_validate(
        {"name": "lt", "entry": "t", "nodes": [{"id": "t", "type": "tool", "tool": "local.fake"}]}
    )


def test_local_tool_node_bypasses_orchestrator_and_records_data(monkeypatch):
    runner, final = _runner_with_io(_local_flow(), "lt1", monkeypatch)

    async def _boom(node):
        raise AssertionError("orchestrator must not be called for a local tool")

    async def _fake(params):
        return {"ok": True, "n": 1}

    monkeypatch.setattr(runner, "_dispatch", _boom)
    monkeypatch.setitem(tools.LOCAL_TOOLS, "local.fake", _fake)
    asyncio.run(runner._run())
    assert final["status"] is HyperFlowRunStatus.COMPLETED
    done = [e for e in runner._history if e["status"] == "completed"][0]
    assert done["result"]["success"] is True
    assert done["result"]["data"] == {"ok": True, "n": 1}


def test_local_tool_not_ok_is_recorded_as_unsuccessful(monkeypatch):
    runner, final = _runner_with_io(_local_flow(), "lt2", monkeypatch)

    async def _red(params):
        return {"ok": False, "why": "red"}

    monkeypatch.setitem(tools.LOCAL_TOOLS, "local.fake", _red)
    asyncio.run(runner._run())
    done = [e for e in runner._history if e["status"] == "completed"][0]
    assert done["result"]["success"] is False
    assert done["result"]["data"]["why"] == "red"


def test_local_tool_exception_fails_the_run(monkeypatch):
    runner, final = _runner_with_io(_local_flow(), "lt3", monkeypatch)

    async def _raises(params):
        raise RuntimeError("boom")

    monkeypatch.setitem(tools.LOCAL_TOOLS, "local.fake", _raises)
    asyncio.run(runner._run())
    assert final["status"] is HyperFlowRunStatus.FAILED
    assert "boom" in final["error"]


def test_operator_inspect_flow_is_registered():
    fd = get_flow("operator-inspect")
    assert fd is not None and fd.intent
    node = fd.node("inspect")
    assert node.tool == "local.inspect" and node.idempotent is True
