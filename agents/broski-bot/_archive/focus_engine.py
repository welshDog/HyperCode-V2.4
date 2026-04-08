"""
Focus Engine Cog - Hyperfocus Pomodoro sessions with rewards
"""

import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import os
from datetime import datetime

DB_PATH = os.getenv('DB_PATH', 'database/broski_main.db')

class FocusEngine(commands.Cog):
    """Hyperfocus session tracker"""

    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}  # {user_id: start_time}

    @commands.hybrid_command(name="focus", description="Start a hyperfocus session")
    @app_commands.describe(project="What are you working on?")
    async def focus_start(self, ctx, *, project: str = "Coding"):
        """Start focus session"""
        user_id = str(ctx.author.id)

        if user_id in self.active_sessions:
            return await ctx.send("❌ You already have an active session! Use `/focus end` first.")

        self.active_sessions[user_id] = {
            'start': datetime.utcnow(),
            'project': project
        }

        embed = discord.Embed(
            title="⏱️ Hyperfocus Session Started!",
            description=f"**Project:** {project}",
            color=0x3498db
        )
        embed.add_field(name="💰 Rewards", value="Complete session = **+200 BROski$**", inline=False)
        embed.add_field(name="🎯 Tips", value="• Minimize distractions\n• Take breaks\n• Stay hydrated", inline=False)
        embed.set_footer(text="You got this, BROski! 🐶♾️")

        await ctx.send(embed=embed)

        # Award session start tokens
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE users SET broski_tokens = broski_tokens + 50
                WHERE discord_id = ?
            """, (user_id,))
            await db.execute("""
                INSERT INTO economy_transactions (discord_id, amount, direction, reason)
                VALUES (?, 50, 'earn', 'Focus session started')
            """, (user_id,))
            await db.commit()

    @commands.hybrid_command(name="focusend", description="End your hyperfocus session")
    async def focus_end(self, ctx):
        """End focus session"""
        user_id = str(ctx.author.id)

        if user_id not in self.active_sessions:
            return await ctx.send("❌ No active session found! Start one with `/focus`")

        session = self.active_sessions[user_id]
        end_time = datetime.utcnow()
        duration = end_time - session['start']
        duration_mins = int(duration.total_seconds() / 60)

        # Calculate rewards
        base_reward = 200
        time_bonus = min(duration_mins * 2, 500)
        total_reward = base_reward + time_bonus

        # Save to database
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO focus_sessions (discord_id, project_name, start_time, end_time, duration_min, tokens_earned, completed)
                VALUES (?, ?, ?, ?, ?, ?, TRUE)
            """, (user_id, session['project'], session['start'], end_time, duration_mins, total_reward))

            await db.execute("""
                UPDATE users 
                SET broski_tokens = broski_tokens + ?,
                    total_focus_min = total_focus_min + ?,
                    total_xp = total_xp + ?
                WHERE discord_id = ?
            """, (total_reward, duration_mins, duration_mins * 5, user_id))

            await db.execute("""
                INSERT INTO economy_transactions (discord_id, amount, direction, reason)
                VALUES (?, ?, 'earn', ?)
            """, (user_id, total_reward, f"Focus session completed ({duration_mins} min)"))

            await db.commit()

        # Remove from active
        del self.active_sessions[user_id]

        embed = discord.Embed(
            title="🎉 Hyperfocus Session Complete!",
            description=f"**Project:** {session['project']}",
            color=0x2ecc71
        )
        embed.add_field(name="⏱️ Duration", value=f"**{duration_mins}** minutes", inline=True)
        embed.add_field(name="💰 Earned", value=f"**+{total_reward} BROski$**", inline=True)
        embed.add_field(name="⚡ XP Gained", value=f"**+{duration_mins * 5} XP**", inline=True)

        if duration_mins >= 60:
            embed.add_field(name="🏆 Achievement", value="**LEGENDARY FOCUS** (60+ minutes)!", inline=False)

        embed.set_footer(text="Amazing work, BROski! 🐶♾️")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FocusEngine(bot))
