import discord
from discord.ext import commands, tasks
import httpx
import logging

log = logging.getLogger(__name__)

OPS_ALERTS_CHANNEL_NAME = "ops-alerts"
HEALTH_URL = "http://api:8000/api/v1/health"  # internal Docker network


class OpsAlerts(commands.Cog):
    """Monitors /health and fires Discord alerts in #ops-alerts when degraded."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_status = "healthy"
        self.health_poll.start()

    def cog_unload(self):
        self.health_poll.cancel()

    @tasks.loop(minutes=5)
    async def health_poll(self):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(HEALTH_URL)
                data = resp.json()
                status = data.get("status", "unknown")
        except Exception as e:
            status = "unreachable"
            log.error(f"Health check failed: {e}")

        # Only alert on status change to avoid spam
        if status != self.last_status:
            await self._send_alert(status, data if status != "unreachable" else {})
            self.last_status = status

    async def _send_alert(self, status: str, data: dict):
        for guild in self.bot.guilds:
            channel = discord.utils.get(guild.text_channels, name=OPS_ALERTS_CHANNEL_NAME)
            if not channel:
                continue

            emoji = "✅" if status == "healthy" else "🚨"
            colour = discord.Colour.green() if status == "healthy" else discord.Colour.red()

            embed = discord.Embed(
                title=f"{emoji} HyperCode V2.4 — {status.upper()}",
                colour=colour,
            )
            checks = data.get("checks", {})
            for service, result in checks.items():
                icon = "✅" if result.get("status") == "ok" else "❌"
                embed.add_field(name=service, value=f"{icon} {result.get('status', 'unknown')}", inline=True)

            await channel.send(embed=embed)

    @health_poll.before_loop
    async def before_poll(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(OpsAlerts(bot))
