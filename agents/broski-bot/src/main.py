"""
Main application entry point.
Handles bot initialization, startup, and shutdown.
"""
import sys
import os

# Add the parent directory to sys.path to allow imports from 'src'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import signal
from typing import Optional

import click
import sentry_sdk
from discord.ext import commands

from src.bot import BroskiBot
from src.config.logging import configure_logging, get_logger
from src.config.settings import settings
from src.core.database import db

logger = get_logger(__name__)


async def shutdown(bot: commands.Bot, signal_name: Optional[str] = None) -> None:
    """
    Gracefully shutdown the bot.
    
    Args:
        bot: Discord bot instance
        signal_name: Signal name if triggered by signal
    """
    if signal_name:
        logger.info(f"Received {signal_name} signal, shutting down...")
    else:
        logger.info("Shutting down bot...")
    
    # Close bot connection
    if not bot.is_closed():
        await bot.close()
    
    # Close database connections
    await db.close()
    
    logger.info("Shutdown complete")


async def main() -> None:
    """Main application entry point."""
    # Configure logging
    configure_logging()
    
    logger.info(
        "Starting BROski Bot",
        version=settings.app_version,
        environment=settings.environment,
    )
    
    # Initialize Sentry for error tracking
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
        )
        logger.info("Sentry error tracking enabled")
    
    # Initialize database
    try:
        await db.init()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e), exc_info=True)
        sys.exit(1)
    
    # Create bot instance
    bot = BroskiBot()
    
    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(shutdown(bot, s.name)),
        )
    
    try:
        # Start bot
        async with bot:
            await bot.start(settings.discord_token)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error("Bot crashed", error=str(e), exc_info=True)
        raise
    finally:
        await shutdown(bot)


@click.group()
def cli() -> None:
    """BROski Bot CLI."""
    pass


@cli.command()
def run() -> None:
    """Run the bot."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error("Fatal error", error=str(e), exc_info=True)
        sys.exit(1)


@cli.command()
def migrate() -> None:
    """Run database migrations."""
    import subprocess
    
    logger.info("Running database migrations")
    result = subprocess.run(["alembic", "upgrade", "head"])
    sys.exit(result.returncode)


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind")
@click.option("--port", default=8000, help="Port to bind")
def api(host: str, port: int) -> None:
    """Run the Economy API server."""
    import uvicorn
    uvicorn.run("src.api.main:app", host=host, port=port, reload=settings.debug)


@cli.command()
@click.option("--backup-dir", default="./backups", help="Backup directory")
def backup(backup_dir: str) -> None:
    """Create database backup."""
    import os
    import subprocess
    from datetime import datetime
    
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{backup_dir}/broski_bot_{timestamp}.sql"
    
    logger.info("Creating database backup", file=backup_file)
    
    # Extract connection details from DATABASE_URL
    db_url = str(settings.database_url)
    
    result = subprocess.run(
        ["pg_dump", db_url, "-f", backup_file],
        capture_output=True,
        text=True,
    )
    
    if result.returncode == 0:
        logger.info("Backup created successfully", file=backup_file)
    else:
        logger.error("Backup failed", error=result.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()
