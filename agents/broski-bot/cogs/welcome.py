"""
BROski Bot — Welcome Cog (Section 5 — One Door)
on_member_join → CoreClient → POST /api/v1/discord/actions {action:"member.join"}
Core registers the member. Bot renders the welcome embed + assigns base role.

Auto-role is a pure Discord op (a permission grant, not BROski state) so it
stays bot-side — Core's One Door is for economy/XP/focus state only.
"""
import logging
import os

import discord
from discord.ext import commands
from core_client import CoreClient, render_to_embed, fallback_embed, CoreError

logger = logging.getLogger("broski.welcome")

WELCOME_CHANNEL_NAME = os.getenv("WELCOME_CHANNEL_NAME", "welcome")
AUTO_ROLE_NAME = os.getenv("AUTO_ROLE_NAME", "BROski")


class Welcome(commands.Cog):
    """Member join handler — wired to One Door."""

    def __init__(self, bot: commands.Bot, core: CoreClient):
        self.bot  = bot
        self.core = core

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        ctx = {
            "user_id":        str(member.id),
            "username":       member.name,
            "guild_id":       str(member.guild.id),
            "channel_id":     None,
            "interaction_id": f"join_{member.id}_{member.guild.id}",
        }
        try:
            resp  = await self.core.action("member.join", ctx)
            embed = render_to_embed(resp["render"])
        except CoreError as e:
            # Fallback: still welcome them even if Core is down
            embed = discord.Embed(
                title=f"⚡ Welcome, {member.display_name}!",
                description="You're in the HyperFocus Zone! Use `/daily` to get started. 🔥",
                colour=discord.Colour.purple(),
            )

        channel = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL_NAME)
        if channel:
            await channel.send(embed=embed)

        await self._assign_base_role(member)

    async def _assign_base_role(self, member: discord.Member) -> None:
        """Assign the base role on join. Never crash the join flow."""
        if not AUTO_ROLE_NAME:
            return
        role = discord.utils.get(member.guild.roles, name=AUTO_ROLE_NAME)
        if role is None:
            logger.warning(
                "AUTO_ROLE_NAME=%r not found in guild %s — skipping",
                AUTO_ROLE_NAME, member.guild.id,
            )
            return
        try:
            await member.add_roles(role, reason="BROski auto-role on join")
            logger.info("Assigned %r to %s", AUTO_ROLE_NAME, member.id)
        except discord.Forbidden:
            logger.warning(
                "Missing permission to assign %r in guild %s",
                AUTO_ROLE_NAME, member.guild.id,
            )
        except discord.HTTPException as exc:
            logger.warning("Failed to assign role to %s: %s", member.id, exc)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot, bot.core_client))
