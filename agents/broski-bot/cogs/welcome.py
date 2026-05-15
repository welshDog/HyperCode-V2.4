"""
BROski Bot — Welcome Cog (Section 5 — One Door)
on_member_join → CoreClient → POST /api/v1/discord/actions {action:"member.join"}
Core registers the member. Bot renders the welcome embed.
"""
import discord
from discord.ext import commands
from core_client import CoreClient, render_to_embed, fallback_embed, CoreError
import os

WELCOME_CHANNEL_NAME = os.getenv("WELCOME_CHANNEL_NAME", "welcome")


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


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot, bot.core_client))
