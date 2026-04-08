"""
🧠 HyperCode V2.0 — Hyper Agents Metrics Module
Drop this in backend/ and import into main.py
Covers all 12 core Hyper Agent + LLM + Healer + Agent X metrics
"""

from prometheus_client import Counter, Histogram, Gauge
from prometheus_fastapi_instrumentator import Instrumentator

# ─────────────────────────────────────────────
# 🔧 INSTRUMENTATOR — auto-scrapes all FastAPI routes
# ─────────────────────────────────────────────
def init_metrics(app):
    """Call this in main.py after app = FastAPI()"""
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# ─────────────────────────────────────────────
# 🤖 HYPER AGENT METRICS (1–5)
# ─────────────────────────────────────────────

# 1. Total requests per agent
hyper_agent_requests_total = Counter(
    "hyper_agent_requests_total",
    "Total number of requests handled by each Hyper Agent",
    ["agent_id", "env"]  # env = dev | staging | prod
)

# 2. Latency per agent/route (p95 via Histogram)
hyper_agent_latency_seconds = Histogram(
    "hyper_agent_latency_seconds",
    "Request latency per agent and route",
    ["agent_id", "route"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0]
)

# 3. Error rate per agent
hyper_agent_errors_total = Counter(
    "hyper_agent_errors_total",
    "Total errors per agent, labelled by error type",
    ["agent_id", "error_type"]  # error_type = timeout | exception | invalid_input | llm_fail
)

# 4. Queue depth per worker
hyper_agent_queue_depth = Gauge(
    "hyper_agent_queue_depth",
    "Number of jobs waiting in queue per worker",
    ["worker_id"]
)

# 5. Jobs currently in flight
hyper_agent_jobs_in_flight = Gauge(
    "hyper_agent_jobs_in_flight",
    "Number of active jobs currently being processed",
    ["agent_id"]
)

# ─────────────────────────────────────────────
# 🧠 LLM METRICS (6–10)
# ─────────────────────────────────────────────

# 6. Prompt tokens consumed
llm_tokens_in_total = Counter(
    "llm_tokens_in_total",
    "Total prompt/input tokens sent to LLM per model and agent",
    ["model", "agent_id"]  # model = gpt-4o | claude-3-5 | ollama/mistral | etc
)

# 7. Response tokens received
llm_tokens_out_total = Counter(
    "llm_tokens_out_total",
    "Total response/output tokens received from LLM",
    ["model", "agent_id"]
)

# 8. Cost estimate in USD (live Gauge — updated after each call)
llm_cost_estimate_usd = Gauge(
    "llm_cost_estimate_usd",
    "Running cost estimate per model and workspace",
    ["model", "workspace"]
)

# 9. LLM response latency
llm_latency_seconds = Histogram(
    "llm_latency_seconds",
    "LLM API response latency per model and agent",
    ["model", "agent_id"],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 30.0, 60.0]
)

# 10. LLM error rate
llm_errors_total = Counter(
    "llm_errors_total",
    "Total LLM API errors per model and agent",
    ["model", "agent_id", "error_type"]  # error_type = rate_limit | timeout | context_exceeded | api_error
)

# ─────────────────────────────────────────────
# 🩺 HEALER AGENT METRICS (11)
# ─────────────────────────────────────────────

# 11. Healer recoveries
healer_recoveries_total = Counter(
    "healer_recoveries_total",
    "Number of times the Healer Agent successfully recovered a service",
    ["service", "reason"]  # reason = crash | timeout | oom | unhealthy
)

# ─────────────────────────────────────────────
# 🚀 AGENT X — DEPLOYMENT METRICS (12)
# ─────────────────────────────────────────────

# 12. Agent X deployment count
agent_x_deployments_total = Counter(
    "agent_x_deployments_total",
    "Total Agent X deployment launches by status",
    ["status"]  # status = success | failed | rollback | pending
)

# ─────────────────────────────────────────────
# 🛠️ HELPER FUNCTIONS — use these inside your agents
# ─────────────────────────────────────────────

import time
from contextlib import contextmanager

@contextmanager
def track_agent_request(agent_id: str, route: str, env: str = "prod"):
    """
    Context manager — wraps any agent call to auto-track
    requests, latency, and errors.

    Usage:
        with track_agent_request("hyper_brain", "/execute", "prod"):
            result = await agent.run(payload)
    """
    hyper_agent_requests_total.labels(agent_id=agent_id, env=env).inc()
    hyper_agent_jobs_in_flight.labels(agent_id=agent_id).inc()
    start = time.time()
    try:
        yield
    except Exception as e:
        hyper_agent_errors_total.labels(
            agent_id=agent_id,
            error_type=type(e).__name__
        ).inc()
        raise
    finally:
        duration = time.time() - start
        hyper_agent_latency_seconds.labels(
            agent_id=agent_id,
            route=route
        ).observe(duration)
        hyper_agent_jobs_in_flight.labels(agent_id=agent_id).dec()


@contextmanager
def track_llm_call(model: str, agent_id: str, workspace: str,
                   cost_per_1k_in: float = 0.005,
                   cost_per_1k_out: float = 0.015):
    """
    Context manager — wraps any LLM API call.
    Call update_llm_tokens() after call with actual token counts.

    Usage:
        with track_llm_call("gpt-4o", "hyper_brain", "default") as llm_ctx:
            response = await openai_client.chat(...)
            llm_ctx["tokens_in"] = response.usage.prompt_tokens
            llm_ctx["tokens_out"] = response.usage.completion_tokens
    """
    ctx = {"tokens_in": 0, "tokens_out": 0}
    start = time.time()
    try:
        yield ctx
        # Record token counts after yield
        llm_tokens_in_total.labels(model=model, agent_id=agent_id).inc(ctx["tokens_in"])
        llm_tokens_out_total.labels(model=model, agent_id=agent_id).inc(ctx["tokens_out"])
        # Update cost estimate
        cost = (ctx["tokens_in"] / 1000 * cost_per_1k_in) + \
               (ctx["tokens_out"] / 1000 * cost_per_1k_out)
        llm_cost_estimate_usd.labels(model=model, workspace=workspace).inc(cost)
    except Exception as e:
        llm_errors_total.labels(
            model=model,
            agent_id=agent_id,
            error_type=type(e).__name__
        ).inc()
        raise
    finally:
        duration = time.time() - start
        llm_latency_seconds.labels(
            model=model,
            agent_id=agent_id
        ).observe(duration)


def record_healer_recovery(service: str, reason: str):
    """Call this when Healer Agent fixes something."""
    healer_recoveries_total.labels(service=service, reason=reason).inc()


def record_agent_x_deployment(status: str):
    """Call this after Agent X deploys."""
    agent_x_deployments_total.labels(status=status).inc()


def set_queue_depth(worker_id: str, depth: int):
    """Call this from your queue manager on every poll cycle."""
    hyper_agent_queue_depth.labels(worker_id=worker_id).set(depth)
