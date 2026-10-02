"""HyperCrew Day 2 — plan model, local tools and flow definition (pure, no network)."""

import asyncio

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.hyperflow.registry import get_flow
from app.broski_operator.catalog import TOOL_ARGUMENTS, TOOL_FLOWS, ArgumentError, validate_arguments
from app.broski_operator.tools import LOCAL_TOOLS
from app.crew import plan as plan_mod
from app.crew import tools as crew_tools
from app.crew.plan import (
    CONSTRAINTS, STAGES, CrewStartArgs, build_crew_plan, crew_plan_hash, stage_roles, valid_baton_roles,
)
from app.crew.tools import CrewSealError, crew_plan, crew_seal
from app.models.governance import GovernanceLedger


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def ledger_db(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    GovernanceLedger.__table__.create(bind=eng)
    factory = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    monkeypatch.setattr(crew_tools, "SessionLocal", factory)
    yield factory
    eng.dispose()


# ── CrewStartArgs ──────────────────────────────────────────────────────────────
def test_goal_is_trimmed_and_whitespace_collapsed():
    assert CrewStartArgs(goal="  add   a\nhealth\tendpoint  ").goal == "add a health endpoint"


@pytest.mark.parametrize("bad", ["", "ab", "   ", "x" * 2001])
def test_goal_length_bounds(bad):
    with pytest.raises(ValidationError):
        CrewStartArgs(goal=bad)


def test_goal_over_500_after_cleaning_is_rejected():
    with pytest.raises(ValidationError):
        CrewStartArgs(goal="a" * 501)
    assert len(CrewStartArgs(goal="a" * 500).goal) == 500


def test_goal_rejects_control_characters():
    with pytest.raises(ValidationError):
        CrewStartArgs(goal="do a thing\x00now")


def test_goal_masks_pasted_secrets():
    goal = CrewStartArgs(goal="deploy with password=hunter2 and token=abc123").goal
    assert "hunter2" not in goal and "abc123" not in goal
    assert "password=***" in goal


def test_args_reject_extra_fields_and_non_strings():
    with pytest.raises(ValidationError):
        CrewStartArgs(goal="valid goal", priority="high")
    with pytest.raises(ValidationError):
        CrewStartArgs(goal=["a", "b"])


# ── the plan ───────────────────────────────────────────────────────────────────
def test_plan_is_deterministic_and_hash_is_stable():
    a, b = build_crew_plan("add a health endpoint", "run-1"), build_crew_plan("add a health endpoint", "run-1")
    assert a == b and crew_plan_hash(a) == crew_plan_hash(b)
    assert crew_plan_hash(a).startswith("sha256:") and len(crew_plan_hash(a)) == len("sha256:") + 64


@pytest.mark.parametrize("goal,run_id", [("another goal", "run-1"), ("add a health endpoint", "run-2")])
def test_hash_changes_when_goal_or_run_changes(goal, run_id):
    base = crew_plan_hash(build_crew_plan("add a health endpoint", "run-1"))
    assert crew_plan_hash(build_crew_plan(goal, run_id)) != base


def test_hash_changes_when_any_part_of_the_plan_is_tampered():
    plan = build_crew_plan("add a health endpoint", "run-1")
    base = crew_plan_hash(plan)
    for mutate in (
        lambda p: p["constraints"].remove("no container mutation"),
        lambda p: p["stages"].pop(),
        lambda p: p["limits"].update(max_awake_agents=99),
        lambda p: p.update(risk_hint="mutation"),
    ):
        tampered = build_crew_plan("add a health endpoint", "run-1")
        mutate(tampered)
        assert crew_plan_hash(tampered) != base


def test_plan_is_non_mutating_and_shows_its_constraints():
    plan = build_crew_plan("add a health endpoint", "run-1")
    assert plan["risk_hint"] == "propose"
    assert set(plan["constraints"]) == set(CONSTRAINTS)
    assert "no container mutation" in plan["constraints"]


def test_every_stage_role_is_a_real_baton_role_and_one_human_gate_exists():
    assert stage_roles() <= valid_baton_roles()
    assert [s["id"] for s in STAGES if s["role"] == "human"] == ["review"]
    assert len({s["id"] for s in STAGES}) == len(STAGES)


def test_plan_does_not_alias_module_constants():
    plan = build_crew_plan("add a health endpoint", "run-1")
    plan["constraints"].append("x")
    plan["stages"][0]["id"] = "hacked"
    assert "x" not in plan_mod.CONSTRAINTS and plan_mod.STAGES[0]["id"] == "chunk"


# ── catalog ────────────────────────────────────────────────────────────────────
def test_catalog_registers_crew_and_only_crew_takes_arguments():
    assert TOOL_FLOWS["hypercode.crew"] == "hypercode-crew"
    assert set(TOOL_ARGUMENTS) == {"hypercode.crew"}


def test_validate_arguments():
    assert validate_arguments("hypercode.crew", {"goal": "  add a thing "}) == {"goal": "add a thing"}
    assert validate_arguments("hypercode.inspect", {}) == {}
    for tool, args in (("hypercode.inspect", {"x": 1}), ("hypercode.crew", {}), ("hypercode.crew", {"goal": "x"})):
        with pytest.raises(ArgumentError):
            validate_arguments(tool, args)


def test_argument_error_never_echoes_the_input():
    with pytest.raises(ArgumentError) as exc:
        validate_arguments("hypercode.crew", {"goal": "hi", "secret_field": "SUPERSECRET"})
    assert "SUPERSECRET" not in str(exc.value)


# ── crew_plan tool ─────────────────────────────────────────────────────────────
def test_crew_plan_builds_a_hashed_proposal():
    out = run(crew_plan({}, {"run_id": "r1", "arguments": {"goal": "add a health endpoint"}}))
    assert out["ok"] and out["has_proposal"]
    prop = out["proposal"]
    assert prop["plan"]["goal"] == "add a health endpoint" and prop["plan"]["run_id"] == "r1"
    assert prop["plan_hash"] == crew_plan_hash(prop["plan"])
    assert prop["summary"].startswith("crew run: add a health endpoint")


@pytest.mark.parametrize("arguments", [None, {}, {"goal": ""}, {"goal": 5}, "goal", {"goal": "x"}])
def test_crew_plan_fails_closed_without_a_valid_goal(arguments):
    out = run(crew_plan({}, {"run_id": "r1", "arguments": arguments}))
    assert out["ok"] is False and out["has_proposal"] is False and out["proposal"] is None


def test_crew_plan_summary_is_bounded():
    out = run(crew_plan({}, {"run_id": "r1", "arguments": {"goal": "g" * 500}}))
    assert len(out["proposal"]["summary"]) <= len("crew run: ") + 100


# ── crew_seal tool ─────────────────────────────────────────────────────────────
def _history(approved=True, by="bro@example.com", gate_hash="MATCH", tamper=False):
    plan_out = run(crew_plan({}, {"run_id": "r1", "arguments": {"goal": "add a health endpoint"}}))
    h = plan_out["proposal"]["plan_hash"]
    if tamper:
        plan_out["proposal"]["plan"]["goal"] = "something else entirely"
    gate = {"success": True, "approved": approved}
    if by:
        gate["by"] = by
    gate["plan_hash"] = h if gate_hash == "MATCH" else gate_hash
    return [
        {"node": "plan", "status": "completed", "result": {"data": plan_out}},
        {"node": "approve", "status": "completed", "result": gate},
    ], h


def test_seal_happy_path_writes_one_ledger_row(ledger_db):
    history, h = _history()
    out = run(crew_seal({}, {"run_id": "r1", "history": history}))
    assert out["sealed"] and out["performed"] is False and out["plan_hash"] == h
    assert out["approved_by"] == "bro@example.com" and out["ledger"] is True
    rows = ledger_db().query(GovernanceLedger).filter_by(action="crew_plan_approved").all()
    assert len(rows) == 1 and rows[0].approved_by == "bro@example.com"
    assert rows[0].payload["performed"] is False


@pytest.mark.parametrize("kwargs,msg", [
    ({"tamper": True}, "plan hash does not match"),
    ({"approved": False}, "not approved"),
    ({"by": None}, "no recorded approver"),
    ({"gate_hash": "sha256:" + "0" * 64}, "not for this plan hash"),
    ({"gate_hash": None}, "not for this plan hash"),
])
def test_seal_refuses_when_any_check_fails(ledger_db, kwargs, msg):
    history, _ = _history(**kwargs)
    with pytest.raises(CrewSealError, match=msg):
        run(crew_seal({}, {"run_id": "r1", "history": history}))
    assert ledger_db().query(GovernanceLedger).count() == 0


def test_seal_with_no_plan_raises():
    with pytest.raises(CrewSealError, match="no plan"):
        run(crew_seal({}, {"run_id": "r1", "history": []}))


def test_seal_survives_a_ledger_failure(monkeypatch):
    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(crew_tools, "SessionLocal", boom)
    history, _ = _history()
    out = run(crew_seal({}, {"run_id": "r1", "history": history}))
    assert out["sealed"] is True and out["ledger"] is False


# ── flow definition ────────────────────────────────────────────────────────────
def test_flow_loads_and_is_shaped_like_the_design():
    flow = get_flow("hypercode-crew")
    assert flow is not None and flow.entry == "plan" and flow.intent
    assert [n.id for n in flow.nodes] == ["plan", "approve", "seal", "build", "verify", "guard", "settle", "scribe", "approve_scribe", "publish"]
    plan, gate, seal = (flow.node(i) for i in ("plan", "approve", "seal"))
    assert plan.tool == "local.crew_plan" and plan.idempotent and plan.params["with_arguments"] is True
    assert plan.success_key == "has_proposal"
    assert gate.type.value == "human_approval_gate" and gate.params["show_from"] == "plan"
    assert seal.tool == "local.crew_seal" and not seal.idempotent  # never re-run blindly after a restart


def test_flow_dispatch_nodes_are_strict_propose_only_and_use_the_static_registry():
    from app.crew.dispatch import CREW_AGENTS

    flow = get_flow("hypercode-crew")
    assert flow.version == 4
    for node_id, role in (("build", "builder"), ("verify", "verifier")):
        node = flow.node(node_id)
        assert node.type.value == "agent_dispatch" and node.agent == CREW_AGENTS[role]
        assert node.params["role"] == role and node.params["stage"] == node_id
        assert node.idempotent  # propose-only: safe to re-run after a restart
    assert flow.node("verify").params["input_from"] == "build"
    guard = flow.node("guard")
    assert guard.tool == "local.crew_guard" and guard.success_key == "allowed"


def test_flow_order_is_plan_approve_seal_build_verify_guard():
    flow = get_flow("hypercode-crew")
    order, cur = [flow.entry], flow.entry
    while flow.edges_from(cur):
        cur = flow.edges_from(cur)[0].dst
        order.append(cur)
    assert order == ["plan", "approve", "seal", "build", "verify", "guard", "settle", "scribe", "approve_scribe", "publish"]


def test_flow_only_continues_to_the_gate_when_a_plan_exists():
    flow = get_flow("hypercode-crew")
    to_gate = [e for e in flow.edges_from("plan")]
    assert len(to_gate) == 1 and to_gate[0].dst == "approve" and to_gate[0].condition is True


def test_flow_tools_are_registered_local_tools():
    for name in ("local.crew_plan", "local.crew_seal", "local.crew_guard"):
        assert name in LOCAL_TOOLS
    flow = get_flow("hypercode-crew")
    for node in flow.nodes:
        if node.tool:
            assert node.tool in LOCAL_TOOLS


def test_no_docker_or_network_imports_in_crew_tools():
    import ast
    import pathlib

    banned = {"docker", "httpx", "requests", "subprocess", "socket"}
    for mod in (crew_tools, plan_mod):
        tree = ast.parse(pathlib.Path(mod.__file__).read_text())
        names = {
            a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
        } | {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        assert not (names & banned), f"{mod.__name__} imports {names & banned}"
