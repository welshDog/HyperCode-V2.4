import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.economy import router as economy_router
from app.core.config import settings
from app.db.base_class import Base
from app.db.session import get_db
from app.models.broski import CourseSyncEvent
from app.models.models import User


@pytest.mark.asyncio
async def test_award_from_course_smoke_idempotent(monkeypatch):
    monkeypatch.setattr(settings, "COURSE_SYNC_SECRET", "test_sync_secret")

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    assert CourseSyncEvent.__tablename__ == "course_sync_events"
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        user = User(
            email="bro@example.com",
            hashed_password="not-used-in-this-test",
            discord_id="discord_123",
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        db.commit()

        app = FastAPI()
        app.include_router(economy_router, prefix="/api/v1/economy")

        def override_get_db():
            session = TestingSessionLocal()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "source_id": "source_abc",
                "discord_id": "discord_123",
                "tokens": 25,
                "reason": "smoke test",
            }

            resp1 = await ac.post(
                "/api/v1/economy/award-from-course",
                json=payload,
                headers={"X-Sync-Secret": "test_sync_secret"},
            )
            assert resp1.status_code == 200
            data1 = resp1.json()
            assert data1["awarded"] is True
            assert data1["coins_balance"] == 25
            assert data1["source_id"] == "source_abc"

            resp2 = await ac.post(
                "/api/v1/economy/award-from-course",
                json=payload,
                headers={"X-Sync-Secret": "test_sync_secret"},
            )
            assert resp2.status_code == 409

            resp3 = await ac.post(
                "/api/v1/economy/award-from-course",
                json={**payload, "source_id": "source_def"},
                headers={"X-Sync-Secret": "wrong"},
            )
            assert resp3.status_code == 401
    finally:
        db.close()
