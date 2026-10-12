"""HyperCrew Day 9 — the Morning Card: one calm card, one traffic light, one next action, never shaming."""

from datetime import datetime, timedelta, timezone

import pytest

from app.crew.morning import build_morning_card, traffic_light
from app.main import app
from app.models.broski import QuestSettlement
from app.models.hyperflow import HyperFlowRun
from tests.test_crew_operator_api import _as

NOW = datetime(2026, 10, 3, 8, 0, tzinfo=timezone.utc)
FLOOR = 1200
BASE = "/api/v1/operator"


def card(db, user_id=1, mb=4000, floor=FLOOR):
    return build_morning_card(db, now=NOW, user_id=user_id, available_mb=mb, floor_mb=floor)


def win(db, run, xp=20, user_id=1, hours_ago=3, status="awarded", quest="crew_run"):
    db.add(QuestSettlement(source_id=f"{run}:{quest}", run_id=run, quest_id=quest, user_id=user_id, status=status,
                           xp=xp, coins=0, created_at=NOW - timedelta(hours=hours_ago)))
    db.commit()


def run_row(db, run_id, status, context=None):
    db.add(HyperFlowRun(id=run_id, flow_name="hypercode-crew", flow_version=4, status=status,
                        current_node="approve", state={"history": [], "context": context or {}}))
    db.commit()


@pytest.mark.parametrize("mb,expected", [
    (4000, "green"), (1800, "green"), (1799, "amber"), (1200, "amber"), (1199, "red"), (0, "red"), (None, "amber"),
])
def test_the_light_is_green_amber_or_red_and_unreadable_is_never_a_confident_green(mb, expected):
    assert traffic_light(mb, FLOOR) == expected


def test_a_quiet_day_reads_as_fine_with_one_calm_next_step(db):
    out = card(db)
    c = out["calmCard"]
    assert c["status"] == "done" and c["next_action"] == "Start one small quest when you are ready"
    assert c["tldr"][0] == "Last 24 hours: a quiet one. That is fine." and out["light"] == "green"
    assert "Fleet: green (3.9 GB free)" in c["tldr"]


def test_yesterdays_wins_are_counted_for_the_human_only(db):
    win(db, "aaaaaaaa-1", 20)
    win(db, "bbbbbbbb-2", 10)
    win(db, "cccccccc-3", 20, user_id=2)  # someone else's
    win(db, "dddddddd-4", 20, hours_ago=30)  # too old
    win(db, "eeeeeeee-5", 0, status="capped")  # not a win
    c = card(db)["calmCard"]
    assert c["tldr"][0] == "Last 24 hours: 2 verified runs, +30 XP"
    assert c["details"] == ["Run aaaaaaaa: +20 XP", "Run bbbbbbbb: +10 XP"]


def test_an_agent_key_sees_no_ones_xp(db):
    win(db, "aaaaaaaa-1")
    assert card(db, user_id=None)["calmCard"]["tldr"][0] == "Last 24 hours: a quiet one. That is fine."


def test_a_run_waiting_on_you_is_the_one_next_action(db):
    run_row(db, "w1", "awaiting_approval")
    c = card(db, mb=500)["calmCard"]  # even with a red light the waiting run comes first
    assert c["status"] == "waiting_on_you" and c["next_action"] == "Open the run that is waiting on you"
    assert "1 run is waiting on you" in c["tldr"]


def test_a_paused_run_says_it_is_safe_and_offers_resume(db):
    run_row(db, "p1", "awaiting_approval", {"paused": {"at": "t", "by": "bro", "snapshot": {}}})
    run_row(db, "p2", "running", {"paused": {"at": "t", "by": "bro", "snapshot": {}}})
    c = card(db)["calmCard"]
    assert c["status"] == "paused" and c["next_action"] == "Resume when you are ready"
    assert "2 runs are paused and safe" in c["tldr"] and not any("waiting on you" in t for t in c["tldr"])


def test_a_red_light_is_the_next_action_when_nothing_else_is(db):
    c = card(db, mb=300)["calmCard"]
    assert c["status"] == "blocked" and c["next_action"] == "Free some memory before starting anything"


def test_finished_runs_do_not_count_as_waiting(db):
    run_row(db, "d1", "completed")
    run_row(db, "d2", "failed")
    assert card(db)["calmCard"]["status"] == "done"


def test_the_card_obeys_the_calm_rules_and_never_shames(db):
    run_row(db, "w1", "awaiting_approval")
    run_row(db, "p1", "running", {"paused": {"at": "t", "by": "bro", "snapshot": {}}})
    win(db, "aaaaaaaa-1")
    c = card(db, mb=None)["calmCard"]
    assert 1 <= len(c["tldr"]) <= 5 and "\n" not in c["next_action"] and "*" not in c["plain_text"]
    text = c["plain_text"].lower()
    assert not any(w in text for w in ("streak", "missed", "behind", "lost", "failed", "overdue"))


# ── over the API ─────────────────────────────────────────────────────────────────────
def test_the_endpoint_returns_the_card_and_the_light_for_a_human(client, db):
    _as()
    r = client.get(f"{BASE}/morning")
    assert r.status_code == 200
    body = r.json()
    assert body["calmCard"]["status"] in ("done", "blocked") and body["light"] in ("green", "amber", "red")
    assert "generatedAt" in body and len(body["calmCard"]["tldr"]) <= 5


def test_the_endpoint_needs_authentication(client):
    app.dependency_overrides.clear()
    assert client.get(f"{BASE}/morning").status_code == 401


def test_the_endpoint_is_read_only(client):
    _as()
    for verb in ("post", "put", "delete", "patch"):
        assert getattr(client, verb)(f"{BASE}/morning").status_code in (404, 405)
