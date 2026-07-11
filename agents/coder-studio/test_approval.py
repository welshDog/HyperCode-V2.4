"""Unit tests for the Approval primitive — the race-safety core of the
interactive ESCALATE gate. settle() must be atomic and first-wins."""

from __future__ import annotations

import asyncio

from sessions import Approval, ApprovalState, Session


def _approval() -> Approval:
    return Approval(
        id="ap_1", tool_name="Write", target="app.py", rule="unknown_tool",
        reason="needs a human", expires_at="2026-07-11T09:35:00Z",
    )


async def test_settle_records_the_decision_and_sets_the_event():
    ap = _approval()
    assert ap.status is ApprovalState.PENDING
    assert not ap.event.is_set()

    result = await ap.settle(ApprovalState.APPROVED)

    assert result is ApprovalState.APPROVED
    assert ap.status is ApprovalState.APPROVED
    assert ap.event.is_set()


async def test_first_settle_wins_second_is_a_noop():
    ap = _approval()

    first = await ap.settle(ApprovalState.APPROVED)
    second = await ap.settle(ApprovalState.DENIED)

    assert first is ApprovalState.APPROVED
    assert second is ApprovalState.APPROVED   # returns the settled state, no overwrite
    assert ap.status is ApprovalState.APPROVED


async def test_concurrent_settles_produce_exactly_one_winner():
    ap = _approval()

    results = await asyncio.gather(
        ap.settle(ApprovalState.APPROVED),
        ap.settle(ApprovalState.DENIED),
        ap.settle(ApprovalState.DISCARDED),
    )

    # Every caller sees the same settled status; the event is set once.
    assert len(set(results)) == 1
    assert ap.status in (ApprovalState.APPROVED, ApprovalState.DENIED, ApprovalState.DISCARDED)
    assert ap.event.is_set()


def test_session_starts_with_an_empty_approval_registry():
    s = Session(id="cs_x", prompt="do a thing")
    assert s.pending_approvals == {}
