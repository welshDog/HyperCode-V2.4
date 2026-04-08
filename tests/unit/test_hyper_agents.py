"""Unit tests for the HyperCode hyper_agents package."""
from __future__ import annotations
import pytest

from src.agents.hyper_agents import (
    HyperAgent,
    AgentStatus,
    AgentArchetype,
    NDErrorResponse,
    ArchitectAgent,
    ObserverAgent,
    WorkerAgent,
)
from src.agents.hyper_agents.architect import GoalStatus, Goal, PlanStep


# ── Concrete test doubles ────────────────────────────────────────────────────

class _ConcreteArchitect(ArchitectAgent):
    async def execute(self, task):
        return {"status": "done", "message": "test"}


class _ConcreteObserver(ObserverAgent):
    async def execute(self, task):
        return {"status": "done", "message": "test"}


class _ConcreteWorker(WorkerAgent):
    async def execute(self, task):
        return {"status": "done", "message": "test"}


# ── Public API ───────────────────────────────────────────────────────────────

class TestPublicAPI:
    def test_all_symbols_importable(self):
        assert HyperAgent
        assert AgentStatus
        assert AgentArchetype
        assert NDErrorResponse
        assert ArchitectAgent
        assert ObserverAgent
        assert WorkerAgent
        assert _ConcreteArchitect
        assert Goal
        assert PlanStep
        assert GoalStatus

    def test_agent_archetype_values(self):
        for archetype in [
            AgentArchetype.WORKER,
            AgentArchetype.OBSERVER,
            AgentArchetype.ARCHITECT,
        ]:
            assert archetype.value

    def test_agent_status_values(self):
        for status in AgentStatus:
            assert status.value


# ── ArchitectAgent ───────────────────────────────────────────────────────────

class TestArchitectAgent:
    def setup_method(self):
        self.agent = _ConcreteArchitect(name="test-architect-01", archetype=AgentArchetype.ARCHITECT)

    def test_initialize_sets_idle_status(self):
        assert self.agent.status is not None

    def test_create_goal_returns_id(self):
        goal_id = self.agent.create_goal("Test goal")
        assert isinstance(goal_id, str)
        assert len(goal_id) > 0

    def test_created_goal_is_retrievable(self):
        goal_id = self.agent.create_goal("Retrievable goal")
        goal = self.agent.get_goal(goal_id)
        assert goal is not None
        assert goal.description == "Retrievable goal"

    def test_add_step_to_goal(self):
        goal_id = self.agent.create_goal("Goal with step")
        step_id = self.agent.add_step(goal_id, "Step one")
        assert isinstance(step_id, str)

    def test_add_step_with_dependency(self):
        goal_id = self.agent.create_goal("Goal with deps")
        step_a = self.agent.add_step(goal_id, "Step A")
        step_b = self.agent.add_step(goal_id, "Step B", depends_on=[step_a])
        goal = self.agent.get_goal(goal_id)
        step = next(s for s in goal.steps if s.step_id == step_b)
        assert step_a in step.depends_on

    def test_get_ready_steps_respects_dependencies(self):
        goal_id = self.agent.create_goal("Dep test")
        step_a = self.agent.add_step(goal_id, "A")
        step_b = self.agent.add_step(goal_id, "B", depends_on=[step_a])
        ready = self.agent.get_ready_steps(goal_id)
        ready_ids = [s.step_id for s in ready]
        assert step_a in ready_ids
        assert step_b not in ready_ids

    def test_update_step_status_to_completed(self):
        goal_id = self.agent.create_goal("Update test")
        step_id = self.agent.add_step(goal_id, "Complete me")
        self.agent.complete_step(goal_id, step_id)
        goal = self.agent.get_goal(goal_id)
        step = next(s for s in goal.steps if s.step_id == step_id)
        assert step.status == GoalStatus.COMPLETED

    def test_goal_fails_if_step_fails(self):
        goal_id = self.agent.create_goal("Fail test")
        step_id = self.agent.add_step(goal_id, "Will fail")
        self.agent.fail_step(goal_id, step_id)
        goal = self.agent.get_goal(goal_id)
        assert goal.status == GoalStatus.FAILED

    def test_register_agent(self):
        self.agent.register_sub_agent("worker-01", "worker")
        assert "worker-01" in self.agent.registered_agents

    def test_stats_property(self):
        stats = self.agent.stats
        assert isinstance(stats, dict)

    def test_goal_progress_calculation(self):
        goal_id = self.agent.create_goal("Progress test")
        s1 = self.agent.add_step(goal_id, "S1")
        s2 = self.agent.add_step(goal_id, "S2")
        self.agent.complete_step(goal_id, s1)
        progress = self.agent.goal_progress(goal_id)
        assert 0.0 <= progress <= 1.0

    def test_shutdown(self):
        self.agent.shutdown()
        assert self.agent.status == AgentStatus.STOPPING


# ── ObserverAgent ────────────────────────────────────────────────────────────

class TestObserverAgent:
    def setup_method(self):
        self.agent = _ConcreteObserver(name="test-observer-01", archetype=AgentArchetype.OBSERVER)

    def test_initialize_sets_idle(self):
        assert self.agent.status is not None

    def test_archetype_is_observer(self):
        assert self.agent.archetype == AgentArchetype.OBSERVER

    def test_shutdown(self):
        self.agent.shutdown()
        assert self.agent.status == AgentStatus.STOPPING


# ── WorkerAgent ──────────────────────────────────────────────────────────────

class TestWorkerAgent:
    def setup_method(self):
        self.agent = _ConcreteWorker(name="test-worker-01", archetype=AgentArchetype.WORKER)

    def test_initialize_sets_idle(self):
        assert self.agent.status is not None

    def test_archetype_is_worker(self):
        assert self.agent.archetype == AgentArchetype.WORKER

    @pytest.mark.asyncio
    async def test_execute_task_returns_dict(self):
        result = await self.agent.execute({"type": "test"})
        assert isinstance(result, dict)
        assert "status" in result

    def test_shutdown(self):
        self.agent.shutdown()
        assert self.agent.status == AgentStatus.STOPPING


# ── NDErrorResponse ──────────────────────────────────────────────────────────

class TestNDErrorResponse:
    def test_nd_error_response_has_required_fields(self):
        err = NDErrorResponse(
            title="Test Error",
            what_happened="Something broke during init.",
            why_it_matters="The agent cannot start.",
            options=["Restart the agent", "Check the logs"],
            error_code="TEST_001",
        )
        assert err.title == "Test Error"
        assert err.error_code == "TEST_001"
        assert isinstance(err.options, list)
        assert len(err.options) == 2
