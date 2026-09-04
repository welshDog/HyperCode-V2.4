import fakeredis.aioredis
import pytest

import approvals
import redis_state


@pytest.fixture
def fake(monkeypatch):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    return r


async def _approve(mid, who, ph="sha256:p"):
    return await approvals.record(
        mission_id=mid, plan_hash=ph, approver_id=who, decision="approved", reason="ok"
    )


@pytest.mark.asyncio
async def test_reversible_needs_one(fake):
    assert await approvals.satisfied(
        mission_id="m1", plan_hash="sha256:p", proposer_id="mission-director", risk_class="REVERSIBLE_ACTION"
    ) is None
    await _approve("m1", "alice")
    assert await approvals.satisfied(
        mission_id="m1", plan_hash="sha256:p", proposer_id="mission-director", risk_class="REVERSIBLE_ACTION"
    ) is not None


@pytest.mark.asyncio
async def test_dangerous_needs_two_distinct(fake):
    await _approve("m2", "alice")
    assert await approvals.satisfied(
        mission_id="m2", plan_hash="sha256:p", proposer_id="bob", risk_class="INFRASTRUCTURE_MUTATION"
    ) is None
    await _approve("m2", "alice")  # same person again — still 1 distinct
    assert await approvals.satisfied(
        mission_id="m2", plan_hash="sha256:p", proposer_id="bob", risk_class="INFRASTRUCTURE_MUTATION"
    ) is None
    await _approve("m2", "carol")
    assert await approvals.satisfied(
        mission_id="m2", plan_hash="sha256:p", proposer_id="bob", risk_class="INFRASTRUCTURE_MUTATION"
    ) is not None


@pytest.mark.asyncio
async def test_proposer_never_counts(fake):
    await _approve("m3", "alice")
    await _approve("m3", "dave")
    assert await approvals.satisfied(
        mission_id="m3", plan_hash="sha256:p", proposer_id="dave", risk_class="INFRASTRUCTURE_MUTATION"
    ) is None  # only alice counts


@pytest.mark.asyncio
async def test_plan_hash_must_match(fake):
    await _approve("m4", "alice", ph="sha256:OLD")
    assert await approvals.satisfied(
        mission_id="m4", plan_hash="sha256:NEW", proposer_id="bob", risk_class="REVERSIBLE_ACTION"
    ) is None
