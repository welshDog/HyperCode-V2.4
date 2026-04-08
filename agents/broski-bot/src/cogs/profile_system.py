#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BROski-Bot Profile System
View profiles, badges, and achievements

Commands:
- /profile [@user] - View user profile card
- /badges - View all badges and progress
- /setbio <text> - Set your profile bio
"""

import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import logging
from datetime import datetime
from typing import Optional
import math

logger = logging.getLogger(__name__)

DB_PATH = "database/broski_main.db"


class ProfileSystem(commands.Cog):
    """Profile cards, badges, and user customization."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = DB_PATH
    
    def _calculate_level(self, xp: int) -> tuple[int, int, int]:
        """Calculate level, current XP, and XP needed for next level."""
        level = int(math.sqrt(xp / 100)) + 1
        xp_for_current_level = (level - 1) ** 2 * 100
        xp_for_next_level = level ** 2 * 100
        current_level_xp = xp - xp_for_current_level
        xp_needed = xp_for_next_level - xp_for_current_level
        return level, current_level_xp, xp_needed
    
    async def _check_badge_unlocks(self, user_id: int):
        """Check and unlock badges for user."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get user stats
            async with db.execute("""
                SELECT broski_tokens, total_xp, total_focus_min, daily_streak
                FROM users WHERE discord_id = ?
            """, (str(user_id),)) as cursor:
                stats = await cursor.fetchone()
            
            if not stats:
                return
            
            tokens, xp, focus_min, streak = stats
            
            # Get all badges
            async with db.execute("SELECT badge_id, requirement_type, requirement_value FROM badges") as cursor:
                badges = await cursor.fetchall()
            
            # Check each badge
            for badge_id, req_type, req_value in badges:
                # Check if already unlocked
                async with db.execute("""
                    SELECT 1 FROM user_badges WHERE user_id = ? AND badge_id = ?
                """, (user_id, badge_id)) as cursor:
                    if await cursor.fetchone():
                        continue  # Already unlocked
                
                # Check requirement
                unlock = False
                if req_type == "tokens_earned" and tokens >= req_value:
                    unlock = True
                elif req_type == "xp_earned" and xp >= req_value:
                    unlock = True
                elif req_type == "focus_minutes" and focus_min >= req_value:
                    unlock = True
                elif req_type == "streak_days" and streak >= req_value:
                    unlock = True
                
                # Unlock if met
                if unlock:
                    await db.execute("""
                        INSERT INTO user_badges (user_id, badge_id, unlocked_at)
                        VALUES (?, ?, ?)
                    """, (user_id, badge_id, datetime.utcnow().isoformat()))
            
            await db.commit()
    
    @app_commands.command(name="profile", description="View a user's profile card")
    @app_commands.describe(user="User to view (defaults to you)")
    async def profile(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Display user profile."""
        target_user = user or interaction.user
        user_id = target_user.id
        
        # Check for badge unlocks
        await self._check_badge_unlocks(user_id)
        
        # Get user data
        async with aiosqlite.connect(self.db_path) as db:
            # Basic stats
            async with db.execute("""
                SELECT username, broski_tokens, total_xp, total_focus_min, daily_streak
                FROM users WHERE discord_id = ?
            """, (str(user_id),)) as cursor:
                stats = await cursor.fetchone()
            
            if not stats:
                await interaction.response.send_message(
                    f"❌ {target_user.mention} hasn't used the bot yet!",
                    ephemeral=True
                )
                return
            
            username, tokens, xp, focus_min, streak = stats
            
            # Profile info
            async with db.execute("""
                SELECT bio, profile_views FROM user_profiles WHERE user_id = ?
            """, (user_id,)) as cursor:
                profile_data = await cursor.fetchone()
                bio = profile_data[0] if profile_data else "No bio set"
                views = profile_data[1] if profile_data else 0
            
            # Badges
            async with db.execute("""
                SELECT b.icon, b.name
                FROM user_badges ub
                JOIN badges b ON ub.badge_id = b.badge_id
                WHERE ub.user_id = ?
                LIMIT 5
            """, (user_id,)) as cursor:
                badges = await cursor.fetchall()
            
            # Customization
            async with db.execute("""
                SELECT custom_title FROM user_customization WHERE user_id = ?
            """, (user_id,)) as cursor:
                custom_data = await cursor.fetchone()
                title = custom_data[0] if custom_data else None
        
        # Calculate level
        level, current_xp, needed_xp = self._calculate_level(xp)
        progress = int((current_xp / needed_xp) * 10)
        progress_bar = "█" * progress + "░" * (10 - progress)
        
        # Build embed
        embed = discord.Embed(
            title=f"{'👑 ' if title else ''}{target_user.display_name}",
            description=bio,
            color=target_user.color or discord.Color.blue()
        )
        
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        if title:
            embed.add_field(name="Title", value=title, inline=False)
        
        # Stats
        embed.add_field(
            name="📊 Level",
            value=f"**Level {level}**\n{progress_bar}\n{current_xp}/{needed_xp} XP",
            inline=True
        )
        embed.add_field(
            name="💰 Tokens",
            value=f"**{tokens:,}** BROski$",
            inline=True
        )
        embed.add_field(
            name="🔥 Streak",
            value=f"**{streak}** days",
            inline=True
        )
        
        embed.add_field(
            name="⏱️ Focus Time",
            value=f"**{focus_min:,}** min",
            inline=True
        )
        embed.add_field(
            name="⭐ Total XP",
            value=f"**{xp:,}**",
            inline=True
        )
        embed.add_field(
            name="👁️ Views",
            value=f"**{views:,}**",
            inline=True
        )
        
        # Badges
        if badges:
            badge_text = " ".join([f"{icon} {name}" for icon, name in badges])
            embed.add_field(
                name=f"🏆 Badges ({len(badges)})",
                value=badge_text,
                inline=False
            )
        
        embed.set_footer(text=f"Member since {target_user.created_at.strftime('%Y-%m-%d')}")
        
        # Update view count
        if target_user != interaction.user:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO user_profiles (user_id, profile_views, last_viewed)
                    VALUES (?, 1, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        profile_views = profile_views + 1,
                        last_viewed = ?
                """, (user_id, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
                await db.commit()
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="badges", description="View all badges and your progress")
    async def badges(self, interaction: discord.Interaction):
        """Display badge collection."""
        user_id = interaction.user.id
        
        # Check for unlocks
        await self._check_badge_unlocks(user_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            # Get all badges with unlock status
            async with db.execute("""
                SELECT 
                    b.badge_id,
                    b.name,
                    b.icon,
                    b.description,
                    b.requirement_type,
                    b.requirement_value,
                    ub.unlocked_at
                FROM badges b
                LEFT JOIN user_badges ub ON b.badge_id = ub.badge_id AND ub.user_id = ?
                ORDER BY b.badge_id
            """, (user_id,)) as cursor:
                badges = await cursor.fetchall()
            
            # Get user stats for progress
            async with db.execute("""
                SELECT broski_tokens, total_xp, total_focus_min, daily_streak
                FROM users WHERE discord_id = ?
            """, (str(user_id),)) as cursor:
                stats = await cursor.fetchone()
        
        if not badges:
            await interaction.response.send_message(
                "🏆 No badges available yet!",
                ephemeral=True
            )
            return
        
        tokens, xp, focus_min, streak = stats if stats else (0, 0, 0, 0)
        
        # Build embed
        embed = discord.Embed(
            title=f"🏆 {interaction.user.display_name}'s Badge Collection",
            color=discord.Color.gold()
        )
        
        unlocked_count = 0
        
        for badge_id, name, icon, desc, req_type, req_value, unlocked_at in badges:
            if unlocked_at:
                unlocked_count += 1
                status = f"✅ Unlocked <t:{int(datetime.fromisoformat(unlocked_at).timestamp())}:R>"
            else:
                # Show progress
                current = 0
                if req_type == "tokens_earned":
                    current = tokens
                elif req_type == "xp_earned":
                    current = xp
                elif req_type == "focus_minutes":
                    current = focus_min
                elif req_type == "streak_days":
                    current = streak
                
                progress_pct = min(100, int((current / req_value) * 100))
                status = f"🔒 Progress: {current}/{req_value} ({progress_pct}%)"
            
            embed.add_field(
                name=f"{icon} {name}",
                value=f"{desc}\n{status}",
                inline=False
            )
        
        embed.description = f"**{unlocked_count}/{len(badges)}** badges unlocked"
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="setbio", description="Set your profile bio")
    @app_commands.describe(bio="Your bio text (max 200 characters)")
    async def setbio(self, interaction: discord.Interaction, bio: str):
        """Set user bio."""
        user_id = interaction.user.id
        
        if len(bio) > 200:
            await interaction.response.send_message(
                "❌ Bio must be 200 characters or less!",
                ephemeral=True
            )
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_profiles (user_id, bio)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET bio = ?
            """, (user_id, bio, bio))
            await db.commit()
        
        await interaction.response.send_message(
            f"✅ Bio updated!\n```{bio}```",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    """Load the profile system cog."""
    await bot.add_cog(ProfileSystem(bot))
