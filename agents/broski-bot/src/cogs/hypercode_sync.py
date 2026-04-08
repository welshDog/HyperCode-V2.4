"""
HyperCode Sync Cog — bridges the Discord bot into the live HyperCode ecosystem.

Provides:
  /hcpulse   — live BROski$ economy snapshot from the stack
  /hcagents  — live agent roster with status + circuit breaker health
  /hcstatus  — full system status embed (core, agents, economy)

Background task: updates bot presence every 5 min with live agent count.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Status → emoji mapping (mirrors ActiveAgentsPanel STATUS_CONFIG)
STATUS_EMOJI = {
    "online":   "🟢",
    "working":  "⚡",
    "thinking": "🟡",
    "busy":     "🟡",
    "idle":     "⚪",
    "error":    "🔴",
    "offline":  "⛔",
}

LEVEL_EMOJI = ["🥚", "🐣", "🐥", "🦅", "🔥", "⚡", "🌌", "♾️"]


def _level_emoji(level: int) -> str:
    idx = min(level - 1, len(LEVEL_EMOJI) - 1)
    return LEVEL_EMOJI[max(idx, 0)]


class HyperCodeSync(commands.Cog):
    """Live HyperCode ecosystem data, surfaced in Discord."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._session: Optional[aiohttp.ClientSession] = None
        self.presence_loop.start()

    def cog_unload(self) -> None:
        self.presence_loop.cancel()
        if self._session and not self._session.closed:
            # Schedule session close
            import asyncio
            asyncio.create_task(self._session.close())

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=8),
                headers={"Accept": "application/json"},
            )
        return self._session

    async def _fetch(self, path: str) -> Optional[dict[str, Any]]:
        """GET from HyperCode core. Returns None on any failure."""
        url = f"{settings.hypercode_core_url}{path}"
        try:
            session = await self._get_session()
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.warning("HyperCode API %s → %d", path, resp.status)
        except Exception as exc:
            logger.warning("HyperCode API fetch failed (%s): %s", path, exc)
        return None

    # ── Presence background task ─────────────────────────────────────────────

    @tasks.loop(minutes=5)
    async def presence_loop(self) -> None:
        """Update bot presence with live agent count every 5 minutes."""
        pulse = await self._fetch("/api/v1/broski/pulse")
        if pulse:
            agents = pulse.get("agentsOnline", "?")
            coins  = pulse.get("coins", "?")
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"{agents} agents | {coins} BROski$",
                )
            )

    @presence_loop.before_loop
    async def before_presence_loop(self) -> None:
        await self.bot.wait_until_ready()

    # ── /hcpulse ─────────────────────────────────────────────────────────────

    @app_commands.command(
        name="hcpulse",
        description="Live HyperCode BROski$ economy snapshot",
    )
    async def hcpulse(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        pulse = await self._fetch("/api/v1/broski/pulse")

        if not pulse:
            await interaction.followup.send(
                "⚠️ HyperCode core is unreachable — try again in a moment.",
                ephemeral=True,
            )
            return

        level      = pulse.get("level", 1)
        level_name = pulse.get("level_name", "Recruit")
        coins      = pulse.get("coins", 0)
        xp         = pulse.get("xp", 0)
        agents     = pulse.get("agentsOnline", 0)
        users      = pulse.get("userCount", 0)
        emoji      = _level_emoji(level)

        embed = discord.Embed(
            title=f"{emoji} HyperCode BROski$ Pulse",
            description=f"**System Level {level}** — {level_name}",
            color=discord.Color.from_rgb(120, 86, 255),
            timestamp=datetime.now(tz=timezone.utc),
        )
        embed.add_field(name="💰 Total Coins",    value=f"{coins:,}",  inline=True)
        embed.add_field(name="⚡ Total XP",       value=f"{xp:,}",     inline=True)
        embed.add_field(name="🤖 Agents Online",  value=str(agents),   inline=True)
        embed.add_field(name="👥 Users",          value=str(users),    inline=True)
        embed.set_footer(text="HyperCode V2.0 • Live data")
        await interaction.followup.send(embed=embed)

    # ── /hcagents ────────────────────────────────────────────────────────────

    @app_commands.command(
        name="hcagents",
        description="Live HyperCode agent roster — who's online right now",
    )
    async def hcagents(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        data = await self._fetch("/api/v1/agents/status")

        if not data:
            await interaction.followup.send(
                "⚠️ Could not reach the HyperCode agent registry.",
                ephemeral=True,
            )
            return

        agents     = data.get("agents", [])
        updated_at = data.get("updatedAt", "")

        embed = discord.Embed(
            title="🤖 HyperCode Agent Roster",
            color=discord.Color.from_rgb(0, 200, 120),
            timestamp=datetime.now(tz=timezone.utc),
        )

        if not agents:
            embed.description = "No agents reporting in right now."
        else:
            lines = []
            for agent in agents:
                status  = agent.get("status", "unknown")
                name    = agent.get("name", agent.get("id", "?"))
                seen    = agent.get("last_seen", "")
                dot     = STATUS_EMOJI.get(status, "❓")
                # Trim last_seen to HH:MM:SS
                if seen and "T" in seen:
                    seen = seen.split("T")[1][:8] + " UTC"
                lines.append(f"{dot} **{name}** — `{status}` · {seen}")
            embed.description = "\n".join(lines)

        if updated_at and "T" in updated_at:
            embed.set_footer(text=f"Refreshed {updated_at.split('T')[1][:8]} UTC")
        else:
            embed.set_footer(text="HyperCode V2.0 • Live data")

        await interaction.followup.send(embed=embed)

    # ── /hcstatus ────────────────────────────────────────────────────────────

    @app_commands.command(
        name="hcstatus",
        description="Full HyperCode system status — economy + agents + health",
    )
    async def hcstatus(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)

        # Fire both requests concurrently
        import asyncio
        pulse_task  = asyncio.create_task(self._fetch("/api/v1/broski/pulse"))
        agents_task = asyncio.create_task(self._fetch("/api/v1/agents/status"))
        health_task = asyncio.create_task(self._fetch("/health"))
        pulse, agents_data, health = await asyncio.gather(
            pulse_task, agents_task, health_task
        )

        core_ok    = health is not None and health.get("status") == "ok"
        status_str = "🟢 Operational" if core_ok else "🔴 Degraded"

        embed = discord.Embed(
            title="🚀 HyperCode V2.0 — System Status",
            color=discord.Color.from_rgb(120, 86, 255) if core_ok else discord.Color.red(),
            timestamp=datetime.now(tz=timezone.utc),
        )

        # Core health
        embed.add_field(name="⚙️ Core API", value=status_str, inline=True)
        if health:
            env = health.get("environment", "?")
            ver = health.get("version", "?")
            embed.add_field(name="📦 Version", value=f"v{ver} ({env})", inline=True)

        embed.add_field(name="\u200b", value="\u200b", inline=False)  # spacer

        # Economy
        if pulse:
            level      = pulse.get("level", 1)
            level_name = pulse.get("level_name", "?")
            emoji      = _level_emoji(level)
            embed.add_field(
                name="💰 Economy",
                value=(
                    f"{emoji} Level {level} · {level_name}\n"
                    f"**{pulse.get('coins', 0):,}** coins · **{pulse.get('xp', 0):,}** XP\n"
                    f"👥 {pulse.get('userCount', 0)} users"
                ),
                inline=True,
            )
        else:
            embed.add_field(name="💰 Economy", value="⚠️ Unavailable", inline=True)

        # Agents
        if agents_data:
            agents = agents_data.get("agents", [])
            online = [a for a in agents if a.get("status") not in ("offline", "error")]
            lines  = [
                f"{STATUS_EMOJI.get(a.get('status','?'), '❓')} {a.get('name', a.get('id'))}"
                for a in online[:8]
            ]
            if len(agents) > 8:
                lines.append(f"…and {len(agents) - 8} more")
            embed.add_field(
                name=f"🤖 Agents ({len(online)}/{len(agents)} online)",
                value="\n".join(lines) if lines else "None reporting",
                inline=True,
            )
        else:
            embed.add_field(name="🤖 Agents", value="⚠️ Unavailable", inline=True)

        embed.set_footer(text="HyperCode V2.0 • Mission Control")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HyperCodeSync(bot))
