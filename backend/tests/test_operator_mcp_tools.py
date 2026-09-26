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
