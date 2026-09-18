from __future__ import annotations

import asyncio
import os
import sys
import uuid
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

_AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

from skills import (  # noqa: E402
    BACKEND_SPECIALIST_SKILLS,
    curate_skills_for_registration,
    validate_skill_entry,
)


def _null_logger() -> Any:
    m = MagicMock()
    m.info = MagicMock()
    m.warning = MagicMock()
    m.error = MagicMock()
    m.exception = MagicMock()
    return m


# ----------------------------------------------------------------------------
# Task 1: validator tests (TR-1.1, TR-1.2, TR-1.3)
# ----------------------------------------------------------------------------
def test_all_curated_backend_skills_pass_validation() -> None:
    """TR-1.1: every entry in BACKEND_SPECIALIST_SKILLS passes validator."""
    for idx, skill in enumerate(BACKEND_SPECIALIST_SKILLS):
        errors = validate_skill_entry(skill)
        assert errors == [], f"skill #{idx} id={skill.get('skill_id')!r} errors: {errors}"
    assert len(BACKEND_SPECIALIST_SKILLS) >= 6


@pytest.mark.parametrize(
    "mutator,expected_error_substring",
    [
        (lambda s: dict(s, category="bogus_category_xyz"), "invalid category"),
        (lambda s: dict(s, skill_id=""), "required key 'skill_id' is empty"),
        (lambda s: dict(s, inputs=["not", "a", "dict"]), "inputs must be dict"),
        (lambda s: {k: v for k, v in s.items() if k != "outputs"}, "missing required key: outputs"),
    ],
    ids=[
        "invalid-category",
        "empty-skill-id",
        "inputs-list-not-dict",
        "missing-outputs-key",
    ],
)
def test_validate_skill_entry_rejects_invalid(mutator, expected_error_substring) -> None:
    """TR-1.2: 4 specific invalid-mutation cases each return >=1 error."""
    original = BACKEND_SPECIALIST_SKILLS[0]
    mutated = mutator(original)
    errors = validate_skill_entry(mutated)
    assert len(errors) >= 1, f"expected >=1 error for {mutated}"
    assert any(expected_error_substring in e for e in errors), (
        f"no error matched {expected_error_substring!r} in {errors}"
    )


def test_curate_skills_drops_invalid_and_counts_correctly() -> None:
    """TR-1.3: mixed list -> valid_batch + dropped_invalid counts match."""
    good1, good2 = BACKEND_SPECIALIST_SKILLS[0], BACKEND_SPECIALIST_SKILLS[1]
    bad1 = dict(good1, category="does_not_exist")
    bad2 = dict(good2, skill_id="")
    mixed: List[Dict[str, Any]] = [good1, bad1, good2, bad2]

    valid, dropped = curate_skills_for_registration(mixed, _null_logger())
    assert len(valid) == 2
    assert len(dropped) == 2
    assert [s["skill_id"] for s in valid] == [good1["skill_id"], good2["skill_id"]]
    assert dropped[0]["reasons"], "first drop must have reasons list"


# ----------------------------------------------------------------------------
# Task 2: retry + skip + degraded state logic in agent.py (TR-2.1..2.6)
# ----------------------------------------------------------------------------
def _make_agent_with_stubs(monkeypatch) -> Any:
    """Return a BackendSpecialist instance ready for initialize() with stubs."""
    monkeypatch.setenv("SKILLWEAVER_SKIP_REGISTER", "")
    monkeypatch.setenv("SKILLWEAVER_URL", "http://skillweaver:8051")

    import agent as agent_mod

    sw_client_cls = MagicMock()
    reg_agent_skills = AsyncMock()

    monkeypatch.setattr(agent_mod, "SkillWeaverClient", sw_client_cls)
    monkeypatch.setattr(agent_mod, "register_agent_skills", reg_agent_skills)

    sw_client = MagicMock()
    sw_client.close = AsyncMock()
    sw_client_cls.return_value = sw_client

    agent_inst = agent_mod.BackendSpecialist()
    # _install_health_override may need routes. FastAPI app is already there.
    # Attach stubs to instance so callers can assert.
    agent_inst._sw_client_cls = sw_client_cls
    agent_inst._reg_agent_skills = reg_agent_skills
    agent_inst._sw_client = sw_client
    return agent_inst


@pytest.mark.asyncio
async def test_skip_register_env_skips_http_and_marks_unattempted(monkeypatch) -> None:
    """TR-2.1: SKILLWEAVER_SKIP_REGISTER=true -> zero HTTP, status unattempted."""
    monkeypatch.setenv("SKILLWEAVER_SKIP_REGISTER", "true")
    monkeypatch.setenv("SKILLWEAVER_URL", "http://skillweaver:8051")

    import agent as agent_mod

    sw_client_cls = MagicMock()
    reg_agent_skills = AsyncMock()
    monkeypatch.setattr(agent_mod, "SkillWeaverClient", sw_client_cls)
    monkeypatch.setattr(agent_mod, "register_agent_skills", reg_agent_skills)

    agent_inst = agent_mod.BackendSpecialist()
    start_state = dict(agent_inst._skillweaver_state)
    await agent_inst.initialize()
    end_state = dict(agent_inst._skillweaver_state)

    assert sw_client_cls.call_count == 0, "no SkillWeaverClient constructed"
    assert reg_agent_skills.call_count == 0, "no register_agent_skills call"
    assert end_state["status"] == "unattempted", end_state
    assert start_state["status"] == "unattempted"  # default


@pytest.mark.asyncio
async def test_retry_fires_once_on_503_then_succeeds(monkeypatch) -> None:
    """TR-2.2: call count = 2 when 503 once then 200 ok; status=ok."""
    agent_inst = _make_agent_with_stubs(monkeypatch)
    reg = agent_inst._reg_agent_skills

    call_count = {"n": 0}

    async def _side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            req = httpx.Request("POST", "http://skillweaver:8051/api/v1/skills/register_batch")
            resp = httpx.Response(503, request=req)
            raise httpx.HTTPStatusError("503", request=req, response=resp)
        return ["execute_backend_plan", "generate_api_endpoint", "db_plan"]

    reg.side_effect = _side_effect
    sleep_mock = AsyncMock()
    monkeypatch.setattr("agent.asyncio.sleep", sleep_mock)

    await agent_inst.initialize()

    assert reg.call_count == 2, f"expected retry=2 calls, got {reg.call_count}"
    assert sleep_mock.call_count == 1, f"expected one sleep (between attempts), got {sleep_mock.call_count}"
    assert agent_inst._skillweaver_state["status"] == "ok", agent_inst._skillweaver_state
    assert agent_inst._skillweaver_state["registered_count"] == 3
    # Validate sleep shape: 2 seconds for first retry (2^0 * base=2)
    first_sleep_arg = sleep_mock.call_args_list[0].args[0]
    assert 1.9 <= first_sleep_arg <= 2.1, f"expected 2s first backoff, got {first_sleep_arg}"


@pytest.mark.asyncio
async def test_four_consecutive_503_degrades_gracefully_no_raise(monkeypatch) -> None:
    """TR-2.3: 4 consecutive 503 -> no exception, status degraded, r=0."""
    agent_inst = _make_agent_with_stubs(monkeypatch)
    reg = agent_inst._reg_agent_skills

    async def _side_effect(*args, **kwargs):
        req = httpx.Request("POST", "http://skillweaver:8051/api/v1/skills/register_batch")
        resp = httpx.Response(503, request=req)
        raise httpx.HTTPStatusError("503", request=req, response=resp)

    reg.side_effect = _side_effect
    sleep_mock = AsyncMock()
    monkeypatch.setattr("agent.asyncio.sleep", sleep_mock)

    # Must NOT raise to caller (graceful degradation)
    await agent_inst.initialize()

    assert reg.call_count == 4, f"expected 4 attempts, got {reg.call_count}"
    assert sleep_mock.call_count == 3, f"expected 3 sleeps between 4 attempts, got {sleep_mock.call_count}"
    state = agent_inst._skillweaver_state
    assert state["status"] == "degraded", state
    assert state["registered_count"] == 0
    assert state["attempted_count"] == 6  # BACKEND_SPECIALIST_SKILLS has 6 valid
    assert state["last_error"] == "HTTPStatusError"


@pytest.mark.asyncio
async def test_400_is_not_retried_even_once(monkeypatch) -> None:
    """Retry logic sanity: 4xx (non-429) MUST NOT retry per spec."""
    agent_inst = _make_agent_with_stubs(monkeypatch)
    reg = agent_inst._reg_agent_skills

    async def _side_effect(*args, **kwargs):
        req = httpx.Request("POST", "http://skillweaver:8051/api/v1/skills/register_batch")
        resp = httpx.Response(400, request=req)
        raise httpx.HTTPStatusError("400", request=req, response=resp)

    reg.side_effect = _side_effect
    sleep_mock = AsyncMock()
    monkeypatch.setattr("agent.asyncio.sleep", sleep_mock)

    await agent_inst.initialize()
    assert reg.call_count == 1, f"400 must not retry. calls={reg.call_count}"
    assert sleep_mock.call_count == 0
    assert agent_inst._skillweaver_state["status"] == "degraded"


def test_retry_constant_shape_matches_spec() -> None:
    """Sanity: retry constants meet spec (4 attempts max, base=2, max_sleep=8)."""
    import agent as agent_mod
    assert agent_mod._SKILLWEAVER_MAX_ATTEMPTS == 4
    assert agent_mod._SKILLWEAVER_BASE_SLEEP_SECONDS == 2.0
    assert agent_mod._SKILLWEAVER_MAX_SLEEP_SECONDS == 8.0
    assert agent_mod._SKILLWEAVER_STARTUP_CEILING_SECONDS == 45


# ----------------------------------------------------------------------------
# Health override shape (AC-2 rule: skillweaver object in /health response)
# ----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_health_endpoint_includes_skillweaver_subobject(monkeypatch) -> None:
    """Always: /health returns {skillweaver: {...}} with 4 required fields."""
    monkeypatch.setenv("SKILLWEAVER_SKIP_REGISTER", "true")
    import agent as agent_mod
    from fastapi.testclient import TestClient

    agent_inst = agent_mod.BackendSpecialist()
    with TestClient(agent_inst.app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "skillweaver" in body, body
    sw = body["skillweaver"]
    for key in ("registered_count", "attempted_count", "status", "last_error"):
        assert key in sw, f"missing key {key!r} in health.skillweaver: {sw}"
    assert isinstance(sw["registered_count"], int)
    assert sw["status"] in {"ok", "degraded", "unattempted"}


# ----------------------------------------------------------------------------
# Task 5 integration: live SkillWeaver round-trip
# ----------------------------------------------------------------------------
@pytest.mark.skipif(
    not os.getenv("TEST_SKILLWEAVER_URL"),
    reason="TEST_SKILLWEAVER_URL not set — run with SkillWeaver container reachable",
)
@pytest.mark.asyncio
async def test_end_to_end_register_then_deregister() -> None:
    """FR-10 integration: register curated skills, confirm in /list, deregister, confirm gone."""
    try:
        from shared.skillweaver_sdk import (  # type: ignore
            SkillWeaverClient,
            register_agent_skills,
        )
    except ModuleNotFoundError:
        # Host-side fallback (container only has /app/shared mount). If
        # services.skillweaver.sdk is importable via repo root in PYTHONPATH
        # we use that; otherwise re-raise with a clearer diagnostic.
        _repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        for _candidate in (_repo_root, os.path.join(_repo_root, "services")):
            if _candidate not in sys.path:
                sys.path.insert(0, _candidate)
        try:
            from skillweaver.sdk import (  # type: ignore
                SkillWeaverClient,
                register_agent_skills,
            )
        except ModuleNotFoundError as exc:
            raise AssertionError(
                "Cannot import SkillWeaver SDK. Inside containers the shared "
                "volume exposes it as `shared.skillweaver_sdk`. On the host, "
                "add the HyperCode-V2.4 root or services/ dir to PYTHONPATH "
                "so `skillweaver.sdk` can import from services/skillweaver/sdk.py."
            ) from exc

    base_url = os.environ["TEST_SKILLWEAVER_URL"].rstrip("/")
    agent_id = f"backend-specialist-test-{uuid.uuid4().hex[:10]}"

    valid, dropped = curate_skills_for_registration(
        list(BACKEND_SPECIALIST_SKILLS),
        _null_logger(),
    )
    assert dropped == []
    assert len(valid) == 6

    # Use a generous timeout here because the staging SkillWeaver server on
    # Windows Docker mounts can be slow on write-heavy calls. The production
    # agent path uses the shared SDK default timeout + retry.
    client = SkillWeaverClient(base_url, timeout=60.0)
    try:
        h = await client.health()
        assert h.get("status") == "healthy", h

        registered = await register_agent_skills(client, agent_id, valid, best_effort=False)
        assert len(registered) == 6, f"all 6 should register, got {registered}"

        # NOTE: the running SkillWeaver server has a route-ordering quirk where
        # GET /api/v1/skills/{skill_id} is registered before /list, so the
        # literal word "list" gets captured as a path param. For this test we
        # verify the 6 skills exist via /stats skills_by_agent bucket, then
        # individually GET each real skill_id (as returned by the SDK — those
        # never collide with a route literal).
        stats = await client.stats()
        by_agent = stats.get("skills_by_agent", {})
        assert by_agent.get(agent_id) == 6, f"stats skills_by_agent wrong: {stats}"

        got_back_names = []
        for actual_skill_id in registered:
            fetched = await client.get_skill(actual_skill_id)
            assert fetched.get("skill_id") == actual_skill_id
            assert fetched.get("agent_id") == agent_id
            got_back_names.append(fetched.get("name"))
        assert len(got_back_names) == 6

        removed = await client.deregister_agent(agent_id)
        assert removed.get("removed", 0) == 6, removed

        # After deregister, the agent_id bucket should be gone or zero in stats.
        stats2 = await client.stats()
        after_bucket = stats2.get("skills_by_agent", {}).get(agent_id, 0)
        assert after_bucket == 0, f"after deregister bucket should be empty: {stats2}"
    finally:
        await client.close()
