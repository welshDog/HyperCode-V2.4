"""Integration: our tool mapping against the REAL Shepherd policy + manifest.

The unit tests in test_shepherd.py mock Shepherd's HTTP, so they prove our
contract, not that the contract matches reality. This file imports the actual
``policy.evaluate`` and the actual ``capabilities.json`` and asserts the
security invariants survive the whole chain:

    Agent SDK tool call -> map_tool_call -> policy.evaluate -> decision

If someone loosens ``capabilities.json``, these fail.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from shepherd import STUDIO_AGENT, map_tool_call

_SHEPHERD_DIR = (Path(__file__).parent / ".." / "safety-shepherd").resolve()

if not (_SHEPHERD_DIR / "policy.py").exists():  # pragma: no cover - container builds
    pytest.skip("safety-shepherd source not present", allow_module_level=True)

sys.path.insert(0, str(_SHEPHERD_DIR))

from policy import ALLOW, BLOCK, ESCALATE, evaluate  # noqa: E402

MANIFEST = json.loads((_SHEPHERD_DIR / "capabilities.json").read_text(encoding="utf-8"))


def decide(tool_name: str, tool_input: dict, *, action_count: int = 0):
    payload = map_tool_call(tool_name, tool_input)
    assert payload is not None, f"{tool_name} did not map"
    return evaluate(MANIFEST, payload, action_count=action_count)


def test_the_studio_agent_has_an_explicit_grant():
    """Without one it silently inherits the '*' wildcard, whose file_paths are
    /workspace/** — every worktree-relative write would come back BLOCK.
    """
    assert STUDIO_AGENT in MANIFEST["agents"]


def test_ordinary_source_writes_are_allowed():
    assert decide("Write", {"file_path": "backend/app/foo.py"}).decision == ALLOW
    assert decide("Edit", {"file_path": "agents/coder-studio/main.py"}).decision == ALLOW


def test_reading_ordinary_source_is_allowed():
    assert decide("Read", {"file_path": "backend/app/main.py"}).decision == ALLOW


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        "backend/.env",
        "backend/.env.local",
        "a/b/c/.env.production",
        "backend/secrets/jwt.txt",
        "deploy/id_rsa",
        "keys/service_key.txt",
    ],
)
def test_secrets_are_blocked_for_writes(path: str):
    outcome = decide("Write", {"file_path": path})
    assert outcome.decision == BLOCK, f"{path} was {outcome.decision}"
    assert outcome.rule == "blocked_path"


@pytest.mark.parametrize("path", [".env", "backend/.env", "backend/secrets/jwt.txt"])
def test_secrets_are_blocked_for_reads_too(path: str):
    """Exfiltration is as bad as tampering — rule 2 ignores the category."""
    assert decide("Read", {"file_path": path}).decision == BLOCK


def test_bash_is_not_granted_even_if_the_service_arms_it():
    """Belt and braces: shepherd.py withholds bash, and the manifest also
    declines to grant it. Either alone would stop `cat backend/.env`.
    """
    assert decide("Bash", {"command": "pytest -q"}).decision == ESCALATE


def test_outbound_http_is_not_granted():
    assert decide("WebFetch", {"url": "https://evil.example.com/x"}).decision == ESCALATE
    assert decide("WebFetch", {"url": "https://api.anthropic.com/v1"}).decision == ESCALATE


def test_action_ceiling_escalates_a_runaway_agent():
    ceiling = MANIFEST["agents"][STUDIO_AGENT]["max_actions"]
    outcome = decide("Write", {"file_path": "app.py"}, action_count=ceiling)

    assert outcome.decision == ESCALATE
    assert outcome.rule == "rate_ceiling"
