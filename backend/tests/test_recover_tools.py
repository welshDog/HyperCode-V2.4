"""BROski recover — propose/seal local tools and the operator-recover flow end to end."""

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.hyperflow.registry import get_flow
from app.broski_operator import catalog, recover, recover_tools, tools
from app.broski_operator.recover_tools import RecoverSealError, recover_propose, recover_seal
from app.models.governance import GovernanceLedger
from app.models.hyperflow import HyperFlowRunStatus
from tests.test_hyperflow import _runner_with_io


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "off")
    monkeypatch.setattr("app.agents.hyperflow_runner.APPROVAL_POLL_SECONDS", 0.01)


def S(name, state, status, labels=None, cid="a1b2c3d4e5f6"):
    return {"Id": cid, "Names": ["/" + name], "State": state, "Status": status, "Labels": labels or {}}


def _docker(monkeypatch, summaries, details=None):
    async def fetch():
        return summaries

    async def detail(cid):
        return (details or {}).get(cid)

    async def cooldown(name):
        return {"count": 0, "limit": 3, "window_s": 300}

    monkeypatch.setattr(recover_tools, "_fetch_summaries", fetch)
    monkeypatch.setattr(recover_tools, "_get_detail", detail)
    monkeypatch.setattr(recover_tools, "_cooldown", cooldown)


def test_propose_picks_the_eligible_unhealthy_container(monkeypatch):
    _docker(monkeypatch, [
        S("hypercode-core", "running", "Up (unhealthy)", cid="c0c0c0c0c0c0"),
        S("zz-nolabel", "running", "Up (unhealthy)", cid="c1c1c1c1c1c1"),
        S("skillweaver", "running", "Up (unhealthy)", cid="c2c2c2c2c2c2"),
        S("chroma", "running", "Up (healthy)", cid="c3c3c3c3c3c3"),
    ])
    out = asyncio.run(recover_propose({}, {"run_id": "r1", "history": []}))
    assert out["ok"] is True and out["has_proposal"] is True
    assert out["proposal"]["plan"]["target"] == "skillweaver"
    assert "hypercode-core: never_list" in out["not_eligible"]
    assert "zz-nolabel: not_allowlisted" in out["not_eligible"]
    assert out["proposal"]["plan"]["run_id"] == "r1" and "checked_at" in out


def test_propose_nothing_to_recover(monkeypatch):
    _docker(monkeypatch, [S("chroma", "running", "Up (healthy)")])
    out = asyncio.run(recover_propose({}, {"run_id": "r1", "history": []}))
    assert out["ok"] is True and out["has_proposal"] is False and out["proposal"] is None


def test_propose_docker_unreachable_is_structured_not_an_exception(monkeypatch):
    async def boom():
        raise RuntimeError("redis://:hunter2@host connection refused")

    monkeypatch.setattr(recover_tools, "_fetch_summaries", boom)
    out = asyncio.run(recover_propose({}, {"run_id": "r1", "history": []}))
    assert out["ok"] is False and out["has_proposal"] is False and out["proposal"] is None
    assert "hunter2" not in " ".join(out["notes"])   # Review focus 5


def test_propose_includes_inspect_attention_notes(monkeypatch):
    _docker(monkeypatch, [])
    hist = [{"node": "inspect", "status": "completed",
             "result": {"success": True, "data": {"attention": ["dead-letter queue has 3 tasks"]}}}]
    out = asyncio.run(recover_propose({}, {"run_id": "r1", "history": hist}))
    assert "dead-letter queue has 3 tasks" in out["notes"]


def test_get_detail_rejects_non_hex_ids_before_any_http(monkeypatch):
    called = []

    class Boom:
        def __init__(self, **kw):
            called.append("client")

    monkeypatch.setattr(recover_tools.httpx, "AsyncClient", Boom)
    for bad in ("../../etc", "abc/../x", "", "zz zz", "g" * 12, "a" * 65):   # Review focus 6
        assert asyncio.run(recover_tools._get_detail(bad)) is None
    assert called == []


def test_cooldown_timeout_falls_back_instead_of_hanging(monkeypatch):
    """Minor fix #2: a black-holed Redis must not hang `propose` — `_cooldown` is bounded."""

    async def fetch():
        return [S("skillweaver", "running", "Up (unhealthy)", cid="c2c2c2c2c2c2")]

    async def detail(cid):
        return None

    async def hangs(name):
        await asyncio.sleep(0.3)
        return {"count": 999, "limit": recover_tools._COOLDOWN_LIMIT, "window_s": recover_tools._COOLDOWN_WINDOW}

    monkeypatch.setattr(recover_tools, "_fetch_summaries", fetch)
    monkeypatch.setattr(recover_tools, "_get_detail", detail)
    monkeypatch.setattr(recover_tools, "_cooldown", hangs)
    monkeypatch.setattr(recover_tools, "_COOLDOWN_TIMEOUT_S", 0.02, raising=False)

    out = asyncio.run(recover_propose({}, {"run_id": "r1", "history": []}))
    assert out["ok"] is True and out["has_proposal"] is True
    cand = next(c for c in out["candidates"] if c["container"] == "skillweaver")
    assert cand["cooldown"] == {
        "count": None, "limit": recover_tools._COOLDOWN_LIMIT, "window_s": recover_tools._COOLDOWN_WINDOW
    }


# ── seal ────────────────────────────────────────────────────────────────────

PLAN = {"version": 1, "action": "restart", "target": "skillweaver", "reason": "unhealthy",
        "evidence_digest": "sha256:e", "run_id": "r1"}
H = recover.plan_hash(PLAN)


def _hist(approved=True, by="bro@example.com", gate_hash=H, proposal_hash=H, plan=PLAN):
    return [
        {"node": "propose", "type": "tool", "status": "completed",
         "result": {"success": True, "data": {"proposal": {"plan": plan, "plan_hash": proposal_hash}}}},
        {"node": "approve", "type": "human_approval_gate", "status": "completed",
         "result": {"success": True, "approved": approved, "by": by, "plan_hash": gate_hash}},
    ]


@pytest.fixture
def ledger_db(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    GovernanceLedger.__table__.create(bind=eng)
    factory = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    monkeypatch.setattr(recover_tools, "SessionLocal", factory)
    yield factory
    eng.dispose()


def test_seal_success_records_ledger_and_never_performs(ledger_db):
    out = asyncio.run(recover_seal({}, {"run_id": "r1", "history": _hist()}))
    assert out["ok"] is True and out["sealed"] is True and out["performed"] is False
    assert out["plan_hash"] == H and out["approved_by"] == "bro@example.com" and out["ledger"] is True
    s = ledger_db()
    rows = s.query(GovernanceLedger).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.action == "recover_plan_approved" and row.tool_used == "hypercode.recover"
    assert row.decision == "approved" and row.approved_by == "bro@example.com"
    assert row.payload["run_id"] == "r1" and row.payload["performed"] is False and row.payload["plan_hash"] == H
    s.close()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"proposal_hash": "sha256:" + "0" * 64},                       # proposal hash != recomputed
        {"plan": {**PLAN, "target": "postgres"}},                       # tampered plan, old hash
        {"gate_hash": "sha256:" + "1" * 64},                            # approved a different hash
        {"approved": False},                                            # not approved
        {"by": None},                                                   # no recorded approver
        {"by": ""},
    ],
)
def test_seal_refuses_hash_or_approver_problems(ledger_db, kwargs):
    with pytest.raises(RecoverSealError):
        asyncio.run(recover_seal({}, {"run_id": "r1", "history": _hist(**kwargs)}))
    assert ledger_db().query(GovernanceLedger).count() == 0   # Review focus 7: nothing sealed


def test_seal_refuses_without_a_proposal_or_gate(ledger_db):
    with pytest.raises(RecoverSealError):
        asyncio.run(recover_seal({}, {"run_id": "r1", "history": []}))


def test_ledger_failure_does_not_block_the_seal(monkeypatch):
    monkeypatch.setattr(recover_tools, "_write_ledger", lambda entry: False)
    out = asyncio.run(recover_seal({}, {"run_id": "r1", "history": _hist()}))
    assert out["sealed"] is True and out["ledger"] is False


# ── registry + flow ──────────────────────────────────────────────────────────

def test_tools_and_catalog_registered():
    assert "local.recover_propose" in tools.LOCAL_TOOLS and "local.recover_seal" in tools.LOCAL_TOOLS
    assert catalog.TOOL_FLOWS["hypercode.recover"] == "operator-recover"
    assert catalog.tool_for_flow("operator-recover") == "hypercode.recover"


def test_flow_shape():
    fd = get_flow("operator-recover")
    assert fd is not None and fd.intent and fd.entry == "inspect"
    assert fd.node("inspect").idempotent is True and fd.node("propose").idempotent is True
    assert fd.node("propose").success_key == "has_proposal"
    assert fd.node("approve").params["show_from"] == "propose"
    assert fd.node("seal").idempotent is False


def test_operator_recover_flow_end_to_end(monkeypatch, ledger_db):
    """Real flow + real local tools + real runner: propose -> gate (hash shown) -> approve -> seal."""
    _docker(monkeypatch, [S("skillweaver", "running", "Up (unhealthy)", cid="f1f1f1f1f1f1")])

    async def fake_inspect(params, ctx=None):
        return {"ok": True, "attention": []}

    monkeypatch.setitem(tools.LOCAL_TOOLS, "local.inspect", fake_inspect)
    runner, final = _runner_with_io(get_flow("operator-recover"), "e2e-run", monkeypatch)

    async def scenario():
        runner._task = asyncio.create_task(runner._run())
        for _ in range(100):
            if runner.parked_gate == "approve":
                break
            await asyncio.sleep(0.02)
        assert runner.parked_gate == "approve"
        awaiting = [e for e in runner._history if e["status"] == "awaiting_approval"][0]
        shown_hash = awaiting["result"]["plan_hash"]
        assert awaiting["result"]["context"]["proposal"]["plan"]["target"] == "skillweaver"

        def take(node_id=None):
            runner._last_decision_meta = {"by": "bro@example.com", "plan_hash": shown_hash}
            return True

        monkeypatch.setattr(runner, "_take_persisted_decision", take)
        runner.resume(True)
        await runner._task

    asyncio.run(scenario())
    assert final["status"] is HyperFlowRunStatus.COMPLETED
    sealed = [e for e in runner._history if e["node"] == "seal" and e["status"] == "completed"][0]
    assert sealed["result"]["data"]["sealed"] is True and sealed["result"]["data"]["performed"] is False
    assert ledger_db().query(GovernanceLedger).count() == 1
