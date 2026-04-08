import pytest


class _BrainStub:
    def __init__(self, planner: str, coder_by_title: dict[str, str], review: str):
        self._planner = planner
        self._coder_by_title = coder_by_title
        self._review = review
        self.calls: list[tuple[str, str]] = []

    async def think(self, role: str, prompt: str, use_memory: bool = False, **kwargs) -> str:
        self.calls.append((role, prompt))
        if role == "Planner Agent":
            return self._planner
        if role == "Reviewer Agent":
            return self._review
        if role == "Coder Agent":
            for title, code in self._coder_by_title.items():
                if f"Task: {title}\n" in prompt:
                    return code
            return "print('default')"
        return "unknown"


@pytest.mark.asyncio
async def test_architect_process_happy_path_with_archive(monkeypatch):
    import app.agents.architect as architect_mod
    from app.agents.architect import ArchitectAgent

    planner = """
```json
[
  {"title": "Step A", "description": "Do A"},
  {"title": "Step B", "description": "Do B"}
]
```
""".strip()
    brain_stub = _BrainStub(planner=planner, coder_by_title={"Step A": "print('A')", "Step B": "print('B')"}, review="PASS")

    class DummyStorage:
        def upload_file(self, file_content: str, filename: str, metadata: dict):
            return "agent-reports/" + filename

    monkeypatch.setattr(architect_mod, "brain", brain_stub)
    monkeypatch.setattr(architect_mod, "get_storage", lambda: DummyStorage())

    agent = ArchitectAgent()
    report = await agent.process("Ship it", context={"task_id": "t-1"})

    assert "Multi-Agent Build Report: Ship it" in report
    assert "Step 1: Step A" in report
    assert "Step 2: Step B" in report
    assert "PASS" in report
    assert "Archived in MinIO" in report


@pytest.mark.asyncio
async def test_architect_process_plan_parse_failure_falls_back(monkeypatch):
    import app.agents.architect as architect_mod
    from app.agents.architect import ArchitectAgent

    brain_stub = _BrainStub(planner="not json", coder_by_title={"Execute Goal": "print('x')"}, review="OK")
    monkeypatch.setattr(architect_mod, "brain", brain_stub)
    monkeypatch.setattr(architect_mod, "get_storage", lambda: object())

    agent = ArchitectAgent()
    report = await agent.process("Goal", context=None)

    assert "Execute Goal" in report
    assert "OK" in report


@pytest.mark.asyncio
async def test_architect_process_archive_upload_failure_does_not_append(monkeypatch):
    import app.agents.architect as architect_mod
    from app.agents.architect import ArchitectAgent

    planner = '[{"title": "Step A", "description": "Do A"}]'
    brain_stub = _BrainStub(planner=planner, coder_by_title={"Step A": "print('A')"}, review="PASS")

    class DummyStorage:
        def upload_file(self, file_content: str, filename: str, metadata: dict):
            raise RuntimeError("minio down")

    monkeypatch.setattr(architect_mod, "brain", brain_stub)
    monkeypatch.setattr(architect_mod, "get_storage", lambda: DummyStorage())

    agent = ArchitectAgent()
    report = await agent.process("Ship it", context={"task_id": "t-1"})

    assert "Archived in MinIO" not in report
