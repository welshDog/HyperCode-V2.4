"""
BROski Bot — Weekly Digest (Server Guardian Phase 2)

The "never log in" payoff + the trust audit trail. A weekly DM to Lyndz
summarising everything BROski did. Bot calls Core's digest.weekly One Door
action; Core aggregates Postgres; bot DMs the rendered embed.

Sacred Rule preserved — bot is UI, Core is the brain.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core_client import CoreClient, CoreError, render_to_embed


def _digest_user_id() -> int:
    raw = os.getenv("DIGEST_DM_USER_ID") or os.getenv("DISCORD_USER_ID") or "0"
    try:
        return int(raw)
    except ValueError:
        return 0


def _digest_weekday() -> int:
    """0=Mon … 6=Sun. Default Monday."""
    try:
        return max(0, min(6, int(os.getenv("DIGEST_WEEKDAY", "0"))))
    except ValueError:
        return 0


def _primary_guild(bot: commands.Bot) -> discord.Guild | None:
    gid = os.getenv("DISCORD_GUILD_ID")
    if gid:
        try:
            g = bot.get_guild(int(gid))
            if g:
                return g
        except ValueError:
            pass
    return bot.guilds[0] if bot.guilds else None


class Digest(commands.Cog):
    """Weekly digest DM — Core aggregates, bot delivers."""

    def __init__(self, bot: commands.Bot, core: CoreClient):
        self.bot = bot
        self.core = core
        self._user_id = _digest_user_id()
        self._weekday = _digest_weekday()
        self._last_sent_week: str | None = None

    async def cog_load(self):
        if self._user_id:
            self.digest_loop.start()

    async def cog_unload(self):
        self.digest_loop.cancel()

    def _ctx(self, *, manual: bool) -> dict:
        if manual:
            iid = f"digest-manual-{uuid.uuid4().hex[:12]}"
        else:
            iso = datetime.now(timezone.utc).isocalendar()
            iid = f"digest-{iso.year}-W{iso.week:02d}"
        return {
            "user_id": "system",
            "username": "broski-guardian",
            "guild_id": None,
            "channel_id": None,
            "interaction_id": iid,
        }

    async def _fetch_digest_embed(self, *, manual: bool) -> discord.Embed | None:
        guild = _primary_guild(self.bot)
        payload = {"guild_member_count": guild.member_count if guild else None}
        try:
            resp = await self.core.action("digest.weekly", self._ctx(manual=manual), payload)
        except CoreError:
            return None
        if not resp.get("render"):
            return None
        return render_to_embed(resp["render"])

    async def _deliver(self, embed: discord.Embed) -> bool:
        user = self.bot.get_user(self._user_id)
        if user is None:
            try:
                user = await self.bot.fetch_user(self._user_id)
            except discord.HTTPException:
                return False
        try:
            await user.send(embed=embed)
            return True
        except discord.Forbidden:
            return False  # DMs closed
        except discord.HTTPException:
            return False

    @tasks.loop(hours=24)
    async def digest_loop(self):
        now = datetime.now(timezone.utc)
        if now.weekday() != self._weekday:
            return
        iso = now.isocalendar()
        week_tag = f"{iso.year}-W{iso.week:02d}"
        if self._last_sent_week == week_tag:
            return
        embed = await self._fetch_digest_embed(manual=False)
        if embed is not None and await self._deliver(embed):
            self._last_sent_week = week_tag

    @digest_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="digest",
        description="📊 Send the weekly BROski digest now (admin)",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def digest_now(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not self._user_id:
            await interaction.followup.send(
                "⚠️ `DIGEST_DM_USER_ID` not set — nowhere to send.", ephemeral=True
            )
            return

        embed = await self._fetch_digest_embed(manual=True)
        if embed is None:
            await interaction.followup.send(
                "⚠️ Couldn't build the digest — Core unavailable?", ephemeral=True
            )
            return

        if await self._deliver(embed):
            await interaction.followup.send(
                f"✅ Digest DM'd to <@{self._user_id}>.", ephemeral=True
            )
        else:
            await interaction.followup.send(
                content="⚠️ Couldn't DM the target (DMs closed?). Here it is:",
                embed=embed,
                ephemeral=True,
            )

    @digest_now.error
    async def _on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "🔒 Manage Server permission required.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "💀 Digest failed. Check logs.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Digest(bot, bot.core_client))
