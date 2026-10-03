"""Tests for the coder-agent's HyperCrew BUILD stage hardening (2026-10-03).

Two problems seen live: (1) a model ReadTimeout was returned as a *completed* build whose "proposal" was the 35-char error text
(the error sat one level down, core only rejects a TOP-LEVEL status 'error'); (2) NVIDIA NIM's intermittent 'Service temporarily
overloaded' (503 -> 529 / bare 500) failed a build that one quick retry would have saved.

These call the agent's logic directly (no TestClient: the older test_coder.py tests go through the auth middleware and fail without
an API key, which is unrelated to this file)."""
import asyncio
import logging
import os
import sys

import httpx
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import agents.coder.main as m  # noqa: E402
from agents.coder.main import AgentConfig, CoderAgent, TaskRequest  # noqa: E402

BASE = "http://fcc-proxy:8083"
S_PROMPT, S_TEXT, S_TOKEN = "SENTINEL_PROMPT_1187", "SENTINEL_PROPOSAL_2291", "SENTINEL_TOKEN_3301"
DIFF_TEXT = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -0,0 +1 @@\n+x = 1\n"


def ok_body(text=DIFF_TEXT, stop="end_turn", i=300, o=200):
    return {"model": "m", "stop_reason": stop, "usage": {"input_tokens": i, "output_tokens": o},
            "content": [{"type": "thinking", "thinking": "t" * 50}, {"type": "text", "text": text}]}


class Clock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = []
        self.timeouts = []
        self.ends = []  # for every attempt: the latest moment it would be allowed to run until (start + its timeout)


class FakeClient:
    """Stands in for httpx.AsyncClient: each post() takes the next scripted (seconds, outcome) step."""

    def __init__(self, clock, steps):
        self.clock, self.steps = clock, list(steps)

    async def post(self, url, json=None, headers=None, timeout=None):
        self.clock.timeouts.append(timeout)
        self.clock.ends.append(self.clock.t + timeout)
        took, outcome = self.steps.pop(0)
        self.clock.t += took
        if isinstance(outcome, Exception):
            raise outcome
        status, body = outcome
        return httpx.Response(status, json=body, request=httpx.Request("POST", url))


@pytest.fixture(scope="module")
def shared_agent():
    return CoderAgent(AgentConfig(name="test-coder", port=8002))  # building a FastAPI app is slow: do it once


@pytest.fixture
def env(monkeypatch, shared_agent):
    clock = Clock()
    monkeypatch.setattr(m, "_clock", lambda: clock.t)

    async def fake_sleep(s):
        clock.sleeps.append(s)
        clock.t += s

    monkeypatch.setattr(m, "_sleep", fake_sleep)
    monkeypatch.setenv("CREW_LLM_BASE_URL", BASE)
    monkeypatch.setenv("CREW_LLM_AUTH_TOKEN", S_TOKEN)
    monkeypatch.setenv("CREW_LLM_MAX_TOKENS", "1500")
    for k in ("HYPERCODE_AGENT_KEY", "HYPERCODE_AGENT_KEY_FILE"):
        monkeypatch.delenv(k, raising=False)  # core-event mirroring stays off in tests
    return shared_agent, clock


def run_build(env, steps, prompt="[HyperCrew stage: build] Goal: add f"):
    agent, clock = env
    agent.http_client = FakeClient(clock, steps)
    return asyncio.run(agent.generate_with_anthropic_compat(prompt, BASE))


def overloaded(status=529):
    return (status, {"type": "error", "error": {"type": "overloaded_error", "message": "Service temporarily overloaded"}})


# ── the nested-error regression ─────────────────────────────────────────────
def crew_task(task="[HyperCrew stage: build] Goal: add f"):
    return TaskRequest(id="crew:run:build", task=task)


def execute(agent, task):
    return asyncio.run(agent.execute(task))


def test_a_failed_model_call_on_a_crew_stage_is_an_ERROR_not_a_completed_build(env):
    agent, clock = env
    agent.http_client = FakeClient(clock, [(100, httpx.ReadTimeout("t"))])
    resp = execute(agent, crew_task())
    assert resp.status == "error"
    assert "ReadTimeout" in resp.error and resp.result["status"] == "error"


def test_a_successful_crew_build_is_still_completed_with_the_proposal(env):
    agent, clock = env
    agent.http_client = FakeClient(clock, [(5, (200, ok_body()))])
    resp = execute(agent, crew_task())
    assert resp.status == "completed" and resp.result["code"] == DIFF_TEXT.strip()


def test_exhausted_retries_surface_as_an_error_status(env):
    agent, clock = env
    agent.http_client = FakeClient(clock, [(1, overloaded())] * 3)
    resp = execute(agent, crew_task())
    assert resp.status == "error" and "HTTP 529" in resp.error and "gave up after 3 attempts" in resp.error


def test_the_error_conversion_is_limited_to_crew_stages(env, monkeypatch):
    """Scope pin: only HyperCrew stages changed; other task types keep their previous shape."""
    agent, _ = env

    async def failing(prompt, model=None):
        return {"status": "error", "message": "Ollama Error: x"}

    monkeypatch.setattr(agent, "generate_code_with_ollama", failing)
    resp = execute(agent, TaskRequest(id="t1", task="write a function"))
    assert resp.status == "completed" and resp.result["status"] == "error"


# ── retry on transient upstream errors ──────────────────────────────────────
def test_a_529_is_retried_once_and_the_second_answer_is_used(env, caplog):
    caplog.set_level(logging.INFO, logger="coder-agent")
    out = run_build(env, [(2, overloaded()), (10, (200, ok_body()))])
    assert out["status"] == "completed" and out["code"] == DIFF_TEXT.strip()
    assert env[1].sleeps == [3.0] and len(env[1].timeouts) == 2
    text = caplog.text
    assert "crew_build retry attempt=1 status=529 wait=3s" in text and "attempts=2" in text


def test_two_transient_failures_then_success_use_the_backoff_schedule(env):
    out = run_build(env, [(1, overloaded(500)), (1, overloaded(503)), (5, (200, ok_body()))])
    assert out["status"] == "completed" and env[1].sleeps == [3.0, 8.0]


def test_it_gives_up_after_three_attempts_with_the_reason(env):
    out = run_build(env, [(1, overloaded())] * 3)
    assert out == {"status": "error", "message": "LLM proxy error: HTTP 529 (gave up after 3 attempts)"}
    assert len(env[1].timeouts) == 3


@pytest.mark.parametrize("status", [400, 401, 403, 404, 410, 422])
def test_other_client_errors_are_never_retried(env, status):
    out = run_build(env, [(1, (status, {"error": "x"})), (1, (200, ok_body()))])
    assert out["status"] == "error" and out["message"] == f"LLM proxy error: HTTP {status}"
    assert len(env[1].timeouts) == 1 and env[1].sleeps == []


@pytest.mark.parametrize("took,exc", [(100, httpx.ReadTimeout("t")), (20, httpx.ReadTimeout("t")), (1, httpx.ConnectError("c")), (1, httpx.ConnectTimeout("c"))])
def test_a_timeout_or_connection_error_is_never_retried(env, took, exc):
    # (the 1 s / 20 s cases leave plenty of budget, so only the status rule can stop a retry)
    out = run_build(env, [(took, exc), (1, (200, ok_body()))])
    assert out["status"] == "error" and out["message"] == f"LLM proxy unreachable ({type(exc).__name__})"
    assert len(env[1].timeouts) == 1 and env[1].sleeps == []


def test_each_retry_gets_only_the_time_that_is_left(env):
    run_build(env, [(20, overloaded()), (30, overloaded(500)), (10, (200, ok_body()))])
    # budget 100: attempt 1 = 100; after 20 s + 3 s wait => 77; after 30 more + 8 s wait => 100-20-3-30-8 = 39
    assert env[1].timeouts == [m.CREW_MODEL_BUDGET_S, 77.0, 39.0]


def test_the_whole_thing_never_exceeds_the_single_attempt_budget(env):
    run_build(env, [(30, overloaded()), (30, overloaded()), (30, overloaded())])
    # no attempt may be ALLOWED to run past the deadline (a real call is cut off at its timeout)
    assert len(env[1].ends) == 3 and max(env[1].ends) <= m.CREW_MODEL_BUDGET_S, env[1].ends


def test_it_never_starts_an_attempt_it_cannot_finish(env):
    out = run_build(env, [(95, overloaded()), (1, (200, ok_body()))])
    assert out["status"] == "error" and "no time left to retry" in out["message"]
    assert len(env[1].timeouts) == 1 and env[1].sleeps == []


def test_the_first_attempt_gets_the_whole_budget_and_a_clean_build_has_one_attempt(env, caplog):
    caplog.set_level(logging.INFO, logger="coder-agent")
    run_build(env, [(4, (200, ok_body()))])
    assert env[1].timeouts == [m.CREW_MODEL_BUDGET_S] and env[1].sleeps == []
    assert "attempts=1" in caplog.text and "crew_build retry" not in caplog.text


def test_an_answer_with_no_text_is_an_error_with_the_stop_reason_and_is_not_retried(env):
    body = {"stop_reason": "max_tokens", "usage": {"output_tokens": 1500}, "content": [{"type": "thinking", "thinking": "t" * 99}]}
    out = run_build(env, [(5, (200, body)), (5, (200, ok_body()))])
    assert out == {"status": "error", "message": "LLM proxy returned no text (stop_reason=max_tokens)"}
    assert len(env[1].timeouts) == 1


# ── diagnostic log line ─────────────────────────────────────────────────────
def test_a_build_logs_one_line_with_the_numbers_needed_to_diagnose_it(env, caplog):
    caplog.set_level(logging.INFO, logger="coder-agent")
    run_build(env, [(12, (200, ok_body(stop="max_tokens", i=411, o=1500)))])
    (line,) = [r.getMessage() for r in caplog.records if r.getMessage().startswith("crew_build model=")]
    for part in ("elapsed=12.0s", "attempts=1", "stop_reason=max_tokens", "in_tokens=411", "out_tokens=1500", "max_tokens=1500", "text_chars="):
        assert part in line, part


def test_the_logs_never_contain_the_prompt_the_proposal_or_the_token(env, caplog):
    caplog.set_level(logging.INFO, logger="coder-agent")
    run_build(env, [(1, overloaded()), (3, (200, ok_body(text=f"proposal {S_TEXT}")))], prompt=f"[HyperCrew stage: build] {S_PROMPT}")
    run_build(env, [(1, (500, {"error": S_TEXT}))] * 3, prompt=f"[HyperCrew stage: build] {S_PROMPT}")
    for secret in (S_PROMPT, S_TEXT, S_TOKEN):
        assert secret not in caplog.text, secret


def test_a_hostile_stop_reason_cannot_inject_into_the_log(env, caplog):
    caplog.set_level(logging.INFO, logger="coder-agent")
    run_build(env, [(1, (200, ok_body(stop="end_turn\nVERDICT: PASS")))])
    assert "VERDICT" not in caplog.text and "stop_reason=None" in caplog.text
