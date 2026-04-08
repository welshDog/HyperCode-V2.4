import pytest


class _BrainStub:
    def __init__(self, content: str):
        self._content = content
        self.calls: list[tuple[str, str]] = []

    async def think(self, role: str, prompt: str, use_memory: bool = False, **kwargs) -> str:
        self.calls.append((role, prompt))
        return self._content


@pytest.mark.asyncio
async def test_researcher_process_archives_when_storage_returns_key(monkeypatch):
    import app.agents.researcher as researcher_mod
    from app.agents.researcher import ResearchAgent

    brain_stub = _BrainStub("report")

    class DummyStorage:
        def upload_file(self, file_content: str, filename: str, metadata: dict):
            return "agent-reports/" + filename

    monkeypatch.setattr(researcher_mod, "brain", brain_stub)
    monkeypatch.setattr(researcher_mod, "get_storage", lambda: DummyStorage())

    agent = ResearchAgent()
    result = await agent.process("topic", context={"task_id": "t1"})
    assert result.startswith("report")
    assert "Archived in MinIO" in result


@pytest.mark.asyncio
async def test_researcher_process_handles_upload_exception(monkeypatch):
    import app.agents.researcher as researcher_mod
    from app.agents.researcher import ResearchAgent

    brain_stub = _BrainStub("report")

    class DummyStorage:
        def upload_file(self, file_content: str, filename: str, metadata: dict):
            raise RuntimeError("minio down")

    monkeypatch.setattr(researcher_mod, "brain", brain_stub)
    monkeypatch.setattr(researcher_mod, "get_storage", lambda: DummyStorage())

    agent = ResearchAgent()
    result = await agent.process("topic", context={"task_id": "t1"})
    assert "Archive Error" in result
    assert "minio down" in result


@pytest.mark.asyncio
async def test_researcher_process_writes_handoff_when_conversation_id_present(monkeypatch):
    import app.agents.researcher as researcher_mod
    from app.agents.researcher import ResearchAgent

    brain_stub = _BrainStub("report")

    class DummyStorage:
        def upload_file(self, file_content: str, filename: str, metadata: dict):
            return "agent-reports/" + filename

    captured: dict = {}

    def write_handoff(to_agent_id: str, from_agent_id: str, summary: str, links=None):
        captured["to_agent_id"] = to_agent_id
        captured["from_agent_id"] = from_agent_id
        captured["summary"] = summary
        captured["links"] = links
        return True

    monkeypatch.setattr(researcher_mod, "brain", brain_stub)
    monkeypatch.setattr(researcher_mod, "get_storage", lambda: DummyStorage())
    import app.core.agent_memory as am
    monkeypatch.setattr(am, "write_handoff", write_handoff)

    agent = ResearchAgent()
    result = await agent.process("topic", context={"task_id": "t1"}, conversation_id="task-t1")
    assert result.startswith("report")
    assert captured["to_agent_id"] == "architect"
    assert captured["from_agent_id"] == "researcher"
    assert "conversation_id: task-t1" in captured["summary"]
