"""Pytest configuration and fixtures for HyperCode tests."""

import asyncio
import os
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ["ENVIRONMENT"] = "test"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import redis.asyncio as redis

# Import your app modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
def mock_PERPLEXITY_API_KEY(monkeypatch):
    """Mock PERPLEXITY API key for tests."""
    monkeypatch.setenv("PERPLEXITY_API_KEY", "sk-ant-test-key-12345")


@pytest.fixture(scope="function")
def mock_openai_api_key(monkeypatch):
    """Mock OpenAI API key for tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-test-key-12345")
