"""
BROski Bot — Brain Briefing Cog (Level 13)

Pulls vault context from the morning-briefing brain agent and delivers a
rich daily briefing: yesterday's wins, active projects, overdue tasks,
GitHub issues, streak, focus forecast, and AI-calculated Top 3.

Runs daily at BRIEFING_HOUR_UTC (default 07:00 UTC) as a DM to
DIGEST_DM_USER_ID, and optionally posts to BRIEFING_CHANNEL_ID.

Bot is a render adapter — all content comes from the brain agent.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import discord
import httpx
from discord import app_commands
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)

_AGENT_URL = os.getenv("MORNING_BRIEFING_URL", "http://agent-morning-briefing:3304")
_BRIEFING_HOUR = int(os.getenv("BRIEFING_HOUR_UTC", "7"))


def _owner_id() -> int:
    raw = os.getenv("DIGEST_DM_USER_ID") or os.getenv("DISCORD_USER_ID") or "0"
    try:
        return int(raw)
    except ValueError:
        return 0


def _briefing_channel_id() -> int:
    try:
        return int(os.getenv("BRIEFING_CHANNEL_ID", "0"))
    except ValueError:
        return 0


async def _fetch_briefing() -> dict | None:
    """Call the brain agent and return the briefing dict, or None on failure."""
    try:
        # graph-aware RAG on CPU Ollama — cold model load can push past 90s,
        # agent's own bridge budget is 240s
        async with httpx.AsyncClient(timeout=270.0) as client:
            resp = await client.post(f"{_AGENT_URL}/generate", json={})
            resp.raise_for_status()
            return resp.json().get("briefing")
    except Exception as exc:
        logger.warning("Brain briefing agent unreachable: %s", exc)
        return None


def _build_embed(briefing: dict) -> discord.Embed:
    date = briefing.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    embed = discord.Embed(
        title=f"🌅 Morning Briefing — {date}",
        color=0x9B59B6,
    )

    # Top 3 priorities
    top3 = briefing.get("top_3") or []
    if top3:
        embed.add_field(
            name="🎯 Top 3 Today",
            value="\n".join(f"{i+1}. {t}" for i, t in enumerate(top3[:3])),
            inline=False,
        )

    # Yesterday's wins
    wins = briefing.get("yesterday_wins") or []
    if wins:
        wins_text = "\n".join(f"✅ `{w}`" for w in wins[:3])
        if len(wins) > 3:
            wins_text += f"\n_+ {len(wins) - 3} more_"
        embed.add_field(name="🎉 Yesterday's Wins", value=wins_text, inline=False)
    else:
        embed.add_field(name="🎉 Yesterday's Wins", value="Nothing logged yet — go make one!", inline=False)

    # Active projects count
    projects = briefing.get("active_projects") or []
    overdue = briefing.get("overdue_tasks") or []
    embed.add_field(
        name="🏗️ Projects",
        value=f"{len(projects)} active",
        inline=True,
    )
    embed.add_field(
        name="⚠️ Overdue",
        value=f"{len(overdue)} task(s)" if overdue else "✅ Nothing overdue",
        inline=True,
    )

    # Streak
    streak = briefing.get("streak") or {}
    current = streak.get("current_streak", 0)
    longest = streak.get("longest_streak", 0)
    tokens = streak.get("recovery_tokens", 0)
    embed.add_field(
        name="🔥 Streak",
        value=f"**{current}** days · Best: {longest} 🏆 · Recovery: {tokens} 🎟️",
        inline=False,
    )

    # Focus forecast
    forecast = briefing.get("focus_forecast")
    if forecast:
        flow = forecast.get("predicted_flow", "?")
        embed.add_field(
            name="🔮 Focus Forecast",
            value=(
                f"**Best window:** {forecast.get('best_window', 'Unknown')}\n"
                f"**Flow:** {flow}/10 · **Difficulty:** {forecast.get('recommended_difficulty', 'medium')}\n"
                f"**Avoid:** {forecast.get('avoid', '—')}"
            ),
            inline=False,
        )

    # Brain citations — notes + skills the AI prioritization was grounded in
    ai = briefing.get("ai_suggestions") or {}
    cited = ai.get("sources") or []
    skills = ai.get("skills") or []
    if cited or skills:
        lines = []
        if cited:
            lines.append("📎 " + " · ".join(
                f"`{os.path.splitext(os.path.basename(p))[0]}`" for p in cited[:3]
            ))
        if skills:
            lines.append("🦸 " + " · ".join(
                f"`{s.removeprefix('skill:')}`" for s in skills[:4]
            ))
        embed.add_field(name="🧠 Brain Citations", value="\n".join(lines)[:1024], inline=False)

    # GitHub issues
    issues = briefing.get("github_issues") or []
    if issues:
        issues_text = "\n".join(
            f"🐛 `{i['repo']}` #{i['number']}: {i['title'][:45]}"
            for i in issues[:3]
        )
        embed.add_field(name="🐛 GitHub Issues", value=issues_text, inline=False)

    embed.set_footer(text="BROski Brain · Level 13 · Start small. Start now. The rest follows.")
    return embed


def _fallback_embed() -> discord.Embed:
    """Minimal embed when the brain agent is unreachable."""
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    embed = discord.Embed(
        title=f"🌅 Morning Briefing — {date}",
        description=(
            "Brain agent offline — vault data unavailable.\n\n"
            "Use `/briefing` for stack health + BROski$ balance.\n"
            "Check: `docker compose --profile brain-agents up -d`"
        ),
        color=0xE67E22,
    )
    embed.set_footer(text="BROski Brain · Level 13")
    return embed


class BrainBriefing(commands.Cog):
    """Daily vault-context briefing from the morning-briefing brain agent."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._owner_id = _owner_id()
        self._channel_id = _briefing_channel_id()
        self._last_briefing_date: str | None = None

    async def cog_load(self):
        if self._owner_id:
            self.briefing_loop.start()

    async def cog_unload(self):
        self.briefing_loop.cancel()

    async def _send_briefing(self, *, manual: bool = False) -> bool:
        """Fetch briefing and deliver via DM + optional channel. Returns True on success."""
        briefing_data = await _fetch_briefing()
        embed = _build_embed(briefing_data) if briefing_data else _fallback_embed()

        sent = False
        if self._owner_id:
            user = self.bot.get_user(self._owner_id)
            if user is None:
                try:
                    user = await self.bot.fetch_user(self._owner_id)
                except discord.HTTPException:
                    user = None
            if user is not None:
                try:
                    await user.send(embed=embed)
                    sent = True
                except (discord.Forbidden, discord.HTTPException):
                    pass

        if self._channel_id:
            channel = self.bot.get_channel(self._channel_id)
            if channel is not None:
                try:
                    await channel.send(embed=embed)
                    sent = True
                except discord.HTTPException:
                    pass

        return sent

    @tasks.loop(hours=1)
    async def briefing_loop(self):
        now = datetime.now(timezone.utc)
        if now.hour != _BRIEFING_HOUR:
            return
        today = now.strftime("%Y-%m-%d")
        if self._last_briefing_date == today:
            return  # already sent today
        if await self._send_briefing():
            self._last_briefing_date = today

    @briefing_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="brain-briefing",
        description="🌅 Generate today's vault briefing from the Brain agent (admin)",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def brain_briefing_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        briefing_data = await _fetch_briefing()
        embed = _build_embed(briefing_data) if briefing_data else _fallback_embed()

        # Always show inline in the interaction
        await interaction.followup.send(embed=embed, ephemeral=False)

        # Also DM if different from interaction user
        if self._owner_id and self._owner_id != interaction.user.id:
            user = self.bot.get_user(self._owner_id)
            if user is None:
                try:
                    user = await self.bot.fetch_user(self._owner_id)
                except discord.HTTPException:
                    user = None
            if user is not None:
                try:
                    await user.send(embed=embed)
                except (discord.Forbidden, discord.HTTPException):
                    pass

    @brain_briefing_cmd.error
    async def _on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "🔒 Manage Server permission required.", ephemeral=True
            )
        else:
            await interaction.response.send_message("💀 Brain briefing failed.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(BrainBriefing(bot))
