"""HyperCrew Day 1 — Baton + Calm Card contracts (spec §3.1, §6)."""

import pytest
from pydantic import ValidationError

from app.crew import Baton, CalmCard, Evidence, strip_markdown

SHA = "a" * 64


def _baton(**over):
    data = dict(
        baton_id="run123:build:1", from_role="builder", to_role="verifier",
        goal="Add a health endpoint", done_so_far=["wrote the route", "added a test"],
        next_action="Run the new test", constraints=["draft PR only"],
        evidence=[{"kind": "diff", "ref": "branch:feat/x", "sha256": SHA}],
        open_questions=["Which port?"], risk_hint="propose",
    )
    data.update(over)
    return Baton(**data)


def _card(**over):
    data = dict(status="running", tldr=["Tests are running"], next_action="Wait for results")
    data.update(over)
    return CalmCard(**data)


# ── Baton ──────────────────────────────────────────────────────────────────────
def test_baton_valid_round_trip():
    b = _baton()
    assert Baton.model_validate(b.model_dump()) == b
    assert b.risk_hint == "propose" and not b.is_mutating


def test_baton_defaults_to_read_risk():
    assert _baton(risk_hint="read").risk_hint == "read"
    data = _baton().model_dump()
    del data["risk_hint"]
    assert Baton(**data).risk_hint == "read"


def test_mutation_hint_is_flagged():
    assert _baton(risk_hint="mutation").is_mutating


def test_baton_must_pass_between_different_roles():
    with pytest.raises(ValidationError):
        _baton(from_role="builder", to_role="builder")


@pytest.mark.parametrize("field,value", [
    ("goal", "x" * 201),
    ("goal", "   "),
    ("goal", "two\nlines"),
    ("next_action", "x" * 201),
    ("next_action", ""),
    ("done_so_far", ["ok"] * 6),
    ("done_so_far", ["x" * 141]),
    ("done_so_far", ["multi\nline"]),
    ("constraints", ["c"] * 9),
    ("open_questions", ["q"] * 6),
    ("evidence", [{"kind": "log", "ref": "r", "sha256": SHA}] * 11),
])
def test_baton_hard_caps(field, value):
    with pytest.raises(ValidationError):
        _baton(**{field: value})


def test_baton_caps_are_inclusive():
    b = _baton(goal="g" * 200, next_action="n" * 200, done_so_far=["d" * 140] * 5)
    assert len(b.done_so_far) == 5


def test_baton_rejects_unknown_role_and_risk_and_extra_fields():
    with pytest.raises(ValidationError):
        _baton(to_role="wizard")
    with pytest.raises(ValidationError):
        _baton(risk_hint="yolo")
    with pytest.raises(ValidationError):
        _baton(secret_note="nope")


@pytest.mark.parametrize("bad", ["", "has space", "a/b", "x" * 129, "semi;colon"])
def test_baton_id_charset(bad):
    with pytest.raises(ValidationError):
        _baton(baton_id=bad)


@pytest.mark.parametrize("sha", ["", "A" * 64, "a" * 63, "g" * 64])
def test_evidence_requires_lowercase_sha256(sha):
    with pytest.raises(ValidationError):
        Evidence(kind="test", ref="pytest-run-1", sha256=sha)


def test_evidence_is_a_pointer_not_pasted_content():
    with pytest.raises(ValidationError):
        Evidence(kind="log", ref="line1\nline2", sha256=SHA)
    with pytest.raises(ValidationError):
        Evidence(kind="log", ref="r" * 257, sha256=SHA)
    with pytest.raises(ValidationError):
        Evidence(kind="screenshot", ref="r", sha256=SHA)


def test_baton_is_immutable():
    b = _baton()
    with pytest.raises(ValidationError):
        b.goal = "changed"


# ── Calm Card ──────────────────────────────────────────────────────────────────
def test_card_valid_and_collapsed_by_default():
    c = _card()
    assert c.details_collapsed is True and c.status == "running"


@pytest.mark.parametrize("status", ["unknown", "", "orange"])
def test_card_status_never_unknown(status):
    with pytest.raises(ValidationError):
        _card(status=status)


@pytest.mark.parametrize("status", ["running", "waiting_on_you", "paused", "blocked", "done"])
def test_card_all_real_statuses_allowed(status):
    assert _card(status=status).status == status


def test_card_tldr_between_1_and_5_lines():
    assert len(_card(tldr=["a"] * 5).tldr) == 5
    with pytest.raises(ValidationError):
        _card(tldr=[])
    with pytest.raises(ValidationError):
        _card(tldr=["a"] * 6)


def test_card_tldr_lines_are_short_and_single_line():
    with pytest.raises(ValidationError):
        _card(tldr=["x" * 121])
    with pytest.raises(ValidationError):
        _card(tldr=["one\ntwo"])


def test_card_requires_exactly_one_next_action():
    with pytest.raises(ValidationError):
        _card(next_action="")
    with pytest.raises(ValidationError):
        _card(next_action="Do A\nDo B")
    with pytest.raises(ValidationError):
        _card(next_action="- Do A")
    with pytest.raises(ValidationError):
        _card(next_action="1. Do A")
    with pytest.raises(ValidationError):
        CalmCard(status="running", tldr=["x"])  # missing
    with pytest.raises(ValidationError):
        _card(next_action=["Do A", "Do B"])  # a list is not one action


def test_card_plain_text_has_no_markdown():
    c = _card(tldr=["**Bold** win", "See [the PR](http://x.y/1)", "`code` ran"],
              next_action="Review the **diff**")
    text = c.plain_text
    assert text == "Bold win\nSee the PR\ncode ran\nNext: Review the diff"
    for ch in "*_`#>[]()":
        assert ch not in text


def test_strip_markdown_cases():
    assert strip_markdown("- item") == "item"
    assert strip_markdown("1. item") == "item"
    assert strip_markdown("# Title") == "Title"
    assert strip_markdown("![alt](http://i/p.png)") == "alt"
    assert strip_markdown("a   b") == "a b"
    assert strip_markdown("") == ""


def test_plain_text_is_in_serialised_output():
    assert "plain_text" in _card().model_dump()


def test_card_is_immutable_and_rejects_extras():
    c = _card()
    with pytest.raises(ValidationError):
        c.status = "done"
    with pytest.raises(ValidationError):
        _card(shout="LOUD")


def test_card_from_baton_uses_last_five_done_and_one_action():
    done = [f"step {i}" for i in range(5)]
    b = _baton(done_so_far=done, next_action="Run the new test")
    c = CalmCard.from_baton(b, status="waiting_on_you")
    assert c.tldr == done and c.next_action == "Run the new test"
    assert c.status == "waiting_on_you"
    assert "Open question: Which port?" in c.details
    assert "Constraint: draft PR only" in c.details


def test_card_from_baton_falls_back_to_goal_when_nothing_done():
    c = CalmCard.from_baton(_baton(done_so_far=[]))
    assert c.tldr == ["Add a health endpoint"]


def test_card_from_baton_truncates_long_fields_instead_of_failing():
    c = CalmCard.from_baton(_baton(goal="g" * 200, done_so_far=[], next_action="n" * 200))
    assert len(c.tldr[0]) <= 120 and len(c.next_action) <= 120
