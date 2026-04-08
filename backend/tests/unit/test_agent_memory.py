import json
from unittest.mock import MagicMock

import pytest


def _make_redis_mock() -> MagicMock:
    r = MagicMock()
    pipe = MagicMock()
    pipe.rpush.return_value = pipe
    pipe.ltrim.return_value = pipe
    pipe.expire.return_value = pipe
    pipe.execute.return_value = True
    r.pipeline.return_value = pipe
    return r


def test_append_turn_redacts_and_trims(monkeypatch):
    from app.core import agent_memory

    r = _make_redis_mock()
    monkeypatch.setattr(agent_memory, "_get_redis", lambda: r)

    ok = agent_memory.append_turn(
        conversation_id="task-1",
        agent_id="architect",
        role="user",
        content="api_key=supersecret sk-" + ("a" * 24),
        task_id=1,
        tags=["t"],
    )
    assert ok is True

    pipe = r.pipeline.return_value
    assert pipe.rpush.called
    args, _ = pipe.rpush.call_args
    assert args[0] == "memory:conversation:task-1"
    stored = json.loads(args[1])
    assert stored["agent_id"] == "architect"
    assert stored["role"] == "user"
    assert "[REDACTED]" in stored["content"]


def test_get_history_returns_parsed_entries(monkeypatch):
    from app.core import agent_memory

    r = MagicMock()
    r.lrange.return_value = [
        json.dumps({"agent_id": "a", "role": "user", "content": "hi"}),
        json.dumps({"agent_id": "a", "role": "assistant", "content": "yo"}),
    ]
    monkeypatch.setattr(agent_memory, "_get_redis", lambda: r)

    history = agent_memory.get_history("task-2", last_n=2)
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_write_and_consume_handoffs(monkeypatch):
    from app.core import agent_memory

    r = _make_redis_mock()
    r.lrange.return_value = [
        json.dumps({"from_agent_id": "r", "to_agent_id": "a", "summary": "one"}),
        json.dumps({"from_agent_id": "r", "to_agent_id": "a", "summary": "two"}),
    ]
    monkeypatch.setattr(agent_memory, "_get_redis", lambda: r)

    ok = agent_memory.write_handoff("architect", "researcher", "token=NOPE")
    assert ok is True

    notes = agent_memory.read_handoffs("architect", limit=2, consume=True)
    assert len(notes) == 2
    assert notes[0]["summary"] == "one"

    pipe = r.pipeline.return_value
    assert pipe.ltrim.called


@pytest.mark.asyncio
async def test_brain_memory_block_order(monkeypatch):
    from app.agents.brain import Brain

    def read_handoffs(agent_id: str, limit: int = 5, consume: bool = False):
        return [{"from_agent_id": "researcher", "summary": "handoff"}]

    def get_history(conversation_id: str, last_n: int = 10):
        return [{"agent_id": "architect", "role": "user", "content": "prior"}]

    import app.core.agent_memory as am
    monkeypatch.setattr(am, "read_handoffs", read_handoffs)
    monkeypatch.setattr(am, "get_history", get_history)

    b = Brain()
    out = b._build_memory_context(
        conversation_id="task-9",
        agent_id="architect",
        memory_mode="shared",
        rag_context="--- Semantic Memory (RAG) ---\nrag",
    )

    first = out.find("Handoff Notes")
    second = out.find("Semantic Memory")
    third = out.find("Conversation History")
    assert first != -1 and second != -1 and third != -1
    assert first < second < third
