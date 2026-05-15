"""
BROski Bot — Welcome Cog
Fires on member join → upserts broski_members → sends embed
"""
import discord
from discord.ext import commands
from datetime import datetime, timezone
import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
WELCOME_CHANNEL_NAME = os.getenv("WELCOME_CHANNEL_NAME", "welcome")

def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


class Welcome(commands.Cog):
    """Handles member join events and welcome messages."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Upsert member into broski_members and send welcome embed."""
        sb = get_supabase()
        sb.table("broski_members").upsert({
            "discord_id": str(member.id),
            "username": member.name,
            "joined_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="discord_id").execute()

        channel = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL_NAME)
        if not channel:
            return

        embed = discord.Embed(
            title=f"⚡ Welcome to the HyperFocus Zone, {member.display_name}!",
            description=(
                "You're now part of the most **neurodivergent-powered** community on Discord.\n\n"
                "🧠 **What's here for you:**\n"
                "• `/daily` — claim your daily BROski$ tokens\n"
                "• `/quests` — pick up missions and earn XP\n"
                "• `/balance` — check your BROski$ wallet\n"
                "• `/mypet` — meet your BROskiPet companion\n\n"
                "You belong here. Let's build something legendary. 🔥"
            ),
            colour=discord.Colour.purple(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="BROski Bot • HyperFocus Zone")
        embed.add_field(name="💰 Starting Balance", value="0 BROski$", inline=True)
        embed.add_field(name="🎯 First Move", value="Try `/daily` right now!", inline=True)

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"[Welcome Cog] ✅ Ready — listening for member joins")


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
