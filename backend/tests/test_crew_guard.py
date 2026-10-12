"""HyperCrew Day 3 — the Guardian: ALLOW only when every deterministic check passes."""

import asyncio

import pytest

from app.crew.evidence import sha256_hex, verify_bundle
from app.crew.plan import build_crew_plan, crew_plan_hash
from app.crew.tools import crew_guard

PLAN = build_crew_plan("add a health endpoint", "r1")
GOOD_BUILD = "```diff\n+def health():\n+    return {'ok': True}\n```\nAdds a health route."
GOOD_VERIFY = "The route is small and correct.\nVERDICT: PASS"


def run(coro):
    return asyncio.run(coro)


def _history(plan=PLAN, sealed=True, build=GOOD_BUILD, verify=GOOD_VERIFY):
    h = [{"node": "seal", "status": "completed",
          "result": {"data": {"sealed": sealed, "plan": plan, "plan_hash": crew_plan_hash(plan)}}}]
    if build is not None:
        h.append({"node": "build", "status": "completed", "result": {"data": {"summary": build}}})
    if verify is not None:
        h.append({"node": "verify", "status": "completed", "result": {"data": {"summary": verify}}})
    return h


def guard(history):
    return run(crew_guard({}, {"run_id": "r1", "history": history}))


def names(out, passed):
    return {c["name"] for c in out["checks"] if c["passed"] is passed}


def test_everything_good_is_allowed_with_a_valid_bundle():
    out = guard(_history())
    assert out["allowed"] is True and out["verdict"] == "ALLOW" and out["failed_checks"] == []
    assert out["performed"] is False and out["ok"] is True
    bundle = out["evidence_bundle"]
    assert verify_bundle(bundle) and bundle["plan_hash"] == crew_plan_hash(PLAN)
    kinds = {(e["kind"], e["ref"]): e["sha256"] for e in bundle["evidence"]}
    assert kinds[("diff", "run:r1:node:build")] == sha256_hex(GOOD_BUILD)
    assert kinds[("log", "run:r1:node:verify")] == sha256_hex(GOOD_VERIFY)


def test_a_failing_verdict_blocks():
    out = guard(_history(verify="problems found\nVERDICT: FAIL"))
    assert out["verdict"] == "BLOCK" and out["failed_checks"] == ["verifier_verdict"]


@pytest.mark.parametrize("verify", ["looks fine to me", "VERDICT: PASS maybe", ""])
def test_a_missing_or_unreadable_verdict_blocks_never_assumes_pass(verify):
    assert guard(_history(verify=verify))["allowed"] is False


@pytest.mark.parametrize("bad", ["git push origin main", "rm -rf /", "mount docker.sock", "DROP TABLE users"])
def test_a_forbidden_command_in_the_proposal_blocks(bad):
    out = guard(_history(build=f"```sh\n{bad}\n```"))
    assert out["allowed"] is False and "build_clean" in out["failed_checks"]
    detail = next(c["detail"] for c in out["checks"] if c["name"] == "build_clean")
    assert detail.startswith("proposal contains:")


def test_missing_stages_block_with_specific_reasons():
    out = guard(_history(build=None, verify=None))
    assert {"build_present", "verify_present", "verifier_verdict"} <= set(out["failed_checks"])
    assert out["evidence_bundle"]["evidence"] == []


def test_an_unsealed_plan_blocks():
    out = guard(_history(sealed=False))
    assert "plan_sealed" in out["failed_checks"] and out["allowed"] is False


def test_a_mutating_plan_blocks():
    plan = dict(PLAN, risk_hint="mutation")
    assert "plan_non_mutating" in guard(_history(plan=plan))["failed_checks"]


def test_empty_history_blocks_everything_and_does_not_crash():
    out = guard([])
    assert out["allowed"] is False and out["verdict"] == "BLOCK"
    assert "plan_sealed" in out["failed_checks"] and verify_bundle(out["evidence_bundle"])


def test_garbage_shapes_in_history_fail_closed():
    hist = [{"node": "seal", "status": "completed", "result": {"data": {"sealed": True, "plan": "nope", "plan_hash": 5}}},
            {"node": "build", "status": "completed", "result": {"data": {"summary": 123}}}]
    out = guard(hist)
    assert out["allowed"] is False


def test_the_latest_completed_entry_for_a_stage_is_the_one_judged():
    hist = _history(verify="old\nVERDICT: FAIL") + [
        {"node": "verify", "status": "completed", "result": {"data": {"summary": "new\nVERDICT: PASS"}}}]
    assert guard(hist)["allowed"] is True


def test_every_check_reports_a_detail_string():
    out = guard(_history())
    assert len(out["checks"]) == 6 and all(isinstance(c["detail"], str) and c["detail"] for c in out["checks"])
    assert names(out, True) == {c["name"] for c in out["checks"]}
