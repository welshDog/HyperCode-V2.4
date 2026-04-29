import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.v1.endpoints.pets import router as pets_router
from app.core.config import settings
from app.db.base_class import Base
from app.db.session import get_db
from app.models.broski import BROskiWallet
from app.models.models import User


def _make_httpx_response(status_code: int, json_data: dict | None = None, text: str = ""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    if json_data is None:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_data
    return resp


def _make_mock_client(get_sequence: list, post_sequence: list):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=get_sequence)
    mock_client.post = AsyncMock(side_effect=post_sequence)
    return mock_client


@pytest.mark.asyncio
async def test_pets_provision_spends_300_and_is_idempotent(monkeypatch):
    monkeypatch.setattr(settings, "SHOP_SYNC_SECRET", "shop_secret")
    monkeypatch.setattr(settings, "PETS_BRIDGE_URL", "http://pets-bridge:8098")
    monkeypatch.setattr(settings, "API_KEY", "core_key")

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    seed = TestingSessionLocal()
    try:
        user = User(
            email="bro@example.com",
            hashed_password="x",
            discord_id="discord_123",
            is_active=True,
            is_superuser=False,
        )
        seed.add(user)
        seed.commit()
        seed.refresh(user)
        seed.add(BROskiWallet(user_id=user.id, coins=500, xp=0, level=1, level_name="BROski Recruit"))
        seed.commit()
    finally:
        seed.close()

    app = FastAPI()
    app.include_router(pets_router, prefix="/api/v1/pets")

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    get_sequence = [
        _make_httpx_response(404, json_data={"detail": "No pet found for this discord_id"}),
    ]
    post_sequence = [
        _make_httpx_response(
            200,
            json_data={
                "pet_id": "pet_1",
                "name": "Brave Cat",
                "species": "CatEep",
                "rarity": "Common",
                "message": "Your pet has hatched!",
            },
        ),
    ]
    mock_client = _make_mock_client(get_sequence=get_sequence, post_sequence=post_sequence)

    with patch("app.api.v1.endpoints.pets.httpx.AsyncClient", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "source_id": "source_abc",
                "discord_id": "discord_123",
                "course_modules_completed": 3,
            }
            r1 = await ac.post(
                "/api/v1/pets/provision",
                json=payload,
                headers={"X-Sync-Secret": "shop_secret"},
            )
            assert r1.status_code == 200

            r2 = await ac.post(
                "/api/v1/pets/provision",
                json=payload,
                headers={"X-Sync-Secret": "shop_secret"},
            )
            assert r2.status_code == 409
    assert mock_client.get.await_args.kwargs["headers"]["x-api-key"] == "core_key"
    assert mock_client.post.await_args.kwargs["headers"]["x-api-key"] == "core_key"

    check = TestingSessionLocal()
    try:
        wallet = check.query(BROskiWallet).filter(BROskiWallet.user_id == 1).first()
        assert wallet is not None
        assert wallet.coins == 200
    finally:
        check.close()


@pytest.mark.asyncio
async def test_pets_feed_spends_10(monkeypatch):
    monkeypatch.setattr(settings, "SHOP_SYNC_SECRET", "shop_secret")
    monkeypatch.setattr(settings, "PETS_BRIDGE_URL", "http://pets-bridge:8098")
    monkeypatch.setattr(settings, "API_KEY", "core_key")

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    seed = TestingSessionLocal()
    try:
        user = User(
            email="bro@example.com",
            hashed_password="x",
            discord_id="discord_123",
            is_active=True,
            is_superuser=False,
        )
        seed.add(user)
        seed.commit()
        seed.refresh(user)
        seed.add(BROskiWallet(user_id=user.id, coins=25, xp=0, level=1, level_name="BROski Recruit"))
        seed.commit()
    finally:
        seed.close()

    app = FastAPI()
    app.include_router(pets_router, prefix="/api/v1/pets")

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    get_sequence = [
        _make_httpx_response(200, json_data={"pet_id": "pet_1"}),
    ]
    post_sequence = [
        _make_httpx_response(
            200,
            json_data={"discord_id": "discord_123", "hunger": 80, "energy": 90, "happiness": 75},
        ),
    ]
    mock_client = _make_mock_client(get_sequence=get_sequence, post_sequence=post_sequence)

    with patch("app.api.v1.endpoints.pets.httpx.AsyncClient", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/v1/pets/feed",
                json={"discord_id": "discord_123"},
                headers={"X-Sync-Secret": "shop_secret"},
            )
            assert r.status_code == 200
    assert mock_client.get.await_args.kwargs["headers"]["x-api-key"] == "core_key"
    assert mock_client.post.await_args.kwargs["headers"]["x-api-key"] == "core_key"

    check = TestingSessionLocal()
    try:
        wallet = check.query(BROskiWallet).filter(BROskiWallet.user_id == 1).first()
        assert wallet is not None
        assert wallet.coins == 15
    finally:
        check.close()
