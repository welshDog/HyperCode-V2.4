"""Unit tests for IdentityAgent pure logic (no DB — JSONB persistence is proven
via the live postgres E2E)."""

from app.agents.identity_agent import IDENTITY_HEADER, IdentityAgent
from app.models.identity import BROskiIdentityAgent


def _agent(state=None, discord_id="123", user_id=1):
    rec = BROskiIdentityAgent(user_id=user_id, discord_id=discord_id, state=state or {})
    return IdentityAgent(rec, db=None)  # db unused by the pure methods under test


def test_permission_allow_by_default():
    a = _agent({"permissions": {}})
    assert a.check_permission("shop.purchase") is True


def test_permission_explicit_deny():
    a = _agent({"permissions": {"deny": ["shop.refund"]}})
    assert a.check_permission("shop.refund") is False
    assert a.check_permission("shop.purchase") is True


def test_permission_allow_list_restricts():
    a = _agent({"permissions": {"allow": ["tokens.award", "quest.claim"]}})
    assert a.check_permission("tokens.award") is True
    assert a.check_permission("shop.refund") is False


def test_identity_header_prefers_discord_id():
    a = _agent(discord_id="418075243404591106")
    assert a.identity_header() == {IDENTITY_HEADER: "418075243404591106"}


def test_identity_header_falls_back_to_user_id():
    a = _agent(discord_id=None, user_id=7)
    assert a.identity_header()[IDENTITY_HEADER] == "7"


def test_state_is_a_copy():
    a = _agent({"tier": "free"})
    s = a.state
    s["tier"] = "pro"  # mutating the returned dict must not affect the record
    assert a.state["tier"] == "free"


class _FakeDB:
    """Minimal session stub — ring commits succeed; ledger add() raises."""

    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1

    def refresh(self, _obj):
        pass

    def add(self, _obj):
        raise RuntimeError("no governance_ledger table here")

    def rollback(self):
        pass


def test_log_action_is_fail_soft_when_ledger_unavailable():
    rec = BROskiIdentityAgent(user_id=1, discord_id="123", state={})
    agent = IdentityAgent(rec, _FakeDB())
    entry = agent.log_action("award_tokens", {"amount": 10}, "ALLOW")
    # Action still recorded in the in-state ring despite the ledger insert failing.
    assert entry["decision"] == "ALLOW"
    assert "ledger_id" not in entry
    assert rec.state["recent_actions"][-1]["tool"] == "award_tokens"
