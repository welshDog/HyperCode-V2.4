"""
Server Builder Cog - Designer & Builder skill for BROski Bot.
Creates the ultimate "HYPERFOCUS ZONE" server layout.
"""
import discord
from discord import app_commands
from discord.ext import commands

from src.config.logging import get_logger

logger = get_logger(__name__)

class ServerBuilder(commands.Cog):
    """Server Designer & Builder skill for the ultimate HYPERFOCUS ZONE."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="hyperfocus_setup", description="Build the ultimate HYPERFOCUS ZONE server layout")
    @app_commands.checks.has_permissions(administrator=True)
    async def hyperfocus_setup(self, interaction: discord.Interaction) -> None:
        """
        Creates the structured categories, channels, and roles for the HYPERFOCUS ZONE.
        Requires Administrator permissions.
        """
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ This command must be run in a server.", ephemeral=True)
            return

        await interaction.response.send_message("🏗️ **BROski Server Builder activated!** Designing the HYPERFOCUS ZONE...\nThis might take a minute.", ephemeral=False)

        try:
            # 1. Create Roles
            roles_to_create = [
                {"name": "Captain", "color": discord.Color.purple(), "hoist": True},
                {"name": "BROski", "color": discord.Color.blue(), "hoist": True},
                {"name": "In The Zone", "color": discord.Color.red(), "hoist": True}
            ]
            
            role_objects = {}
            for role_data in roles_to_create:
                existing_role = discord.utils.get(guild.roles, name=role_data["name"])
                if not existing_role:
                    role_objects[role_data["name"]] = await guild.create_role(**role_data)
                    logger.info(f"Created role: {role_data['name']}")
                else:
                    role_objects[role_data["name"]] = existing_role

            # 2. Define Category & Channel Structure
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
                ]
            }

            # 3. Create Categories and Channels
            for cat_name, channels in layout.items():
                category = discord.utils.get(guild.categories, name=cat_name)
                if not category:
                    category = await guild.create_category(cat_name)
                    logger.info(f"Created category: {cat_name}")

                for ch_data in channels:
                    existing_channel = discord.utils.get(guild.channels, name=ch_data["name"], category=category)
                    if not existing_channel:
                        if ch_data["type"] == discord.ChannelType.text:
                            await guild.create_text_channel(ch_data["name"], category=category)
                        elif ch_data["type"] == discord.ChannelType.voice:
                            await guild.create_voice_channel(ch_data["name"], category=category)
                        logger.info(f"Created channel: {ch_data['name']} in {cat_name}")

            # 4. Final Success Message
            embed = discord.Embed(
                title="✅ HYPERFOCUS ZONE Built!",
                description="The server has been tidied up and structured for maximum focus.",
                color=0x2ECC71,
            )
            embed.add_field(name="Roles Created", value=", ".join([r["name"] for r in roles_to_create]), inline=False)
            embed.add_field(name="Categories", value="\n".join(layout.keys()), inline=False)
            embed.set_footer(text="NICE ONE BROski♾! 🦅🔥")

            await interaction.followup.send(embed=embed)
            logger.info("Server Builder completed successfully.", guild_id=guild.id)

        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to manage channels and roles. Please give me Administrator permissions.")
        except Exception as e:
            logger.error("Failed to build server", error=str(e), exc_info=True)
            await interaction.followup.send(f"❌ An error occurred while building the server: {e}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ServerBuilder(bot))
