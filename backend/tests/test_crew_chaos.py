"""HyperCrew Day 10 — chaos. Break things on purpose and prove the crew stops safely, never pays, never publishes.

Sandbox proof (real runner, real DB rows, real recovery code; faked: the orchestrator hop and GitHub). The live
Docker proof is ``scripts/prove-crew.py``. Scenarios: Safety Shepherd down (fail closed) · a specialist dies
mid-run · duplicate and concurrent starts · cancel in the middle of a dispatch · core restart at the handover
gate and with a decision made while core was down · the kill-switch · a burst of runs against the 3-slot cap.
"""

import asyncio
import threading
import time

import httpx
import pytest

import app.broski_operator.recovery as recovery_mod
from app.crew import dispatch as crew_dispatch
from app.crew import github_pr
from app.crew.agui import history_to_events
from app.crew.cards import calm_card_for_run
from app.crew.evidence import sha256_hex
from app.models.broski import BROskiWallet, QuestSettlement
from app.models.hyperflow import HyperFlowRun
from app.models.models import User
from tests.test_crew_operator_api import GOAL, KEY, _as, _drive, _fake_dispatch
from tests.test_crew_restart_proof import answer_handover, restart_core, start, wait_for

BASE = "/api/v1/operator"
OK_BUILD = "```diff\n+def health():\n+    return {'ok': True}\n```\nAdds a health route."


@pytest.fixture(autouse=True)
def no_github_and_no_kill(monkeypatch):
    """Nothing here may ever reach GitHub, and no stray kill file may leak in from the environment."""
    for name in ("CREW_GITHUB_TOKEN", "CREW_GITHUB_TOKEN_FILE", "CREW_KILL_FILE"):
        monkeypatch.delenv(name, raising=False)


class Recorder:
    def __init__(self):
        self.proposals = []

    async def __call__(self, proposal, **_kw):
        self.proposals.append(proposal)
        return {"status": "not_configured", "detail": "no token"}


def completed(runner, node):
    return [e for e in runner._history if e["node"] == node and e["status"] == "completed"]


def nothing_after_the_stop(runner, *nodes):
    return all(not completed(runner, n) for n in nodes)


# ── 1. Safety Shepherd down: fail CLOSED ─────────────────────────────────────────────
@pytest.mark.parametrize("mode", ["monitor", "enforce"])
def test_shepherd_down_blocks_the_first_step_that_would_reach_an_agent(monkeypatch, ledger_db, slot_gate, mode):
    calls, rec = [], Recorder()
    monkeypatch.setattr(github_pr, "open_draft_pr", rec)
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, shepherd=mode,
                           dispatch=_fake_dispatch(calls=calls))
    assert final["status"].value == "failed" and "unreachable" in final["error"] and "fail closed" in final["error"]
    assert calls == []  # no agent was ever asked
    assert nothing_after_the_stop(runner, "build", "verify", "guard", "settle", "scribe", "publish")
    assert [e["status"] for e in runner._history if e["node"] == "build"][-2:] == ["safety_unreachable", "failed"]
    assert rec.proposals == [] and slot_gate.active == 0


def test_the_stop_is_explained_in_plain_words_and_mapped_to_the_event_stream(monkeypatch, ledger_db, slot_gate):
    runner, _ = _drive(monkeypatch, {"goal": GOAL}, approve=True, shepherd="monitor")
    events = [e["event"] for e in history_to_events("e2e-crew", runner._history)]
    decision = [e["value"] for e in events if e.get("name") == "hypercode.safety.decision"]
    assert decision and decision[-1]["decision"] == "UNREACHABLE" and "could not be reached" in decision[-1]["reason"]
    card = calm_card_for_run(run_id="e2e-crew", run_status="failed", history=runner._history,
                             current_node="build", error="safety shepherd unreachable: blocked (fail closed)",
                             at_gate=False)
    assert card.status == "blocked" and any("Stopped" in t for t in card.tldr)


def test_a_shepherd_that_answers_allow_lets_the_crew_carry_on(monkeypatch, ledger_db, slot_gate):
    import app.agents.hyperflow_runner as runner_mod

    async def allow(self, req):
        return {"decision": "ALLOW", "reason": "fine"}

    monkeypatch.setattr(runner_mod.HyperFlowRunner, "_safety_evaluate", allow)
    monkeypatch.setattr(github_pr, "open_draft_pr", Recorder())
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, shepherd="monitor")
    assert final["status"].value == "completed", final.get("error")


def test_a_shepherd_that_answers_block_stops_the_run_in_enforce_mode(monkeypatch, ledger_db, slot_gate):
    import app.agents.hyperflow_runner as runner_mod

    async def block(self, req):
        return {"decision": "BLOCK", "reason": "no"}

    monkeypatch.setattr(runner_mod.HyperFlowRunner, "_safety_evaluate", block)
    calls = []
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, shepherd="enforce",
                           dispatch=_fake_dispatch(calls=calls))
    assert final["status"].value == "failed" and "safety blocked" in final["error"] and calls == []


# ── 2. A specialist dies mid-run ─────────────────────────────────────────────────────
def test_the_verifier_dying_after_a_good_build_ends_the_run_with_no_guard_no_xp_no_pr(monkeypatch, ledger_db, slot_gate):
    seen, rec = [], Recorder()
    monkeypatch.setattr(github_pr, "open_draft_pr", rec)
    good = _fake_dispatch(calls=seen)

    async def verifier_dies(**kw):
        if kw["stage"] == "verify":
            seen.append(kw)
            raise crew_dispatch.DispatchError("qa-engineer unreachable (ConnectError)")
        return await good(**kw)

    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, dispatch=verifier_dies)
    assert final["status"].value == "failed" and "unreachable" in final["error"]
    assert completed(runner, "build") and nothing_after_the_stop(runner, "verify", "guard", "settle", "scribe", "publish")
    assert rec.proposals == [] and slot_gate.active == 0


@pytest.mark.parametrize("response", [
    lambda: httpx.Response(500, text="oops"),
    lambda: httpx.Response(200, text="<html>not json</html>"),
    lambda: httpx.Response(200, json={"status": "completed", "mocked": True, "results": {"coder-agent": {"result": "x"}}}),
    lambda: httpx.Response(200, json={"status": "completed", "results": {"coder-agent": {"status": "error", "result": "x"}}}),
    lambda: httpx.Response(200, json={"status": "completed", "results": {"coder-agent": {"result": "   "}}}),
    lambda: httpx.Response(200, json={"status": "completed"}),
    lambda: httpx.Response(200, json={"status": "completed", "results": {"someone-else": {"result": "x"}}}),
])
def test_an_orchestrator_that_answers_with_junk_fails_the_run_never_a_green(monkeypatch, ledger_db, slot_gate, response):
    """The REAL strict dispatch code talks to a misbehaving orchestrator (mock HTTP), through the whole flow."""
    real = crew_dispatch.dispatch_to_agent
    transport = httpx.MockTransport(lambda request: response())

    async def via_bad_orchestrator(**kw):
        return await real(client_factory=lambda **k: httpx.AsyncClient(transport=transport, **k), **kw)

    rec = Recorder()
    monkeypatch.setattr(github_pr, "open_draft_pr", rec)
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, dispatch=via_bad_orchestrator)
    assert final["status"].value == "failed"
    assert nothing_after_the_stop(runner, "build", "verify", "guard", "settle", "scribe", "publish")
    assert rec.proposals == [] and slot_gate.active == 0


# ── 3. Duplicate and concurrent starts ───────────────────────────────────────────────
def test_eight_simultaneous_starts_with_one_key_make_exactly_one_run(client, db, monkeypatch):
    from unittest.mock import AsyncMock

    from app.api.v1.endpoints import operator_tasks

    started = AsyncMock(return_value=None)
    monkeypatch.setattr(operator_tasks, "start_flow_run", started)
    _as()
    results, gate = [], threading.Barrier(8)

    def go():
        gate.wait()
        r = client.post(f"{BASE}/tasks", json={"tool": "hypercode.crew", "arguments": {"goal": GOAL}, "idempotency_key": KEY})
        results.append((r.status_code, r.json().get("taskId")))

    threads = [threading.Thread(target=go) for _ in range(8)]
    [t.start() for t in threads]
    [t.join(30) for t in threads]
    assert len(results) == 8 and {code for code, _ in results} == {200}
    assert len({tid for _, tid in results}) == 1  # everyone got the same task
    db.expire_all()
    assert db.query(HyperFlowRun).count() == 1 and started.await_count == 1


def test_the_same_key_with_different_arguments_is_refused_not_silently_merged(client, db, monkeypatch):
    from unittest.mock import AsyncMock

    from app.api.v1.endpoints import operator_tasks

    monkeypatch.setattr(operator_tasks, "start_flow_run", AsyncMock(return_value=None))
    _as()
    first = client.post(f"{BASE}/tasks", json={"tool": "hypercode.crew", "arguments": {"goal": GOAL}, "idempotency_key": KEY})
    other = client.post(f"{BASE}/tasks", json={"tool": "hypercode.crew", "arguments": {"goal": "something else"}, "idempotency_key": KEY})
    assert first.status_code == 200 and other.status_code == 409


# ── 4. Cancel in the middle of a dispatch ────────────────────────────────────────────
def test_cancelling_during_a_dispatch_stops_the_run_and_hands_the_slot_back(client, db, real_runner, slot_gate, monkeypatch):
    entered, calls, cancelled_in_flight = threading.Event(), [], []

    async def slow(**kw):
        calls.append(kw["stage"])
        entered.set()
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            cancelled_in_flight.append(True)
            raise
        return {}

    monkeypatch.setattr(crew_dispatch, "dispatch_to_agent", slow)
    _as()
    task_id = start(client)["taskId"]
    parked = wait_for(client, task_id, "input_required", "approve")
    h = parked["inputRequests"]["approval"]["plan_hash"]
    assert client.post(f"{BASE}/tasks/{task_id}/input", json={"decision": "approve", "plan_hash": h}).status_code == 200
    assert entered.wait(15), "the builder never started"
    assert slot_gate.active == 1  # a slot is held while the agent works

    r = client.post(f"{BASE}/tasks/{task_id}/cancel", json={"reason": "chaos"})
    assert r.status_code == 200
    body = wait_for(client, task_id, "cancelled")
    assert body["status"] == "cancelled"
    assert calls == ["build"] and cancelled_in_flight == [True]  # the in-flight call was cancelled, verify never began
    deadline = time.time() + 5
    while slot_gate.active and time.time() < deadline:
        time.sleep(0.05)
    assert slot_gate.active == 0
    assert client.post(f"{BASE}/tasks/{task_id}/input", json={"decision": "approve", "plan_hash": h}).status_code == 409


# ── 5. Core restarts at the handover gate / a decision is made while core is down ────
@pytest.fixture
def human(db):
    u = User(email="bro", hashed_password="x", is_active=True, is_superuser=True)  # `_as()` signs in as "bro"
    db.add(u)
    db.commit()
    from app.services.broski_service import seed_achievements

    seed_achievements(db)
    return u.id  # an id, not the object: other sessions commit while the run goes on


def reach_handover_gate(client, task_id):
    parked = wait_for(client, task_id, "input_required", "approve")
    h = parked["inputRequests"]["approval"]["plan_hash"]
    assert client.post(f"{BASE}/tasks/{task_id}/input", json={"decision": "approve", "plan_hash": h}).status_code == 200
    return wait_for(client, task_id, "input_required", "approve_scribe")


def test_restart_at_the_handover_gate_then_approve_publishes_once_and_pays_once(client, db, human, real_runner, slot_gate, monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(github_pr, "open_draft_pr", rec)
    _as()
    task_id = start(client)["taskId"]
    before = reach_handover_gate(client, task_id)
    draft_hash = before["inputRequests"]["approval"]["plan_hash"]
    xp_at_gate = db.query(BROskiWallet).filter_by(user_id=human).one().xp

    restart_core(client, task_id)
    assert client.portal.call(recovery_mod.recover_runs)["resume"] == 1
    again = wait_for(client, task_id, "input_required", "approve_scribe")
    assert again["inputRequests"]["approval"]["plan_hash"] == draft_hash  # the same draft, not a new one
    names = [e["event"].get("name") for e in history_to_events(task_id, _history(db, task_id)) if e["event"]["type"] == "CUSTOM"]
    assert names.count("hypercode.approval.required") == 2 and names.count("hypercode.handover.drafted") == 1  # plan gate + one handover gate

    assert client.post(f"{BASE}/tasks/{task_id}/input", json={"decision": "approve", "plan_hash": draft_hash}).status_code == 200
    assert wait_for(client, task_id, "completed")["result"]["success"] is True
    assert len(rec.proposals) == 1
    db.expire_all()
    assert db.query(QuestSettlement).filter_by(run_id=task_id, quest_id="crew_run").count() == 1
    assert db.query(BROskiWallet).filter_by(user_id=human).one().xp >= xp_at_gate  # never less, never a second 20


def test_a_decision_made_while_core_is_down_is_honoured_after_recovery_and_publishes_once(client, db, human, real_runner, slot_gate, monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(github_pr, "open_draft_pr", rec)
    _as()
    task_id = start(client)["taskId"]
    gate = reach_handover_gate(client, task_id)
    restart_core(client, task_id)  # core is "down": no runner owns the run
    r = client.post(f"{BASE}/tasks/{task_id}/input",
                    json={"decision": "approve", "plan_hash": gate["inputRequests"]["approval"]["plan_hash"]})
    assert r.status_code == 200  # the decision is stored with the run
    assert client.portal.call(recovery_mod.recover_runs)["resume"] == 1
    assert wait_for(client, task_id, "completed")["result"]["success"] is True
    assert len(rec.proposals) == 1


def test_replaying_the_whole_settle_and_publish_tail_pays_and_publishes_at_most_once(client, db, human, real_runner, slot_gate, monkeypatch):
    """A crash can replay the tail of a run. Settlement is keyed by run_id:quest, so replays add nothing."""
    from app.crew import tools as crew_tools

    rec = Recorder()
    monkeypatch.setattr(github_pr, "open_draft_pr", rec)
    _as()
    task_id = start(client)["taskId"]
    reach_handover_gate(client, task_id)
    hist = _history(db, task_id)
    xp = db.query(BROskiWallet).filter_by(user_id=human).one().xp
    for _ in range(3):
        out = asyncio.run(crew_tools.crew_settle({}, {"run_id": task_id, "history": hist}))
        assert out["status"] == "awarded" and out["already_settled"] is True
    db.expire_all()
    assert db.query(BROskiWallet).filter_by(user_id=human).one().xp == xp
    assert db.query(QuestSettlement).filter_by(run_id=task_id).count() == 1


def _history(db, task_id):
    db.expire_all()
    return list(db.get(HyperFlowRun, task_id).state["history"])


# ── 6. The kill-switch ───────────────────────────────────────────────────────────────
def test_kill_switch_states(tmp_path, monkeypatch):
    from app.crew.killswitch import kill_reason

    assert kill_reason() is None  # not configured: off
    sentinel = tmp_path / "KILL"
    monkeypatch.setenv("CREW_KILL_FILE", str(sentinel))
    assert kill_reason() is None  # configured, healthy directory, no file
    sentinel.write_text("stop")
    assert kill_reason() == "kill switch engaged"
    monkeypatch.setenv("CREW_KILL_FILE", str(tmp_path / "gone" / "KILL"))
    assert "unknowable" in kill_reason()  # the directory vanished: an unknowable state counts as killed
    monkeypatch.setenv("CREW_KILL_FILE", "")
    assert kill_reason() is None


def test_an_engaged_kill_switch_stops_a_run_before_it_does_anything(monkeypatch, ledger_db, slot_gate, tmp_path):
    sentinel = tmp_path / "KILL"
    sentinel.write_text("stop")
    monkeypatch.setenv("CREW_KILL_FILE", str(sentinel))
    calls = []
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, dispatch=_fake_dispatch(calls=calls))
    assert final["status"].value == "failed" and "kill switch engaged" in final["error"]
    assert calls == [] and not completed(runner, "plan") and not completed(runner, "seal")


def test_a_kill_switch_pulled_during_the_build_stops_the_run_before_the_next_step(monkeypatch, ledger_db, slot_gate, tmp_path):
    sentinel = tmp_path / "KILL"
    monkeypatch.setenv("CREW_KILL_FILE", str(sentinel))  # healthy and absent at first
    seen, rec = [], Recorder()
    monkeypatch.setattr(github_pr, "open_draft_pr", rec)
    good = _fake_dispatch(calls=seen)

    async def pulls_the_switch(**kw):
        out = await good(**kw)
        if kw["stage"] == "build":
            sentinel.write_text("stop")  # the operator trips the kill-switch while the builder is working
        return out

    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, dispatch=pulls_the_switch)
    assert final["status"].value == "failed" and "kill switch engaged" in final["error"]
    assert [c["stage"] for c in seen] == ["build"]  # the verifier was never asked
    assert nothing_after_the_stop(runner, "verify", "guard", "settle", "scribe", "publish")
    assert rec.proposals == [] and slot_gate.active == 0


def test_a_kill_switch_pulled_while_waiting_at_the_gate_stops_the_run_after_approval(client, db, real_runner, slot_gate, tmp_path, monkeypatch):
    sentinel = tmp_path / "KILL"
    monkeypatch.setenv("CREW_KILL_FILE", str(sentinel))
    _as()
    task_id = start(client)["taskId"]
    parked = wait_for(client, task_id, "input_required", "approve")
    sentinel.write_text("stop")
    h = parked["inputRequests"]["approval"]["plan_hash"]
    assert client.post(f"{BASE}/tasks/{task_id}/input", json={"decision": "approve", "plan_hash": h}).status_code == 200
    body = wait_for(client, task_id, "failed")
    assert "kill switch engaged" in body["error"]
    assert not [e for e in _history(db, task_id) if e["node"] in ("build", "verify", "guard") and e["status"] == "completed"]


def test_a_killed_run_reads_as_blocked_with_the_reason_in_the_card(monkeypatch, ledger_db, slot_gate, tmp_path):
    sentinel = tmp_path / "KILL"
    sentinel.write_text("stop")
    monkeypatch.setenv("CREW_KILL_FILE", str(sentinel))
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True)
    card = calm_card_for_run(run_id="x", run_status="failed", history=runner._history, current_node=None,
                             error=final["error"], at_gate=False)
    assert card.status == "blocked" and card.next_action == "Read why it stopped"
    assert any("kill switch engaged" in t for t in card.tldr)


# ── 7. A burst of runs against the 3-slot cap ────────────────────────────────────────
def test_six_runs_at_once_never_wake_more_than_three_agents_and_all_finish_cleanly(client, db, human, real_runner, slot_gate, monkeypatch):
    lock, live, peak, total = threading.Lock(), [0], [0], [0]

    async def tracked(**kw):
        with lock:
            live[0] += 1
            peak[0] = max(peak[0], live[0])
            total[0] += 1
        try:
            await asyncio.sleep(0.15)
            text = OK_BUILD if kw["stage"] == "build" else "Fine.\nVERDICT: PASS"
            return {"ok": True, "agent": kw["agent"], "role": kw["role"], "stage": kw["stage"], "status": "completed",
                    "summary": text, "summary_hash": sha256_hex(text), "truncated": False}
        finally:
            with lock:
                live[0] -= 1

    monkeypatch.setattr(crew_dispatch, "dispatch_to_agent", tracked)
    monkeypatch.setattr(github_pr, "open_draft_pr", Recorder())
    _as()
    ids = [start(client, key=f"burst-{i}-aaaaaaaa", goal=f"add health endpoint number {i}")["taskId"] for i in range(6)]
    assert len(set(ids)) == 6
    done, deadline = set(), time.time() + 90
    while len(done) < 6 and time.time() < deadline:
        for tid in ids:
            if tid in done:
                continue
            body = client.get(f"{BASE}/tasks/{tid}").json()
            if body["status"] == "completed":
                done.add(tid)
            elif body["status"] == "failed":
                raise AssertionError(f"run {tid} failed: {body.get('error')}")
            elif body["status"] == "input_required":
                a = body["inputRequests"]["approval"]
                payload = {"decision": "approve", "plan_hash": a["plan_hash"]} if a["node"] == "approve" else {"decision": "reject"}
                client.post(f"{BASE}/tasks/{tid}/input", json=payload)
        time.sleep(0.1)
    assert len(done) == 6, f"only {len(done)} of 6 finished"
    assert total[0] == 12 and 2 <= peak[0] <= 3 and slot_gate.active == 0  # real overlap happened, and never past the cap
    db.expire_all()
    assert db.query(QuestSettlement).filter_by(quest_id="crew_run").count() == 6  # one each, never doubled
    assert db.query(BROskiWallet).filter_by(user_id=human).one().xp <= 100 + 6 * 10  # the daily ceiling held (plus one-off badges)
