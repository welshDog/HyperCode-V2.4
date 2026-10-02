"""HyperCrew Day 5 — AG-UI-shaped events and the Calm Card, derived from run history."""

import pytest

from app.crew import agui
from app.crew.agui import MAX_EVENTS_PER_CALL, events_after, history_to_events, node_label
from app.crew.cards import calm_card_for_run
from app.api.v1.endpoints import operator_tasks
from app.main import app
from app.models.hyperflow import HyperFlowRun
from tests.test_crew_operator_api import GOAL, _as, _drive

BASE = "/api/v1/operator"


def types(events):
    return [e["event"]["type"] for e in events]


def names(events):
    return [e["event"].get("name") for e in events if e["event"]["type"] == "CUSTOM"]


def by_name(events, name):
    return [e["event"]["value"] for e in events if e["event"].get("name") == name]


@pytest.fixture
def full_history(monkeypatch, ledger_db, slot_gate):
    runner, _ = _drive(monkeypatch, {"goal": GOAL}, approve=True)
    return "e2e-crew", list(runner._history)


# ── mapper ─────────────────────────────────────────────────────────────────────
def test_run_always_starts_with_run_started_and_sequences_are_contiguous(full_history):
    run_id, hist = full_history
    ev = history_to_events(run_id, hist)
    assert ev[0]["seq"] == 0 and ev[0]["event"] == {"type": "RUN_STARTED", "threadId": run_id, "runId": run_id}
    assert [e["seq"] for e in ev] == list(range(len(ev)))


def test_empty_history_is_just_run_started():
    assert types(history_to_events("r", [])) == ["RUN_STARTED"]


def test_a_real_crew_run_tells_the_whole_story_in_order(full_history):
    run_id, hist = full_history
    ev = history_to_events(run_id, hist)
    story = [n for n in names(ev) if n in (
        "hypercode.plan.created", "hypercode.approval.required", "hypercode.approval.resolved",
        "hypercode.plan.sealed", "hypercode.guard.verdict")]
    assert story == ["hypercode.plan.created", "hypercode.approval.required",
                     "hypercode.approval.resolved", "hypercode.plan.sealed", "hypercode.guard.verdict"]
    steps_started = [e["event"]["stepName"] for e in ev if e["event"]["type"] == "STEP_STARTED"]
    steps_finished = [e["event"]["stepName"] for e in ev if e["event"]["type"] == "STEP_FINISHED"]
    assert steps_started[:1] == ["plan"] and "guard" in steps_finished
    assert sorted(set(steps_finished)) == sorted(steps_finished)  # each node finishes once


def test_the_approval_card_event_carries_the_hash_but_not_the_plan_body(full_history):
    run_id, hist = full_history
    approval = by_name(history_to_events(run_id, hist), "hypercode.approval.required")[0]
    assert approval["approvalId"] == f"{run_id}:approve" and approval["action"] == "approve_plan"
    assert approval["planHash"].startswith("sha256:") and "plan" not in approval and "goal" not in approval


def test_agent_dispatch_becomes_a_tool_call_triple_with_one_id(full_history):
    run_id, hist = full_history
    ev = history_to_events(run_id, hist)
    calls = [e["event"] for e in ev if e["event"]["type"].startswith("TOOL_CALL")]
    assert [c["type"] for c in calls] == ["TOOL_CALL_START", "TOOL_CALL_END", "TOOL_CALL_RESULT"] * 2
    assert calls[0]["toolCallId"] == calls[1]["toolCallId"] == calls[2]["toolCallId"] == f"{run_id}:build"
    assert calls[0]["toolCallName"] == "coder-agent" and calls[3]["toolCallName"] == "qa-engineer"
    import json

    assert json.loads(calls[2]["content"])["stage"] == "build"


def test_guard_verdict_event_reports_checks_and_bundle_hash(full_history):
    run_id, hist = full_history
    v = by_name(history_to_events(run_id, hist), "hypercode.guard.verdict")[0]
    assert v["verdict"] == "ALLOW" and v["failedChecks"] == [] and len(v["checks"]) == 6
    assert v["bundleHash"].startswith("sha256:")


def test_events_are_append_only_so_replay_is_exact(full_history):
    """The property replay depends on: more history never changes an event already sent."""
    run_id, hist = full_history
    previous = history_to_events(run_id, [])
    for k in range(1, len(hist) + 1):
        current = history_to_events(run_id, hist[:k])
        assert current[: len(previous)] == previous
        previous = current


def test_after_returns_only_what_was_missed(full_history):
    run_id, hist = full_history
    ev = history_to_events(run_id, hist)
    assert events_after(ev, -1) == ev[:MAX_EVENTS_PER_CALL]
    mid = ev[len(ev) // 2]["seq"]
    assert [e["seq"] for e in events_after(ev, mid)] == [e["seq"] for e in ev if e["seq"] > mid]
    assert events_after(ev, ev[-1]["seq"]) == [] and events_after(ev, 10**6) == []


def test_one_call_never_returns_more_than_the_cap():
    hist = [{"node": f"n{i}", "type": "tool", "status": "completed", "result": {"success": True}} for i in range(300)]
    ev = history_to_events("r", hist)
    assert len(ev) > MAX_EVENTS_PER_CALL and len(events_after(ev, -1)) == MAX_EVENTS_PER_CALL


def test_terminal_entries_map_to_run_finished_or_run_error():
    done = {"node": None, "type": "terminal", "status": "completed", "result": {}}
    failed = {"node": None, "type": "terminal", "status": "failed", "result": {"error": "boom"}}
    cancelled = {"node": None, "type": "terminal", "status": "cancelled", "result": {"error": "stop (by bro)"}}
    assert history_to_events("r", [done])[-1]["event"] == {"type": "RUN_FINISHED", "threadId": "r", "runId": "r"}
    err = history_to_events("r", [failed])[-1]["event"]
    assert err == {"type": "RUN_ERROR", "message": "boom", "code": "RUN_FAILED"}
    assert history_to_events("r", [cancelled])[-1]["event"]["code"] == "CANCELLED"


def test_run_error_messages_are_redacted_and_capped():
    failed = {"node": None, "type": "terminal", "status": "failed",
              "result": {"error": "bad key sk-abcdefghijklmnopqrstuvwxyz123456 " + "x" * 600}}
    msg = history_to_events("r", [failed])[-1]["event"]["message"]
    assert "sk-abc" not in msg and len(msg) <= 200


def test_secrets_inside_agent_output_never_reach_the_stream():
    entry = {"node": "build", "type": "agent_dispatch", "status": "completed", "result": {
        "success": True, "data": {"agent": "coder-agent", "stage": "build", "status": "completed",
                                  "summary": "token ghp_abcdefghijklmnopqrstuvwxyz0123 here", "summary_hash": "h"}}}
    blob = str(history_to_events("r", [entry]))
    assert "ghp_abc" not in blob and "[REDACTED]" in blob


def test_safety_and_failure_entries_become_custom_events():
    hist = [
        {"node": "build", "type": "agent_dispatch", "status": "safety_block", "result": {"reason": "no"}},
        {"node": "build", "type": "agent_dispatch", "status": "failed", "result": {"error": "unreachable"}},
        {"node": "plan", "type": "tool", "status": "completed",
         "result": {"success": False, "data": {"notes": ["no valid goal stored with this run"]}}},
    ]
    ev = history_to_events("r", hist)
    assert by_name(ev, "hypercode.safety.decision") == [{"node": "build", "decision": "BLOCK", "reason": "no"}]
    assert by_name(ev, "hypercode.step.failed")[0]["reason"] == "unreachable"
    assert by_name(ev, "hypercode.step.unsuccessful")[0]["reason"].startswith("no valid goal")


def test_a_gate_re_parked_after_a_restart_is_the_same_wait_not_a_new_one():
    gate = {"node": "approve", "type": "human_approval_gate", "status": "awaiting_approval",
            "result": {"prompt": "Approve?", "plan_hash": "sha256:" + "a" * 64}}
    once = history_to_events("r", [gate])
    twice = history_to_events("r", [gate, dict(gate, ts="later")])
    assert twice == once
    assert names(once).count("hypercode.approval.required") == 1


def test_a_gate_that_resolves_can_be_asked_again_later():
    gate = {"node": "approve", "type": "human_approval_gate", "status": "awaiting_approval", "result": {}}
    resolved = {"node": "approve", "type": "human_approval_gate", "status": "completed", "result": {"approved": True}}
    ev = history_to_events("r", [gate, resolved, gate])
    assert names(ev).count("hypercode.approval.required") == 2


def test_garbage_history_entries_are_ignored_not_fatal():
    ev = history_to_events("r", ["x", None, {}, {"node": None, "status": "completed"}, {"node": 5}])
    assert types(ev)[0] == "RUN_STARTED"


def test_node_labels_are_plain_words():
    assert node_label("guard") == "Guardian is checking it"
    assert node_label("zzz") == "Running zzz" and node_label(None) == "Finishing up"
    assert agui.NODE_LABELS["approve"] == "Waiting for your approval"


# ── calm card ──────────────────────────────────────────────────────────────────
def card(**kw):
    base = dict(run_id="r", run_status="running", history=[], current_node="plan", error=None, at_gate=False)
    base.update(kw)
    return calm_card_for_run(**base)


def test_card_for_a_fresh_run_says_nothing_is_needed():
    c = card()
    assert c.status == "running" and c.tldr == ["Starting up"]
    assert c.next_action.startswith("Nothing needed") and "writing the plan" in c.next_action


def test_card_waiting_at_the_plan_gate_tells_you_what_to_do(full_history):
    run_id, hist = full_history
    gate_at = next(i for i, e in enumerate(hist) if e["status"] == "awaiting_approval")
    c = card(run_status="awaiting_approval", history=hist[:gate_at], current_node="approve", at_gate=True)
    assert c.status == "waiting_on_you" and c.next_action == "Read the plan, then approve or reject it"
    assert c.tldr == ["Plan written"]


def test_card_for_a_safety_escalation_is_not_the_plan_gate():
    c = card(run_status="awaiting_approval", at_gate=False)
    assert c.status == "waiting_on_you" and "safety" in c.next_action.lower()


def test_card_for_an_allowed_crew_run_points_at_the_evidence(full_history):
    run_id, hist = full_history
    c = card(run_status="completed", history=hist, current_node=None)
    assert c.status == "done" and c.next_action == "Review the evidence and the proposed change"
    assert c.tldr[-1] == "Guardian allowed it" and len(c.tldr) <= 5


def test_card_for_a_blocked_crew_run_names_the_failed_checks():
    hist = [{"node": "guard", "type": "tool", "status": "completed", "result": {
        "success": False, "data": {"verdict": "BLOCK", "failed_checks": ["verifier_verdict", "build_clean"]}}}]
    c = card(run_status="completed", history=hist)
    assert c.status == "blocked" and c.next_action == "Read why the guard blocked it"
    assert c.tldr[-1] == "Guardian blocked it: verifier_verdict, build_clean"


def test_card_for_a_failed_run_shows_a_redacted_reason():
    c = card(run_status="failed", error="orchestrator unreachable sk-abcdefghijklmnopqrstuvwxyz123456")
    assert c.status == "blocked" and c.next_action == "Read why it stopped"
    assert "sk-abc" not in c.plain_text and c.tldr[-1].startswith("Stopped:")


def test_card_for_a_cancelled_run_is_paused():
    c = card(run_status="cancelled")
    assert c.status == "paused" and c.tldr[-1] == "Cancelled"


def test_card_for_a_non_crew_completed_run_still_has_one_next_action():
    c = card(run_status="completed", history=[{"node": "inspect", "status": "completed", "result": {}}])
    assert c.status == "done" and c.next_action == "Check the result" and c.tldr == ["Finished inspect"]


def test_card_keeps_only_the_last_five_lines_and_every_line_is_short():
    hist = [{"node": f"node_with_a_very_long_name_{i}" * 6, "status": "completed", "result": {}} for i in range(9)]
    c = card(run_status="running", history=hist)
    assert len(c.tldr) == 5 and all(len(line) <= 120 for line in c.tldr)
    assert "\n" not in c.next_action and "\n" in c.plain_text


def test_card_plain_text_has_no_markdown(full_history):
    run_id, hist = full_history
    text = card(run_status="completed", history=hist).plain_text
    assert all(ch not in text for ch in "*_`#>")


# ── endpoint ───────────────────────────────────────────────────────────────────
def _seed(db, history, status="running", node="build", error=None, run_id="ev-run"):
    state = {"history": history}
    if error:
        state["error"] = error
    db.add(HyperFlowRun(id=run_id, flow_name="hypercode-crew", flow_version=2, status=status,
                        current_node=node, state=state))
    db.commit()


def test_events_endpoint_returns_events_card_and_poll_hint(client, db, full_history):
    _as()
    _, hist = full_history
    _seed(db, hist)
    body = client.get(f"{BASE}/tasks/ev-run/events").json()
    assert body["taskId"] == "ev-run" and body["status"] == "working" and body["done"] is False
    assert body["events"][0]["event"]["type"] == "RUN_STARTED" and body["nextAfter"] == body["events"][-1]["seq"]
    assert body["calmCard"]["status"] == "running" and body["calmCard"]["plain_text"]
    assert body["pollInterval"] == 2000 and "now" in body


def test_events_endpoint_replays_only_what_the_client_missed(client, db, full_history):
    _as()
    _, hist = full_history
    _seed(db, hist)
    everything = client.get(f"{BASE}/tasks/ev-run/events").json()
    cut = everything["events"][3]["seq"]
    rest = client.get(f"{BASE}/tasks/ev-run/events", params={"after": cut}).json()
    assert [e["seq"] for e in rest["events"]] == [e["seq"] for e in everything["events"] if e["seq"] > cut]
    caught_up = client.get(f"{BASE}/tasks/ev-run/events", params={"after": everything["nextAfter"]}).json()
    assert caught_up["events"] == [] and caught_up["nextAfter"] == everything["nextAfter"]


def test_events_endpoint_for_a_finished_run_says_done(client, db, full_history):
    _as()
    _, hist = full_history
    hist = hist + [{"node": None, "type": "terminal", "status": "completed", "result": {}, "ts": "t"}]
    _seed(db, hist, status="completed", node=None)
    body = client.get(f"{BASE}/tasks/ev-run/events").json()
    assert body["done"] is True and body["status"] == "completed" and body["pollInterval"] is None
    assert body["events"][-1]["event"]["type"] == "RUN_FINISHED" and body["now"] is None
    assert body["calmCard"]["status"] == "done"


def test_events_endpoint_for_a_failed_run(client, db):
    _as()
    _seed(db, [{"node": None, "type": "terminal", "status": "failed", "result": {"error": "boom"}}],
          status="failed", node=None, error="boom")
    body = client.get(f"{BASE}/tasks/ev-run/events").json()
    assert body["events"][-1]["event"]["code"] == "RUN_FAILED" and body["calmCard"]["status"] == "blocked"


def test_events_endpoint_marks_the_approval_gate(client, db, full_history):
    _as()
    _, hist = full_history
    gate_at = next(i for i, e in enumerate(hist) if e["status"] == "awaiting_approval")
    _seed(db, hist[: gate_at + 1], status="awaiting_approval", node="approve")
    body = client.get(f"{BASE}/tasks/ev-run/events").json()
    assert body["status"] == "input_required" and body["calmCard"]["status"] == "waiting_on_you"
    assert "approve" in body["calmCard"]["next_action"]
    assert "hypercode.approval.required" in [e["event"].get("name") for e in body["events"]]


def test_events_endpoint_validates_and_hides_non_catalog_runs(client, db):
    _as()
    _seed(db, [])
    assert client.get(f"{BASE}/tasks/ev-run/events", params={"after": -2}).status_code == 422
    assert client.get(f"{BASE}/tasks/ev-run/events", params={"after": "x"}).status_code == 422
    assert client.get(f"{BASE}/tasks/nope/events").status_code == 404
    db.add(HyperFlowRun(id="other", flow_name="not-a-catalog-flow", flow_version=1, status="running", state={}))
    db.commit()
    assert client.get(f"{BASE}/tasks/other/events").status_code == 404


def test_events_endpoint_requires_authentication(client, db):
    app.dependency_overrides.pop(operator_tasks.operator_principal, None)
    _seed(db, [])
    assert client.get(f"{BASE}/tasks/ev-run/events").status_code == 401
