"""HyperCrew Day 8 — Quest Settler: small, capped, idempotent, evidence-backed, human-only."""

import asyncio
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from app.crew import quests, tools as crew_tools
from app.crew.evidence import build_bundle, evidence_for
from app.crew.plan import build_crew_plan, crew_plan_hash
from app.models.broski import BROskiTransaction, BROskiUserAchievement, BROskiWallet, QuestSettlement
from app.models.models import User
from app.services.broski_service import seed_achievements

RUN = "00000000-0000-4000-8000-000000000001"
PLAN = build_crew_plan("add a health endpoint", RUN)
HASH = crew_plan_hash(PLAN)
NOW = datetime(2026, 10, 2, 15, 0, tzinfo=timezone.utc)


def history(run_id=RUN, approver="bro@example.com", verdict="ALLOW", extra=(), plan_hash=HASH, bundle_run=None,
            tamper=False, sealed=True, build_twice=False):
    items = [evidence_for("diff", run_id, "build", "diff text"), evidence_for("log", run_id, "verify", "VERDICT: PASS")]
    bundle = build_bundle(bundle_run or run_id, plan_hash, items)
    if tamper:
        bundle["run_id"] = "someone-else"  # contents changed after hashing
    allowed = verdict == "ALLOW"
    h = [
        {"node": "seal", "status": "completed",
         "result": {"data": {"sealed": sealed, "plan": PLAN, "plan_hash": HASH, "approved_by": approver}}},
        {"node": "build", "status": "completed", "result": {"data": {"summary": "x"}}},
        {"node": "verify", "status": "completed", "result": {"data": {"summary": "VERDICT: PASS"}}},
        {"node": "guard", "status": "completed",
         "result": {"data": {"verdict": verdict, "allowed": allowed, "failed_checks": [] if allowed else ["verifier_verdict"],
                             "evidence_bundle": bundle}}},
    ]
    if build_twice:
        h.insert(2, {"node": "build", "status": "completed", "result": {"data": {"summary": "x"}}})
    h.extend(extra)
    return h


@pytest.fixture
def human(db):
    u = User(email="bro@example.com", hashed_password="x", is_active=True, is_superuser=True)
    db.add(u)
    db.commit()
    seed_achievements(db)
    return u


def wallet(db, user):
    db.expire_all()
    return db.query(BROskiWallet).filter_by(user_id=user.id).first()


def settle(db, hist=None, run=RUN, now=NOW):
    return quests.settle_run(db, run, history() if hist is None else hist, now=now)


# ── paying the right person, the right amount ────────────────────────────────────────
def test_a_verified_run_pays_the_approving_human_with_a_traceable_transaction(db, human):
    s = settle(db)
    assert (s.status, s.xp, s.coins) == ("awarded", 20, 10)
    w = wallet(db, human)
    assert w.xp >= 20 and w.coins >= 10
    tx = db.query(BROskiTransaction).filter_by(wallet_id=w.id).filter(BROskiTransaction.reason == "Quest: crew run").one()
    assert tx.meta["source_id"] == f"{RUN}:crew_run"
    row = db.query(QuestSettlement).one()
    assert row.source_id == f"{RUN}:crew_run" and row.user_id == human.id and row.bundle_hash.startswith("sha256:")


def test_a_run_that_needed_a_second_go_still_earns_just_less(db, human):
    s = settle(db, history(build_twice=True))
    assert s.xp == quests.RETRIED_XP and 0 < s.xp < quests.BASE_XP
    assert "zero_retry_run" not in {a.achievement_slug for a in db.query(BROskiUserAchievement).all()}


# ── replay can never pay twice ───────────────────────────────────────────────────────
def test_replaying_a_settle_pays_nothing_more(db, human):
    first = settle(db)
    xp_after_first = wallet(db, human).xp
    again = settle(db)
    assert again.already_settled is True and (again.status, again.xp) == (first.status, first.xp)
    assert wallet(db, human).xp == xp_after_first
    assert db.query(QuestSettlement).count() == 1


def test_the_database_itself_refuses_a_second_row_for_the_same_run(db, human):
    settle(db)
    db.add(QuestSettlement(source_id=f"{RUN}:crew_run", run_id=RUN, quest_id="crew_run", status="awarded"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_a_lost_race_pays_once_and_reports_already_settled(db, human, monkeypatch):
    """Another process settled between our look and our insert: the UNIQUE key makes us the loser."""
    real = db.query(QuestSettlement)
    settle_first = quests.settle_run(db, RUN, history(), now=NOW)
    assert settle_first.xp == 20
    xp_before = wallet(db, human).xp
    orig = type(db).query
    calls = {"n": 0}

    def blind_first_lookup(self, *a, **k):
        q = orig(self, *a, **k)
        if a and a[0] is QuestSettlement and calls["n"] == 0:
            calls["n"] += 1
            return q.filter(QuestSettlement.id == -1)  # "nothing there yet"
        return q

    monkeypatch.setattr(type(db), "query", blind_first_lookup)
    again = quests.settle_run(db, RUN, history(), now=NOW)
    monkeypatch.undo()
    assert again.already_settled is True
    assert real.count() == 1 and wallet(db, human).xp == xp_before  # not paid twice


# ── no evidence, no XP ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("hist,why", [
    (lambda: history(verdict="BLOCK"), "guard did not ALLOW"),
    (lambda: history(tamper=True), "does not verify"),
    (lambda: history(bundle_run="other-run"), "not for this run"),
    (lambda: history(plan_hash="sha256:" + "1" * 64), "not for this run and plan"),
    (lambda: history(sealed=False), "never sealed"),
    (lambda: history(approver=""), "no recorded human approver"),
    (lambda: [], "never sealed"),
])
def test_a_run_without_proof_earns_zero_and_leaves_no_wallet_change(db, human, hist, why):
    s = settle(db, hist())
    assert s.status == "no_award" and s.xp == 0 and why in s.reason
    assert wallet(db, human) is None  # not even a wallet was opened for the human


def test_a_blocked_run_cannot_be_paid_later_by_replaying_it(db, human):
    settle(db, history(verdict="BLOCK"))
    again = settle(db)  # same run id, now with a good-looking history
    assert again.already_settled is True and again.xp == 0


@pytest.mark.parametrize("approver", ["agent:coder-agent", "stranger@example.com", "coder-agent"])
def test_only_a_known_active_human_superuser_is_ever_paid(db, human, approver):
    s = settle(db, history(approver=approver))
    assert s.status == "no_award" and s.xp == 0
    assert db.query(BROskiTransaction).count() == 0


def test_an_inactive_or_non_super_account_is_not_paid(db):
    db.add(User(email="gone@example.com", hashed_password="x", is_active=False, is_superuser=True))
    db.add(User(email="plain@example.com", hashed_password="x", is_active=True, is_superuser=False))
    db.commit()
    for email in ("gone@example.com", "plain@example.com"):
        assert settle(db, history(approver=email), run=f"{RUN}-{email}").xp == 0


# ── caps ─────────────────────────────────────────────────────────────────────────────
def _earlier(db, user, xp, when):
    db.add(QuestSettlement(source_id=f"r{when.isoformat()}{xp}:q", run_id="r", quest_id="q", user_id=user.id,
                           status="awarded", xp=xp, coins=0, created_at=when))
    db.commit()


def test_the_daily_ceiling_trims_then_stops_the_award_without_ever_going_negative(db, human):
    _earlier(db, human, quests.DAILY_XP_CAP - 5, NOW - timedelta(hours=3))
    trimmed = settle(db)
    assert trimmed.status == "awarded" and trimmed.xp == 5 and "ceiling" in trimmed.reason
    capped = settle(db, history(run_id="r2"), run="r2")
    assert capped.status == "capped" and capped.xp == 0 and capped.coins == 0
    assert wallet(db, human).xp >= 0


def test_yesterdays_xp_does_not_count_against_today(db, human):
    _earlier(db, human, quests.DAILY_XP_CAP, NOW - timedelta(days=1))
    assert settle(db).xp == quests.BASE_XP


def test_a_capped_run_stays_unpaid_when_replayed_tomorrow(db, human):
    _earlier(db, human, quests.DAILY_XP_CAP, NOW - timedelta(hours=1))
    assert settle(db).status == "capped"
    tomorrow = settle(db, now=NOW + timedelta(days=1))
    assert tomorrow.already_settled is True and tomorrow.xp == 0


def test_no_code_path_in_the_settler_subtracts_xp():
    src = Path(quests.__file__).read_text()
    assert not re.search(r"\bxp\s*-=", src) and not re.search(r"\.xp\s*-=", src)
    assert "max(0," in src  # the only subtraction is the headroom floor under the cap


# ── achievements ─────────────────────────────────────────────────────────────────────
def earned(db):
    return {a.achievement_slug for a in db.query(BROskiUserAchievement).all()}


def test_a_clean_first_run_unlocks_the_run_achievements_once(db, human):
    s = settle(db)
    assert earned(db) == {"first_squad_run", "zero_retry_run", "green_first_verify"}
    assert len(s.achievements) == 3
    settle(db, history(run_id="r2"), run="r2")
    assert earned(db) == {"first_squad_run", "zero_retry_run", "green_first_verify"}  # one-off per wallet
    assert db.query(BROskiUserAchievement).count() == 3


def test_panic_used_well_needs_pause_and_resume_on_the_same_day(db, human):
    same = [{"type": "control", "status": "paused", "ts": "2026-10-02T10:00:00+00:00"},
            {"type": "control", "status": "resumed", "ts": "2026-10-02T18:00:00+00:00"}]
    settle(db, history(extra=same))
    assert "panic_used_well" in earned(db)


def test_a_pause_resumed_the_next_day_is_not_panic_used_well(db, human):
    nextday = [{"type": "control", "status": "paused", "ts": "2026-10-02T23:00:00+00:00"},
               {"type": "control", "status": "resumed", "ts": "2026-10-03T08:00:00+00:00"}]
    settle(db, history(extra=nextday))
    assert "panic_used_well" not in earned(db)


def test_handover_written_is_seeded_but_only_the_scribe_can_unlock_it(db, human):
    from app.models.broski import BROskiAchievement

    assert db.query(BROskiAchievement).filter_by(slug="handover_written").count() == 1
    settle(db)
    assert "handover_written" not in earned(db)


def test_a_run_without_proof_unlocks_no_achievement(db, human):
    settle(db, history(verdict="BLOCK"))
    assert earned(db) == set()


# ── agents and MCP clients have no path to it ────────────────────────────────────────
def test_there_is_no_route_or_mcp_tool_that_settles_or_awards_crew_quests():
    from app.main import app

    assert not [r.path for r in app.routes if "settle" in getattr(r, "path", "")]
    server = (Path(__file__).resolve().parents[2] / "services/hypercode-mcp-server/server.py").read_text()
    assert "settle" not in server.lower() and "award" not in server.lower()


def test_the_settle_tool_is_only_a_flow_node_after_a_guard_allow():
    from app.agents.hyperflow.registry import get_flow

    flow = get_flow("hypercode-crew")
    assert flow.version == 3 and flow.node("settle").tool == "local.crew_settle" and flow.node("settle").idempotent
    edge = [e for e in flow.edges if e.dst == "settle"]
    assert len(edge) == 1 and edge[0].src == "guard" and edge[0].condition is True


# ── the tool never turns finished work into a failure ────────────────────────────────
def test_a_settlement_error_is_reported_not_raised(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("db down")

    monkeypatch.setattr(crew_tools, "_settle_sync", boom)
    out = asyncio.run(crew_tools.crew_settle({}, {"run_id": RUN, "history": history()}))
    assert out["ok"] is True and out["status"] == "error" and out["xp"] == 0 and out["performed"] is False


# ── how a win is shown: quiet, one line, never a "you got nothing" ───────────────────
def _settle_entry(**data):
    return {"node": "settle", "status": "completed", "result": {"data": {"ok": True, **data}}}


def test_the_card_shows_one_quiet_xp_line_only_for_a_real_award():
    from app.crew.cards import calm_card_for_run

    def card(*entries):
        return calm_card_for_run(run_id=RUN, run_status="completed", history=history(extra=entries),
                                 current_node=None, error=None, at_gate=False)

    won = card(_settle_entry(status="awarded", xp=20))
    assert won.tldr[-1] == "+20 XP for a verified run" and len(won.tldr) <= 5
    for quiet in (_settle_entry(status="no_award", xp=0), _settle_entry(status="capped", xp=0),
                  _settle_entry(status="error", xp=0)):
        c = card(quiet)
        assert all("XP" not in line and "settle" not in line.lower() for line in c.tldr)  # nothing to feel bad about


def test_the_event_stream_announces_a_win_only_when_one_was_awarded():
    from app.crew.agui import history_to_events

    def quest_events(**data):
        ev = history_to_events(RUN, history(extra=[_settle_entry(**data)]))
        return [e["event"] for e in ev if e["event"].get("name") == "hypercode.quest.settled"]

    got = quest_events(status="awarded", xp=20, coins=10, achievements=["a"])
    assert len(got) == 1 and got[0]["value"]["xp"] == 20
    assert quest_events(status="capped", xp=0) == [] and quest_events(status="no_award", xp=0) == []
