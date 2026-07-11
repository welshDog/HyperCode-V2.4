"""Unit tests for the Claude Agent SDK wiring.

The whole safety story rests on ``can_use_tool`` actually being invoked. The SDK
will happily *not* invoke it — an ``allowed_tools`` entry naming a whole tool,
``permission_mode="bypassPermissions"``, or an allow-rule in a settings file all
auto-approve the call first, emitting only a warning. These tests pin that shut.
"""

from pathlib import Path

import httpx
import pytest
from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny, ToolPermissionContext

from agent_runner import (
    DEFAULT_MODEL,
    GateShadowedError,
    assert_gate_not_shadowed,
    build_options,
    make_gate,
)
from shepherd import ALLOW, BLOCK, ESCALATE, ShepherdClient
from worktree import Worktree


@pytest.fixture
def worktree(tmp_path: Path) -> Worktree:
    wt = tmp_path / "wt"
    wt.mkdir()
    return Worktree(repo=tmp_path / "repo", path=wt, branch="agent/x", base="main")


def shepherd_saying(decision: str, **extra) -> ShepherdClient:
    body = {"decision": decision, "reason": extra.pop("reason", "because"), "rule": "r", **extra}
    return ShepherdClient(
        base_url="http://shepherd:8096",
        api_key="k",
        transport=httpx.MockTransport(lambda _r: httpx.Response(200, json=body)),
    )


def shepherd_that_is_down() -> ShepherdClient:
    def handler(_r: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    return ShepherdClient("http://shepherd:8096", "k", transport=httpx.MockTransport(handler))


def ctx() -> ToolPermissionContext:
    return ToolPermissionContext(tool_use_id="toolu_1")


# --- The options must never shadow the gate ---


def test_allowed_tools_is_empty_so_nothing_is_auto_approved(worktree):
    options = build_options(worktree, make_gate(shepherd_saying(ALLOW), worktree))

    assert options.allowed_tools == []


def test_permission_mode_is_never_bypass(worktree):
    options = build_options(worktree, make_gate(shepherd_saying(ALLOW), worktree))

    assert options.permission_mode != "bypassPermissions"


def test_settings_files_cannot_grant_allow_rules(worktree):
    """Allow-rules from user/project settings shadow the callback invisibly."""
    options = build_options(worktree, make_gate(shepherd_saying(ALLOW), worktree))

    assert options.setting_sources == []


def test_bash_is_disallowed_at_the_sdk_level_too(worktree):
    options = build_options(worktree, make_gate(shepherd_saying(ALLOW), worktree))

    assert "Bash" in options.disallowed_tools


def test_agent_runs_inside_the_worktree(worktree):
    options = build_options(worktree, make_gate(shepherd_saying(ALLOW), worktree))

    assert Path(options.cwd) == worktree.path


def test_model_defaults_to_sonnet_and_is_overridable(worktree, monkeypatch):
    monkeypatch.delenv("STUDIO_MODEL", raising=False)
    assert build_options(worktree, make_gate(shepherd_saying(ALLOW), worktree)).model == DEFAULT_MODEL
    assert DEFAULT_MODEL == "claude-sonnet-5"

    # Global override via env.
    monkeypatch.setenv("STUDIO_MODEL", "claude-haiku-4-5")
    assert build_options(worktree, make_gate(shepherd_saying(ALLOW), worktree)).model == "claude-haiku-4-5"

    # Per-session override wins over env (this is what the UI picker sends).
    picked = build_options(worktree, make_gate(shepherd_saying(ALLOW), worktree), model="claude-opus-4-8")
    assert picked.model == "claude-opus-4-8"


def test_the_sdk_itself_agrees_our_options_do_not_shadow_the_gate(worktree):
    """Binds to the SDK's own detector, so an SDK rule change fails here."""
    from claude_agent_sdk.types import _get_can_use_tool_shadowed_warning

    options = build_options(worktree, make_gate(shepherd_saying(ALLOW), worktree))

    assert _get_can_use_tool_shadowed_warning(options.permission_mode, options.allowed_tools) is None


def test_assert_gate_not_shadowed_rejects_a_whole_tool_allowance(worktree):
    options = build_options(worktree, make_gate(shepherd_saying(ALLOW), worktree))
    options.allowed_tools = ["Write"]

    with pytest.raises(GateShadowedError):
        assert_gate_not_shadowed(options)


def test_assert_gate_not_shadowed_rejects_bypass_permissions(worktree):
    options = build_options(worktree, make_gate(shepherd_saying(ALLOW), worktree))
    options.permission_mode = "bypassPermissions"

    with pytest.raises(GateShadowedError):
        assert_gate_not_shadowed(options)


# --- The gate translates Shepherd verdicts into SDK permission results ---


async def test_allow_becomes_permission_result_allow(worktree):
    gate = make_gate(shepherd_saying(ALLOW), worktree)

    result = await gate("Write", {"file_path": "app.py"}, ctx())

    assert isinstance(result, PermissionResultAllow)


async def test_block_becomes_deny_carrying_the_reason(worktree):
    gate = make_gate(shepherd_saying(BLOCK, reason="target is hard-blocked"), worktree)

    result = await gate("Write", {"file_path": "app.py"}, ctx())

    assert isinstance(result, PermissionResultDeny)
    assert "hard-blocked" in result.message


async def test_escalate_denies_rather_than_allowing(worktree):
    """Phase 1 has no approval UI. An ESCALATE must never fall through to allow."""
    gate = make_gate(shepherd_saying(ESCALATE, reason="tool not granted"), worktree)

    result = await gate("Write", {"file_path": "app.py"}, ctx())

    assert isinstance(result, PermissionResultDeny)
    assert "approval" in result.message.lower()


async def test_shepherd_down_denies(worktree):
    gate = make_gate(shepherd_that_is_down(), worktree)

    result = await gate("Write", {"file_path": "app.py"}, ctx())

    assert isinstance(result, PermissionResultDeny)


async def test_dotenv_write_denies_without_contacting_shepherd(worktree):
    def explode(_r: httpx.Request) -> httpx.Response:
        raise AssertionError("Shepherd must not be consulted for an escape")

    down = ShepherdClient("http://s:8096", "k", transport=httpx.MockTransport(explode))
    gate = make_gate(down, worktree)

    result = await gate("Write", {"file_path": "../../../etc/passwd"}, ctx())

    assert isinstance(result, PermissionResultDeny)


# --- Every decision is recorded, for the SSE stream and the audit ledger ---


async def test_each_decision_is_recorded(worktree):
    seen = []
    gate = make_gate(shepherd_saying(BLOCK, reason="nope"), worktree, on_decision=seen.append)

    await gate("Write", {"file_path": "app.py"}, ctx())

    assert len(seen) == 1
    record = seen[0]
    assert record["tool"] == "Write"
    assert record["decision"] == BLOCK
    assert record["tool_use_id"] == "toolu_1"


# --- ESCALATE with optional approval callback ---


async def test_escalate_with_approval_granted_becomes_allow(worktree):
    async def approve(tool_name, tool_input, verdict):
        return True

    gate = make_gate(shepherd_saying(ESCALATE, reason="tool not granted"), worktree,
                     resolve_escalation=approve)

    result = await gate("Write", {"file_path": "app.py"}, ctx())

    assert isinstance(result, PermissionResultAllow)


async def test_escalate_with_approval_denied_becomes_deny(worktree):
    async def deny(tool_name, tool_input, verdict):
        return False

    gate = make_gate(shepherd_saying(ESCALATE, reason="tool not granted"), worktree,
                     resolve_escalation=deny)

    result = await gate("Write", {"file_path": "app.py"}, ctx())

    assert isinstance(result, PermissionResultDeny)


async def test_escalate_receives_the_tool_and_verdict(worktree):
    seen = {}

    async def capture(tool_name, tool_input, verdict):
        seen["tool"] = tool_name
        seen["rule"] = verdict.rule
        return True

    gate = make_gate(shepherd_saying(ESCALATE, rule="unknown_tool"), worktree,
                     resolve_escalation=capture)

    await gate("Write", {"file_path": "app.py"}, ctx())

    assert seen == {"tool": "Write", "rule": "unknown_tool"}
