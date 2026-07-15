"""
BROski Bot — Ops Alerts Cog (Section 7 — ONE TRUE BOT)
Passive infra monitor: polls Core's deep /api/v1/health every 5 minutes and
posts an embed to #ops-alerts only when the status changes (no spam).

Read-only — no writes, no decisions. Does not go through the One Door
(which governs actions); this is a render-on-poll monitor, same shape as the
health_check / codehealth_voice cogs.

Resurrected 2026-05-22 from agents/broski-bot/src/cogs/ops_alerts.py. Only
change from the orphan: the Core host is now env-driven (HYPERCODE_API_URL)
instead of a hardcoded Docker hostname, so it works in any deployment.
"""
import os
import logging

import discord
from discord.ext import commands, tasks
import httpx

log = logging.getLogger(__name__)

OPS_ALERTS_CHANNEL_NAME = "ops-alerts"

# Env-driven so it works in Docker, locally, or any deployment. Matches the
# HYPERCODE_API_URL that CoreClient reads. Falls back to the Docker hostname.
_CORE_URL = os.getenv("HYPERCODE_API_URL", "http://hypercode-core:8000").rstrip("/")
HEALTH_URL = f"{_CORE_URL}/api/v1/health"  # deep health: Postgres/Redis/Discord + breakers


class OpsAlerts(commands.Cog):
    """Monitors /api/v1/health and fires Discord alerts in #ops-alerts when degraded."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_status = "healthy"
        self.health_poll.start()

    def cog_unload(self):
        self.health_poll.cancel()

    @tasks.loop(minutes=5)
    async def health_poll(self):
        data = {}
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
                if isinstance(result, dict):
                    icon = "✅" if result.get("status") == "ok" else "❌"
                    embed.add_field(name=service, value=f"{icon} {result.get('status', 'unknown')}", inline=True)
                    continue
                if isinstance(result, list):
                    states = []
                    for b in result[:6]:
                        if isinstance(b, dict):
                            states.append(f"{b.get('name', 'unknown')}={b.get('state', 'unknown')}")
                    embed.add_field(
                        name=service,
                        value=", ".join(states) if states else "unknown",
                        inline=False,
                    )
                    continue
                embed.add_field(name=service, value="unknown", inline=True)

            await channel.send(embed=embed)

    @health_poll.before_loop
    async def before_poll(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(OpsAlerts(bot))
