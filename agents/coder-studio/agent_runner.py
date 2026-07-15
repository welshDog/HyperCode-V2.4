"""Claude Agent SDK wiring for coder-studio.

The agent runs inside a throwaway git worktree, and every tool call it attempts
is routed through Safety Shepherd via ``can_use_tool``.

⚠️ The SDK will silently skip ``can_use_tool``. Any of these auto-approve a call
*before* the callback is consulted, emitting only a ``CanUseToolShadowedWarning``:

  * an ``allowed_tools`` entry naming a whole tool (``"Write"``, ``"Read()"``)
  * ``permission_mode="bypassPermissions"``
  * ``skills="all"``
  * an allow-rule in a user/project settings file (invisible to the SDK's own check)

So ``allowed_tools`` stays empty, ``setting_sources`` stays empty, and
``assert_gate_not_shadowed`` is called before every run.
"""

from __future__ import annotations

import os
from typing import Any, AsyncIterator, Awaitable, Callable, Optional

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)
from claude_agent_sdk.types import _get_can_use_tool_shadowed_warning

from shepherd import ALLOW, BLOCK, ESCALATE, ShepherdClient, check_tool_call
from worktree import Worktree

# Sonnet 5 is the everyday default — near-Opus quality on coding at a fraction
# of the cost. Override per-session (the UI model picker) or globally via
# STUDIO_MODEL. Any valid model id is accepted; the UI offers the current set.
DEFAULT_MODEL = "claude-sonnet-5"

# Belt and braces. shepherd.py withholds bash and the manifest declines to grant
# it; this stops the SDK from offering it in the first place.
DISALLOWED_TOOLS = ["Bash", "WebFetch", "WebSearch", "Task", "KillShell"]

DecisionSink = Callable[[dict[str, Any]], None]
EscalationResolver = Callable[[str, dict[str, Any], Any], Awaitable[bool]]


class GateShadowedError(RuntimeError):
    """The options would let a tool run without consulting Safety Shepherd."""


def assert_gate_not_shadowed(options: ClaudeAgentOptions) -> None:
    """Refuse to run if the SDK would bypass ``can_use_tool``.

    Delegates to the SDK's own detector so that if its shadowing rules change,
    we fail loudly here instead of silently running an ungated agent.
    """
    if options.can_use_tool is None:
        raise GateShadowedError("no can_use_tool callback: every tool call would be ungated")

    warning = _get_can_use_tool_shadowed_warning(options.permission_mode, options.allowed_tools)
    if warning is not None:
        raise GateShadowedError(warning)

    if options.setting_sources:
        raise GateShadowedError(
            "setting_sources must be empty: allow-rules in settings files shadow "
            "can_use_tool invisibly"
        )


def make_gate(
    shepherd: ShepherdClient,
    worktree: Worktree,
    on_decision: Optional[DecisionSink] = None,
    resolve_escalation: Optional[EscalationResolver] = None,
):
    """Build the ``can_use_tool`` callback. Denies on anything but a clear ALLOW."""

    async def gate(
        tool_name: str,
        tool_input: dict[str, Any],
        context: ToolPermissionContext,
    ) -> PermissionResultAllow | PermissionResultDeny:
        verdict = await check_tool_call(shepherd, worktree, tool_name, tool_input)

        if on_decision is not None:
            on_decision(
                {
                    "tool": tool_name,
                    "input": tool_input,
                    "decision": verdict.decision,
                    "reason": verdict.reason,
                    "rule": verdict.rule,
                    "approval_id": verdict.approval_id,
                    "tool_use_id": context.tool_use_id,
                }
            )

        if verdict.decision == ALLOW:
            return PermissionResultAllow()

        if verdict.decision == ESCALATE:
            if resolve_escalation is None:
                # Preserved safe default: no approval wired -> fail closed.
                return PermissionResultDeny(
                    message=f"Needs human approval ({verdict.rule}): {verdict.reason}"
                )
            approved = await resolve_escalation(tool_name, tool_input, verdict)
            if approved:
                return PermissionResultAllow()
            return PermissionResultDeny(message="Denied by human review (or timed out)")

        assert verdict.decision == BLOCK
        return PermissionResultDeny(message=f"Blocked by Safety Shepherd: {verdict.reason}")

    return gate


def build_options(worktree: Worktree, gate, model: Optional[str] = None) -> ClaudeAgentOptions:
    """Options that keep the agent inside the worktree and behind the gate."""
    return ClaudeAgentOptions(
        cwd=str(worktree.path),
        model=model or os.getenv("STUDIO_MODEL") or DEFAULT_MODEL,
        can_use_tool=gate,
        # Empty: any whole-tool entry here would auto-approve before the gate.
        allowed_tools=[],
        disallowed_tools=list(DISALLOWED_TOOLS),
        # Empty: settings-file allow-rules shadow the gate and are invisible.
        setting_sources=[],
        permission_mode="default",
        max_turns=int(os.getenv("STUDIO_MAX_TURNS", "30")),
    )


async def run_agent(
    worktree: Worktree,
    shepherd: ShepherdClient,
    prompt: str,
    *,
    model: Optional[str] = None,
    env: Optional[dict[str, str]] = None,
    on_decision: Optional[DecisionSink] = None,
    resolve_escalation: Optional[EscalationResolver] = None,
) -> AsyncIterator[Any]:
    """Run one task inside the worktree, yielding SDK messages as they arrive.

    Uses ``ClaudeSDKClient`` rather than ``query()``. ``query()`` is
    unidirectional: once the prompt iterator is exhausted the SDK closes the
    CLI's stdin, and the permission request dies with
    ``Tool permission request failed: Error: Stream closed`` — the gate is never
    consulted and every tool call fails. The client keeps the control protocol
    open for the life of the turn.
    """
    gate = make_gate(shepherd, worktree, on_decision=on_decision, resolve_escalation=resolve_escalation)
    options = build_options(worktree, gate, model=model)
    if env:
        options.env = env

    # Refuse to run an agent whose tool calls would bypass Safety Shepherd.
    assert_gate_not_shadowed(options)

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            yield message
