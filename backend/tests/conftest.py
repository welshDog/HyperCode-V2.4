"""Pytest configuration and fixtures for HyperCode tests."""

import os
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ["ENVIRONMENT"] = "test"
os.environ["HYPERFLOW_RECOVERY"] = "0"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import redis.asyncio as redis

# Import your app modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.config import settings
from app.db.base_class import Base
from app.db.session import get_db
import app.models.models as _models
del _models

# Use in-memory SQLite for tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

@pytest.fixture(scope="function")
def db():
    """Create a new database for each test."""
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session):
    """Create test client with dependency override."""
    def override_get_db():
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def redis_client():
    """Create Redis test client."""
    client = await redis.from_url(
        settings.HYPERCODE_REDIS_URL,
        decode_responses=True
    )
    yield client
    await client.close()



@pytest.fixture(scope="function")
def mock_openai_api_key(monkeypatch):
    """Mock OpenAI API key for tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-test-key-12345")


@pytest.fixture
def hf_db(monkeypatch):
    """In-memory SQLite holding only ``hyperflow_runs``, patched into the HyperFlow runner."""
    from sqlalchemy.pool import StaticPool

    from app.models.hyperflow import HyperFlowRun

    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    HyperFlowRun.__table__.create(bind=eng)
    factory = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    monkeypatch.setattr("app.agents.hyperflow_runner.SessionLocal", factory)
    monkeypatch.setattr("app.broski_operator.recovery.SessionLocal", factory)
    yield factory
    eng.dispose()


# ── HyperCrew test fixtures (shared by test_crew_*.py) ──────────────────────────
@pytest.fixture
def ledger_db(monkeypatch):
    """An in-memory Governance Ledger the crew tools write to."""
    from sqlalchemy.pool import StaticPool

    from app.crew import tools as crew_tools
    from app.models.governance import GovernanceLedger

    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    GovernanceLedger.__table__.create(bind=eng)
    factory = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    monkeypatch.setattr(crew_tools, "SessionLocal", factory)
    yield factory
    eng.dispose()


@pytest.fixture
def slot_gate():
    """A fresh, RAM-check-free slot gate so tests don't depend on the host's memory."""
    from app.crew.slots import SlotGate, set_slot_gate

    gate = SlotGate(cap=3, min_available_mb=0, poll_s=0.005)
    set_slot_gate(gate)
    yield gate
    set_slot_gate(None)


def _rate_limit_layer(application):
    layer = getattr(application, "middleware_stack", None)
    while layer is not None:
        if layer.__class__.__name__ == "RateLimitMiddleware":
            return layer
        layer = getattr(layer, "app", None)
    return None


@pytest.fixture
def no_rate_limit(client, monkeypatch):
    """The app's per-path limiter (120/min) is shared by the whole test process; polling proofs would trip it."""
    layer = _rate_limit_layer(app)
    if layer is not None:
        import dataclasses

        monkeypatch.setattr(layer, "_config", dataclasses.replace(layer._config, enabled=False))


@pytest.fixture
def real_runner(db, monkeypatch, slot_gate, no_rate_limit):
    """Point every runner-side DB use at the test database; silence only the network fan-out.

    Real: runner, recovery, run rows, operator API. Faked: the orchestrator hop, Redis fan-out, Safety Shepherd.
    """
    import app.agents.hyperflow_runner as runner_mod
    import app.broski_operator.recovery as recovery_mod
    from app.crew import dispatch as crew_dispatch
    from app.crew import tools as crew_tools
    from tests.test_crew_operator_api import _fake_dispatch

    factory = sessionmaker(bind=db.get_bind(), autoflush=False, autocommit=False)
    for mod in (runner_mod, recovery_mod, crew_tools):
        monkeypatch.setattr(mod, "SessionLocal", factory)
    monkeypatch.setattr("app.db.session.SessionLocal", factory)  # the panic ledger write

    async def noop(*_a, **_k):
        return None

    monkeypatch.setattr(runner_mod.HyperFlowRunner, "_publish", noop)
    monkeypatch.setattr(runner_mod.HyperFlowRunner, "_publish_approval_request", noop)
    monkeypatch.setattr(runner_mod, "APPROVAL_POLL_SECONDS", 0.05)
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "off")
    monkeypatch.setattr(crew_dispatch, "dispatch_to_agent", _fake_dispatch())
    return factory
