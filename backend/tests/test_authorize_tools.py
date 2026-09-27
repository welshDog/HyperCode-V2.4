"""BROski recover Phase 2b — authorize: builds a Governor plan, mints DRY_RUN, records the outcome.

Every mint in these tests is refused (ESCALATE, no grant) by design — this increment proves the
pipeline fails closed, it never mints. See docs/superpowers/specs/2026-09-27-broski-recover-2b-design.md.
"""

import ast
import asyncio
import importlib.util
import pathlib
import sys

import httpx
import pytest

# Adaptation (not in the brief's literal snippet): `authorize_tools.httpx` IS this same
# httpx module object (plain `import httpx`, not a copy), so `monkeypatch.setattr(
# authorize_tools.httpx, "AsyncClient", factory)` patches the real, shared
# `httpx.AsyncClient` attribute for every reader of it -- including `factory` itself,
# which otherwise calls back into its own patched self via `httpx.AsyncClient(...)` and
# recurses (`TypeError: got multiple values for keyword argument 'transport'`). Capturing
# the real class once, before any test patches it, and calling that captured reference
# instead of the (by-then-patched) module attribute avoids the self-reference.
_RealAsyncClient = httpx.AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.broski_operator import authorize_tools
from app.broski_operator.authorize_tools import AuthorizeError, authorize, build_plan, canonical_hash
from app.models.governance import GovernanceLedger


@pytest.fixture
def ledger_db(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    GovernanceLedger.__table__.create(bind=eng)
    factory = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    monkeypatch.setattr(authorize_tools, "SessionLocal", factory)
    yield factory
    eng.dispose()


def _load_real_governor_module():
    """Load the REAL agents/governor/models.py in this test process only — never at runtime.

    This is the file-copy convention's intended escape hatch for tests: prove independent
    reimplementations agree, without ever letting production code cross-import agents.
    """
    path = pathlib.Path(__file__).resolve().parents[2] / "agents" / "governor" / "models.py"
    spec = importlib.util.spec_from_file_location("governor_models_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    # Adaptation (not in the brief's literal snippet): agents/governor/models.py uses
    # `from __future__ import annotations`, so Pydantic v2 resolves its forward refs
    # (Literal[...], list[RequestedAction], Constraints) by looking the module up in
    # sys.modules by name. A module loaded via importlib.util but never registered
    # there fails that lookup silently at class-creation time and only surfaces as
    # `PydanticUserError: not fully defined` the first time the model is instantiated.
    # Registering it here is the standard fix and changes nothing about what real
    # module content this test loads (still read-only, still never imported by
    # runtime code).
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _sealed(target: str = "chroma", plan_hash: str = "sha256:" + "a" * 64) -> list[dict]:
    """A minimal, realistic completed `seal` history entry (shape matches
    `recover_tools.recover_seal`'s real return value: `data.plan.target` +
    top-level `data.plan_hash`) — used wherever a test needs `authorize` to get
    past its own precondition checks and actually reach the Governor call.
    """
    return [
        {
            "node": "seal", "type": "tool", "status": "completed",
            "result": {
                "success": True,
                "data": {
                    "ok": True, "sealed": True, "performed": False,
                    "plan": {"version": 1, "action": "restart", "target": target,
                              "reason": "test", "run_id": "run-x"},
                    "plan_hash": plan_hash,
                },
            },
        }
    ]


# ── build_plan / canonical_hash ──────────────────────────────────────────────

def test_build_plan_shape():
    plan = build_plan("run-123", "skillweaver")
    assert plan == {
        "schema_version": 1,
        "mission_id": "run-123",
        "requested_actions": [
            {"action_id": "restart-skillweaver", "kind": "container.restart", "profile": "skillweaver"}
        ],
        "constraints": {"max_services": 25, "allow_profiles": [], "deny_profiles": []},
    }


def test_canonical_hash_matches_governors_real_algorithm():
    """The core parity guarantee: our hash must equal what Governor recomputes server-side."""
    gov = _load_real_governor_module()
    plan_dict = build_plan("run-456", "chroma")
    gov_plan = gov.PlanRequest(**plan_dict)
    assert canonical_hash(plan_dict) == gov.canonical_hash(gov_plan)


def test_canonical_hash_stable_and_content_sensitive():
    p1 = build_plan("run-1", "chroma")
    p2 = build_plan("run-1", "chroma")
    p3 = build_plan("run-1", "skillweaver")
    assert canonical_hash(p1) == canonical_hash(p2)
    assert canonical_hash(p1) != canonical_hash(p3)
    assert canonical_hash(p1).startswith("sha256:") and len(canonical_hash(p1)) == 7 + 64


# ── authorize() ───────────────────────────────────────────────────────────────

REFUSAL_BODY = {
    "capability": None, "jti": None,
    "verdict": {"decision": "ESCALATE", "reason": "no capabilities for agent 'broski-operator'",
                "risk_class": "INFRASTRUCTURE_MUTATION", "policy_version": "safety-2026-09-04.1"},
    "minted": False, "reason": "policy verdict ESCALATE; human approval required",
}


def _client_returning(status_code, json_body=None, raise_exc=None):
    async def handler(request: httpx.Request) -> httpx.Response:
        if raise_exc is not None:
            raise raise_exc
        return httpx.Response(status_code, json=json_body if json_body is not None else {})

    def factory(**kw):
        return _RealAsyncClient(transport=httpx.MockTransport(handler), **kw)

    return factory


def test_authorize_records_a_well_formed_refusal_as_success(monkeypatch, ledger_db):
    monkeypatch.setattr(authorize_tools.httpx, "AsyncClient", _client_returning(200, REFUSAL_BODY))
    out = asyncio.run(authorize({}, {"run_id": "run-1", "history": _sealed()}))
    assert out["ok"] is True
    assert out["minted"] is False
    assert out["mode"] == "DRY_RUN"
    assert out["verdict"]["decision"] == "ESCALATE"
    assert out["verdict"]["risk_class"] == "INFRASTRUCTURE_MUTATION"
    assert out["ledger"] is True
    s = ledger_db()
    rows = s.query(GovernanceLedger).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.action == "recover_authorization_attempted" and row.tool_used == "hypercode.recover"
    assert row.payload["minted"] is False
    assert row.payload["mode"] == "DRY_RUN"
    assert row.payload["governor_verdict"]["decision"] == "ESCALATE"
    s.close()


def test_authorize_never_conflates_the_two_hashes(monkeypatch, ledger_db):
    """Fix-round-1: strengthened per reviewer finding 3 — the original version only checked
    the two hashes differ and were self-consistent between output and ledger, which would
    NOT catch the two values being swapped (assigned to each other's field) as long as they
    stayed consistent with each other. Now asserts each against its own independently
    computed exact expected value.
    """
    sealed_plan_hash = "sha256:" + "a" * 64  # _sealed()'s own default sentinel — 2a's own hash
    expected_governor_hash = canonical_hash(build_plan("run-2", "chroma"))  # _sealed()'s default target
    assert sealed_plan_hash != expected_governor_hash  # sanity: the two sentinels really are distinct

    monkeypatch.setattr(authorize_tools.httpx, "AsyncClient", _client_returning(200, REFUSAL_BODY))
    out = asyncio.run(authorize({}, {"run_id": "run-2", "history": _sealed()}))
    assert out["plan_hash"] == sealed_plan_hash  # 2a's own hash, verbatim from the sealed history
    assert out["governor_plan_hash"] == expected_governor_hash  # freshly computed here, not copied

    s = ledger_db()
    row = s.query(GovernanceLedger).first()
    assert row.payload["plan_hash"] == sealed_plan_hash
    assert row.payload["governor_plan_hash"] == expected_governor_hash
    s.close()


def test_authorize_connection_failure_raises_not_a_fake_refusal(monkeypatch, ledger_db):
    """Review focus 4: a genuine communication failure must fail the node, never look like a policy refusal."""
    monkeypatch.setattr(
        authorize_tools.httpx, "AsyncClient",
        _client_returning(200, raise_exc=httpx.ConnectError("refused")),
    )
    with pytest.raises(AuthorizeError, match="could not reach Governor: ConnectError"):
        asyncio.run(authorize({}, {"run_id": "run-3", "history": _sealed()}))
    assert ledger_db().query(GovernanceLedger).count() == 0  # nothing recorded for a comms failure


def test_authorize_non_200_raises(monkeypatch, ledger_db):
    monkeypatch.setattr(authorize_tools.httpx, "AsyncClient", _client_returning(500, {}))
    with pytest.raises(AuthorizeError, match="HTTP 500"):
        asyncio.run(authorize({}, {"run_id": "run-4", "history": _sealed()}))


def test_authorize_malformed_body_raises(monkeypatch, ledger_db):
    monkeypatch.setattr(authorize_tools.httpx, "AsyncClient", _client_returning(200, {"not": "the expected shape"}))
    with pytest.raises(AuthorizeError, match="missing required fields"):
        asyncio.run(authorize({}, {"run_id": "run-5", "history": _sealed()}))


def test_authorize_null_minted_and_verdict_raises(monkeypatch, ledger_db):
    """Fix-round-1, reviewer finding 2: a well-formed-looking 200 whose `minted`/`verdict`
    are `null` must not be coerced (`bool(None)` -> False, `verdict or {}` -> {}) into a
    fabricated policy refusal. It must raise, never be silently written to the ledger as
    if Governor genuinely refused.
    """
    monkeypatch.setattr(
        authorize_tools.httpx, "AsyncClient",
        _client_returning(200, {"minted": None, "verdict": None}),
    )
    with pytest.raises(AuthorizeError, match="missing required fields"):
        asyncio.run(authorize({}, {"run_id": "run-10", "history": _sealed()}))
    assert ledger_db().query(GovernanceLedger).count() == 0


def test_authorize_wrong_typed_minted_raises(monkeypatch, ledger_db):
    """Fix-round-1, reviewer finding 2: `minted` as a truthy non-bool string must not be
    accepted — `bool("false")` is `True` in Python, which would be a real, dangerous
    misinterpretation of a refusal as a mint.
    """
    monkeypatch.setattr(
        authorize_tools.httpx, "AsyncClient",
        _client_returning(200, {"minted": "false", "verdict": {"decision": "ESCALATE"}}),
    )
    with pytest.raises(AuthorizeError, match="missing required fields"):
        asyncio.run(authorize({}, {"run_id": "run-11", "history": _sealed()}))
    assert ledger_db().query(GovernanceLedger).count() == 0


def test_authorize_verdict_without_decision_raises(monkeypatch, ledger_db):
    """Fix-round-1, reviewer finding 2: a `verdict` present but missing its `decision`
    field is not a well-formed policy verdict and must raise, not be recorded with
    `decision=None` as if Governor had genuinely decided something.
    """
    monkeypatch.setattr(
        authorize_tools.httpx, "AsyncClient",
        _client_returning(200, {"minted": False, "verdict": {}}),
    )
    with pytest.raises(AuthorizeError, match="missing required fields"):
        asyncio.run(authorize({}, {"run_id": "run-12", "history": _sealed()}))
    assert ledger_db().query(GovernanceLedger).count() == 0


def test_authorize_reads_target_from_the_sealed_plan(monkeypatch, ledger_db):
    """authorize takes its target from ctx['history']'s seal result, not a hardcoded value."""
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = __import__("json").loads(request.content)
        return httpx.Response(200, json=REFUSAL_BODY)

    monkeypatch.setattr(
        authorize_tools.httpx, "AsyncClient",
        lambda **kw: _RealAsyncClient(transport=httpx.MockTransport(handler), **kw),
    )
    seal_result = {"node": "seal", "type": "tool", "status": "completed",
                   "result": {"success": True, "data": {
                       "sealed": True, "plan": {"target": "memstream"},
                       "plan_hash": "sha256:" + "c" * 64,
                   }}}
    asyncio.run(authorize({}, {"run_id": "run-6", "history": [seal_result]}))
    assert captured["body"]["target"] == "memstream"
    assert captured["body"]["plan"]["requested_actions"][0]["profile"] == "memstream"
    # Fix-round-1 (Minor, reviewer): the plan_hash sent on the wire must actually match the
    # plan sent alongside it, not just look plausible.
    assert captured["body"]["plan_hash"] == canonical_hash(captured["body"]["plan"])


def test_authorize_no_sealed_plan_raises(monkeypatch, ledger_db):
    """No sealed plan in history must raise before any Governor call is even attempted
    (no httpx.AsyncClient patch here on purpose: reaching the network at all would be
    the bug this test exists to catch)."""
    with pytest.raises(AuthorizeError, match="no sealed plan"):
        asyncio.run(authorize({}, {"run_id": "run-7", "history": []}))


def test_ledger_failure_does_not_block_authorize(monkeypatch):
    monkeypatch.setattr(authorize_tools.httpx, "AsyncClient", _client_returning(200, REFUSAL_BODY))
    monkeypatch.setattr(authorize_tools, "_write_ledger", lambda entry: False)
    out = asyncio.run(authorize({}, {"run_id": "run-8", "history": _sealed()}))
    assert out["ok"] is True and out["ledger"] is False  # Review focus 5


def test_ledger_session_creation_failure_is_fail_soft(monkeypatch):
    """Mirrors Phase 2a's own final-review fix: SessionLocal()/rollback must be inside the try."""
    monkeypatch.setattr(authorize_tools.httpx, "AsyncClient", _client_returning(200, REFUSAL_BODY))

    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(authorize_tools, "SessionLocal", boom)
    out = asyncio.run(authorize({}, {"run_id": "run-9", "history": _sealed()}))
    assert out["ok"] is True and out["ledger"] is False


def test_no_docker_import_anywhere_in_this_module():
    """Review focus 1: this module must never be able to touch Docker.

    Fix-round-1: the original `assert "docker" not in src.lower() or "DOCKER" not in src`
    was vacuous — the module's own docstring legitimately says "Docker" in prose, so the
    first clause is always False and the assertion reduces to only `"DOCKER" not in src`,
    which would not catch `import docker`, `docker.from_env()`, or a raw socket-proxy URL
    string. Parse the AST instead: no `Import`/`ImportFrom` node may name anything
    containing "docker" (case-insensitive) — a real code-level check, not a prose scan —
    and independently guard against the specific known danger strings from `recover_tools.py`
    (`docker.`, `import docker`, `docker-socket`, `DOCKER_`) anywhere outside the docstring,
    since the docstring is the one place the word "Docker" is legitimate.
    """
    src = pathlib.Path(authorize_tools.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    module_docstring = ast.get_docstring(tree) or ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "docker" not in alias.name.lower(), f"forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            assert not (node.module and "docker" in node.module.lower()), f"forbidden import: {node.module}"

    src_without_docstring = src.replace(module_docstring, "", 1) if module_docstring else src
    for forbidden in ("docker.", "import docker", "docker-socket", "DOCKER_"):
        assert forbidden not in src_without_docstring, f"forbidden reference: {forbidden!r}"
