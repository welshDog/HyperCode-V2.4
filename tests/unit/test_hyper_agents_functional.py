"""
HyperCode V2.0 — Hyper Agents Comprehensive Functional Test Suite
=================================================================

Test groups:
  T-010  HyperAgent base class (status transitions, routes, ND error)
  T-030  ArchitectAgent (goals, steps, deps, registry, progress)
  T-060  ObserverAgent  (metrics, alerts, cooldown, callbacks, rate)
  T-100  WorkerAgent    (tasks, retry, timeout, hyperfocus, queue)
  T-140  Integration    (Architect + Worker, Observer watches Worker)
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.agents.hyper_agents import (
    AgentArchetype,
    AgentStatus,
    HyperAgent,
    NDErrorResponse,
    ArchitectAgent,
    ObserverAgent,
    WorkerAgent,
)
from src.agents.hyper_agents.architect import Goal, GoalStatus, PlanStep
from src.agents.hyper_agents.observer import (
    Alert,
    AlertRule,
    AlertSeverity,
    Metric,
    MetricType,
)
from src.agents.hyper_agents.worker import Task, TaskPriority, TaskResult


# ── Concrete test doubles ─────────────────────────────────────────────────────

class _MinimalAgent(HyperAgent):
    """Minimal concrete implementation for base-class tests."""

    async def execute(self, task: dict) -> dict:
        return {"status": "ok", "message": "executed"}


class _ConcreteArchitect(ArchitectAgent):
    async def execute(self, task):
        return {"status": "done", "message": "planned"}


class _ConcreteObserver(ObserverAgent):
    async def execute(self, task):
        return {"status": "done", "message": "observed"}


class _ConcreteWorker(WorkerAgent):
    async def execute(self, task):
        return {"status": "done", "message": "worked"}


# ─────────────────────────────────────────────────────────────────────────────
# T-010  HyperAgent base class
# ─────────────────────────────────────────────────────────────────────────────

class TestHyperAgentBase:
    """T-010 series: base-class status transitions, routes, and ND error."""

    def setup_method(self):
        self.agent = _MinimalAgent(name="base-test-01", archetype=AgentArchetype.CUSTOM)

    # T-011: initial status is STARTING
    def test_initial_status_is_starting(self):
        assert self.agent.status == AgentStatus.STARTING

    # T-012: set_ready transitions to READY
    def test_set_ready_transitions_status(self):
        self.agent.set_ready()
        assert self.agent.status == AgentStatus.READY

    # T-013: set_busy transitions to BUSY
    def test_set_busy_transitions_status(self):
        self.agent.set_busy()
        assert self.agent.status == AgentStatus.BUSY

    # T-014: set_error transitions to ERROR
    def test_set_error_transitions_status(self):
        self.agent.set_error()
        assert self.agent.status == AgentStatus.ERROR

    # T-015: shutdown transitions to STOPPING
    def test_shutdown_transitions_to_stopping(self):
        self.agent.shutdown()
        assert self.agent.status == AgentStatus.STOPPING

    # T-016: status sequence is coherent
    def test_full_status_lifecycle(self):
        self.agent.set_ready()
        assert self.agent.status == AgentStatus.READY
        self.agent.set_busy()
        assert self.agent.status == AgentStatus.BUSY
        self.agent.set_ready()
        assert self.agent.status == AgentStatus.READY
        self.agent.shutdown()
        assert self.agent.status == AgentStatus.STOPPING

    # T-017: /health endpoint returns agent metadata
    def test_health_endpoint_returns_200(self):
        client = TestClient(self.agent.app)
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "base-test-01"
        assert data["archetype"] == AgentArchetype.CUSTOM.value
        assert "status" in data
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], float)

    # T-018: /info endpoint returns correct metadata
    def test_info_endpoint_returns_metadata(self):
        client = TestClient(self.agent.app)
        resp = client.get("/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "base-test-01"
        assert data["archetype"] == AgentArchetype.CUSTOM.value
        assert data["hypercode_version"] == "2.0"
        assert "version" in data
        assert "port" in data

    # T-019: format_nd_error returns properly structured NDErrorResponse
    def test_format_nd_error_returns_nd_error_response(self):
        err = self.agent.format_nd_error(
            title="Connection lost",
            what_happened="Redis dropped the connection.",
            why_it_matters="Tasks cannot be dispatched.",
            options=["Restart Redis", "Check network config"],
            error_code="REDIS_CONN_001",
            technical_detail="ConnectionRefusedError: [Errno 111]",
        )
        assert isinstance(err, NDErrorResponse)
        assert err.title == "Connection lost"
        assert err.error_code == "REDIS_CONN_001"
        assert "Restart Redis" in err.options
        assert err.technical_detail is not None

    # T-020: format_nd_error optional fields default to None
    def test_format_nd_error_optional_fields_nullable(self):
        err = self.agent.format_nd_error(
            title="Minor hiccup",
            what_happened="A step skipped.",
            why_it_matters="Mild delay.",
            options=["Retry the step"],
        )
        assert err.error_code is None
        assert err.technical_detail is None

    # T-021: register_with_crew handles offline orchestrator gracefully
    def test_register_with_crew_offline_returns_pending(self):
        result = self.agent.register_with_crew(crew_url="http://localhost:19999")
        assert result["status"] == "registration_pending"
        assert "error" in result


# ─────────────────────────────────────────────────────────────────────────────
# T-030  ArchitectAgent
# ─────────────────────────────────────────────────────────────────────────────

class TestArchitectAgentFunctional:
    """T-030 series: goal lifecycle, dependency resolution, registry."""

    def setup_method(self):
        self.agent = _ConcreteArchitect(name="arch-func-01", archetype=AgentArchetype.ARCHITECT)

    # T-031: initialize() coroutine sets status to READY
    @pytest.mark.asyncio
    async def test_initialize_sets_ready(self):
        await self.agent.initialize()
        assert self.agent.status == AgentStatus.READY

    # T-032: goal status becomes COMPLETED when all steps complete
    def test_goal_completes_when_all_steps_done(self):
        gid = self.agent.create_goal("Full completion test")
        s1 = self.agent.add_step(gid, "Step A")
        s2 = self.agent.add_step(gid, "Step B")
        self.agent.complete_step(gid, s1)
        self.agent.complete_step(gid, s2)
        goal = self.agent.get_goal(gid)
        assert goal.status == GoalStatus.COMPLETED

    # T-033: goal_progress is 1.0 when all steps complete
    def test_goal_progress_is_1_when_all_complete(self):
        gid = self.agent.create_goal("Progress 100%")
        s1 = self.agent.add_step(gid, "A")
        self.agent.complete_step(gid, s1)
        assert self.agent.goal_progress(gid) == 1.0

    # T-034: goal_progress is 0.0 for unknown goal_id
    def test_goal_progress_unknown_id_returns_zero(self):
        assert self.agent.goal_progress("nonexistent-id") == 0.0

    # T-035: multiple independent goals are tracked separately
    def test_multiple_goals_tracked_independently(self):
        gid1 = self.agent.create_goal("Goal Alpha")
        gid2 = self.agent.create_goal("Goal Beta")
        s1 = self.agent.add_step(gid1, "Alpha step")
        self.agent.complete_step(gid1, s1)
        assert self.agent.goal_progress(gid1) == 1.0
        assert self.agent.goal_progress(gid2) == 0.0

    # T-036: add_step raises ValueError for unknown goal_id
    def test_add_step_invalid_goal_raises_value_error(self):
        with pytest.raises(ValueError, match="not found"):
            self.agent.add_step("bad-id", "This should fail")

    # T-037: register_agent (enum-based) stores archetype value
    def test_register_agent_enum_stores_archetype_value(self):
        self.agent.register_agent("obs-01", AgentArchetype.OBSERVER)
        assert "obs-01" in self.agent.registered_agents
        assert self.agent.registered_agents["obs-01"] == AgentArchetype.OBSERVER.value

    # T-038: get_ready_steps returns empty list when no goals
    def test_get_ready_steps_unknown_goal_returns_empty(self):
        result = self.agent.get_ready_steps("ghost-goal")
        assert result == []

    # T-039: step with completed dependency becomes ready
    def test_step_becomes_ready_after_dep_complete(self):
        gid = self.agent.create_goal("Chain test")
        sa = self.agent.add_step(gid, "First")
        sb = self.agent.add_step(gid, "Second", depends_on=[sa])
        self.agent.complete_step(gid, sa)
        ready = [s.step_id for s in self.agent.get_ready_steps(gid)]
        assert sb in ready

    # T-040: stats reflects goal and agent counts accurately
    def test_stats_reflects_state_accurately(self):
        self.agent.create_goal("Stats check")
        self.agent.register_sub_agent("worker-x", "worker")
        stats = self.agent.stats
        assert stats["total_goals"] == 1
        assert stats["registered_agents"] == 1

    # T-041: completed goal counter increments
    def test_completed_goals_counter_increments(self):
        initial = self.agent.stats["completed_goals"]
        gid = self.agent.create_goal("Completer")
        s = self.agent.add_step(gid, "Only step")
        self.agent.complete_step(gid, s)
        assert self.agent.stats["completed_goals"] == initial + 1


# ─────────────────────────────────────────────────────────────────────────────
# T-060  ObserverAgent
# ─────────────────────────────────────────────────────────────────────────────

class TestObserverAgentFunctional:
    """T-060 series: metric collection, alerting, rate, events."""

    def setup_method(self):
        self.agent = _ConcreteObserver(name="obs-func-01", archetype=AgentArchetype.OBSERVER)

    # T-061: initialize() sets READY
    @pytest.mark.asyncio
    async def test_initialize_sets_ready(self):
        await self.agent.initialize()
        assert self.agent.status == AgentStatus.READY

    # T-062: record() increments total count
    def test_record_increments_total_metrics(self):
        before = self.agent.stats["total_recorded"]
        self.agent.record(Metric("cpu", 42.0))
        assert self.agent.stats["total_recorded"] == before + 1

    # T-063: get_metric_stats returns empty dict for unknown metric
    def test_get_metric_stats_unknown_returns_empty(self):
        result = self.agent.get_metric_stats("ghost_metric")
        assert result == {}

    # T-064: get_metric_stats returns correct aggregates
    def test_get_metric_stats_correct_aggregates(self):
        for val in [10.0, 20.0, 30.0]:
            self.agent.record(Metric("temperature", val))
        stats = self.agent.get_metric_stats("temperature")
        assert stats["min"] == 10.0
        assert stats["max"] == 30.0
        assert stats["avg"] == 20.0
        assert stats["latest"] == 30.0
        assert stats["count"] == 3.0

    # T-065: record_many records all metrics
    def test_record_many_records_all(self):
        metrics = [Metric("m1", float(i)) for i in range(5)]
        self.agent.record_many(metrics)
        assert self.agent.stats["total_recorded"] == 5

    # T-066: add_alert_rule fires alert when threshold exceeded (gt)
    def test_alert_fires_on_threshold_exceeded(self):
        rule = AlertRule(
            name="high-cpu",
            metric_name="cpu",
            threshold=80.0,
            severity=AlertSeverity.CRITICAL,
            message_template="CPU at {value:.0f}% (threshold: {threshold:.0f}%)",
            what_to_do="Scale out compute nodes.",
            comparison="gt",
            cooldown_seconds=0.0,
        )
        self.agent.add_alert_rule(rule)
        self.agent.record(Metric("cpu", 95.0))
        alerts = self.agent.get_active_alerts()
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.CRITICAL

    # T-067: alert does NOT fire when threshold not crossed
    def test_alert_does_not_fire_below_threshold(self):
        rule = AlertRule(
            name="high-mem",
            metric_name="mem",
            threshold=90.0,
            severity=AlertSeverity.WARNING,
            message_template="Memory high",
            what_to_do="Check for leaks.",
            comparison="gt",
            cooldown_seconds=0.0,
        )
        self.agent.add_alert_rule(rule)
        self.agent.record(Metric("mem", 50.0))
        assert len(self.agent.get_active_alerts()) == 0

    # T-068: alert callback is invoked when alert fires
    def test_alert_callback_invoked(self):
        callback = MagicMock()
        agent = _ConcreteObserver(
            name="obs-cb-01",
            archetype=AgentArchetype.OBSERVER,
            alert_callback=callback,
        )
        rule = AlertRule(
            name="low-disk",
            metric_name="disk",
            threshold=10.0,
            severity=AlertSeverity.WARNING,
            message_template="Disk low: {value:.0f}GB",
            what_to_do="Free up disk space.",
            comparison="lt",
            cooldown_seconds=0.0,
        )
        agent.add_alert_rule(rule)
        agent.record(Metric("disk", 5.0))
        callback.assert_called_once()
        fired_alert = callback.call_args[0][0]
        assert isinstance(fired_alert, Alert)

    # T-069: cooldown prevents double-firing within window
    def test_alert_cooldown_prevents_double_fire(self):
        rule = AlertRule(
            name="spam-guard",
            metric_name="errors",
            threshold=5.0,
            severity=AlertSeverity.WARNING,
            message_template="Errors: {value}",
            what_to_do="Check error logs.",
            comparison="gt",
            cooldown_seconds=9999.0,  # very long cooldown
        )
        self.agent.add_alert_rule(rule)
        self.agent.record(Metric("errors", 10.0))  # fires
        self.agent.record(Metric("errors", 15.0))  # blocked by cooldown
        assert self.agent.stats["total_alerts_fired"] == 1

    # T-070: alert resolves when condition clears
    def test_alert_resolves_when_condition_clears(self):
        rule = AlertRule(
            name="temp-high",
            metric_name="temp",
            threshold=75.0,
            severity=AlertSeverity.WARNING,
            message_template="Temp {value}C",
            what_to_do="Check cooling.",
            comparison="gt",
            cooldown_seconds=0.0,
        )
        self.agent.add_alert_rule(rule)
        self.agent.record(Metric("temp", 80.0))  # fires
        assert len(self.agent.get_active_alerts()) == 1
        self.agent.record(Metric("temp", 60.0))  # resolves
        assert len(self.agent.get_active_alerts()) == 0

    # T-071: get_rate returns 0.0 with fewer than 2 samples
    def test_get_rate_insufficient_samples_returns_zero(self):
        self.agent.record(Metric("events", 1.0))
        rate = self.agent.get_rate("events", window_seconds=60.0)
        assert rate == 0.0

    # T-072: get_rate returns 0.0 for unknown metric
    def test_get_rate_unknown_metric_returns_zero(self):
        assert self.agent.get_rate("ghost_metric") == 0.0

    # T-073: log_event stores event in event log
    def test_log_event_stored_in_log(self):
        self.agent.log_event("task_complete", {"task_id": "abc123", "duration_ms": 42})
        assert self.agent.stats["event_log_size"] == 1

    # T-074: stats property reflects current state
    def test_stats_reflects_rules_and_metrics(self):
        self.agent.record(Metric("x", 1.0))
        rule = AlertRule(
            name="x-high", metric_name="x", threshold=0.5, severity=AlertSeverity.INFO,
            message_template="{value}", what_to_do="OK", comparison="gt", cooldown_seconds=0.0
        )
        self.agent.add_alert_rule(rule)
        stats = self.agent.stats
        assert stats["metrics_tracked"] >= 1
        assert stats["alert_rules"] >= 1
        assert stats["total_recorded"] >= 1

    # T-075: AlertRule.evaluate respects all comparison operators
    @pytest.mark.parametrize("comparison,value,threshold,expected", [
        ("gt",  10.0, 5.0,  True),
        ("gt",  3.0,  5.0,  False),
        ("lt",  3.0,  5.0,  True),
        ("lt",  10.0, 5.0,  False),
        ("eq",  5.0,  5.0,  True),
        ("eq",  4.9,  5.0,  False),
        ("gte", 5.0,  5.0,  True),
        ("gte", 4.9,  5.0,  False),
        ("lte", 5.0,  5.0,  True),
        ("lte", 5.1,  5.0,  False),
    ])
    def test_alert_rule_evaluate_operators(self, comparison, value, threshold, expected):
        rule = AlertRule(
            name="op-test", metric_name="x", threshold=threshold,
            severity=AlertSeverity.INFO, message_template="",
            what_to_do="", comparison=comparison, cooldown_seconds=0.0,
        )
        assert rule.evaluate(value) is expected

    # T-076: Alert.summary includes severity and metric name
    def test_alert_summary_format(self):
        alert = Alert(
            alert_id="a-001",
            severity=AlertSeverity.CRITICAL,
            metric_name="cpu",
            current_value=95.0,
            threshold=80.0,
            message="CPU at 95%",
            what_to_do="Scale out.",
        )
        summary = alert.summary
        assert "CRITICAL" in summary
        assert "cpu" in summary

    # T-077: Alert.resolve marks as resolved
    def test_alert_resolve_sets_flag(self):
        alert = Alert(
            alert_id="a-002",
            severity=AlertSeverity.WARNING,
            metric_name="mem",
            current_value=95.0,
            threshold=90.0,
            message="High mem",
            what_to_do="Check leaks.",
        )
        assert not alert.resolved
        alert.resolve()
        assert alert.resolved
        assert "RESOLVED" in alert.summary

    # T-078: window_size caps stored metric samples
    def test_window_size_caps_metric_storage(self):
        small_agent = _ConcreteObserver(
            name="obs-small", archetype=AgentArchetype.OBSERVER, window_size=3
        )
        for i in range(10):
            small_agent.record(Metric("val", float(i)))
        # The deque caps at window_size
        stats = small_agent.get_metric_stats("val")
        assert stats["count"] == 3.0
        assert stats["latest"] == 9.0


# ─────────────────────────────────────────────────────────────────────────────
# T-100  WorkerAgent
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkerAgentFunctional:
    """T-100 series: task execution, retry, timeout, hyperfocus, queue."""

    def setup_method(self):
        self.agent = _ConcreteWorker(name="worker-func-01", archetype=AgentArchetype.WORKER)

    # T-101: initialize() sets READY
    @pytest.mark.asyncio
    async def test_initialize_sets_ready(self):
        await self.agent.initialize()
        assert self.agent.status == AgentStatus.READY

    # T-102: execute_task with sync handler succeeds and returns TaskResult
    @pytest.mark.asyncio
    async def test_execute_task_sync_handler_succeeds(self):
        task = Task(name="sync-job", handler=lambda: {"processed": True})
        result = await self.agent.execute_task(task)
        assert isinstance(result, TaskResult)
        assert result.success is True
        assert result.result == {"processed": True}

    # T-103: execute_task with async handler succeeds
    @pytest.mark.asyncio
    async def test_execute_task_async_handler_succeeds(self):
        async def async_handler():
            await asyncio.sleep(0)
            return {"async": "done"}

        task = Task(name="async-job", handler=async_handler)
        result = await self.agent.execute_task(task)
        assert result.success is True
        assert result.result == {"async": "done"}

    # T-104: TaskResult.summary format is predictable
    @pytest.mark.asyncio
    async def test_task_result_summary_format(self):
        task = Task(name="summarise-me", handler=lambda: 42)
        result = await self.agent.execute_task(task)
        assert result.success is True
        assert "[OK]" in result.summary
        assert "summarise-me" in result.summary

    # T-105: failed task summary shows FAILED
    def test_task_result_failed_summary(self):
        result = TaskResult(task_id="x", task_name="broken-job", success=False, error="oops")
        assert "[FAILED]" in result.summary
        assert "broken-job" in result.summary

    # T-106: Task auto-sets description from name
    def test_task_auto_description(self):
        task = Task(name="auto-desc", handler=lambda: None)
        assert "auto-desc" in task.description

    # T-107: Task generates unique task_id
    def test_task_unique_ids(self):
        ids = {Task(name="t", handler=lambda: None).task_id for _ in range(10)}
        assert len(ids) == 10

    # T-108: handler that raises an exception returns failed TaskResult
    @pytest.mark.asyncio
    async def test_execute_task_exception_returns_failed(self):
        call_count = {"n": 0}

        def failing_handler():
            call_count["n"] += 1
            raise RuntimeError("deliberate failure")

        task = Task(name="fail-job", handler=failing_handler, max_retries=0)
        result = await self.agent.execute_task(task)
        assert result.success is False
        assert result.error is not None
        assert call_count["n"] == 1

    # T-109: retry succeeds on second attempt
    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self):
        attempt = {"n": 0}

        def flaky_handler():
            attempt["n"] += 1
            if attempt["n"] < 2:
                raise RuntimeError("first attempt fails")
            return "recovered"

        task = Task(name="flaky-job", handler=flaky_handler, max_retries=2)
        result = await self.agent.execute_task(task)
        assert result.success is True
        assert result.retries_used == 1
        assert result.result == "recovered"

    # T-110: max retries exceeded returns failure
    @pytest.mark.asyncio
    async def test_max_retries_exceeded_returns_failure(self):
        def always_fails():
            raise RuntimeError("always bad")

        task = Task(name="doomed", handler=always_fails, max_retries=1)
        result = await self.agent.execute_task(task)
        assert result.success is False
        assert result.retries_used == 1

    # T-111: timeout returns failed TaskResult with clear message
    @pytest.mark.asyncio
    async def test_timeout_returns_failed_result(self):
        async def slow_handler():
            await asyncio.sleep(10)

        task = Task(name="slow-job", handler=slow_handler, timeout=0.05, max_retries=0)
        result = await self.agent.execute_task(task)
        assert result.success is False
        assert "timed out" in result.error.lower()

    # T-112: hyperfocus mode blocks second concurrent task
    @pytest.mark.asyncio
    async def test_hyperfocus_blocks_second_task(self):
        hyperfocus_agent = _ConcreteWorker(
            name="hyper-01", archetype=AgentArchetype.WORKER, hyperfocus_mode=True
        )
        # Simulate an active task already in place
        dummy_task = Task(name="active", handler=lambda: None)
        hyperfocus_agent._active_tasks["fake-id"] = dummy_task

        blocked_task = Task(name="blocked", handler=lambda: None)
        result = await hyperfocus_agent.execute_task(blocked_task)
        assert result.success is False
        assert "hyperfocus" in result.error.lower()

    # T-113: enqueue adds task and increments queue size
    def test_enqueue_adds_to_queue(self):
        task = Task(name="queued-job", handler=lambda: None, priority=TaskPriority.HIGH)
        self.agent.enqueue(task)
        assert self.agent._task_queue.qsize() == 1

    # T-114: run_queue processes all queued tasks
    @pytest.mark.asyncio
    async def test_run_queue_processes_all(self):
        for i in range(3):
            self.agent.enqueue(Task(name=f"q-job-{i}", handler=lambda: f"done-{i}"))
        results = await self.agent.run_queue()
        assert len(results) == 3
        assert all(r.success for r in results)

    # T-115: HYPERFOCUS priority queued before NORMAL
    @pytest.mark.asyncio
    async def test_queue_priority_order(self):
        order = []

        def make_handler(label):
            def h():
                order.append(label)
            return h

        self.agent.enqueue(Task(name="normal", handler=make_handler("normal"), priority=TaskPriority.NORMAL))
        self.agent.enqueue(Task(name="hyper",  handler=make_handler("hyper"),  priority=TaskPriority.HYPERFOCUS))
        await self.agent.run_queue()
        assert order[0] == "hyper"
        assert order[1] == "normal"

    # T-116: stats success_rate is 100% when all tasks succeed
    @pytest.mark.asyncio
    async def test_stats_success_rate_all_pass(self):
        task = Task(name="pass-all", handler=lambda: "ok")
        await self.agent.execute_task(task)
        stats = self.agent.stats
        assert stats["success_rate"] == "100.0%"

    # T-117: stats success_rate is 0% when all tasks fail
    @pytest.mark.asyncio
    async def test_stats_success_rate_all_fail(self):
        def fails():
            raise RuntimeError("nope")
        task = Task(name="fail-all", handler=fails, max_retries=0)
        await self.agent.execute_task(task)
        stats = self.agent.stats
        assert stats["success_rate"] == "0.0%"

    # T-118: duration_ms is populated and > 0
    @pytest.mark.asyncio
    async def test_task_result_duration_populated(self):
        task = Task(name="timed-job", handler=lambda: "done")
        result = await self.agent.execute_task(task)
        assert result.duration_ms >= 0.0

    # T-119: stats hyperfocus_mode reflects constructor flag
    def test_stats_reflects_hyperfocus_flag(self):
        hf_agent = _ConcreteWorker(
            name="hf-stats", archetype=AgentArchetype.WORKER, hyperfocus_mode=True
        )
        assert hf_agent.stats["hyperfocus_mode"] is True
        assert self.agent.stats["hyperfocus_mode"] is False


# ─────────────────────────────────────────────────────────────────────────────
# T-140  Integration
# ─────────────────────────────────────────────────────────────────────────────

class TestHyperAgentIntegration:
    """T-140 series: multi-agent coordination flows."""

    # T-141: Architect creates goal, Worker executes step handler
    @pytest.mark.asyncio
    async def test_architect_assigns_step_to_worker(self):
        architect = _ConcreteArchitect(name="integ-arch", archetype=AgentArchetype.ARCHITECT)
        worker = _ConcreteWorker(name="integ-worker", archetype=AgentArchetype.WORKER)
        await architect.initialize()
        await worker.initialize()

        architect.register_agent("integ-worker", AgentArchetype.WORKER)

        gid = architect.create_goal("Deploy pipeline")
        s1 = architect.add_step(gid, "Build image", assigned_to="integ-worker")

        task = Task(
            name="build-image",
            handler=lambda: {"image": "app:latest", "pushed": True},
            description="Build Docker image for deploy",
        )
        result = await worker.execute_task(task)
        assert result.success is True

        architect.complete_step(gid, s1)
        assert architect.goal_progress(gid) == 1.0

    # T-142: Observer records Worker metrics and fires alert
    @pytest.mark.asyncio
    async def test_observer_watches_worker_and_fires_alert(self):
        fired_alerts: list[Alert] = []

        observer = _ConcreteObserver(
            name="integ-obs",
            archetype=AgentArchetype.OBSERVER,
            alert_callback=lambda a: fired_alerts.append(a),
        )
        worker = _ConcreteWorker(name="integ-worker-2", archetype=AgentArchetype.WORKER)

        await observer.initialize()
        await worker.initialize()

        observer.add_alert_rule(AlertRule(
            name="high-failure-rate",
            metric_name="task_failures",
            threshold=2.0,
            severity=AlertSeverity.CRITICAL,
            message_template="Task failures: {value}",
            what_to_do="Check worker logs and reduce concurrency.",
            comparison="gte",
            cooldown_seconds=0.0,
        ))

        # Simulate 3 task failures
        for _ in range(3):
            def fails():
                raise RuntimeError("simulated failure")
            task = Task(name="fail-task", handler=fails, max_retries=0)
            await worker.execute_task(task)
            observer.record(Metric("task_failures", float(worker.stats["total_executed"])))

        assert len(fired_alerts) >= 1
        assert fired_alerts[0].severity == AlertSeverity.CRITICAL

    # T-143: Architect + Observer track goal progress together
    @pytest.mark.asyncio
    async def test_architect_progress_observed_correctly(self):
        architect = _ConcreteArchitect(name="integ-arch-2", archetype=AgentArchetype.ARCHITECT)
        observer = _ConcreteObserver(name="integ-obs-2", archetype=AgentArchetype.OBSERVER)
        await architect.initialize()
        await observer.initialize()

        gid = architect.create_goal("Multi-step deployment")
        steps = [architect.add_step(gid, f"Step {i}") for i in range(4)]

        for i, sid in enumerate(steps):
            architect.complete_step(gid, sid)
            progress = architect.goal_progress(gid)
            observer.record(Metric("goal_progress", progress))

        stats = observer.get_metric_stats("goal_progress")
        assert stats["latest"] == 1.0
        assert stats["min"] == 0.25
        goal = architect.get_goal(gid)
        assert goal.status == GoalStatus.COMPLETED
