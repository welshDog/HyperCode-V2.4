"""Unit tests for the Safety Shepherd decision engine (pure, no infra)."""

import json
from pathlib import Path

import pytest

from policy import ALLOW, BLOCK, ESCALATE, evaluate

MANIFEST = json.loads((Path(__file__).parent / "capabilities.json").read_text(encoding="utf-8"))


def d(agent, **kw):
    """Helper: d."""
    return evaluate(MANIFEST, {"agent": agent, **kw}, action_count=kw.pop("_count", 0))


def test_stripe_is_always_exempt():
    # Even for an unknown agent, Stripe must never be gated.
    """Test stripe is always exempt."""
    out = evaluate(MANIFEST, {"agent": "whoever", "category": "stripe", "domain": "api.stripe.com"})
    assert out.decision == ALLOW and out.rule == "exempt"


def test_hard_blocked_path_beats_everything():
    """Test hard blocked path beats everything."""
    out = d("backend_specialist", category="file_write", tool="file_write", target="backend/secrets/jwt_secret.txt")
    assert out.decision == BLOCK and out.rule == "blocked_path"

    out2 = d("coder_agent", category="file_write", tool="file_write", target="backend/.env")
    assert out2.decision == BLOCK


def test_unknown_agent_uses_wildcard_then_escalates_dangerous():
    # "*" wildcard grants file_read only → a docker action escalates.
    """Test unknown agent uses wildcard then escalates dangerous."""
    out = d("mystery_agent", category="docker", tool="docker_run")
    assert out.decision == ESCALATE


def test_allowed_file_write_within_paths():
    """Test allowed file write within paths."""
    out = d("coder_agent", category="file_write", tool="file_write", target="backend/app/main.py")
    assert out.decision == ALLOW and out.rule == "default_allow"


def test_file_write_outside_allowed_paths_blocks():
    """Test file write outside allowed paths blocks."""
    out = d("database_architect", category="file_write", tool="file_write", target="frontend/src/App.tsx")
    assert out.decision == BLOCK and out.rule == "path_not_allowed"


def test_tool_not_granted_escalates():
    """Test tool not granted escalates."""
    out = d("qa_engineer", category="generic", tool="file_write", target="x")
    assert out.decision == ESCALATE and out.rule == "tool_not_granted"


def test_external_domain_not_allowlisted_escalates():
    """Test external domain not allowlisted escalates."""
    out = d("backend_specialist", category="http_external", tool="http_external", domain="evil.example.com")
    assert out.decision == ESCALATE and out.rule == "domain_not_granted"


def test_external_domain_allowlisted_allows():
    """Test external domain allowlisted allows."""
    out = d("backend_specialist", category="http_external", tool="http_external", domain="github.com")
    assert out.decision == ALLOW


def test_docker_granted_to_devops_allows():
    """Test docker granted to devops allows."""
    out = d("devops_engineer", category="docker", tool="docker")
    assert out.decision == ALLOW


def test_governor_grant_allows_its_two_actions():
    """Follow-up fix (parked I4 from the governor Phase 2 final review):
    before this grant existed, governor was an unknown agent and every real
    mint request ESCALATEd via the wildcard's file_read-only grant (rule 3
    -> rule 9), never reaching a real ALLOW/BLOCK. Pins the exact request
    shape shepherd_client.py sends -- category='docker' always, tool=the
    literal action kind -- for both actions RequestedAction.kind's Literal
    allows."""
    out = d("governor", category="docker", tool="compose_profile.preview")
    assert out.decision == ALLOW and out.rule == "default_allow"

    out2 = d("governor", category="docker", tool="crew.workflow.preview")
    assert out2.decision == ALLOW and out2.rule == "default_allow"


def test_governor_grant_does_not_widen_to_other_docker_actions():
    """The grant is scoped to the two literal action strings, not the whole
    'docker' category -- an action shape governor's own pydantic model
    could never actually send must still escalate, proving this isn't a
    disguised blanket docker grant."""
    out = d("governor", category="docker", tool="compose_profile.start")
    assert out.decision == ESCALATE and out.rule == "tool_not_granted"


def test_rate_ceiling_escalates():
    """Test rate ceiling escalates."""
    out = evaluate(
        MANIFEST,
        {"agent": "qa_engineer", "category": "generic", "tool": "file_read"},
        action_count=999,
    )
    assert out.decision == ESCALATE and out.rule == "rate_ceiling"


def test_blocked_domain():
    """Test blocked domain."""
    manifest = json.loads(json.dumps(MANIFEST))
    manifest["blocked_domains"] = ["malware.test"]
    out = evaluate(manifest, {"agent": "backend_specialist", "category": "http_external",
                              "tool": "http_external", "domain": "malware.test"})
    assert out.decision == BLOCK and out.rule == "blocked_domain"


def test_evaluate_response_backcompat():
    """Test evaluate response backcompat."""
    from policy import evaluate
    manifest = {"agents": {"*": {"tools": []}}, "defaults": {}}
    d = evaluate(manifest, {"agent": "x", "category": "generic"})
    out = d.as_dict()
    assert set(["decision", "reason", "rule", "category"]).issubset(out)  # old contract intact
