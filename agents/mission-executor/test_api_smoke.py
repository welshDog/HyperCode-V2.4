"""HTTP and lifespan tests for mission-executor.

Pins the observable behaviour of the HTTP layer and of the app's lifespan (Redis subscription, the
background pub/sub task, clean shutdown) so a FastAPI / Starlette / pydantic upgrade that changes any
of it fails here. Redis and the agent delegator are replaced by in-memory fakes; the real lifespan runs.

Run: cd agents/mission-executor && python -m pytest -q
"""
from __future__ import annotations

import asyncio
import json
import queue
import time

import pytest
from fastapi.testclient import TestClient

import main
from models import ExecutionResult, ExecutionStatus


class FakePubSub:
    """The slice of redis.asyncio's PubSub the service uses; `listen()` yields what the test pushes."""

    def __init__(self) -> None:
        self.inbox: "queue.Queue[dict]" = queue.Queue()
        self.subscribed: list[str] = []
        self.unsubscribed: list[str] = []

    async def subscribe(self, channel: str) -> None:
        self.subscribed.append(channel)

    async def unsubscribe(self, channel: str) -> None:
        self.unsubscribed.append(channel)

    async def listen(self):
        while True:  # thread-safe polling: the app runs in TestClient's event-loop thread
            try:
                yield self.inbox.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.01)


class FakeRedis:
    def __init__(self) -> None:
        self._pubsub = FakePubSub()
        self.published: list[tuple[str, str]] = []
        self.closed = 0

    def pubsub(self) -> FakePubSub:
        return self._pubsub

    async def publish(self, channel: str, data: str) -> None:
        self.published.append((channel, data))

    async def close(self) -> None:
        self.closed += 1


class FakeDelegator:
    def __init__(self, *args, **kwargs) -> None:
        self.calls: list[str] = []

    async def execute_plan(self, mission_id, plan_request, timeout):
        self.calls.append(mission_id)
        if mission_id == "boom":
            raise RuntimeError("delegator exploded")
        return ExecutionResult(
            mission_id=mission_id,
            status=ExecutionStatus.COMPLETED,
            executed_actions=[{"action": "noop", "status": "completed"}],
            agent_outputs={"agent": "ok"},
        )


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(main.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(main, "AgentDelegator", FakeDelegator)
    return fake


@pytest.fixture
def client(fake_redis):
    with TestClient(main.app) as c:  # entering the context runs the real lifespan
        yield c


def wait_for(predicate, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.02)
    return False


VALID = {"mission_id": "m-1", "goal": "do a thing", "plan": {"requested_actions": []}}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "agent": "mission-executor"}


def test_execute_returns_the_result_and_publishes_it(client, fake_redis):
    response = client.post("/execute", json=VALID)
    assert response.status_code == 200
    body = response.json()
    assert body["mission_id"] == "m-1"
    assert body["status"] == "completed"
    assert body["executed_actions"] == [{"action": "noop", "status": "completed"}]
    assert body["agent_outputs"] == {"agent": "ok"}

    channel, payload = fake_redis.published[-1]
    assert channel == main.RESULT_CHANNEL
    assert json.loads(payload)["mission_id"] == "m-1"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"mission_id": "m-1"},
        {"mission_id": "m-1", "goal": "g", "plan": ["not", "a", "dict"]},
        {"mission_id": 123, "goal": "g", "plan": {}},
    ],
    ids=["empty", "missing-fields", "plan-wrong-type", "id-wrong-type"],
)
def test_execute_rejects_invalid_bodies(client, body):
    assert client.post("/execute", json=body).status_code == 422


def test_unknown_route_and_wrong_method(client):
    assert client.get("/nope").status_code == 404
    assert client.get("/execute").status_code == 405


def test_openapi_describes_the_service(client):
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "mission-executor"
    assert set(spec["paths"]) == {"/health", "/execute"}
    request_schema = spec["components"]["schemas"]["ExecutionRequest"]
    assert set(request_schema["required"]) == {"mission_id", "goal", "plan"}
    assert "example" in request_schema or "examples" in request_schema
    assert client.get("/docs").status_code == 200


def test_lifespan_subscribes_then_cleans_up(fake_redis):
    pubsub = fake_redis.pubsub()
    with TestClient(main.app) as c:
        assert c.get("/health").status_code == 200
        assert pubsub.subscribed == [main.EXECUTION_CHANNEL]
        task = main.app.state.execution_task
        assert not task.done()
    assert pubsub.unsubscribed == [main.EXECUTION_CHANNEL]
    assert fake_redis.closed >= 1
    assert task.cancelled() or task.done()


def test_a_published_request_is_executed_and_its_result_published(client, fake_redis):
    fake_redis.pubsub().inbox.put({"type": "message", "data": json.dumps({**VALID, "mission_id": "via-redis"})})
    assert wait_for(lambda: any(json.loads(p)["mission_id"] == "via-redis" for _, p in fake_redis.published))
    result = next(json.loads(p) for _, p in fake_redis.published if json.loads(p)["mission_id"] == "via-redis")
    assert result["status"] == "completed"


def test_bad_messages_do_not_stop_the_listener(client, fake_redis):
    inbox = fake_redis.pubsub().inbox
    inbox.put({"type": "subscribe", "data": 1})  # not a message: ignored
    inbox.put({"type": "message", "data": "this is not json"})  # logged, skipped
    inbox.put({"type": "message", "data": json.dumps({**VALID, "mission_id": "boom"})})  # delegator raises
    inbox.put({"type": "message", "data": json.dumps({**VALID, "mission_id": "after"})})  # still processed
    assert wait_for(lambda: any(json.loads(p)["mission_id"] == "after" for _, p in fake_redis.published))
    failed = [json.loads(p) for _, p in fake_redis.published if json.loads(p)["mission_id"] == "boom"]
    assert failed and failed[0]["status"] == "failed"
    assert "delegator exploded" in failed[0]["error_message"]


def test_models_round_trip_and_schema():
    result = ExecutionResult(mission_id="x", status=ExecutionStatus.TIMEOUT, error_message="slow")
    again = ExecutionResult.model_validate_json(result.model_dump_json())
    assert again == result
    schema = ExecutionResult.model_json_schema()
    assert schema["properties"]["status"]  # enum field present in the schema
    assert "example" in schema or "examples" in schema  # json_schema_extra still applied
