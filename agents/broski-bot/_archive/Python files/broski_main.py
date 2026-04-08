"""
Main application entry point.
Handles bot initialization, startup, and shutdown.
"""
# src/main.py
import asyncio
import signal
import sys
from typing import Optional

import click
import discord
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
@click.option("--backup-dir", default="./backups", help="Backup directory")
def backup(backup_dir: str) -> None:
    """Create database backup."""
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


# ============================================================================
# src/bot.py
"""
Discord bot initialization and configuration.
"""
import os
from typing import List, Optional

from discord.ext import commands
from prometheus_client import Counter, Histogram, start_http_server

from src.config.logging import get_logger

logger = get_logger(__name__)

# Prometheus metrics
COMMAND_COUNT = Counter(
    "broski_commands_total",
    "Total number of commands executed",
    ["command", "cog"],
)
COMMAND_DURATION = Histogram(
    "broski_command_duration_seconds",
    "Command execution duration",
    ["command"],
)
ERROR_COUNT = Counter(
    "broski_errors_total",
    "Total number of errors",
    ["error_type"],
)


class BroskiBot(commands.Bot):
    """Custom bot class with enhanced functionality."""
    
    def __init__(self) -> None:
        """Initialize bot with intents and configuration."""
        # Configure intents
        intents = discord.Intents.default()
        if settings.discord_intents_all:
            intents = discord.Intents.all()
        else:
            intents.message_content = True
            intents.guilds = True
            intents.members = True
        
        super().__init__(
            command_prefix=settings.discord_command_prefix,
            intents=intents,
            owner_ids=set(settings.discord_owner_ids) if settings.discord_owner_ids else None,
            help_command=None,  # Use custom help command
        )
        
        self.initial_extensions: List[str] = [
            "src.cogs.economy",
            "src.cogs.focus",
            "src.cogs.admin",
            "src.cogs.monitoring",
        ]
    
    async def setup_hook(self) -> None:
        """
        Setup hook called before bot starts.
        Loads extensions and syncs commands.
        """
        logger.info("Running bot setup hook")
        
        # Start Prometheus metrics server
        if settings.prometheus_enabled:
            try:
                start_http_server(settings.prometheus_port)
                logger.info(
                    "Prometheus metrics server started",
                    port=settings.prometheus_port,
                )
            except Exception as e:
                logger.warning(
                    "Failed to start Prometheus server",
                    error=str(e),
                )
        
        # Load extensions (cogs)
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                logger.error(
                    f"Failed to load extension: {extension}",
                    error=str(e),
                    exc_info=True,
                )
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error("Failed to sync commands", error=str(e), exc_info=True)
    
    async def on_ready(self) -> None:
        """Called when bot is ready and connected."""
        logger.info(
            "Bot ready",
            bot_name=self.user.name,
            bot_id=self.user.id,
            guild_count=len(self.guilds),
        )
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | /help",
            )
        )
    
    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError,
    ) -> None:
        """
        Global error handler for commands.
        
        Args:
            ctx: Command context
            error: Command error
        """
        ERROR_COUNT.labels(error_type=type(error).__name__).inc()
        
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
            return
        
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f}s"
            )
            return
        
        logger.error(
            "Command error",
            command=ctx.command.name if ctx.command else "unknown",
            user_id=ctx.author.id,
            guild_id=ctx.guild.id if ctx.guild else None,
            error=str(error),
            exc_info=True,
        )
        
        await ctx.send("❌ An error occurred. The issue has been logged.")
    
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """
        Called when bot joins a new guild.
        
        Args:
            guild: Discord guild
        """
        logger.info(
            "Joined new guild",
            guild_id=guild.id,
            guild_name=guild.name,
            member_count=guild.member_count,
        )
        
        # Update presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | /help",
            )
        )
    
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """
        Called when bot leaves a guild.
        
        Args:
            guild: Discord guild
        """
        logger.info(
            "Left guild",
            guild_id=guild.id,
            guild_name=guild.name,
        )
        
        # Update presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | /help",
            )
        )
