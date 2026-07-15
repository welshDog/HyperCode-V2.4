"""
BROski Bot — Server Builder Cog (Phase 1 Reactive layer)

/hyperfocus_setup builds the HYPERFOCUS ZONE server layout (roles, categories,
channels) idempotently. Pure Discord structure op — no Core/Supabase. Admin only.

Ported from src/cogs/server_builder.py (orphaned pre-May-15 architecture):
stdlib logging instead of src.config.logging; structured-log kwargs flattened.
"""
import logging

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger("broski.server_builder")


class ServerBuilder(commands.Cog):
    """Server Designer & Builder skill for the ultimate HYPERFOCUS ZONE."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="hyperfocus_setup",
        description="Build the ultimate HYPERFOCUS ZONE server layout",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def hyperfocus_setup(self, interaction: discord.Interaction) -> None:
        """Create the structured categories, channels, and roles. Admin only."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                "❌ This command must be run in a server.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🏗️ **BROski Server Builder activated!** Designing the HYPERFOCUS ZONE...\n"
            "This might take a minute.",
            ephemeral=False,
        )

        try:
            roles_to_create = [
                {"name": "Captain", "color": discord.Color.purple(), "hoist": True},
                {"name": "BROski", "color": discord.Color.blue(), "hoist": True},
                {"name": "In The Zone", "color": discord.Color.red(), "hoist": True},
            ]

            role_objects: dict[str, discord.Role] = {}
            for role_data in roles_to_create:
                existing_role = discord.utils.get(guild.roles, name=role_data["name"])
                if not existing_role:
                    role_objects[role_data["name"]] = await guild.create_role(**role_data)
                    logger.info("Created role: %s", role_data["name"])
                else:
                    role_objects[role_data["name"]] = existing_role

            layout = {
                "🚀 THE BRIDGE": [
                    {"name": "welcome", "type": discord.ChannelType.text},
                    {"name": "rules", "type": discord.ChannelType.text},
                    {"name": "announcements", "type": discord.ChannelType.text},
                ],
                "🧠 HYPERFOCUS ZONE": [
                    {"name": "focus-chat", "type": discord.ChannelType.text},
                    {"name": "pomodoro-timers", "type": discord.ChannelType.text},
                    {"name": "🎧 Deep Work", "type": discord.ChannelType.voice},
                ],
                "🛠️ MISSION CONTROL": [
                    {"name": "ops-alerts", "type": discord.ChannelType.text},
                    {"name": "github-logs", "type": discord.ChannelType.text},
                    {"name": "agent-chatter", "type": discord.ChannelType.text},
                ],
                "🐶 BROSKI VIBES": [
                    {"name": "general", "type": discord.ChannelType.text},
                    {"name": "wins-only", "type": discord.ChannelType.text},
                    {"name": "memes", "type": discord.ChannelType.text},
                    {"name": "☕ The Lounge", "type": discord.ChannelType.voice},
                ],
            }

            for cat_name, channels in layout.items():
                category = discord.utils.get(guild.categories, name=cat_name)
                if not category:
                    category = await guild.create_category(cat_name)
                    logger.info("Created category: %s", cat_name)

                for ch_data in channels:
                    existing_channel = discord.utils.get(
                        guild.channels, name=ch_data["name"], category=category
                    )
                    if not existing_channel:
                        if ch_data["type"] == discord.ChannelType.text:
                            await guild.create_text_channel(ch_data["name"], category=category)
                        elif ch_data["type"] == discord.ChannelType.voice:
                            await guild.create_voice_channel(ch_data["name"], category=category)
                        logger.info("Created channel: %s in %s", ch_data["name"], cat_name)

            embed = discord.Embed(
                title="✅ HYPERFOCUS ZONE Built!",
                description="The server has been tidied up and structured for maximum focus.",
                color=0x2ECC71,
            )
            embed.add_field(
                name="Roles Created",
                value=", ".join([r["name"] for r in roles_to_create]),
                inline=False,
            )
            embed.add_field(name="Categories", value="\n".join(layout.keys()), inline=False)
            embed.set_footer(text="NICE ONE BROski♾! 🦅🔥")

            await interaction.followup.send(embed=embed)
            logger.info("Server Builder completed successfully for guild %s", guild.id)

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to manage channels and roles. "
                "Please give me Administrator permissions."
            )
        except discord.HTTPException as e:
            logger.error("Failed to build server: %s", e, exc_info=True)
            await interaction.followup.send(
                f"❌ An error occurred while building the server: {e}"
            )

    @hyperfocus_setup.error
    async def _on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            msg = "🔒 Administrator permission required to build the server."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ServerBuilder(bot))
