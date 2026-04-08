"""Database connection management with async SQLAlchemy.
Provides connection pooling, session management, and migrations.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.config.logging import get_logger
from src.config.settings import settings

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class Database:
    """
    Database manager handling connections and sessions.
    
    Usage:
        db = Database()
        await db.init()
        
        async with db.session() as session:
            result = await session.execute(query)
    """
    
    def __init__(self) -> None:
        """Initialize database manager."""
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    
    async def init(self) -> None:
        """
        Initialize database engine and session factory.
        Creates connection pool and sets up event listeners.
        """
        # Validate required settings
        required_settings = [
            "db_host", "db_port", "db_name", "db_user", "db_password"
        ]
        missing = [s for s in required_settings if not getattr(settings, s, None) or getattr(settings, s) == "placeholder"]
        if missing:
            raise RuntimeError(f"Missing required database settings: {', '.join(missing)}")

        logger.info(
            "Initializing database connection",
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
        )
        
        # Create async engine with connection pooling
        self._engine = create_async_engine(
            settings.database_url,
            **settings.get_database_config(),
            echo=settings.database_echo,
        )
        
        # Set up connection pool event listeners
        @event.listens_for(self._engine.sync_engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Handle new connection events."""
            logger.debug("New database connection established")
        
        @event.listens_for(self._engine.sync_engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Handle connection checkout from pool."""
            logger.debug("Connection checked out from pool")
        
        # Create session factory
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        logger.info("Database initialized successfully")
    
    async def close(self) -> None:
        """Close database connections and dispose engine."""
        if self._engine:
            logger.info("Closing database connections")
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get async database session with automatic cleanup.
        
        Yields:
            AsyncSession: Database session
            
        Example:
            async with db.session() as session:
                result = await session.execute(query)
                await session.commit()
        """
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call init() first.")
        
        session = self._session_factory()
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(
                "Database session failed",
                error=str(e),
                exc_info=True,
            )
            raise
        finally:
            await session.close()

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database transactions.
        Automatically commits on exit or rolls back on exception.
        
        Yields:
            AsyncSession: Database session
        """
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call init() first.")
        
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def create_tables(self) -> None:
        """
        Create all database tables.
        Should only be used in development. Use migrations in production.
        """
        if not self._engine:
            raise RuntimeError("Database not initialized")
        
        logger.warning("Creating database tables (use migrations in production)")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
    
    async def drop_tables(self) -> None:
        """
        Drop all database tables.
        DANGER: This will delete all data!
        """
        if not self._engine:
            raise RuntimeError("Database not initialized")
        
        logger.warning("Dropping all database tables - THIS WILL DELETE ALL DATA")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All database tables dropped")
    
    async def health_check(self) -> bool:
        """
        Check database health by executing a simple query.
        
        Returns:
            bool: True if database is healthy
        """
        try:
            async with self.session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False
    
    @property
    def engine(self) -> AsyncEngine:
        """Get database engine."""
        if not self._engine:
            raise RuntimeError("Database not initialized")
        return self._engine


# Global database instance
db = Database()

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    if not db._session_factory:
        await db.init()
        
    async with db.session() as session:
        yield session
    """
    Dependency injection helper for FastAPI/Discord.py.
    
    Yields:
        AsyncSession: Database session
    """
    async with db.session() as session:
        yield session


async def get_session() -> AsyncSession:
    """
    Get a new database session.
    
    Returns:
        AsyncSession: Database session
    """
    if not db._session_factory:
        await db.init()
    return db._session_factory()
