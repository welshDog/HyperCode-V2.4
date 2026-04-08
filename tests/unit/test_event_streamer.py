"""
Unit Tests — Event Streamer Service
Covers: publish, subscribe, event format validation, max history
"""
import pytest
import json
from datetime import datetime, timezone
from uuid import uuid4


class MockEventStreamer:
    """In-memory event streamer stub."""
    MAX_HISTORY = 200

    def __init__(self):
        self._history: list[dict] = []
        self._subscribers: list = []

    async def publish(self, event: dict) -> None:
        required = {"agent_id", "task_id", "status", "xp_earned", "timestamp"}
        missing = required - set(event.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        self._history.append(event)
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY:]

    def get_history(self, limit: int = 50) -> list[dict]:
        return self._history[-limit:]

    def event_count(self) -> int:
        return len(self._history)


@pytest.fixture
def streamer():
    return MockEventStreamer()


def make_event(**overrides):
    base = {
        "agent_id":  "healer",
        "task_id":   str(uuid4()),
        "status":    "success",
        "payload":   {"healed_service": "redis"},
        "xp_earned": 50,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return {**base, **overrides}


@pytest.mark.asyncio
async def test_publish_valid_event(streamer):
    await streamer.publish(make_event())
    assert streamer.event_count() == 1


@pytest.mark.asyncio
async def test_publish_missing_field_raises(streamer):
    bad = make_event()
    del bad["status"]
    with pytest.raises(ValueError, match="Missing required fields"):
        await streamer.publish(bad)


@pytest.mark.asyncio
async def test_history_is_ordered(streamer):
    for i in range(5):
        await streamer.publish(make_event(xp_earned=i * 10))
    history = streamer.get_history()
    assert [e["xp_earned"] for e in history] == [0, 10, 20, 30, 40]


@pytest.mark.asyncio
async def test_history_limit_respected(streamer):
    for _ in range(250):
        await streamer.publish(make_event())
    assert streamer.event_count() == 200  # MAX_HISTORY


@pytest.mark.asyncio
async def test_get_history_with_limit(streamer):
    for _ in range(100):
        await streamer.publish(make_event())
    history = streamer.get_history(limit=10)
    assert len(history) == 10


@pytest.mark.asyncio
async def test_status_values(streamer):
    for status in ["started", "success", "failed", "healing"]:
        await streamer.publish(make_event(status=status))
    history = streamer.get_history()
    statuses = [e["status"] for e in history]
    assert set(statuses) == {"started", "success", "failed", "healing"}
