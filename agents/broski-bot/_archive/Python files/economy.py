"""
BROski Economy Cog - Token system, daily streaks, leaderboards
"""

import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import os
from datetime import datetime, timedelta
import random

DB_PATH = os.getenv('DB_PATH', 'database/broski_main.db')

# Dopamine hype messages for daily claims
HYPE_MESSAGES = [
    "🔥 LEGENDARY daily claim, BROski!",
    "💎 Crystal vibes incoming!",
    "🚀 Tokens secured, let's GOOO!",
    "⚡ Hyperfocus energy activated!",
    "🐶 Good BROski energy today!",
    "♾️ Infinite potential unlocked!",
    "🎯 Another day, another win!",
    "💪 Building that empire, mate!",
    "🧠 Neurodivergent excellence!",
    "🌟 ADHD superpowers engaged!"
]

class Economy(commands.Cog):
    """Token economy system"""

    def __init__(self, bot):
        self.bot = bot

    async def ensure_user_exists(self, discord_id: str, username: str):
        """Create user record if doesn't exist"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users (discord_id, username)
                VALUES (?, ?)
            """, (discord_id, username))
            await db.commit()

    async def get_balance(self, discord_id: str):
        """Get user token balance"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("""
                SELECT broski_tokens, hyper_gems, daily_streak, cosmic_rank, total_xp
                FROM users WHERE discord_id = ?
            """, (discord_id,)) as cursor:
                row = await cursor.fetchone()
                return row if row else (0, 0, 0, 'Neuro_Friend', 0)

    async def add_tokens(self, discord_id: str, amount: int, reason: str):
        """Add tokens to user account"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE users SET broski_tokens = broski_tokens + ?
                WHERE discord_id = ?
            """, (amount, discord_id))

            await db.execute("""
                INSERT INTO economy_transactions (discord_id, amount, direction, reason)
                VALUES (?, ?, 'earn', ?)
            """, (discord_id, amount, reason))

            await db.commit()

    @commands.hybrid_command(name="balance", description="Check your BROski$ balance")
    @app_commands.describe(user="User to check (optional)")
    async def balance(self, ctx, user: discord.Member = None):
        """Check token balance"""
        target = user or ctx.author
        await self.ensure_user_exists(str(target.id), target.name)

        tokens, gems, streak, rank, xp = await self.get_balance(str(target.id))

        embed = discord.Embed(
            title=f"💰 {target.display_name}'s Wallet",
            color=0xf1c40f
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🪙 BROski Tokens", value=f"**{tokens:,}** BROski$", inline=True)
        embed.add_field(name="💎 HyperGems", value=f"**{gems}**", inline=True)
        embed.add_field(name="🔥 Streak", value=f"**{streak}** days", inline=True)
        embed.add_field(name="🌟 Cosmic Rank", value=f"**{rank}**", inline=True)
        embed.add_field(name="⚡ Total XP", value=f"**{xp:,}**", inline=True)
        embed.set_footer(text="Keep grinding, BROski! 🐶♾️")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="daily", description="Claim your daily reward (streak bonus!)")
    async def daily(self, ctx):
        """Claim daily reward with streak system"""
        discord_id = str(ctx.author.id)
        await self.ensure_user_exists(discord_id, ctx.author.name)

        async with aiosqlite.connect(DB_PATH) as db:
            # Check last claim
            async with db.execute("""
                SELECT last_checkin, daily_streak FROM users WHERE discord_id = ?
            """, (discord_id,)) as cursor:
                row = await cursor.fetchone()
                last_checkin, current_streak = row if row else (None, 0)

            now = datetime.utcnow().date()

            # Check if already claimed today
            if last_checkin:
                last_date = datetime.fromisoformat(last_checkin).date()
                if last_date == now:
                    next_claim = datetime.combine(now + timedelta(days=1), datetime.min.time())
                    hours_left = int((next_claim - datetime.utcnow()).total_seconds() / 3600)

                    embed = discord.Embed(
                        title="⏰ Already Claimed Today!",
                        description=f"Come back in **{hours_left}h** for your next daily, BROski!",
                        color=0xe74c3c
                    )
                    return await ctx.send(embed=embed)

                # Check streak
                days_diff = (now - last_date).days
                if days_diff == 1:
                    current_streak += 1
                elif days_diff > 1:
                    current_streak = 1
            else:
                current_streak = 1

            # Calculate reward
            base_reward = 50
            streak_bonus = min(current_streak * 10, 200)
            total_reward = base_reward + streak_bonus

            # Update database
            await db.execute("""
                UPDATE users 
                SET broski_tokens = broski_tokens + ?,
                    last_checkin = ?,
                    daily_streak = ?
                WHERE discord_id = ?
            """, (total_reward, now.isoformat(), current_streak, discord_id))

            await db.execute("""
                INSERT INTO economy_transactions (discord_id, amount, direction, reason)
                VALUES (?, ?, 'earn', ?)
            """, (discord_id, total_reward, f"Daily claim (streak: {current_streak})"))

            await db.commit()

        # Success embed
        embed = discord.Embed(
            title="🎉 Daily Reward Claimed!",
            description=random.choice(HYPE_MESSAGES),
            color=0x2ecc71
        )
        embed.add_field(name="💰 Earned", value=f"**+{total_reward} BROski$**", inline=True)
        embed.add_field(name="🔥 Streak", value=f"**{current_streak} days**", inline=True)

        if current_streak >= 7:
            embed.add_field(name="🏆 Bonus", value="**Weekly Legend!** +50 extra", inline=False)
            await self.add_tokens(discord_id, 50, "7-day streak bonus")

        embed.set_footer(text="Keep the streak alive! Come back tomorrow 🐶")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="give", description="Gift tokens to another member")
    @app_commands.describe(user="User to gift to", amount="Amount of tokens")
    async def give(self, ctx, user: discord.Member, amount: int):
        """Transfer tokens between users"""
        if user.bot:
            return await ctx.send("❌ Can't gift tokens to bots, BROski!")

        if user.id == ctx.author.id:
            return await ctx.send("❌ Can't gift yourself, mate! 😅")

        if amount <= 0:
            return await ctx.send("❌ Amount must be positive!")

        sender_id = str(ctx.author.id)
        receiver_id = str(user.id)

        await self.ensure_user_exists(sender_id, ctx.author.name)
        await self.ensure_user_exists(receiver_id, user.name)

        # Check sender has enough
        sender_balance = (await self.get_balance(sender_id))[0]
        if sender_balance < amount:
            return await ctx.send(f"❌ Not enough tokens! You have {sender_balance} BROski$")

        # Transfer
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET broski_tokens = broski_tokens - ? WHERE discord_id = ?", 
                           (amount, sender_id))
            await db.execute("UPDATE users SET broski_tokens = broski_tokens + ? WHERE discord_id = ?", 
                           (amount, receiver_id))

            await db.execute("""
                INSERT INTO economy_transactions (discord_id, amount, direction, reason)
                VALUES (?, ?, 'spend', ?)
            """, (sender_id, amount, f"Gift to {user.name}"))

            await db.execute("""
                INSERT INTO economy_transactions (discord_id, amount, direction, reason)
                VALUES (?, ?, 'earn', ?)
            """, (receiver_id, amount, f"Gift from {ctx.author.name}"))

            await db.commit()

        embed = discord.Embed(
            title="🎁 Tokens Gifted!",
            description=f"**{ctx.author.display_name}** → **{user.display_name}**",
            color=0x9b59b6
        )
        embed.add_field(name="Amount", value=f"**{amount:,} BROski$**")
        embed.set_footer(text="Generosity is legendary! 🐶♾️")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="leaderboard", description="View top BROski earners")
    @app_commands.describe(category="What to rank by")
    @app_commands.choices(category=[
        app_commands.Choice(name="Tokens", value="tokens"),
        app_commands.Choice(name="XP", value="xp"),
        app_commands.Choice(name="Streak", value="streak"),
        app_commands.Choice(name="Focus Time", value="focus")
    ])
    async def leaderboard(self, ctx, category: str = "tokens"):
        """Show leaderboards"""
        field_map = {
            "tokens": ("broski_tokens", "💰 Token"),
            "xp": ("total_xp", "⚡ XP"),
            "streak": ("daily_streak", "🔥 Streak"),
            "focus": ("total_focus_min", "⏱️ Focus")
        }

        db_field, display_name = field_map.get(category, ("broski_tokens", "💰 Token"))

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(f"""
                SELECT username, {db_field} FROM users
                WHERE is_active = TRUE
                ORDER BY {db_field} DESC
                LIMIT 10
            """) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            return await ctx.send("❌ No data yet! Start earning, BROski!")

        embed = discord.Embed(
            title=f"🏆 {display_name} Leaderboard - Top 10",
            color=0xf39c12
        )

        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7

        leaderboard_text = ""
        for i, (username, value) in enumerate(rows):
            medal = medals[i]
            leaderboard_text += f"{medal} **{username}** - {value:,}\n"

        embed.description = leaderboard_text
        embed.set_footer(text="Keep grinding to reach the top! 🐶♾️")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))
