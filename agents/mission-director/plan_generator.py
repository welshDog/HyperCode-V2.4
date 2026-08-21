# agents/mission-director/plan_generator.py
"""
LLM call -> forced structured output -> MissionProposal's plan-generation
inputs. Uses Anthropic tool-use with tool_choice pinned to a single tool,
so a well-formed response is either exactly the shape we asked for or the
call fails outright -- never a free-text response to parse. Same
Anthropic->client pattern as agents/09-tips-tricks-writer/base_agent.py's
_build_llm_client, scoped down: this agent has no Ollama fallback, because
a plan proposal with no real reasoning behind it is worse than a clear
"LLM unavailable" (PlanGenerationError -> preview_unavailable) --
Ollama-fallback silence would look like a considered plan.
"""
from __future__ import annotations

import os
from typing import Optional

from pydantic import BaseModel, ValidationError

from models import RequestedAction

_TOOL_NAME = "submit_plan"

_TOOL_SCHEMA = {
    "name": _TOOL_NAME,
    "description": "Submit a proposed DRY-RUN infrastructure-change plan for the given goal.",
    "input_schema": {
        "type": "object",
        "properties": {
            "rationale": {
                "type": "string",
                "description": "Why this plan addresses the goal. Advisory reasoning only, never validated as fact.",
            },
            "requested_actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action_id": {"type": "string"},
                        "kind": {
                            "type": "string",
                            "enum": ["compose_profile.preview", "crew.workflow.preview"],
                        },
                        "profile": {"type": ["string", "null"]},
                    },
                    "required": ["action_id", "kind"],
                },
            },
        },
        "required": ["rationale", "requested_actions"],
    },
}

_SYSTEM_PROMPT = (
    "You are mission-director's planner. Given a human goal, propose a "
    "DRY-RUN infrastructure-change plan using only the action kinds "
    "'compose_profile.preview' or 'crew.workflow.preview'. You have zero "
    "execution authority -- this produces a preview proposal only, "
    "reviewed by a human before anything else can ever happen. Always "
    "call submit_plan with your answer."
)


class LLMPlanOutput(BaseModel):
    rationale: str
    requested_actions: list[RequestedAction]


class PlanGenerationError(Exception):
    """The LLM call failed outright (timeout, API error, no client
    configured) -- an infrastructure failure, not a plan-quality failure.
    Caller maps this to status=preview_unavailable."""


class PlanMalformedError(Exception):
    """The LLM responded but its output didn't validate against
    LLMPlanOutput. Caller maps this to status=rejected_malformed -- never
    coerced, never auto-retried."""


_client = None


def init() -> None:
    """Create the Anthropic client if ANTHROPIC_API_KEY is configured.
    Call from lifespan startup. Leaves _client None otherwise -- generate()
    then always raises PlanGenerationError, fail-closed by omission."""
    global _client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return
    from anthropic import AsyncAnthropic

    _client = AsyncAnthropic(api_key=api_key)


async def aclose() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def generate(goal: str) -> LLMPlanOutput:
    if _client is None:
        raise PlanGenerationError("no LLM client configured (set ANTHROPIC_API_KEY)")

    try:
        resp = await _client.messages.create(
            model=os.getenv("AGENT_MODEL", "claude-sonnet-4-6"),
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": goal}],
            tools=[_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
        )
    except Exception as exc:
        raise PlanGenerationError(str(exc)) from exc

    tool_use = next((b for b in resp.content if getattr(b, "type", None) == "tool_use"), None)
    if tool_use is None:
        raise PlanMalformedError("no tool_use block in LLM response")

    try:
        return LLMPlanOutput(**tool_use.input)
    except ValidationError as exc:
        raise PlanMalformedError(str(exc)) from exc
