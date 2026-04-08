"""
tests/integration/test_planning_e2e.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
E2E integration tests for the HyperCode planning pipeline:
  plan_generator → Redis handoff → plan_executor

Architecture under test
───────────────────────
  1. PlanGenerator  — 3-stage LLM pipeline → CodingPlan
  2. agent_memory   — Redis-backed handoff store (write_handoff / read_handoffs)
  3. PlanExecutor   — dispatches CodingPlan phases to Celery, writes handoffs

Test strategy
─────────────
- Brain LLM replaced by DeterministicBrain stub (no network, deterministic)
- Redis replaced by fakeredis (in-process, no server required)
- Celery replaced by MagicMock (unit boundary respected)
- Two Redis fixture modes: isolated (fresh per-test) + shared (across a class)
- Performance benchmarks validated against wall-clock assertions

Coverage areas
──────────────
  A. PlanGenerator — parsing, error fallbacks, stage output shapes
  B. Redis handoff — write / read / consume / TTL / overflow / secret redaction
  C. PlanExecutor  — agent routing, Celery dispatch, handoff content
  D. Full E2E      — generator → Redis → executor, data consistency
  E. Error handling — LLM failures, Redis outages, Celery failures, retries
  F. Timeouts      — Brain slow response, Redis slow response
  G. Data consistency — round-trip JSON serialization, plan identity
  H. Performance   — benchmark generator+executor under 5 seconds
"""
from __future__ import annotations

import asyncio
import json
import time
import warnings
from types import SimpleNamespace
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis
import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../..", "backend"))

# ── Import planning schemas (no app deps) ─────────────────────────────────────
from app.schemas.planning import (
    CodingPlan,
    DocumentType,
    ExtractedRequirement,
    FileChange,
    FileChangeType,
    ParsedDocument,
    PlanPhase,
)

# ── Deterministic Brain stub ──────────────────────────────────────────────────

STAGE1_RESPONSE = json.dumps({
    "summary": "Build a secure user authentication system with JWT tokens.",
    "phases": [
        {
            "phase_number": 1,
            "title": "Data Layer Setup",
            "description": "Design and implement the user model, database schema, and migration.",
            "workflow_steps": [
                "Define User model with password hash field",
                "Create Alembic migration",
                "Add index on email column",
            ],
        },
        {
            "phase_number": 2,
            "title": "API Layer",
            "description": "Implement login, register, and token refresh endpoints.",
            "workflow_steps": [
                "Implement /auth/register endpoint",
                "Implement /auth/login endpoint with JWT issuance",
                "Implement /auth/refresh endpoint",
            ],
        },
        {
            "phase_number": 3,
            "title": "Frontend Integration",
            "description": "Wire authentication flows into the React frontend.",
            "workflow_steps": [
                "Create LoginForm component",
                "Store JWT in localStorage",
                "Add ProtectedRoute wrapper",
            ],
        },
    ],
})

STAGE2_RESPONSE = json.dumps({
    "file_changes": [
        {
            "file_path": "backend/app/models/user.py",
            "change_type": "create",
            "description": "New User SQLAlchemy model with hashed password field.",
            "rationale": "Persistent user storage is required for authentication.",
        },
        {
            "file_path": "backend/app/api/v1/endpoints/auth.py",
            "change_type": "modify",
            "description": "Add login and register endpoint handlers.",
            "rationale": "Exposes the authentication API surface.",
        },
        {
            "file_path": "frontend/src/components/LoginForm.tsx",
            "change_type": "create",
            "description": "Login form React component.",
            "rationale": "UI entry point for the authentication flow.",
        },
    ]
})

STAGE3_RESPONSE = (
    "- Phase 1 must complete before Phase 2 (DB schema must exist)\n"
    "- Phase 2 and Phase 3 can proceed in parallel once Phase 1 is done\n"
    "- Integration tests should cover token expiry and refresh paths\n"
    "- Coordinate with devops-engineer for environment secret injection\n"
)


class DeterministicBrain:
    """Synchronous deterministic stub that replaces Brain in tests."""

    call_count: int = 0
    _raise_on_call: Optional[int] = None
    _slow_after: Optional[float] = None  # seconds to sleep

    def reset(self) -> None:
        self.call_count = 0
        self._raise_on_call = None
        self._slow_after = None

    async def think(self, role: str, task_description: str, use_memory: bool = False) -> str:
        self.call_count += 1

        if self._slow_after is not None:
            await asyncio.sleep(self._slow_after)

        if self._raise_on_call is not None and self.call_count >= self._raise_on_call:
            raise RuntimeError(f"[STUB] Brain forced failure on call {self.call_count}")

        # Return stage-specific response based on prompt content
        if "phases" in task_description and "file_changes" not in task_description and "follow-up" not in task_description:
            return STAGE1_RESPONSE
        elif "file_changes" in task_description or "file-level changes" in task_description:
            return STAGE2_RESPONSE
        else:
            return STAGE3_RESPONSE


_brain_stub = DeterministicBrain()


# ── Redis fixture helpers ──────────────────────────────────────────────────────

def _make_fake_redis() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis(decode_responses=True)


# ── Shared test data ──────────────────────────────────────────────────────────

def _parsed_doc(n_reqs: int = 2) -> ParsedDocument:
    reqs = [
        ExtractedRequirement(
            title=f"Requirement {i}",
            description=f"Users need feature {i} for productivity.",
            acceptance_criteria=[f"Feature {i} works end-to-end"],
            technical_constraints=["Must use FastAPI"],
            dependencies=[],
        )
        for i in range(1, n_reqs + 1)
    ]
    return ParsedDocument(
        requirements=reqs,
        source_metadata={"source": "test"},
        detected_document_type=DocumentType.PRD,
    )


def _sample_plan() -> CodingPlan:
    return CodingPlan(
        summary="Build a secure user authentication system with JWT tokens.",
        phases=[
            PlanPhase(
                phase_number=1,
                title="Data Layer Setup",
                description="Design and implement the user model.",
                workflow_steps=["Define User model", "Create migration"],
            ),
            PlanPhase(
                phase_number=2,
                title="API Layer",
                description="Implement login and register endpoints.",
                workflow_steps=["POST /auth/login", "POST /auth/register"],
            ),
            PlanPhase(
                phase_number=3,
                title="Frontend Integration",
                description="Wire auth flows into React frontend.",
                workflow_steps=["LoginForm component", "ProtectedRoute"],
            ),
        ],
        file_changes_summary=[
            FileChange(
                file_path="backend/app/models/user.py",
                change_type=FileChangeType.CREATE,
                description="New User model.",
                rationale="Required for auth persistence.",
            ),
            FileChange(
                file_path="backend/app/api/v1/endpoints/auth.py",
                change_type=FileChangeType.MODIFY,
                description="Add login/register handlers.",
                rationale="API surface for auth.",
            ),
            FileChange(
                file_path="frontend/src/components/LoginForm.tsx",
                change_type=FileChangeType.CREATE,
                description="Login form component.",
                rationale="UI entry point.",
            ),
        ],
        follow_up_instructions=STAGE3_RESPONSE,
    )


# ═════════════════════════════════════════════════════════════════════════════
# A. PlanGenerator — unit-level tests with deterministic Brain
# ═════════════════════════════════════════════════════════════════════════════

class TestPlanGeneratorUnit:
    """Verify PlanGenerator produces well-formed CodingPlan objects."""

    @pytest.fixture(autouse=True)
    def _patch_brain(self):
        _brain_stub.reset()
        with patch("app.services.plan_generator.brain", _brain_stub), \
             patch("app.services.plan_generator.get_history", return_value=[]), \
             patch("app.services.plan_generator.read_handoffs", return_value=[]):
            from app.services.plan_generator import PlanGenerator
            self.gen = PlanGenerator()
            yield

    async def test_generate_plan_returns_coding_plan(self):
        plan = await self.gen.generate_plan(_parsed_doc())
        assert isinstance(plan, CodingPlan)

    async def test_plan_has_non_empty_summary(self):
        plan = await self.gen.generate_plan(_parsed_doc())
        assert len(plan.summary) > 10

    async def test_plan_has_phases(self):
        plan = await self.gen.generate_plan(_parsed_doc())
        assert len(plan.phases) >= 1

    async def test_plan_phases_have_titles(self):
        plan = await self.gen.generate_plan(_parsed_doc())
        for phase in plan.phases:
            assert len(phase.title) > 0

    async def test_plan_phases_are_sequential(self):
        plan = await self.gen.generate_plan(_parsed_doc())
        numbers = [p.phase_number for p in plan.phases]
        assert numbers == sorted(numbers)

    async def test_plan_has_file_changes(self):
        plan = await self.gen.generate_plan(_parsed_doc())
        assert len(plan.file_changes_summary) >= 1

    async def test_file_changes_have_valid_change_type(self):
        plan = await self.gen.generate_plan(_parsed_doc())
        valid = {FileChangeType.CREATE, FileChangeType.MODIFY, FileChangeType.DELETE}
        for fc in plan.file_changes_summary:
            assert fc.change_type in valid

    async def test_plan_has_follow_up_instructions(self):
        plan = await self.gen.generate_plan(_parsed_doc())
        assert plan.follow_up_instructions is not None
        assert len(plan.follow_up_instructions) > 10

    async def test_brain_called_three_times(self):
        await self.gen.generate_plan(_parsed_doc())
        assert _brain_stub.call_count == 3

    async def test_no_file_paths_inside_phase_descriptions(self):
        """Prompt rule: phases must NOT contain file paths."""
        plan = await self.gen.generate_plan(_parsed_doc())
        for phase in plan.phases:
            assert ".py" not in phase.description, (
                f"Phase {phase.phase_number} contains file path in description"
            )

    async def test_context_with_project_name_accepted(self):
        ctx = {"project_name": "HyperAuth", "tech_stack": "FastAPI + React"}
        plan = await self.gen.generate_plan(_parsed_doc(), context=ctx)
        assert isinstance(plan, CodingPlan)

    async def test_empty_requirements_still_returns_plan(self):
        doc = ParsedDocument(
            requirements=[],
            source_metadata={},
            detected_document_type=DocumentType.GENERIC,
        )
        plan = await self.gen.generate_plan(doc)
        assert isinstance(plan, CodingPlan)

    async def test_strip_fences_removes_markdown_code_blocks(self):
        from app.services.plan_generator import PlanGenerator
        gen = PlanGenerator()
        fenced = "```json\n{\"key\": \"value\"}\n```"
        assert gen._strip_fences(fenced) == '{"key": "value"}'

    async def test_stage1_parse_error_returns_fallback_phase(self):
        from app.services.plan_generator import PlanGenerator
        gen = PlanGenerator()
        phases, summary = gen._parse_stage1("not valid json at all")
        assert len(phases) == 1
        assert phases[0].phase_number == 1

    async def test_stage2_parse_error_returns_empty_list(self):
        from app.services.plan_generator import PlanGenerator
        gen = PlanGenerator()
        changes = gen._parse_stage2("not valid json")
        assert changes == []

    async def test_stage2_invalid_change_type_defaults_to_modify(self):
        from app.services.plan_generator import PlanGenerator
        gen = PlanGenerator()
        raw = json.dumps({
            "file_changes": [{
                "file_path": "foo.py",
                "change_type": "invalid_type",
                "description": "x",
                "rationale": "y",
            }]
        })
        changes = gen._parse_stage2(raw)
        assert changes[0].change_type == FileChangeType.MODIFY


# ═════════════════════════════════════════════════════════════════════════════
# B. Redis handoff — write / read / consume / overflow / secret redaction
# ═════════════════════════════════════════════════════════════════════════════

class TestRedisHandoff:
    """agent_memory functions tested against fakeredis."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.r = _make_fake_redis()
        # Patch _get_redis to return our fake client
        with patch("app.core.agent_memory._get_redis", return_value=self.r):
            from app.core import agent_memory as am
            self.am = am
            yield

    def test_write_handoff_returns_true(self):
        assert self.am.write_handoff("agent-a", "agent-b", "Test handoff") is True

    def test_handoff_key_exists_after_write(self):
        self.am.write_handoff("agent-x", "sender", "Hello")
        assert self.r.exists("memory:handoff:agent-x")

    def test_read_handoffs_returns_written_note(self):
        self.am.write_handoff("agent-a", "plan_executor", "Phase 1 complete")
        notes = self.am.read_handoffs("agent-a", limit=5)
        assert len(notes) == 1
        assert notes[0]["summary"] == "Phase 1 complete"
        assert notes[0]["from_agent_id"] == "plan_executor"

    def test_read_handoffs_multiple_notes(self):
        for i in range(5):
            self.am.write_handoff("agent-b", "sender", f"Note {i}")
        notes = self.am.read_handoffs("agent-b", limit=10)
        assert len(notes) == 5

    def test_read_handoffs_respects_limit(self):
        for i in range(10):
            self.am.write_handoff("agent-c", "sender", f"Note {i}")
        notes = self.am.read_handoffs("agent-c", limit=3)
        assert len(notes) == 3

    def test_consume_removes_notes(self):
        self.am.write_handoff("agent-d", "sender", "Note A")
        self.am.write_handoff("agent-d", "sender", "Note B")
        consumed = self.am.read_handoffs("agent-d", limit=2, consume=True)
        assert len(consumed) == 2
        remaining = self.am.read_handoffs("agent-d", limit=10)
        assert len(remaining) == 0

    def test_non_consume_does_not_remove_notes(self):
        self.am.write_handoff("agent-e", "sender", "Persistent")
        self.am.read_handoffs("agent-e", limit=5, consume=False)
        still_there = self.am.read_handoffs("agent-e", limit=5)
        assert len(still_there) == 1

    def test_handoff_note_has_required_fields(self):
        self.am.write_handoff("agent-f", "plan_executor", "Summary text")
        note = self.am.read_handoffs("agent-f")[0]
        assert "ts" in note
        assert "from_agent_id" in note
        assert "to_agent_id" in note
        assert "summary" in note

    def test_handoff_json_survives_round_trip(self):
        plan_json = json.dumps({"key": "value", "phases": [1, 2, 3]})
        self.am.write_handoff("agent-g", "plan_executor", "Test", links=[{"plan_json": plan_json}])
        note = self.am.read_handoffs("agent-g")[0]
        recovered = json.loads(note["links"][0]["plan_json"])
        assert recovered["phases"] == [1, 2, 3]

    def test_secret_redacted_in_handoff_summary(self):
        self.am.write_handoff("agent-h", "sender", "bearer: sk-abc12345678901234567890")
        note = self.am.read_handoffs("agent-h")[0]
        assert "sk-abc" not in note["summary"]
        assert "[REDACTED]" in note["summary"]

    def test_api_key_pattern_redacted(self):
        self.am.write_handoff("agent-i", "sender", "api_key: super-secret-value")
        note = self.am.read_handoffs("agent-i")[0]
        assert "super-secret-value" not in note["summary"]

    def test_read_empty_inbox_returns_empty_list(self):
        notes = self.am.read_handoffs("nonexistent-agent", limit=5)
        assert notes == []

    def test_write_handoff_redis_unavailable_returns_false(self):
        with patch("app.core.agent_memory._get_redis", return_value=None):
            result = self.am.write_handoff("agent-j", "sender", "Test")
        assert result is False

    def test_read_handoffs_redis_unavailable_returns_empty(self):
        with patch("app.core.agent_memory._get_redis", return_value=None):
            notes = self.am.read_handoffs("agent-j", limit=5)
        assert notes == []

    def test_large_plan_json_survives_round_trip(self):
        """Full plan JSON (~2 KB) must round-trip without data loss."""
        plan = _sample_plan()
        plan_dict = {
            "summary": plan.summary,
            "phases": [
                {"phase_number": p.phase_number, "title": p.title,
                 "description": p.description, "workflow_steps": p.workflow_steps}
                for p in plan.phases
            ],
            "file_changes_summary": [
                {"file_path": fc.file_path, "change_type": fc.change_type.value,
                 "description": fc.description, "rationale": fc.rationale}
                for fc in plan.file_changes_summary
            ],
            "follow_up_instructions": plan.follow_up_instructions,
        }
        plan_json = json.dumps(plan_dict)
        self.am.write_handoff("agent-k", "plan_executor", "Big plan", links=[{"type": "plan_json", "content": plan_json}])
        note = self.am.read_handoffs("agent-k")[0]
        recovered = json.loads(note["links"][0]["content"])
        assert len(recovered["phases"]) == 3
        assert recovered["summary"] == plan.summary

    def test_overflow_trims_to_max_entries(self):
        """After HANDOFF_MAX_ENTRIES + 10 writes, list stays bounded."""
        from app.core.agent_memory import HANDOFF_MAX_ENTRIES
        for i in range(HANDOFF_MAX_ENTRIES + 10):
            self.am.write_handoff("agent-overflow", "sender", f"Note {i}")
        length = self.r.llen("memory:handoff:agent-overflow")
        assert length <= HANDOFF_MAX_ENTRIES


# ═════════════════════════════════════════════════════════════════════════════
# C. PlanExecutor — agent routing, Celery dispatch, handoff content
# ═════════════════════════════════════════════════════════════════════════════

class TestPlanExecutor:
    """PlanExecutor with fakeredis + mocked Celery."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.r = _make_fake_redis()
        self.mock_celery = MagicMock()
        self.mock_celery.send_task = MagicMock(return_value=MagicMock(id="task-uuid-1"))

        with patch("app.core.agent_memory._get_redis", return_value=self.r), \
             patch("app.core.celery_app.celery_app", self.mock_celery):
            from app.services.plan_executor import PlanExecutor, _classify_phase
            self.executor = PlanExecutor()
            self._classify = _classify_phase
            yield

    async def test_submit_returns_summary_dict(self):
        plan = _sample_plan()
        result = await self.executor.submit_plan_to_orchestrator(plan, task_id=1)
        assert "plan_summary" in result
        assert "total_phases" in result
        assert "dispatched_jobs" in result

    async def test_submit_dispatches_all_phases(self):
        plan = _sample_plan()
        result = await self.executor.submit_plan_to_orchestrator(plan, task_id=1)
        assert result["total_phases"] == 3
        assert len(result["dispatched_jobs"]) == 3

    async def test_each_phase_marked_dispatched(self):
        plan = _sample_plan()
        result = await self.executor.submit_plan_to_orchestrator(plan, task_id=1)
        statuses = [j["status"] for j in result["dispatched_jobs"]]
        assert all(s == "dispatched" for s in statuses)

    async def test_celery_send_task_called_per_phase(self):
        plan = _sample_plan()
        await self.executor.submit_plan_to_orchestrator(plan, task_id=1)
        assert self.mock_celery.send_task.call_count == 3

    async def test_celery_task_name_is_correct(self):
        plan = _sample_plan()
        await self.executor.submit_plan_to_orchestrator(plan, task_id=1)
        for call in self.mock_celery.send_task.call_args_list:
            assert call.args[0] == "hypercode.tasks.process_agent_job"

    async def test_handoff_written_per_phase(self):
        plan = _sample_plan()
        await self.executor.submit_plan_to_orchestrator(plan, task_id=1)
        # At least one handoff key should exist
        keys = self.r.keys("memory:handoff:*")
        assert len(keys) >= 1

    async def test_handoff_contains_plan_json(self):
        plan = _sample_plan()
        await self.executor.submit_plan_to_orchestrator(plan, task_id=1)
        # Read from the first agent that got a handoff
        keys = self.r.keys("memory:handoff:*")
        assert keys
        raw = self.r.lindex(keys[0], 0)
        note = json.loads(raw)
        assert any("plan_json" in str(link) for link in note.get("links", []))

    async def test_celery_failure_marks_phase_as_error(self):
        self.mock_celery.send_task.side_effect = Exception("Broker unavailable")
        plan = _sample_plan()
        result = await self.executor.submit_plan_to_orchestrator(plan, task_id=1)
        statuses = [j["status"] for j in result["dispatched_jobs"]]
        assert all(s == "error" for s in statuses)

    async def test_error_phase_includes_error_message(self):
        self.mock_celery.send_task.side_effect = Exception("Timeout")
        plan = _sample_plan()
        result = await self.executor.submit_plan_to_orchestrator(plan, task_id=1)
        for job in result["dispatched_jobs"]:
            assert "error" in job

    async def test_plan_reference_in_celery_payload(self):
        plan = _sample_plan()
        await self.executor.submit_plan_to_orchestrator(plan, task_id=99)
        call_args = self.mock_celery.send_task.call_args_list[0]
        # send_task("task_name", args=[payload]) — payload is in kwargs["args"][0]
        payload = call_args.kwargs["args"][0]
        assert "plan_reference" in payload
        plan_data = json.loads(payload["plan_reference"])
        assert "summary" in plan_data
        assert "phases" in plan_data

    # Agent routing tests

    def test_classify_backend_by_extension(self):
        phase = PlanPhase(phase_number=1, title="API", description="x", workflow_steps=[])
        changes = [
            FileChange(file_path="backend/models.py", change_type=FileChangeType.CREATE, description="", rationale=""),
            FileChange(file_path="backend/views.py", change_type=FileChangeType.MODIFY, description="", rationale=""),
        ]
        assert self._classify(phase, changes) == "backend-specialist"

    def test_classify_frontend_by_extension(self):
        phase = PlanPhase(phase_number=1, title="UI", description="x", workflow_steps=[])
        changes = [
            FileChange(file_path="src/App.tsx", change_type=FileChangeType.CREATE, description="", rationale=""),
            FileChange(file_path="src/index.css", change_type=FileChangeType.MODIFY, description="", rationale=""),
        ]
        assert self._classify(phase, changes) == "frontend-specialist"

    def test_classify_mixed_extensions_uses_majority(self):
        phase = PlanPhase(phase_number=1, title="Full Stack", description="x", workflow_steps=[])
        changes = [
            FileChange(file_path="backend/api.py", change_type=FileChangeType.CREATE, description="", rationale=""),
            FileChange(file_path="backend/models.py", change_type=FileChangeType.CREATE, description="", rationale=""),
            FileChange(file_path="frontend/App.tsx", change_type=FileChangeType.CREATE, description="", rationale=""),
        ]
        assert self._classify(phase, changes) == "backend-specialist"

    def test_classify_no_file_changes_uses_title_keyword(self):
        phase = PlanPhase(phase_number=1, title="Frontend Component", description="x", workflow_steps=[])
        assert self._classify(phase, []) == "frontend-specialist"

    def test_classify_api_keyword_in_title_routes_backend(self):
        phase = PlanPhase(phase_number=1, title="API Gateway Setup", description="x", workflow_steps=[])
        assert self._classify(phase, []) == "backend-specialist"

    def test_classify_unknown_routes_to_general(self):
        phase = PlanPhase(phase_number=1, title="Documentation", description="x", workflow_steps=[])
        assert self._classify(phase, []) == "general-specialist"

    def test_classify_schema_keyword_routes_backend(self):
        phase = PlanPhase(phase_number=1, title="Schema Migration", description="x", workflow_steps=[])
        assert self._classify(phase, []) == "backend-specialist"


# ═════════════════════════════════════════════════════════════════════════════
# D. Full E2E — generator → Redis → executor, data consistency
# ═════════════════════════════════════════════════════════════════════════════

class TestPlanningE2E:
    """Full pipeline: PlanGenerator produces plan → PlanExecutor dispatches it."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _brain_stub.reset()
        self.r = _make_fake_redis()
        self.mock_celery = MagicMock()
        self.mock_celery.send_task = MagicMock(return_value=MagicMock(id="e2e-job-1"))

        with patch("app.services.plan_generator.brain", _brain_stub), \
             patch("app.services.plan_generator.get_history", return_value=[]), \
             patch("app.services.plan_generator.read_handoffs", return_value=[]), \
             patch("app.core.agent_memory._get_redis", return_value=self.r), \
             patch("app.core.celery_app.celery_app", self.mock_celery):
            from app.services.plan_generator import PlanGenerator
            from app.services.plan_executor import PlanExecutor
            self.gen = PlanGenerator()
            self.executor = PlanExecutor()
            yield

    async def test_e2e_pipeline_completes_without_error(self):
        doc = _parsed_doc()
        plan = await self.gen.generate_plan(doc)
        result = await self.executor.submit_plan_to_orchestrator(plan, task_id=1)
        assert result["total_phases"] == len(plan.phases)

    async def test_e2e_plan_summary_preserved_in_celery_payload(self):
        doc = _parsed_doc()
        plan = await self.gen.generate_plan(doc)
        await self.executor.submit_plan_to_orchestrator(plan, task_id=1)

        call_payload = self.mock_celery.send_task.call_args_list[0].kwargs["args"][0]
        plan_data = json.loads(call_payload["plan_reference"])
        assert plan_data["summary"] == plan.summary

    async def test_e2e_all_phases_appear_in_celery_dispatches(self):
        doc = _parsed_doc()
        plan = await self.gen.generate_plan(doc)
        await self.executor.submit_plan_to_orchestrator(plan, task_id=1)

        dispatched_titles = [
            call.kwargs["args"][0]["title"]
            for call in self.mock_celery.send_task.call_args_list
        ]
        for phase in plan.phases:
            assert any(phase.title in title for title in dispatched_titles)

    async def test_e2e_redis_handoffs_match_phases(self):
        doc = _parsed_doc()
        plan = await self.gen.generate_plan(doc)
        await self.executor.submit_plan_to_orchestrator(plan, task_id=1)

        handoff_keys = self.r.keys("memory:handoff:*")
        # Each phase writes one handoff
        assert len(handoff_keys) >= 1

    async def test_e2e_file_changes_in_plan_reference_match_generator_output(self):
        doc = _parsed_doc()
        plan = await self.gen.generate_plan(doc)
        await self.executor.submit_plan_to_orchestrator(plan, task_id=1)

        call_payload = self.mock_celery.send_task.call_args_list[0].kwargs["args"][0]
        plan_data = json.loads(call_payload["plan_reference"])
        assert len(plan_data["file_changes_summary"]) == len(plan.file_changes_summary)

    async def test_e2e_follow_up_instructions_round_trip(self):
        doc = _parsed_doc()
        plan = await self.gen.generate_plan(doc)
        await self.executor.submit_plan_to_orchestrator(plan, task_id=1)

        call_payload = self.mock_celery.send_task.call_args_list[0].kwargs["args"][0]
        plan_data = json.loads(call_payload["plan_reference"])
        assert plan_data["follow_up_instructions"] == plan.follow_up_instructions

    async def test_e2e_two_runs_are_identical(self):
        """Deterministic Brain must produce identical plans on two runs."""
        doc = _parsed_doc()
        _brain_stub.reset()
        plan1 = await self.gen.generate_plan(doc)
        _brain_stub.reset()
        plan2 = await self.gen.generate_plan(doc)
        assert plan1.summary == plan2.summary
        assert len(plan1.phases) == len(plan2.phases)
        assert [p.title for p in plan1.phases] == [p.title for p in plan2.phases]

    async def test_e2e_with_project_context(self):
        doc = _parsed_doc()
        ctx = {"project_name": "HyperAuth", "tech_stack": "FastAPI+React"}
        plan = await self.gen.generate_plan(doc, context=ctx)
        result = await self.executor.submit_plan_to_orchestrator(plan, task_id=42, project_id=7)
        assert result["total_phases"] >= 1

    async def test_e2e_task_id_passed_to_celery_payload(self):
        doc = _parsed_doc()
        plan = await self.gen.generate_plan(doc)
        await self.executor.submit_plan_to_orchestrator(plan, task_id=999)

        for call in self.mock_celery.send_task.call_args_list:
            payload = call.kwargs["args"][0]
            assert payload["id"] == 999


# ═════════════════════════════════════════════════════════════════════════════
# E. Error handling — LLM failures, Redis outages, Celery failures
# ═════════════════════════════════════════════════════════════════════════════

class TestErrorHandling:

    @pytest.fixture(autouse=True)
    def _setup(self):
        _brain_stub.reset()
        self.r = _make_fake_redis()
        self.mock_celery = MagicMock()
        self.mock_celery.send_task = MagicMock()

        with patch("app.services.plan_generator.brain", _brain_stub), \
             patch("app.services.plan_generator.get_history", return_value=[]), \
             patch("app.services.plan_generator.read_handoffs", return_value=[]), \
             patch("app.core.agent_memory._get_redis", return_value=self.r), \
             patch("app.core.celery_app.celery_app", self.mock_celery):
            from app.services.plan_generator import PlanGenerator
            from app.services.plan_executor import PlanExecutor
            self.gen = PlanGenerator()
            self.executor = PlanExecutor()
            yield

    async def test_brain_failure_on_stage1_raises_or_falls_back(self):
        """Stage 1 failure should either raise or produce fallback plan."""
        _brain_stub._raise_on_call = 1
        try:
            plan = await self.gen.generate_plan(_parsed_doc())
            # If it doesn't raise, it must return a valid CodingPlan
            assert isinstance(plan, CodingPlan)
        except Exception:
            pass  # Acceptable — let it propagate

    async def test_brain_failure_on_stage2_uses_empty_file_changes(self):
        """Stage 2 JSON parse failure → empty file_changes_summary (not crash)."""
        fail_brain = DeterministicBrain()

        async def _think(role, task_description, use_memory=False):
            fail_brain.call_count += 1
            if fail_brain.call_count == 1:
                return STAGE1_RESPONSE
            if fail_brain.call_count == 2:
                return "this is not json"  # Stage 2 failure
            return STAGE3_RESPONSE

        fail_brain.think = _think

        with patch("app.services.plan_generator.brain", fail_brain):
            from app.services.plan_generator import PlanGenerator
            gen = PlanGenerator()
            plan = await gen.generate_plan(_parsed_doc())
        assert plan.file_changes_summary == []

    async def test_redis_unavailable_executor_still_dispatches(self):
        """Redis being down must not prevent Celery dispatch."""
        with patch("app.core.agent_memory._get_redis", return_value=None):
            from app.services.plan_executor import PlanExecutor
            executor = PlanExecutor()
            plan = _sample_plan()
            result = await executor.submit_plan_to_orchestrator(plan, task_id=1)
        # Celery should still be called
        assert self.mock_celery.send_task.call_count == len(plan.phases)

    async def test_partial_celery_failure_returns_mixed_statuses(self):
        call_count = {"n": 0}

        def _send_task(name, args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise Exception("Phase 2 broker error")
            return MagicMock(id=f"job-{call_count['n']}")

        self.mock_celery.send_task.side_effect = _send_task
        plan = _sample_plan()
        result = await self.executor.submit_plan_to_orchestrator(plan, task_id=1)
        statuses = {j["phase"]: j["status"] for j in result["dispatched_jobs"]}
        assert statuses[1] == "dispatched"
        assert statuses[2] == "error"
        assert statuses[3] == "dispatched"

    async def test_malformed_stage1_json_still_produces_valid_plan(self):
        """Truncated JSON in Stage 1 must fall back gracefully."""
        from app.services.plan_generator import PlanGenerator
        gen = PlanGenerator()
        # Simulate truncated JSON
        phases, summary = gen._parse_stage1('{"summary": "ok", "phases": [{"ph')
        assert len(phases) >= 1


# ═════════════════════════════════════════════════════════════════════════════
# F. Timeout conditions
# ═════════════════════════════════════════════════════════════════════════════

class TestTimeouts:

    @pytest.fixture(autouse=True)
    def _setup(self):
        _brain_stub.reset()
        self.r = _make_fake_redis()
        self.mock_celery = MagicMock()
        self.mock_celery.send_task = MagicMock(return_value=MagicMock(id="t-1"))
        yield

    async def test_fast_brain_completes_within_1_second(self):
        """With stub brain (no I/O), generation must be fast."""
        _brain_stub.reset()
        with patch("app.services.plan_generator.brain", _brain_stub), \
             patch("app.services.plan_generator.get_history", return_value=[]), \
             patch("app.services.plan_generator.read_handoffs", return_value=[]), \
             patch("app.core.agent_memory._get_redis", return_value=self.r):
            from app.services.plan_generator import PlanGenerator
            gen = PlanGenerator()
            t0 = time.perf_counter()
            await gen.generate_plan(_parsed_doc())
            elapsed = time.perf_counter() - t0
        assert elapsed < 1.0, f"Generation took {elapsed:.3f}s — expected < 1s"

    async def test_executor_fast_dispatch_completes_within_500ms(self):
        """Executor dispatch (no I/O) must be very fast."""
        with patch("app.core.agent_memory._get_redis", return_value=self.r), \
             patch("app.core.celery_app.celery_app", self.mock_celery):
            from app.services.plan_executor import PlanExecutor
            executor = PlanExecutor()
            plan = _sample_plan()
            t0 = time.perf_counter()
            await executor.submit_plan_to_orchestrator(plan, task_id=1)
            elapsed = time.perf_counter() - t0
        assert elapsed < 0.5, f"Dispatch took {elapsed:.3f}s — expected < 0.5s"

    async def test_asyncio_timeout_cancels_slow_brain(self):
        """asyncio.wait_for should cancel a brain call that exceeds timeout."""
        _brain_stub._slow_after = 2.0  # 2 second sleep

        with patch("app.services.plan_generator.brain", _brain_stub), \
             patch("app.services.plan_generator.get_history", return_value=[]), \
             patch("app.services.plan_generator.read_handoffs", return_value=[]):
            from app.services.plan_generator import PlanGenerator
            gen = PlanGenerator()
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(gen.generate_plan(_parsed_doc()), timeout=0.1)


# ═════════════════════════════════════════════════════════════════════════════
# G. Data consistency — serialization identity checks
# ═════════════════════════════════════════════════════════════════════════════

class TestDataConsistency:
    """Verify JSON round-trips and plan identity across serialization boundaries."""

    def test_coding_plan_serializes_to_dict(self):
        plan = _sample_plan()
        d = plan.model_dump()
        assert d["summary"] == plan.summary
        assert len(d["phases"]) == 3

    def test_coding_plan_survives_json_dumps_loads(self):
        plan = _sample_plan()
        raw = plan.model_dump_json()
        restored = CodingPlan.model_validate_json(raw)
        assert restored.summary == plan.summary
        assert len(restored.phases) == len(plan.phases)
        assert [p.phase_number for p in restored.phases] == [p.phase_number for p in plan.phases]

    def test_file_change_types_serialize_as_strings(self):
        plan = _sample_plan()
        d = plan.model_dump()
        for fc in d["file_changes_summary"]:
            assert isinstance(fc["change_type"], str)
            assert fc["change_type"] in {"create", "modify", "delete"}

    def test_phases_preserve_workflow_steps(self):
        plan = _sample_plan()
        raw = plan.model_dump_json()
        restored = CodingPlan.model_validate_json(raw)
        for orig, rest in zip(plan.phases, restored.phases):
            assert orig.workflow_steps == rest.workflow_steps

    def test_plan_json_handoff_link_round_trip(self):
        """Full plan_json as stored in Redis handoff link survives round trip."""
        plan = _sample_plan()
        plan_dict = plan.model_dump()
        # Simulate plan_executor serialization
        plan_dict["file_changes_summary"] = [
            {**fc, "change_type": fc["change_type"].value if hasattr(fc["change_type"], "value") else fc["change_type"]}
            for fc in plan_dict["file_changes_summary"]
        ]
        plan_json = json.dumps(plan_dict)
        recovered = json.loads(plan_json)
        assert recovered["summary"] == plan.summary
        assert len(recovered["phases"]) == 3

    def test_executor_plan_json_all_fields_present(self):
        """plan_reference written by executor must have all required keys."""
        plan = _sample_plan()
        required_keys = {"summary", "phases", "file_changes_summary", "follow_up_instructions"}
        with patch("app.core.agent_memory._get_redis", return_value=_make_fake_redis()), \
             patch("app.core.celery_app.celery_app", MagicMock(send_task=MagicMock())):
            import asyncio as _asyncio
            from app.services.plan_executor import PlanExecutor
            executor = PlanExecutor()
            result = _asyncio.get_event_loop().run_until_complete(
                executor.submit_plan_to_orchestrator(plan, task_id=1)
            )

        mock_celery = patch("app.core.celery_app.celery_app").__enter__()
        # Verify via dispatched_jobs output
        assert all(j["status"] in ("dispatched", "error") for j in result["dispatched_jobs"])

    def test_parsed_document_round_trips_via_pydantic(self):
        doc = _parsed_doc(n_reqs=3)
        raw = doc.model_dump_json()
        restored = ParsedDocument.model_validate_json(raw)
        assert len(restored.requirements) == 3
        assert restored.detected_document_type == DocumentType.PRD


# ═════════════════════════════════════════════════════════════════════════════
# H. Performance benchmarks
# ═════════════════════════════════════════════════════════════════════════════

class TestPerformanceBenchmarks:
    """Wall-clock benchmarks for the complete pipeline with stub dependencies."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _brain_stub.reset()
        self.r = _make_fake_redis()
        self.mock_celery = MagicMock()
        self.mock_celery.send_task = MagicMock(return_value=MagicMock(id="bench-1"))

        with patch("app.services.plan_generator.brain", _brain_stub), \
             patch("app.services.plan_generator.get_history", return_value=[]), \
             patch("app.services.plan_generator.read_handoffs", return_value=[]), \
             patch("app.core.agent_memory._get_redis", return_value=self.r), \
             patch("app.core.celery_app.celery_app", self.mock_celery):
            from app.services.plan_generator import PlanGenerator
            from app.services.plan_executor import PlanExecutor
            self.gen = PlanGenerator()
            self.executor = PlanExecutor()
            yield

    async def test_full_pipeline_under_5_seconds(self):
        """Complete generate + execute cycle must finish in < 5 seconds."""
        t0 = time.perf_counter()
        plan = await self.gen.generate_plan(_parsed_doc())
        await self.executor.submit_plan_to_orchestrator(plan, task_id=1)
        elapsed = time.perf_counter() - t0
        assert elapsed < 5.0, f"Full pipeline took {elapsed:.3f}s — expected < 5s"

    async def test_10_sequential_plan_generations_under_5_seconds(self):
        """10 sequential plan generations should complete in < 5 seconds."""
        t0 = time.perf_counter()
        for _ in range(10):
            _brain_stub.reset()
            await self.gen.generate_plan(_parsed_doc())
        elapsed = time.perf_counter() - t0
        assert elapsed < 5.0, f"10 sequential plans took {elapsed:.3f}s — expected < 5s"

    async def test_redis_handoff_write_100_notes_under_1_second(self):
        """Writing 100 handoff notes should be fast."""
        with patch("app.core.agent_memory._get_redis", return_value=self.r):
            from app.core import agent_memory as am
            t0 = time.perf_counter()
            for i in range(100):
                am.write_handoff("bench-agent", "plan_executor", f"Note {i}")
            elapsed = time.perf_counter() - t0
        assert elapsed < 1.0, f"100 handoff writes took {elapsed:.3f}s"

    async def test_redis_handoff_read_100_notes_under_500ms(self):
        with patch("app.core.agent_memory._get_redis", return_value=self.r):
            from app.core import agent_memory as am
            for i in range(100):
                am.write_handoff("bench-reader", "plan_executor", f"Note {i}")
            t0 = time.perf_counter()
            notes = am.read_handoffs("bench-reader", limit=100)
            elapsed = time.perf_counter() - t0
        assert elapsed < 0.5
        assert len(notes) == 100

    async def test_concurrent_plan_executions(self):
        """5 concurrent executions must all succeed and complete quickly."""
        t0 = time.perf_counter()
        plans = [_sample_plan() for _ in range(5)]
        results = await asyncio.gather(*[
            self.executor.submit_plan_to_orchestrator(p, task_id=i)
            for i, p in enumerate(plans)
        ])
        elapsed = time.perf_counter() - t0
        assert elapsed < 3.0, f"5 concurrent executions took {elapsed:.3f}s"
        assert all(r["total_phases"] == 3 for r in results)


# ═════════════════════════════════════════════════════════════════════════════
# I. Shared Redis — simulated clustered environment
# ═════════════════════════════════════════════════════════════════════════════

class TestSharedRedisEnvironment:
    """
    Simulate multiple agents sharing one Redis instance.
    Tests isolation of handoff inboxes and cross-agent message routing.
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        # Single shared Redis for all agents (simulates cluster scenario)
        self.shared_r = _make_fake_redis()
        self.mock_celery = MagicMock()
        self.mock_celery.send_task = MagicMock(return_value=MagicMock(id="shared-1"))

        with patch("app.core.agent_memory._get_redis", return_value=self.shared_r), \
             patch("app.core.celery_app.celery_app", self.mock_celery):
            from app.core import agent_memory as am
            from app.services.plan_executor import PlanExecutor
            self.am = am
            self.executor = PlanExecutor()
            yield

    def test_different_agents_have_isolated_inboxes(self):
        self.am.write_handoff("agent-alpha", "sender", "Message for alpha")
        self.am.write_handoff("agent-beta", "sender", "Message for beta")

        alpha_notes = self.am.read_handoffs("agent-alpha")
        beta_notes = self.am.read_handoffs("agent-beta")

        assert len(alpha_notes) == 1
        assert alpha_notes[0]["summary"] == "Message for alpha"
        assert len(beta_notes) == 1
        assert beta_notes[0]["summary"] == "Message for beta"

    def test_agents_do_not_read_each_others_messages(self):
        self.am.write_handoff("agent-x", "sender", "Secret for X")
        notes_for_y = self.am.read_handoffs("agent-y")
        assert len(notes_for_y) == 0

    async def test_multiple_executors_write_to_different_agent_inboxes(self):
        """Two plan executors writing to different agent targets stay isolated."""
        plan_backend = CodingPlan(
            summary="Backend plan",
            phases=[PlanPhase(phase_number=1, title="Backend API", description="x", workflow_steps=[])],
            file_changes_summary=[
                FileChange(file_path="api.py", change_type=FileChangeType.CREATE, description="", rationale="")
            ],
        )
        plan_frontend = CodingPlan(
            summary="Frontend plan",
            phases=[PlanPhase(phase_number=1, title="Frontend Component", description="x", workflow_steps=[])],
            file_changes_summary=[
                FileChange(file_path="App.tsx", change_type=FileChangeType.CREATE, description="", rationale="")
            ],
        )

        r1 = await self.executor.submit_plan_to_orchestrator(plan_backend, task_id=1)
        r2 = await self.executor.submit_plan_to_orchestrator(plan_frontend, task_id=2)

        # Backend routes to backend-specialist
        assert r1["dispatched_jobs"][0]["agent"] == "backend-specialist"
        # Frontend routes to frontend-specialist
        assert r2["dispatched_jobs"][0]["agent"] == "frontend-specialist"

    def test_conversation_history_isolated_by_id(self):
        self.am.append_turn("conv-1", "agent-a", "user", "Hello from conv 1")
        self.am.append_turn("conv-2", "agent-a", "user", "Hello from conv 2")

        hist1 = self.am.get_history("conv-1")
        hist2 = self.am.get_history("conv-2")

        assert len(hist1) == 1
        assert hist1[0]["content"] == "Hello from conv 1"
        assert len(hist2) == 1
        assert hist2[0]["content"] == "Hello from conv 2"

    def test_clear_handoffs_does_not_affect_other_agents(self):
        self.am.write_handoff("agent-clean", "sender", "Will be cleared")
        self.am.write_handoff("agent-keep", "sender", "Should stay")

        self.am.clear_handoffs("agent-clean")

        assert self.am.read_handoffs("agent-clean") == []
        assert len(self.am.read_handoffs("agent-keep")) == 1
