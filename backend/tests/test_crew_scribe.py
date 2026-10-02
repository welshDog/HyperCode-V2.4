"""HyperCrew Day 9 — the Scribe: a proposal, a human gate bound to its hash, a docs-only DRAFT PR, never a direct write."""

import asyncio
import json
import re
from datetime import date
from pathlib import Path

import httpx
import pytest

from app.crew import github_pr, scribe, tools as crew_tools
from app.crew.evidence import sha256_hex
from app.models.broski import BROskiUserAchievement, QuestSettlement
from app.models.models import User
from app.services.broski_service import seed_achievements
from tests.test_crew_operator_api import GOAL, _drive
from tests.test_crew_quests import HASH, PLAN, RUN, history

DAY = date(2026, 10, 2)
SECRET = "sk-ant-api03-" + "A" * 40
REPO_ROOT = Path(__file__).resolve().parents[2]


def draft(hist=None):
    return scribe.build_proposal(RUN, history() if hist is None else hist, DAY)


def with_scribe(proposal, *, approved=True, sent=None, by="bro@example.com"):
    """A history where the Scribe drafted ``proposal`` and a human answered the gate."""
    return history(extra=[
        {"node": "scribe", "status": "completed", "result": {"data": {"proposal": proposal}}},
        {"node": "approve_scribe", "type": "human_approval_gate", "status": "completed",
         "result": {"approved": approved, "by": by, "plan_hash": sent or proposal["plan_hash"]}},
    ])


# ── the draft itself ─────────────────────────────────────────────────────────────────
def test_the_draft_matches_the_repos_handover_format():
    p = draft()
    handover = next(f for f in p["files"] if f["path"].startswith(scribe.HANDOVER_PREFIX))
    text = handover["content"]
    assert re.match(r"^# 📋 NEXT_SESSION_HANDOVER — 2026-10-02 \(HyperCrew run [0-9a-f]{8}\)\n", text)
    assert re.fullmatch(r"docs/NEXT_SESSION_HANDOVER_2026-10-02_crew-[0-9a-f]{8}\.md", handover["path"])
    real = REPO_ROOT / "docs" / "NEXT_SESSION_HANDOVER_2026-09-18.md"
    if real.exists():  # the headings a human handover uses, so a reader finds the same things in the same place
        real_text = real.read_text()
        for heading in ("## 🟢 LIVE STATE RIGHT NOW", "## ✅ PROOF"):
            assert heading in real_text and heading in text
    assert text.count("## ▶️ NEXT TASK") == 1 and "## ⚠️ NOT DONE / NOT PROVEN" in text
    next_task = text.split("## ▶️ NEXT TASK")[1].strip()
    assert len([ln for ln in next_task.splitlines() if ln.strip()]) == 1  # ONE next task, one sentence


def test_it_says_plainly_that_nothing_was_applied():
    text = draft()["files"][0]["content"]
    assert "Nothing was applied" in text.replace("**", "") or "Nothing here was written" in text
    assert "**Nothing was applied, built, deployed or restarted.**" in text


def test_the_whats_done_entry_is_a_new_proposal_file_never_an_edit_of_whats_done():
    paths = [f["path"] for f in draft()["files"]]
    assert all("WHATS_DONE.md" not in p for p in paths)
    assert any(p.startswith(scribe.PROPOSALS_PREFIX) for p in paths)


def test_the_draft_is_deterministic_and_hash_pinned():
    a, b = draft(), draft()
    assert a == b and a["plan_hash"] == scribe.proposal_hash(a) and a["plan_hash"].startswith("sha256:")
    changed = json.loads(json.dumps(a))
    changed["files"][0]["content"] += "x"
    assert scribe.proposal_hash(changed) != a["plan_hash"]
    assert all(f["sha256"] == sha256_hex(f["content"]) for f in a["files"])


def test_secrets_in_agent_text_never_reach_the_draft():
    hist = history()
    hist[1]["result"]["data"]["summary"] = f"uses key {SECRET} here"
    p = draft(hist)
    assert SECRET not in json.dumps(p)


def test_pipes_in_a_check_detail_cannot_break_the_table():
    hist = history()
    hist[3]["result"]["data"]["checks"] = [{"name": "x", "passed": True, "detail": "a | b"}]
    text = draft(hist)["files"][0]["content"]
    assert "| x | PASS | a / b |" in text


@pytest.mark.parametrize("hist", [
    lambda: history(verdict="BLOCK"), lambda: history(sealed=False), lambda: history(tamper=True), lambda: [],
])
def test_a_run_the_guardian_did_not_allow_gets_no_write_up(hist):
    with pytest.raises(scribe.ScribeError):
        draft(hist())


@pytest.mark.parametrize("path,ok", [
    ("docs/NEXT_SESSION_HANDOVER_2026-10-02_crew-abcd1234.md", True),
    ("docs/crew-proposals/x.md", True),
    ("WHATS_DONE.md", False), ("CLAUDE.md", False), ("docs/STATUS.md", False),
    ("docs/crew-proposals/../../CLAUDE.md", False), ("/docs/crew-proposals/x.md", False),
    ("docs/crew-proposals/x.py", False), ("backend/app/main.py", False), (".github/workflows/x.md", False),
])
def test_only_new_docs_markdown_paths_are_allowed(path, ok):
    assert scribe.path_allowed(path) is ok


# ── the human gate is bound to the draft ─────────────────────────────────────────────
def test_approval_for_exactly_this_draft_is_accepted():
    p = draft()
    proposal, approver = scribe.approved_proposal(with_scribe(p))
    assert proposal == p and approver == "bro@example.com"


@pytest.mark.parametrize("make,why", [
    (lambda p: with_scribe(p, approved=False), "not approved"),
    (lambda p: with_scribe(p, sent="sha256:" + "1" * 64), "not for this exact draft"),
    (lambda p: with_scribe(p, by=""), "no recorded approver"),
])
def test_a_missing_declined_or_mismatched_approval_publishes_nothing(make, why):
    with pytest.raises(scribe.ScribeError, match=why):
        scribe.approved_proposal(make(draft()))


def test_no_draft_means_nothing_to_publish():
    with pytest.raises(scribe.ScribeError):
        scribe.approved_proposal(history())


def test_a_draft_edited_after_it_was_shown_is_refused():
    p = draft()
    h = with_scribe(p)
    h[-2]["result"]["data"]["proposal"]["files"][0]["content"] += "\nsneaky"
    with pytest.raises(scribe.ScribeError):
        scribe.approved_proposal(h)


def test_a_path_smuggled_in_with_a_consistent_hash_is_still_refused():
    p = json.loads(json.dumps(draft()))
    evil = "CLAUDE.md"
    p["files"][0]["path"] = evil
    p["plan_hash"] = scribe.proposal_hash(p)  # attacker recomputes the hash too
    with pytest.raises(scribe.ScribeError, match="not allowed"):
        scribe.approved_proposal(with_scribe(p))


# ── the PR opener ────────────────────────────────────────────────────────────────────
TOKEN = "ghp_" + "Z" * 36


class Github:
    """A tiny fake GitHub that records every request."""

    def __init__(self, *, existing_branch=False, existing_pr=None, base_status=200, fail_put=False):
        self.calls, self.existing_branch, self.existing_pr = [], existing_branch, existing_pr
        self.base_status, self.fail_put = base_status, fail_put

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        self.calls.append((request.method, request.url.path, body))
        path, method = request.url.path, request.method
        if method == "GET" and "/git/ref/heads/" in path:
            return httpx.Response(self.base_status, json={"object": {"sha": "base-sha"}})
        if method == "POST" and path.endswith("/git/refs"):
            return httpx.Response(422 if self.existing_branch else 201, json={})
        if method == "PUT" and "/contents/" in path:
            return httpx.Response(500 if self.fail_put else 201, json={})
        if method == "GET" and path.endswith("/pulls"):
            return httpx.Response(200, json=[{"html_url": self.existing_pr}] if self.existing_pr else [])
        if method == "POST" and path.endswith("/pulls"):
            return httpx.Response(201, json={"html_url": "https://github.com/o/r/pull/9"})
        return httpx.Response(404, json={})


@pytest.fixture
def token(monkeypatch):
    monkeypatch.setenv("CREW_GITHUB_TOKEN", TOKEN)
    monkeypatch.delenv("CREW_GITHUB_TOKEN_FILE", raising=False)


def publish(gh, proposal=None):
    return asyncio.run(github_pr.open_draft_pr(proposal or draft(), transport=httpx.MockTransport(gh)))


def test_with_no_token_nothing_is_sent_and_it_says_so(monkeypatch):
    monkeypatch.delenv("CREW_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("CREW_GITHUB_TOKEN_FILE", raising=False)
    gh = Github()
    out = publish(gh)
    assert out["status"] == "not_configured" and gh.calls == []


def test_it_opens_a_draft_pr_from_a_new_branch_with_docs_files_only(token):
    gh = Github()
    out = publish(gh)
    assert out == {"status": "opened", "url": "https://github.com/o/r/pull/9"}
    pr = [b for m, p, b in gh.calls if m == "POST" and p.endswith("/pulls")][0]
    assert pr["draft"] is True and pr["base"] == "main" and pr["head"].startswith("crew/handover-2026-10-02-")
    ref = [b for m, p, b in gh.calls if m == "POST" and p.endswith("/git/refs")][0]
    assert ref["ref"] == "refs/heads/" + pr["head"] and ref["sha"] == "base-sha"
    puts = [(p, b) for m, p, b in gh.calls if m == "PUT"]
    assert len(puts) == 2 and all(b["branch"] == pr["head"] and "sha" not in b for _, b in puts)  # create-only
    assert all(re.search(r"/contents/docs/(NEXT_SESSION_HANDOVER_|crew-proposals/)", p) for p, _ in puts)


def test_it_never_merges_never_touches_the_base_branch_never_edits_a_file(token):
    gh = Github()
    publish(gh)
    for method, path, body in gh.calls:
        assert "/merge" not in path and method != "DELETE" and method != "PATCH"
        if method in ("POST", "PUT"):
            assert "heads/main" not in path and (body or {}).get("branch", "crew/x").startswith("crew/") \
                or path.endswith("/pulls") or path.endswith("/git/refs")


def test_the_token_never_appears_in_the_result_even_on_failure(token):
    for gh in (Github(), Github(fail_put=True), Github(base_status=401)):
        assert TOKEN not in json.dumps(publish(gh))


def test_a_retry_after_a_partial_failure_finishes_the_job_without_a_second_pr(token):
    first = publish(Github(fail_put=True))
    assert first["status"] == "error"
    again = publish(Github(existing_branch=True, existing_pr="https://github.com/o/r/pull/9"))
    assert again == {"status": "exists", "url": "https://github.com/o/r/pull/9"}


def test_a_failed_base_lookup_is_an_error_not_a_pretend_success(token):
    out = publish(Github(base_status=404))
    assert out["status"] == "error" and "404" in out["detail"]


@pytest.mark.parametrize("mutate", [
    lambda p: p["pr"].update(draft=False),
    lambda p: p["pr"].update(branch="main"),
    lambda p: p["files"][0].update(path="CLAUDE.md"),
    lambda p: p.update(files=[]),
])
def test_the_publisher_refuses_anything_that_is_not_a_docs_only_draft_on_a_crew_branch(token, mutate):
    p = json.loads(json.dumps(draft()))
    mutate(p)
    gh = Github()
    assert publish(gh, p)["status"] == "refused" and gh.calls == []


def test_a_repo_that_is_not_owner_slash_name_is_refused(token, monkeypatch):
    monkeypatch.setenv("CREW_GITHUB_REPO", "evil.example/../x")
    gh = Github()
    assert publish(gh)["status"] == "refused" and gh.calls == []


def test_a_network_error_is_reported_without_raising(token):
    def boom(request):
        raise httpx.ConnectError("down")

    assert publish(boom)["status"] == "error"


# ── the whole flow ───────────────────────────────────────────────────────────────────
class Recorder:
    def __init__(self, outcome=None):
        self.proposals, self.outcome = [], outcome or {"status": "not_configured", "detail": "no token"}

    async def __call__(self, proposal, **_kw):
        self.proposals.append(proposal)
        return self.outcome


def entries(runner, node):
    return [e for e in runner._history if e["node"] == node and e["status"] == "completed"]


def test_e2e_an_approved_draft_is_published_exactly_once(monkeypatch, ledger_db, slot_gate):
    rec = Recorder({"status": "opened", "url": "https://github.com/o/r/pull/9"})
    monkeypatch.setattr(github_pr, "open_draft_pr", rec)
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, scribe="approve")
    assert final["status"].value == "completed", final.get("error")
    assert len(rec.proposals) == 1
    data = entries(runner, "publish")[0]["result"]["data"]
    assert data["pr_opened"] is True and data["performed"] is True and data["pr"]["url"].endswith("/pull/9")
    row = ledger_db().query(crew_tools.GovernanceLedger).filter_by(action="crew_handover_published").one()
    assert row.approved_by == "bro@example.com" and row.payload["pr_url"].endswith("/pull/9")


def test_e2e_with_no_github_token_the_draft_stays_in_the_run_and_nothing_pretends_otherwise(monkeypatch, ledger_db, slot_gate):
    monkeypatch.setattr(github_pr, "open_draft_pr", Recorder())
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, scribe="approve")
    data = entries(runner, "publish")[0]["result"]["data"]
    assert final["status"].value == "completed" and data["pr_opened"] is False and data["performed"] is False


def test_e2e_skipping_the_handover_ends_the_run_cleanly_and_opens_nothing(monkeypatch, ledger_db, slot_gate):
    rec = Recorder()
    monkeypatch.setattr(github_pr, "open_draft_pr", rec)
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, scribe="skip")
    assert final["status"].value == "completed" and rec.proposals == [] and entries(runner, "publish") == []
    gate = entries(runner, "approve_scribe")[0]["result"]
    assert gate["declined"] is True and gate["approved"] is False


def test_e2e_an_approval_for_a_different_draft_fails_the_run_and_opens_nothing(monkeypatch, ledger_db, slot_gate):
    rec = Recorder()
    monkeypatch.setattr(github_pr, "open_draft_pr", rec)
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, scribe="wrong_hash")
    assert final["status"].value == "failed" and "exact draft" in final["error"] and rec.proposals == []


def test_e2e_a_blocked_run_never_reaches_the_scribe(monkeypatch, ledger_db, slot_gate):
    from tests.test_crew_operator_api import _fake_dispatch

    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, dispatch=_fake_dispatch(verify="No.\nVERDICT: FAIL"))
    assert entries(runner, "scribe") == [] and entries(runner, "publish") == []


# ── "Handover Written" and who can reach any of this ─────────────────────────────────
@pytest.fixture
def human(db):
    u = User(email="bro@example.com", hashed_password="x", is_active=True, is_superuser=True)
    db.add(u)
    db.commit()
    seed_achievements(db)
    return u


def earned(db):
    db.expire_all()
    return {a.achievement_slug for a in db.query(BROskiUserAchievement).all()}


def test_handover_written_unlocks_for_the_approver_once(db, human):
    from app.crew.quests import settle_handover

    first = settle_handover(db, RUN, history(), "bro@example.com")
    assert first.status == "awarded" and "handover_written" in earned(db) and len(first.achievements) == 1
    again = settle_handover(db, RUN, history(), "bro@example.com")
    assert again.already_settled is True and again.achievements == []
    assert db.query(QuestSettlement).filter_by(quest_id="handover_written").count() == 1


@pytest.mark.parametrize("approver,hist", [
    ("stranger@example.com", lambda: history()), ("agent:coder-agent", lambda: history()),
    ("bro@example.com", lambda: history(verdict="BLOCK")),
])
def test_handover_written_is_for_a_known_human_and_a_guard_allowed_run_only(db, human, approver, hist):
    from app.crew.quests import settle_handover

    assert settle_handover(db, RUN, hist(), approver).status == "no_award"
    assert "handover_written" not in earned(db)


def test_the_publisher_and_scribe_are_flow_nodes_only_with_a_declinable_gate():
    from app.agents.hyperflow.registry import get_flow

    flow = get_flow("hypercode-crew")
    gate = flow.node("approve_scribe")
    assert gate.type.value == "human_approval_gate" and gate.params["show_from"] == "scribe"
    assert gate.params["on_reject"] == "end"
    assert [e.dst for e in flow.edges if e.src == "approve_scribe"] == ["publish"]
    assert [e.src for e in flow.edges if e.dst == "scribe"] == ["settle"]
    assert flow.node("publish").tool == "local.crew_publish"


def test_no_route_or_mcp_tool_can_publish_or_draft():
    from app.main import app

    assert not [r.path for r in app.routes if re.search(r"publish|scribe|handover", getattr(r, "path", ""))]
    server = (REPO_ROOT / "services/hypercode-mcp-server/server.py").read_text().lower()
    assert "publish" not in server and "scribe" not in server and "open_draft_pr" not in server


def test_the_crew_tools_that_publish_fail_closed_without_a_valid_draft():
    with pytest.raises(crew_tools.CrewSealError):
        asyncio.run(crew_tools.crew_publish({}, {"run_id": RUN, "history": history()}))
    with pytest.raises(crew_tools.CrewSealError):
        asyncio.run(crew_tools.crew_scribe({}, {"run_id": RUN, "history": history(verdict="BLOCK")}))
