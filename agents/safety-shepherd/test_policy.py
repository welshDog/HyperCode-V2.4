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


# -- crew stage tools (2026-10-03, found by the IDE health check) ------------------------------------
# The orchestrator asks the Shepherd about tools `crew_build` / `crew_verify` using the HYPHENATED agent names
# (`coder-agent`, `qa-engineer`). policy._agent_caps is an exact-key lookup and the manifest's per-agent entries are
# underscored (`coder_agent`, `qa_engineer`), so these agents fell through to the `*` wildcard (tools: file_read only):
# every crew dispatch ESCALATEd ("tool not granted"), hidden by monitor mode (enforce would have stalled every crew build).
# Fix (data only, least privilege): two hyphenated entries = the wildcard's rights + exactly ONE crew tool each.

def test_the_builder_may_dispatch_crew_build_under_the_name_the_orchestrator_sends():
    assert d("coder-agent", category="generic", tool="crew_build").decision == ALLOW


def test_the_verifier_may_dispatch_crew_verify_under_the_name_the_orchestrator_sends():
    assert d("qa-engineer", category="generic", tool="crew_verify").decision == ALLOW


def test_separation_of_duties_builder_cannot_verify_and_verifier_cannot_build():
    for agent, tool in (("coder-agent", "crew_verify"), ("qa-engineer", "crew_build")):
        out = d(agent, category="generic", tool=tool)
        assert out.decision == ESCALATE and out.rule == "tool_not_granted", (agent, tool)


def test_no_other_agent_holds_a_crew_tool():
    holders = {name: sorted(t for t in caps.get("tools", []) if t.startswith("crew_"))
               for name, caps in MANIFEST["agents"].items()
               if any(t.startswith("crew_") for t in caps.get("tools", []))}
    assert holders == {"coder-agent": ["crew_build"], "qa-engineer": ["crew_verify"]}


def test_the_underscored_entries_were_not_widened():
    # they are not what the orchestrator sends; granting them would have changed nothing live (and widened them for nothing)
    for agent in ("coder_agent", "qa_engineer"):
        for tool in ("crew_build", "crew_verify"):
            assert d(agent, category="generic", tool=tool).decision == ESCALATE, (agent, tool)


BATTERY = [  # everything EXCEPT the crew tools: the new entries must behave exactly like the wildcard they replace
    dict(category="file_write", tool="file_write", target="/workspace/a.txt"),
    dict(category="file_write", tool="file_write", target="backend/.env"),
    dict(category="file_write", tool="file_write", target="/etc/passwd"),
    dict(category="generic", tool="file_read", target="/workspace/a.txt"),
    dict(category="generic", tool="git"),
    dict(category="generic", tool="docker"),
    dict(category="docker", tool="docker"),
    dict(category="http_external", tool="http_external", domain="github.com"),
    dict(category="http_external", tool="http_external", domain="evil.example.com"),
    dict(category="generic"),
    dict(category="stripe", domain="api.stripe.com"),
]


@pytest.mark.parametrize("agent", ["coder-agent", "qa-engineer"])
@pytest.mark.parametrize("req", BATTERY, ids=lambda r: f"{r['category']}:{r.get('tool', '-')}:{r.get('target', r.get('domain', '-'))}")
def test_apart_from_its_one_crew_tool_the_new_entry_decides_exactly_like_the_wildcard(agent, req):
    via_wildcard = evaluate(MANIFEST, {"agent": "an-agent-with-no-entry", **req})
    via_entry = evaluate(MANIFEST, {"agent": agent, **req})
    assert (via_entry.decision, via_entry.rule) == (via_wildcard.decision, via_wildcard.rule), (agent, req)
