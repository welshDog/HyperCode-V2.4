"""
CourseStats Cog — Phase 1 Identity Bridge

/coursestats — Shows a unified embed with the user's Hyper-Vibe-Coding-Course
               progress AND their HyperCode V2.4 platform data, merged on Discord ID.

Calls the course-profile Supabase edge function which fans out to:
  - Supabase (course XP, level, BROski$ tokens, lessons)
  - HyperCode V2.4 API (role, projects, active tasks)
"""
from __future__ import annotations

import logging
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from src.config.settings import settings

logger = logging.getLogger(__name__)

LEVEL_EMOJI = ["🥚", "🐣", "🐥", "🦅", "🔥", "⚡", "🌌", "♾️"]

def _level_emoji(level: int) -> str:
    idx = min(level - 1, len(LEVEL_EMOJI) - 1)
    return LEVEL_EMOJI[max(idx, 0)]


class CourseStats(commands.Cog):
    """Cross-system course + HyperCode profile stats."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._session: Optional[aiohttp.ClientSession] = None

    async def cog_load(self) -> None:
        self._session = aiohttp.ClientSession()

    async def cog_unload(self) -> None:
        if self._session:
            await self._session.close()

    # ── /coursestats ─────────────────────────────────────────────────────────

    @app_commands.command(
        name="coursestats",
        description="Show your Hyper-Vibe-Coding-Course progress + HyperCode platform stats",
    )
    @app_commands.describe(member="Whose stats to show (defaults to you)")
    async def coursestats(
        self,
        interaction: discord.Interaction,
        member: Optional[discord.Member] = None,
    ) -> None:
        await interaction.response.defer()

        target = member or interaction.user
        discord_id = str(target.id)

        profile = await self._fetch_profile(discord_id)
        embed = self._build_embed(target, profile)
        await interaction.followup.send(embed=embed)

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _fetch_profile(self, discord_id: str) -> dict:
        """Call the course-profile edge function."""
        edge_url = getattr(settings, "course_profile_edge_url", None)
        if not edge_url:
            logger.warning("course_profile_edge_url not set in settings — returning empty profile")
            return {}
        url = f"{edge_url}?discord_id={discord_id}"
        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.warning("course-profile edge fn returned %s for %s", resp.status, discord_id)
                return {}
        except Exception as exc:
            logger.warning("course-profile fetch failed: %s", exc)
            return {}

    def _build_embed(self, target: discord.Member, profile: dict) -> discord.Embed:
        course = profile.get("course") or {}
        hc = profile.get("hypercode") or {}

        title = f"{target.display_name}'s HyperCode Profile"
        embed = discord.Embed(
            title=title,
            color=discord.Color.from_str("#7C3AED"),
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        # ── Course block ──────────────────────────────────────────────────────
        if course:
            level = course.get("level", 1)
            xp = course.get("xp", 0)
            tokens = course.get("broski_tokens", 0)
            lessons = course.get("lessons_completed", 0)
            emoji = _level_emoji(level)

            embed.add_field(
                name="📚 Hyper-Vibe Coding Course",
                value=(
                    f"{emoji} **Level {level}**\n"
                    f"⚡ XP: `{xp:,}`\n"
                    f"🪙 BROski$: `{tokens:,}`\n"
                    f"✅ Lessons done: `{lessons}`"
                ),
                inline=True,
            )
        else:
            embed.add_field(
                name="📚 Hyper-Vibe Coding Course",
                value="❌ Not enrolled (or Discord not linked)",
                inline=True,
            )

        # ── HyperCode block ───────────────────────────────────────────────────
        if hc:
            role = hc.get("role", "developer").title()
            name = hc.get("full_name") or hc.get("email", "Unknown")
            active = "🟢 Active" if hc.get("is_active") else "🔴 Inactive"

            embed.add_field(
                name="🦅 HyperCode Platform",
                value=(
                    f"👤 **{name}**\n"
                    f"🎖️ Role: `{role}`\n"
                    f"Status: {active}"
                ),
                inline=True,
            )
        else:
            embed.add_field(
                name="🦅 HyperCode Platform",
                value="❌ No HyperCode account linked",
                inline=True,
            )

        if not course and not hc:
            embed.description = (
                "⚠️ No linked accounts found.\n"
                "Link your Discord in the course portal to see stats here."
            )

        embed.set_footer(text="HyperCode Identity Bridge · Phase 1")
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CourseStats(bot))
