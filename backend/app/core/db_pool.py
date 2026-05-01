# backend/app/core/db_pool.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncAdaptedQueuePool
from sqlalchemy.pool import NullPool
from app.core.config import get_settings

settings = get_settings()

def _async_url(url: str) -> str:
    """Ensure URL uses asyncpg driver, not psycopg2."""
    url = url.replace("postgresql://", "postgresql+asyncpg://")
    url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    return url

# NullPool for prod/staging, AsyncAdaptedQueuePool for local dev
# QueuePool is SYNC-only — never use with async engine
POOL_CLASS = NullPool if os.getenv("ENVIRONMENT") in ("production", "staging") else AsyncAdaptedQueuePool

# Gordon Tier 3: Adaptive pooling
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "25"))  # UP from 10 -> 25
MAX_OVERFLOW = int(os.getenv("DB_POOL_MAX_OVERFLOW", "10"))  # Burst capacity
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # Wait up to 30s

engine = create_async_engine(
    _async_url(settings.HYPERCODE_DB_URL),
    echo=False,
    poolclass=POOL_CLASS,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_pre_ping=True,
    echo_pool=os.getenv("ECHO_DB_POOL", "false").lower() == "true",
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_async_db():
    async with async_session() as session:
        yield session
