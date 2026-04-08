import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import settings and models for autogenerate support
from src.config.settings import settings
from src.core.database import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata for autogenerate
target_metadata = Base.metadata

# Override sqlalchemy.url with settings.database_url
# Use a placeholder if DB settings are not fully configured (e.g. during CI/CD or initial setup)
try:
    url = settings.database_url
except Exception:
    url = "postgresql+asyncpg://user:pass@localhost/dbname"

config.set_main_option("sqlalchemy.url", url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # If we are just generating a revision and no database is available,
    # we can skip the online migration part or use a mock connection if possible.
    # However, autogenerate usually needs a live connection to compare.
    
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    except Exception as e:
        # If we're just trying to generate a revision and it fails due to connection,
        # we might be in a state where we can't connect.
        if os.environ.get("ALEMBIC_OFFLINE_GENERATE"):
             print(f"Connection failed, but ALEMBIC_OFFLINE_GENERATE is set: {e}")
             return
        raise e
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We are in an existing event loop (e.g. during pytest-asyncio)
        # We need to run this in a way that doesn't block or use asyncio.run()
        # However, alembic's command.upgrade is synchronous.
        # This is a known issue when mixing alembic and pytest-asyncio.
        # The best approach for testing is often to run migrations in a separate thread/process
        # or use a synchronous wrapper.
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.run(run_async_migrations())
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
