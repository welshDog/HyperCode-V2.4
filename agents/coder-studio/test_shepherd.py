"""Unit tests for the coder-studio Safety Shepherd gate.

The gate is the only thing standing between an LLM and 22 repos full of .env
files. Every ambiguous outcome must resolve to "deny". Real httpx is used via
MockTransport — no mocking of our own code.
"""

from pathlib import Path

import httpx
import pytest

from shepherd import (
    ALLOW,
    BLOCK,
    ESCALATE,
    STUDIO_AGENT,
    ShepherdClient,
    check_tool_call,
    map_tool_call,
)
from worktree import Worktree


@pytest.fixture
def worktree(tmp_path: Path) -> Worktree:
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / "app.py").write_text("x = 1\n", encoding="utf-8")
    return Worktree(repo=tmp_path / "repo", path=wt, branch="agent/x", base="main")


def shepherd_returning(payload: dict, status: int = 200) -> ShepherdClient:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=payload)

    client = ShepherdClient(
        base_url="http://shepherd:8096",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    client.seen = seen  # type: ignore[attr-defined]
    return client


def shepherd_that_must_not_be_called() -> ShepherdClient:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"Shepherd was contacted for {request.url}")

    return ShepherdClient(
        base_url="http://shepherd:8096",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )


def shepherd_that_is_down() -> ShepherdClient:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    return ShepherdClient(
        base_url="http://shepherd:8096",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )


# --- map_tool_call: Agent SDK tool names -> Shepherd's vocabulary ---


def test_write_maps_to_file_write():
    payload = map_tool_call("Write", {"file_path": "app.py", "content": "x"})

    assert payload["category"] == "file_write"
    assert payload["tool"] == "file_write"
    assert payload["target"] == "app.py"
    assert payload["agent"] == STUDIO_AGENT


def test_edit_maps_to_file_write():
    payload = map_tool_call("Edit", {"file_path": "app.py"})
    assert payload["category"] == "file_write"


def test_read_maps_to_file_read():
    payload = map_tool_call("Read", {"file_path": "app.py"})

    assert payload["tool"] == "file_read"
    assert payload["target"] == "app.py"


def test_grep_and_glob_map_to_file_read():
    for tool in ("Grep", "Glob"):
        payload = map_tool_call(tool, {"pattern": "x", "path": "src"})
        assert payload["tool"] == "file_read"
        assert payload["target"] == "src"


def test_bash_maps_with_the_command_as_target():
    payload = map_tool_call("Bash", {"command": "pytest -q"})

    assert payload["tool"] == "bash"
    assert payload["target"] == "pytest -q"


def test_webfetch_maps_domain_not_path():
    payload = map_tool_call("WebFetch", {"url": "https://pypi.org/simple/httpx/"})

    assert payload["category"] == "http_external"
    assert payload["domain"] == "pypi.org"


def test_unknown_tool_does_not_map():
    assert map_tool_call("LaunchMissiles", {"target": "moon"}) is None


# --- check_tool_call: the gate itself ---


async def test_allow_passes_through(worktree):
    shepherd = shepherd_returning({"decision": ALLOW, "reason": "ok", "rule": "default_allow"})

    verdict = await check_tool_call(shepherd, worktree, "Write", {"file_path": "app.py"})

    assert verdict.decision == ALLOW


async def test_block_is_relayed(worktree):
    shepherd = shepherd_returning(
        {"decision": BLOCK, "reason": "hard-blocked", "rule": "blocked_path"}
    )

    verdict = await check_tool_call(shepherd, worktree, "Write", {"file_path": ".env"})

    assert verdict.decision == BLOCK
    assert verdict.rule == "blocked_path"


async def test_escalate_carries_the_approval_id(worktree):
    shepherd = shepherd_returning(
        {"decision": ESCALATE, "reason": "not granted", "rule": "tool_not_granted", "approval_id": "ap_1"}
    )

    verdict = await check_tool_call(shepherd, worktree, "Write", {"file_path": "app.py"})

    assert verdict.decision == ESCALATE
    assert verdict.approval_id == "ap_1"


async def test_agent_key_header_is_sent(worktree):
    shepherd = shepherd_returning({"decision": ALLOW, "reason": "", "rule": ""})

    await check_tool_call(shepherd, worktree, "Read", {"file_path": "app.py"})

    assert shepherd.seen[0].headers["X-Agent-Key"] == "test-key"


# --- Fail-closed: every ambiguous outcome denies ---


async def test_shepherd_unreachable_denies(worktree):
    verdict = await check_tool_call(
        shepherd_that_is_down(), worktree, "Write", {"file_path": "app.py"}
    )

    assert verdict.decision == BLOCK
    assert "unreachable" in verdict.reason.lower()


async def test_shepherd_error_status_denies(worktree):
    shepherd = shepherd_returning({"detail": "boom"}, status=500)

    verdict = await check_tool_call(shepherd, worktree, "Write", {"file_path": "app.py"})

    assert verdict.decision == BLOCK


async def test_shepherd_garbage_response_denies(worktree):
    shepherd = shepherd_returning({"unexpected": "shape"})

    verdict = await check_tool_call(shepherd, worktree, "Write", {"file_path": "app.py"})

    assert verdict.decision == BLOCK


async def test_unknown_tool_escalates_without_asking_shepherd(worktree):
    verdict = await check_tool_call(
        shepherd_that_must_not_be_called(), worktree, "LaunchMissiles", {}
    )

    assert verdict.decision == ESCALATE


# --- Local containment: refuse before the network, defence in depth ---


async def test_write_outside_worktree_is_blocked_without_asking_shepherd(worktree):
    verdict = await check_tool_call(
        shepherd_that_must_not_be_called(),
        worktree,
        "Write",
        {"file_path": "../../../etc/passwd"},
    )

    assert verdict.decision == BLOCK
    assert "outside" in verdict.reason.lower()


async def test_read_outside_worktree_is_blocked_without_asking_shepherd(worktree):
    verdict = await check_tool_call(
        shepherd_that_must_not_be_called(),
        worktree,
        "Read",
        {"file_path": "/etc/shadow"},
    )

    assert verdict.decision == BLOCK


# --- Shepherd sees a normalised, worktree-relative POSIX path ---
# Its blocked_paths globs (**/.env) and file_paths grants are matched with
# fnmatch against whatever string we send. Sending raw agent input would let
# host-absolute paths and backslashes slip past those globs.


async def test_target_sent_to_shepherd_is_worktree_relative(worktree):
    import json

    shepherd = shepherd_returning({"decision": ALLOW, "reason": "", "rule": ""})

    await check_tool_call(
        shepherd, worktree, "Write", {"file_path": str(worktree.path / "pkg" / "mod.py")}
    )

    sent = json.loads(shepherd.seen[0].content)
    assert sent["target"] == "pkg/mod.py"


async def test_dotenv_target_is_normalised_so_blocked_paths_can_match(worktree):
    import json

    shepherd = shepherd_returning({"decision": ALLOW, "reason": "", "rule": ""})

    await check_tool_call(
        shepherd, worktree, "Write", {"file_path": str(worktree.path / "backend" / ".env")}
    )

    sent = json.loads(shepherd.seen[0].content)
    # fnmatch("backend/.env", "**/.env") -> True; the host-absolute form would not
    # reliably match on Windows, where the separator is a backslash.
    assert sent["target"] == "backend/.env"
    assert "\\" not in sent["target"]


# --- Bash is withheld in Phase 1: its target is a command, not a path, so
# --- Shepherd's blocked_paths globs cannot see `cat backend/.env`.


async def test_bash_is_denied_by_default(worktree, monkeypatch):
    monkeypatch.delenv("STUDIO_ALLOW_BASH", raising=False)

    verdict = await check_tool_call(
        shepherd_that_must_not_be_called(), worktree, "Bash", {"command": "cat backend/.env"}
    )

    assert verdict.decision == BLOCK
    assert "bash" in verdict.reason.lower()


async def test_bash_can_be_armed_explicitly(worktree, monkeypatch):
    monkeypatch.setenv("STUDIO_ALLOW_BASH", "1")
    shepherd = shepherd_returning({"decision": ALLOW, "reason": "ok", "rule": "default_allow"})

    verdict = await check_tool_call(shepherd, worktree, "Bash", {"command": "pytest -q"})

    assert verdict.decision == ALLOW
