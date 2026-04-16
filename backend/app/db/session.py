import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# ---------------------------------------------------------------------------
# Sync engine — kept for Celery workers, Alembic, and legacy sync code
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.HYPERCODE_DB_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Sync DB dependency — use in sync routes / Celery tasks."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Async engine — Gordon Tier 3: native asyncpg driver with connection pooling
#
# pool_pre_ping=True  — before handing a connection from the pool, SQLAlchemy
#   fires a cheap "SELECT 1" to confirm it is still alive.  This prevents
#   "server closed the connection unexpectedly" errors after idle periods or
#   postgres restarts — critical for long-running Docker services.
#
# pool_recycle=3600   — connections older than 1 hour are retired and replaced.
#   Prevents silent TCP timeouts on cloud/NAT environments.
# ---------------------------------------------------------------------------
_async_db_url = settings.HYPERCODE_DB_URL.replace(
    "postgresql://", "postgresql+asyncpg://", 1
).replace(
    "postgres://", "postgresql+asyncpg://", 1
)

async_engine = create_async_engine(
    _async_db_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

# async_sessionmaker is the async equivalent of sessionmaker
_AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI async dependency — yields a native async SQLAlchemy session.

    Usage in a route::

        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(MyModel))
            return result.scalars().all()
    """
    async with _AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Legacy async proxy — kept for backward compat with Phase 10G / 10D callers
# that use:  async with AsyncSessionLocal() as db:  ...
#
# New code should use get_async_db() or _AsyncSessionFactory directly.
# ---------------------------------------------------------------------------

class _AsyncSessionProxy:
    """Async-compatible proxy around a sync SQLAlchemy session.

    Runs blocking DB operations on the thread-pool executor so async
    handlers can await them without blocking the event loop.
    Used by Phase 10G (Stripe webhooks) and Phase 10D (agent auth).

    Deprecated: prefer get_async_db() which uses the native asyncpg driver.
    """

    def __init__(self, session):
        self._session = session

    async def execute(self, statement, params=None):
        loop = asyncio.get_running_loop()
        if params is not None:
            return await loop.run_in_executor(
                None, lambda: self._session.execute(statement, params)
            )
        return await loop.run_in_executor(
            None, lambda: self._session.execute(statement)
        )

    async def commit(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._session.commit)

    async def rollback(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._session.rollback)


@asynccontextmanager
async def AsyncSessionLocal():
    """Async context manager yielding an async-compatible DB session.

    Usage::

        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
            await db.commit()

    Deprecated: prefer get_async_db() which uses the native asyncpg driver.
    """
    session = SessionLocal()
    proxy = _AsyncSessionProxy(session)
    try:
        yield proxy
    except Exception:
        await proxy.rollback()
        raise
    finally:
        session.close()
