"""
Focus Engine Cog v2.0 - Refactored for PostgreSQL/SQLAlchemy
Hyperfocus Pomodoro sessions with BROski$ rewards
"""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from sqlalchemy import select

from src.core.database import get_db_session
from src.models import User, FocusSession, Transaction
from src.config.logging import get_logger

logger = get_logger(__name__)


class FocusEngine(commands.Cog):
    """Hyperfocus session tracker — PostgreSQL edition 🧠"""

    def __init__(self, bot):
        self.bot = bot
        self.active_sessions: dict = {}  # {user_id: {start, project}}

    @commands.hybrid_command(name="focus", description="Start a hyperfocus session")
    @app_commands.describe(project="What are you working on?")
    async def focus_start(self, ctx, *, project: str = "Coding"):
        user_id = ctx.author.id

        if user_id in self.active_sessions:
            return await ctx.send("❌ Already in session! Use `/focusend` first.")

        self.active_sessions[user_id] = {
            "start": datetime.now(timezone.utc),
            "project": project,
        }

        async with get_db_session() as session:
            # Ensure user exists
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                # Need username/discriminator for User model creation
                user = User(
                    id=user_id, 
                    username=ctx.author.name,
                    discriminator=ctx.author.discriminator
                )
                session.add(user)
                await session.flush() # Ensure ID is available if autoincrement (though here it's explicit)

            # Check if economy record exists, create if not
            if not user.economy:
                 from src.models.economy import Economy
                 economy = Economy(user_id=user_id, balance=0)
                 session.add(economy)
                 user.economy = economy

            # Award session-start tokens (+50)
            # Using relation or direct update
            # Since economy is a separate model linked via relationship
            user.economy.balance += 50
            
            session.add(Transaction(
                user_id=user_id,
                amount=50,
                type="credit",
                category="focus",
                description="Focus session started",
            ))
            await session.commit()

        embed = discord.Embed(
            title="⏱️ Hyperfocus Session Started!",
            description=f"**Project:** {project}",
            color=0x3498DB,
        )
        embed.add_field(name="💰 Rewards", value="Complete = **+200 BROski$** + time bonus", inline=False)
        embed.add_field(name="🎯 Tips", value="• Minimise distractions\n• Stay hydrated\n• You got this!", inline=False)
        embed.set_footer(text="Let's GO, BROski! 🐶♾️")
        await ctx.send(embed=embed)
        logger.info("Focus session started", user_id=user_id, project=project)

    @commands.hybrid_command(name="focusend", description="End your hyperfocus session")
    async def focus_end(self, ctx):
        user_id = ctx.author.id

        if user_id not in self.active_sessions:
            return await ctx.send("❌ No active session! Start one with `/focus`")

        session_data = self.active_sessions.pop(user_id)
        end_time = datetime.now(timezone.utc)
        duration_mins = max(1, int((end_time - session_data["start"]).total_seconds() / 60))

        base_reward = 200
        time_bonus = min(duration_mins * 2, 500)
        total_reward = base_reward + time_bonus
        xp_earned = duration_mins * 5

        async with get_db_session() as session:
            # Log the focus session to PostgreSQL
            focus_row = FocusSession(
                user_id=user_id,
                project_name=session_data["project"],
                duration_minutes=duration_mins,
                tokens_earned=total_reward,
                # xp_earned=xp_earned, # FocusSession model doesn't have xp_earned column in provided schema
                start_time=session_data["start"],
                end_time=end_time,
                is_active=False,
                is_hyperfocus=True
            )
            session.add(focus_row)

            # Update user totals
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                if user.economy:
                    user.economy.balance += total_reward
                else:
                     # Fallback if economy record missing (shouldn't happen if start ran)
                     from src.models.economy import Economy
                     economy = Economy(user_id=user_id, balance=total_reward)
                     session.add(economy)
                
                user.xp += xp_earned

            # Log transaction
            session.add(Transaction(
                user_id=user_id,
                amount=total_reward,
                type="credit",
                category="focus",
                description=f"Focus session completed ({duration_mins} min)",
            ))
            await session.commit()

        embed = discord.Embed(
            title="🎉 Hyperfocus Session Complete!",
            description=f"**Project:** {session_data['project']}",
            color=0x2ECC71,
        )
        embed.add_field(name="⏱️ Duration", value=f"**{duration_mins}** min", inline=True)
        embed.add_field(name="💰 Earned", value=f"**+{total_reward} BROski$**", inline=True)
        embed.add_field(name="⚡ XP", value=f"**+{xp_earned}**", inline=True)
        if duration_mins >= 60:
            embed.add_field(name="🏆 Achievement", value="**LEGENDARY FOCUS** (60+ min)!", inline=False)
        embed.set_footer(text="Smashed it, BROski! 🐶♾️")
        await ctx.send(embed=embed)
        logger.info("Focus session ended", user_id=user_id, duration=duration_mins, reward=total_reward)


async def setup(bot):
    await bot.add_cog(FocusEngine(bot))
