"""
Discord bot initialization and configuration.
"""
# pylint: disable=import-error, no-name-in-module, broad-exception-caught

from typing import List

import discord
from discord.ext import commands
from prometheus_client import Counter, Histogram, start_http_server

from src.config.logging import get_logger
from src.config.settings import settings

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
            "src.cogs.ai_relay",
            "src.cogs.slash_ask",
            "src.cogs.briefing",
            "src.cogs.hypercode_sync",
            "src.cogs.pets",
            "src.cogs.admin",
            "src.cogs.life_engine",
            "src.cogs.profile",
            "src.cogs.course_stats",
            "src.cogs.ops_alerts",    # Phase 5: health-poll → #ops-alerts Discord alerts
            "src.cogs.health_check",  # /health — NemoClaw live code health scan
            "src.cogs.server_builder", # 🏗️ HYPERFOCUS ZONE Server Builder skill
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
            if settings.discord_guild_id and settings.is_development:
                guild = discord.Object(id=settings.discord_guild_id)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info(
                    "Synced %d slash commands to guild %s",
                    len(synced),
                    settings.discord_guild_id,
                )

                try:
                    global_synced = await self.tree.sync()
                    logger.info("Also synced %d global slash commands", len(global_synced))
                except Exception as e:
                    logger.warning("Global slash command sync failed", error=str(e))
            else:
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
        context: commands.Context,
        exception: commands.CommandError,
    ) -> None:
        """
        Global error handler for commands.
        
        Args:
            context: Command context
            exception: Command error
        """
        ERROR_COUNT.labels(error_type=type(exception).__name__).inc()
        
        if isinstance(exception, commands.CommandNotFound):
            return  # Ignore unknown commands
        
        if isinstance(exception, commands.MissingPermissions):
            await context.send("❌ You don't have permission to use this command.")
            return
        
        if isinstance(exception, commands.CommandOnCooldown):
            await context.send(
                f"⏰ This command is on cooldown. Try again in {exception.retry_after:.1f}s"
            )
            return
        
        logger.error(
            "Command error",
            command=context.command.name if context.command else "unknown",
            user_id=context.author.id,
            guild_id=context.guild.id if context.guild else None,
            error=str(exception),
            exc_info=True,
        )
        
        await context.send("❌ An error occurred. The issue has been logged.")
    
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
