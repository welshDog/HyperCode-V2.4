"""
BROski Bot — AI Cog (One Door)
Commands: /broski /ask
All calls go via CoreClient → POST /api/v1/discord/actions
"""
import discord
from discord import app_commands
from discord.ext import commands
from core_client import CoreClient, render_to_embed, fallback_embed, CoreError


class AI(commands.Cog):
    def __init__(self, bot: commands.Bot, core: CoreClient):
        self.bot = bot
        self.core = core

    def _ctx(self, interaction: discord.Interaction) -> dict:
        return {
            "user_id": str(interaction.user.id),
            "username": interaction.user.name,
            "guild_id": str(interaction.guild_id) if interaction.guild_id else None,
            "channel_id": str(interaction.channel_id),
            "interaction_id": str(interaction.id),
        }

    @app_commands.command(name="broski", description="Chat with BROski AI 🧠")
    @app_commands.describe(message="What do you want to ask?")
    async def broski(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer()
        try:
            resp = await self.core.action(
                "ai.chat",
                self._ctx(interaction),
                payload={"message": message},
            )
            embed = render_to_embed(resp["render"])
        except CoreError as e:
            embed = fallback_embed(e)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ask", description="Quick question to BROski ⚡")
    @app_commands.describe(question="Your question")
    async def ask(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer(ephemeral=True)
        try:
            resp = await self.core.action(
                "ai.ask",
                self._ctx(interaction),
                payload={"question": question},
            )
            embed = render_to_embed(resp["render"])
        except CoreError as e:
            embed = fallback_embed(e)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AI(bot, bot.core_client))

