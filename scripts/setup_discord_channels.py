# scripts/setup_discord_channels.py
# One-shot script to scaffold the full HyperFocus Zone Discord channel structure
# Usage: python scripts/setup_discord_channels.py
# Needs: DISCORD_TOKEN + DISCORD_GUILD_ID in .env

import discord
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

STRUCTURE = [
    {
        "category": "🚀 START HERE",
        "channels": [
            ("👋・welcome", "text", "Welcome to the HyperFocus Zone! Start here."),
            ("📜・rules", "text", "Read before anything else."),
            ("🎭・get-your-roles", "text", "React to get your roles!"),
        ]
    },
    {
        "category": "📣 HQ BROADCAST",
        "channels": [
            ("📢・announcements", "text", "Official HyperFocus Zone updates."),
            ("🔧・build-updates", "text", "HyperCode agent + infra alerts."),
            ("🤖・agent-logs", "text", "Live agent activity feed from HyperCode."),
        ]
    },
    {
        "category": "💻 BUILD MODE",
        "channels": [
            ("💬・code-chat", "text", "General dev chat."),
            ("🚀・project-showcase", "text", "Show what you built!"),
            ("⚡・hyperfocus-sessions", "text", "Active focus sessions. Lock in here."),
            ("🆘・code-help", "text", "Stuck? Drop it here. Community helps."),
        ]
    },
    {
        "category": "🪙 ECONOMY HQ",
        "channels": [
            ("🏆・broski-leaderboard", "text", "Top BROski$ earners."),
            ("🛒・token-shop", "text", "Spend your BROski$ here."),
            ("🎖️・achievements", "text", "Milestone unlocks and celebrations!"),
        ]
    },
    {
        "category": "🧠 BRAIN ZONE",
        "channels": [
            ("☀️・morning-briefing", "text", "Daily 08:00 BST briefing. Use /briefing."),
            ("✅・daily-checkin", "text", "Post your daily goal here."),
            ("🎉・adhd-wins", "text", "Celebrate every win, big or small!"),
            ("🎮・chill", "text", "Off-topic, memes, vibes."),
        ]
    },
]


class SetupBot(discord.Client):
    async def on_ready(self):
        guild = self.get_guild(GUILD_ID)
        if not guild:
            print(f"❌ Guild {GUILD_ID} not found! Check DISCORD_GUILD_ID in .env")
            await self.close()
            return

        print(f"✅ Connected to: {guild.name}")
        print("🏗️  Building HyperFocus Zone channel structure...\n")

        for cat_data in STRUCTURE:
            category = await guild.create_category(cat_data["category"])
            print(f"📁 Created category: {cat_data['category']}")
            for name, kind, topic in cat_data["channels"]:
                if kind == "text":
                    await guild.create_text_channel(name, category=category, topic=topic)
                    print(f"  ✅ #{name}")
                await asyncio.sleep(0.5)  # rate limit safety

        print("\n🎉 HyperFocus Zone Discord structure built! Nice one BROski\u267e\ufe0f!")
        await self.close()


if __name__ == "__main__":
    if not TOKEN:
        print("❌ DISCORD_TOKEN not found in .env")
        exit(1)
    if GUILD_ID == 0:
        print("❌ DISCORD_GUILD_ID not set in .env")
        exit(1)

    intents = discord.Intents.default()
    client = SetupBot(intents=intents)
    client.run(TOKEN)
