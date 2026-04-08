"""
╔══════════════════════════════════════════════════════╗
║   🧠 HYPER AGENTS — PROMETHEUS METRICS MODULE        ║
║   metrics.py — The Full Observability Brain          ║
║   Drop in: backend/ or agents/shared/                ║
╚══════════════════════════════════════════════════════╝
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
)

# ─────────────────────────────────────────────
# 🎯 KNOWN AGENTS — all 18 from your repo
# ─────────────────────────────────────────────
HYPER_AGENTS = [
    "frontend-specialist",
    "backend-specialist",
    "database-architect",
    "qa-engineer",
    "devops-engineer",
    "security-engineer",
    "system-architect",
    "project-strategist",
    "tips-tricks-writer",
    "architect",
    "broski-bot",
    "broski-nemoclaw",
    "crew-orchestrator",
    "healer",
    "memory",
    "super-hyper-broski",
    "throttle-agent",
    "agent-factory",
]

# ─────────────────────────────────────────────
# ⚡ 1. REQUEST COUNTERS
# ─────────────────────────────────────────────

agent_requests_total = Counter(
    "hyper_agent_requests_total",
    "Total requests handled per agent",
    ["agent_id", "env", "status"],  # status: success | error | timeout
)

agent_tasks_completed = Counter(
    "hyper_agent_tasks_completed_total",
    "Total tasks completed per agent",
    ["agent_id", "task_type"],
)

# ─────────────────────────────────────────────
# 🕐 2. LATENCY HISTOGRAMS
# ─────────────────────────────────────────────

agent_latency = Histogram(
    "hyper_agent_latency_seconds",
    "Agent response latency in seconds",
    ["agent_id", "route"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0],
)

llm_latency = Histogram(
    "llm_response_latency_seconds",
    "LLM response latency per model per agent",
    ["model", "agent_id"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0],
)

# ─────────────────────────────────────────────
# 💥 3. ERROR TRACKING
# ─────────────────────────────────────────────

agent_errors_total = Counter(
    "hyper_agent_errors_total",
    "Total errors per agent",
    ["agent_id", "error_type"],
    # error_type: timeout | llm_fail | tool_fail | memory_fail | crash
)

agent_error_rate = Gauge(
    "hyper_agent_error_rate",
    "Rolling error rate per agent (0.0 - 1.0)",
    ["agent_id"],
)

# ─────────────────────────────────────────────
# 📬 4. QUEUE + JOB TRACKING
# ─────────────────────────────────────────────

agent_queue_depth = Gauge(
    "hyper_agent_queue_depth",
    "Number of jobs waiting in queue",
    ["agent_id", "priority"],  # priority: high | normal | low
)

agent_jobs_in_flight = Gauge(
    "hyper_agent_jobs_in_flight",
    "Number of jobs actively being processed",
    ["agent_id"],
)

agent_job_wait_seconds = Histogram(
    "hyper_agent_job_wait_seconds",
    "Time jobs spend waiting before pickup",
    ["agent_id"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

# ─────────────────────────────────────────────
# 🤖 5. LLM / TOKEN METRICS
# ─────────────────────────────────────────────

llm_tokens_in = Counter(
    "llm_tokens_in_total",
    "Total prompt tokens sent to LLM",
    ["model", "agent_id", "workspace"],
)

llm_tokens_out = Counter(
    "llm_tokens_out_total",
    "Total completion tokens received from LLM",
    ["model", "agent_id", "workspace"],
)

llm_cost_estimate = Gauge(
    "llm_cost_estimate_usd",
    "Estimated LLM cost in USD (rolling)",
    ["model", "agent_id", "workspace"],
)

llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM API calls",
    ["model", "agent_id", "status"],  # status: success | error | ratelimit
)

llm_context_window_usage = Gauge(
    "llm_context_window_usage_pct",
    "Context window usage as % of max (0-100)",
    ["model", "agent_id"],
)

# ─────────────────────────────────────────────
# 🩺 6. HEALER AGENT METRICS
# ─────────────────────────────────────────────

healer_recoveries_total = Counter(
    "healer_recoveries_total",
    "Total services recovered by Healer Agent",
    ["service", "reason", "success"],
)

healer_checks_total = Counter(
    "healer_health_checks_total",
    "Total health checks performed",
    ["service", "result"],  # result: healthy | degraded | dead
)

healer_recovery_latency = Histogram(
    "healer_recovery_latency_seconds",
    "Time taken to recover a service",
    ["service"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

# ─────────────────────────────────────────────
# 🦅 7. AGENT X — META ARCHITECT METRICS
# ─────────────────────────────────────────────

agent_x_deployments = Counter(
    "agent_x_deployments_total",
    "Total agent deployments by Agent X",
    ["agent_type", "status"],  # status: success | failed | rollback
)

agent_x_evolution_cycles = Counter(
    "agent_x_evolution_cycles_total",
    "Times Agent X triggered self-evolution pipeline",
    ["trigger"],  # trigger: scheduled | anomaly | manual
)

agent_x_active_agents = Gauge(
    "agent_x_active_agents_count",
    "Number of agents currently active in the system",
    ["env"],
)

# ─────────────────────────────────────────────
# 🔬 8. NEMOCLAW — CODE HEALTH METRICS
# ─────────────────────────────────────────────

nemoclaw_health_score = Gauge(
    "nemoclaw_code_health_score",
    "NemoClaw code health score (0-100)",
    ["target_module", "scan_type"],
    # scan_type: ruff | secrets | ast | overall
)

nemoclaw_issues_found = Counter(
    "nemoclaw_issues_found_total",
    "Total code issues detected by NemoClaw",
    ["issue_type", "severity"],
    # issue_type: lint | secret | syntax | bare_except
    # severity: critical | warning | info
)

nemoclaw_scans_total = Counter(
    "nemoclaw_scans_total",
    "Total scans run by NemoClaw",
    ["trigger", "result"],
    # trigger: commit | scheduled | manual
)

# ─────────────────────────────────────────────
# 🎮 9. CREW ORCHESTRATOR METRICS
# ─────────────────────────────────────────────

crew_tasks_dispatched = Counter(
    "crew_tasks_dispatched_total",
    "Tasks dispatched by Crew Orchestrator",
    ["target_agent", "task_type"],
)

crew_routing_latency = Histogram(
    "crew_routing_latency_seconds",
    "Time to route a task to the right agent",
    ["routing_strategy"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

crew_agent_pool_size = Gauge(
    "crew_agent_pool_size",
    "Current size of available agent pool",
    ["agent_type"],
)

# ─────────────────────────────────────────────
# 💾 10. MEMORY AGENT METRICS
# ─────────────────────────────────────────────

memory_reads = Counter(
    "memory_agent_reads_total",
    "Memory agent context read operations",
    ["agent_id", "memory_type"],
    # memory_type: short_term | long_term | episodic
)

memory_writes = Counter(
    "memory_agent_writes_total",
    "Memory agent context write operations",
    ["agent_id", "memory_type"],
)

memory_hit_rate = Gauge(
    "memory_agent_hit_rate",
    "Cache hit rate for memory lookups (0.0-1.0)",
    ["agent_id"],
)

memory_size_bytes = Gauge(
    "memory_agent_size_bytes",
    "Total memory store size in bytes",
    ["memory_type"],
)

# ─────────────────────────────────────────────
# 🛡️ 11. THROTTLE AGENT METRICS
# ─────────────────────────────────────────────

throttle_blocks_total = Counter(
    "throttle_agent_blocks_total",
    "Total requests blocked by throttle agent",
    ["reason", "agent_id"],
    # reason: rate_limit | cost_cap | slo_risk | manual
)

throttle_active_limits = Gauge(
    "throttle_active_limits",
    "Number of active throttle rules",
    ["limit_type"],
)

# ─────────────────────────────────────────────
# 🏆 12. BROSKI$ GAMIFICATION METRICS
# ─────────────────────────────────────────────

broski_coins_earned = Counter(
    "broski_coins_earned_total",
    "BROski$ coins earned by agents/users",
    ["agent_id", "reason"],
)

broski_xp_total = Gauge(
    "broski_xp_total",
    "Total XP accumulated in system",
    ["agent_id"],
)

broski_level = Gauge(
    "broski_level",
    "Current BROski level per agent",
    ["agent_id"],
)

# ─────────────────────────────────────────────
# 🔧 HELPER — Instrument any agent in 1 line
# ─────────────────────────────────────────────

class AgentMetrics:
    """
    Drop-in metrics helper for any Hyper Agent.
    Usage:
        m = AgentMetrics("broski-nemoclaw")
        m.request("success")
        m.latency("/scan", 1.23)
        m.error("lint_fail")
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def request(self, status: str = "success", env: str = "prod") -> None:
        agent_requests_total.labels(
            agent_id=self.agent_id, env=env, status=status
        ).inc()

    def latency(self, route: str, duration: float) -> None:
        agent_latency.labels(
            agent_id=self.agent_id, route=route
        ).observe(duration)

    def error(self, error_type: str) -> None:
        agent_errors_total.labels(
            agent_id=self.agent_id, error_type=error_type
        ).inc()

    def queue(self, depth: int, priority: str = "normal") -> None:
        agent_queue_depth.labels(
            agent_id=self.agent_id, priority=priority
        ).set(depth)

    def llm_call(
        self,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost: float,
        workspace: str = "default",
    ) -> None:
        llm_tokens_in.labels(
            model=model, agent_id=self.agent_id, workspace=workspace
        ).inc(tokens_in)
        llm_tokens_out.labels(
            model=model, agent_id=self.agent_id, workspace=workspace
        ).inc(tokens_out)
        llm_cost_estimate.labels(
            model=model, agent_id=self.agent_id, workspace=workspace
        ).inc(cost)

    def nemoclaw_score(self, score: float, module: str = "all") -> None:
        nemoclaw_health_score.labels(
            target_module=module, scan_type="overall"
        ).set(score)

    def broski_win(self, coins: int = 10, reason: str = "task_complete") -> None:
        broski_coins_earned.labels(
            agent_id=self.agent_id, reason=reason
        ).inc(coins)
