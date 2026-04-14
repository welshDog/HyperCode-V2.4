import asyncio
from contextlib import asynccontextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

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
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class _AsyncSessionProxy:
    """Async-compatible proxy around a sync SQLAlchemy session.

    Runs blocking DB operations on the thread-pool executor so async
    handlers can await them without blocking the event loop.
    Used by Phase 10G (Stripe webhooks) and Phase 10D (agent auth).
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
