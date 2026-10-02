"""BROski operator — MCP tools on hypercode-mcp-server (loaded from its source file)."""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

SERVER = Path(__file__).resolve().parents[2] / "services" / "hypercode-mcp-server" / "server.py"
pytestmark = pytest.mark.skipif(not SERVER.exists(), reason="services/ not present in this image")

GOOD_ID = "0f8fad5b-d9cb-469f-a165-70867728950e"


def _load(monkeypatch, key=""):
    monkeypatch.setenv("HYPERCODE_AGENT_KEY", key)
    spec = importlib.util.spec_from_file_location("hypercode_mcp_server_under_test", SERVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_core_headers_only_for_core_and_only_with_key(monkeypatch):
    mod = _load(monkeypatch, key="k123")
    assert mod._core_headers(mod.CORE_URL) == {"X-Agent-Key": "k123"}
    assert mod._core_headers(mod.ORCH_URL) == {}  # never leaked to other hosts
    assert _load(monkeypatch, key="")._core_headers(mod.CORE_URL) == {}


def test_inspect_posts_the_allow_listed_tool(monkeypatch):
    import asyncio

    mod = _load(monkeypatch)
    mod._post = AsyncMock(return_value={"taskId": GOOD_ID})
    out = asyncio.run(mod.hypercode_inspect())
    assert out == {"taskId": GOOD_ID}
    mod._post.assert_awaited_once_with(
        "/api/v1/operator/tasks", {"tool": "hypercode.inspect", "arguments": {}}
    )


def test_task_get_and_cancel_hit_the_right_routes(monkeypatch):
    import asyncio

    mod = _load(monkeypatch)
    mod._get = AsyncMock(return_value={"status": "working"})
    mod._post = AsyncMock(return_value={"status": "cancelled"})
    assert asyncio.run(mod.hypercode_task_get(GOOD_ID)) == {"status": "working"}
    mod._get.assert_awaited_once_with(f"/api/v1/operator/tasks/{GOOD_ID}")
    assert asyncio.run(mod.hypercode_task_cancel(GOOD_ID, "done with it")) == {"status": "cancelled"}
    mod._post.assert_awaited_once_with(
        f"/api/v1/operator/tasks/{GOOD_ID}/cancel", {"reason": "done with it"}
    )


@pytest.mark.parametrize("bad", ["../../admin", "x/../y", "", "a b", GOOD_ID + "/cancel"])
def test_bad_task_ids_rejected_before_any_http_call(monkeypatch, bad):
    import asyncio

    mod = _load(monkeypatch)
    mod._get = AsyncMock()
    mod._post = AsyncMock()
    assert "error" in asyncio.run(mod.hypercode_task_get(bad))
    assert "error" in asyncio.run(mod.hypercode_task_cancel(bad, ""))
    mod._get.assert_not_awaited()
    mod._post.assert_not_awaited()


@pytest.mark.parametrize("bad", [GOOD_ID + "\n", "-" * 36, None, 42, GOOD_ID.replace("-", "")])
def test_task_id_must_be_a_real_uuid(monkeypatch, bad):
    import asyncio

    mod = _load(monkeypatch)
    mod._get = AsyncMock()
    mod._post = AsyncMock()
    assert asyncio.run(mod.hypercode_task_get(bad)) == {"error": "invalid task_id"}
    assert asyncio.run(mod.hypercode_task_cancel(bad, "")) == {"error": "invalid task_id"}
    mod._get.assert_not_awaited()
    mod._post.assert_not_awaited()


def test_uppercase_uuid_accepted_and_normalised(monkeypatch):
    import asyncio

    mod = _load(monkeypatch)
    mod._get = AsyncMock(return_value={"status": "working"})
    assert asyncio.run(mod.hypercode_task_get(GOOD_ID.upper())) == {"status": "working"}
    mod._get.assert_awaited_once_with(f"/api/v1/operator/tasks/{GOOD_ID}")


def test_cancel_reason_none_is_tolerated_and_truncated(monkeypatch):
    import asyncio

    mod = _load(monkeypatch)
    mod._post = AsyncMock(return_value={})
    asyncio.run(mod.hypercode_task_cancel(GOOD_ID, None))
    mod._post.assert_awaited_with(f"/api/v1/operator/tasks/{GOOD_ID}/cancel", {"reason": ""})
    asyncio.run(mod.hypercode_task_cancel(GOOD_ID, "x" * 500))
    assert len(mod._post.await_args.args[1]["reason"]) == 200


def test_recover_posts_the_allow_listed_tool_and_no_approval_tool_exists(monkeypatch):
    import asyncio

    mod = _load(monkeypatch)
    mod._post = AsyncMock(return_value={"taskId": GOOD_ID})
    assert asyncio.run(mod.hypercode_recover()) == {"taskId": GOOD_ID}
    mod._post.assert_awaited_once_with(
        "/api/v1/operator/tasks", {"tool": "hypercode.recover", "arguments": {}}
    )
    tool_names = [n for n in dir(mod) if n.startswith("hypercode_")]
    assert not any("approve" in n or "input" in n for n in tool_names)


# ── HyperCrew tools ───────────────────────────────────────────────────────────

def test_crew_start_posts_the_allow_listed_tool_with_the_goal(monkeypatch):
    import asyncio

    mod = _load(monkeypatch)
    mod._post = AsyncMock(return_value={"taskId": GOOD_ID})
    assert asyncio.run(mod.hypercode_crew_start("add a health endpoint")) == {"taskId": GOOD_ID}
    mod._post.assert_awaited_once_with(
        "/api/v1/operator/tasks", {"tool": "hypercode.crew", "arguments": {"goal": "add a health endpoint"}}
    )


def test_crew_start_forwards_an_idempotency_key_only_when_given(monkeypatch):
    import asyncio

    mod = _load(monkeypatch)
    mod._post = AsyncMock(return_value={})
    asyncio.run(mod.hypercode_crew_start("a goal here", "retry-safe-key-1"))
    assert mod._post.await_args.args[1]["idempotency_key"] == "retry-safe-key-1"
    asyncio.run(mod.hypercode_crew_start("a goal here"))
    assert "idempotency_key" not in mod._post.await_args.args[1]


def test_crew_start_cannot_pick_the_tool_or_smuggle_arguments(monkeypatch):
    import asyncio

    mod = _load(monkeypatch)
    mod._post = AsyncMock(return_value={})
    asyncio.run(mod.hypercode_crew_start("goal", ""))
    body = mod._post.await_args.args[1]
    assert body["tool"] == "hypercode.crew" and list(body["arguments"]) == ["goal"]


def test_crew_status_asks_for_events_after_the_cursor(monkeypatch):
    import asyncio

    mod = _load(monkeypatch)
    mod._get = AsyncMock(return_value={"events": []})
    assert asyncio.run(mod.hypercode_crew_status(GOOD_ID)) == {"events": []}
    mod._get.assert_awaited_once_with(f"/api/v1/operator/tasks/{GOOD_ID}/events", after=-1)
    asyncio.run(mod.hypercode_crew_status(GOOD_ID.upper(), 7))
    assert mod._get.await_args.args == (f"/api/v1/operator/tasks/{GOOD_ID}/events",)
    assert mod._get.await_args.kwargs == {"after": 7}


@pytest.mark.parametrize("bad", ["../../admin", "", GOOD_ID + "/cancel", None, 42, GOOD_ID.replace("-", "")])
def test_crew_status_rejects_a_bad_task_id_before_any_http_call(monkeypatch, bad):
    import asyncio

    mod = _load(monkeypatch)
    mod._get = AsyncMock()
    assert asyncio.run(mod.hypercode_crew_status(bad)) == {"error": "invalid task_id"}
    mod._get.assert_not_awaited()


@pytest.mark.parametrize("bad", [-2, 10**10, "abc", None, "1.5"])
def test_crew_status_rejects_a_bad_cursor(monkeypatch, bad):
    import asyncio

    mod = _load(monkeypatch)
    mod._get = AsyncMock()
    assert asyncio.run(mod.hypercode_crew_status(GOOD_ID, bad)) == {"error": "invalid after"}
    mod._get.assert_not_awaited()


def test_no_crew_tool_can_approve_a_plan(monkeypatch):
    mod = _load(monkeypatch)
    tool_names = [n for n in dir(mod) if n.startswith("hypercode_")]
    assert {"hypercode_crew_start", "hypercode_crew_status"} <= set(tool_names)
    assert not any("approve" in n or "input" in n or "decide" in n for n in tool_names)


def test_the_crew_tools_are_registered_with_the_mcp_server(monkeypatch):
    import asyncio

    mod = _load(monkeypatch)
    names = {t.name for t in asyncio.run(mod.mcp.list_tools())}
    assert {"hypercode_crew_start", "hypercode_crew_status", "hypercode_task_get", "hypercode_task_cancel"} <= names
    assert not any("approve" in n for n in names)


def test_crew_pause_posts_to_the_pause_route_and_truncates_the_reason(monkeypatch):
    import asyncio

    mod = _load(monkeypatch)
    mod._post = AsyncMock(return_value={"paused": True})
    assert asyncio.run(mod.hypercode_crew_pause(GOOD_ID.upper(), "x" * 500)) == {"paused": True}
    path, body = mod._post.await_args.args
    assert path == f"/api/v1/operator/tasks/{GOOD_ID}/pause" and len(body["reason"]) == 200
    asyncio.run(mod.hypercode_crew_pause(GOOD_ID, None))
    assert mod._post.await_args.args[1] == {"reason": ""}


@pytest.mark.parametrize("bad", ["../../admin", "", GOOD_ID + "/resume", None, 42])
def test_crew_pause_rejects_a_bad_task_id_before_any_http_call(monkeypatch, bad):
    import asyncio

    mod = _load(monkeypatch)
    mod._post = AsyncMock()
    assert asyncio.run(mod.hypercode_crew_pause(bad)) == {"error": "invalid task_id"}
    mod._post.assert_not_awaited()


def test_agents_can_pause_but_there_is_no_resume_tool(monkeypatch):
    import asyncio

    mod = _load(monkeypatch)
    names = {t.name for t in asyncio.run(mod.mcp.list_tools())}
    assert "hypercode_crew_pause" in names
    assert not any("resume" in n or "unpause" in n or "panic" in n for n in names)
