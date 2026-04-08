#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BROski-Bot Mystery Box System
Open loot boxes for random rewards

Commands:
- /openbox <type> - Open a mystery box (basic/premium/legendary)
- /boxhistory - View your box opening history
"""

import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import logging
import random
from datetime import datetime
from typing import Literal

logger = logging.getLogger(__name__)

DB_PATH = "database/broski_main.db"


class MysteryBox(commands.Cog):
    """Mystery box system for random rewards."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = DB_PATH
        
        # Box definitions
        self.box_types = {
            "basic": {
                "price": 300,
                "rewards": {
                    "tokens": {
                        "weight": 70,
                        "amounts": [50, 100, 200, 350, 500]
                    },
                    "xp": {
                        "weight": 20,
                        "amounts": [100, 200, 300, 500]
                    },
                    "rare_item": {
                        "weight": 10,
                        "items": ["🎯 Lucky Charm", "⭐ Rare Badge", "💎 Mini Crystal"]
                    }
                },
                "icon": "📦",
                "color": discord.Color.blue()
            },
            "premium": {
                "price": 800,
                "rewards": {
                    "tokens": {
                        "weight": 60,
                        "amounts": [200, 500, 750, 1000, 1500]
                    },
                    "xp": {
                        "weight": 25,
                        "amounts": [300, 500, 750, 1000]
                    },
                    "rare_item": {
                        "weight": 15,
                        "items": ["🏆 Premium Badge", "💎 Power Crystal", "🌟 VIP Pass (3 days)"]
                    }
                },
                "icon": "🎁",
                "color": discord.Color.purple()
            },
            "legendary": {
                "price": 2000,
                "rewards": {
                    "tokens": {
                        "weight": 50,
                        "amounts": [1000, 2000, 3000, 5000, 7500]
                    },
                    "xp": {
                        "weight": 30,
                        "amounts": [1000, 1500, 2000, 3000]
                    },
                    "rare_item": {
                        "weight": 20,
                        "items": ["👑 Legendary Badge", "💎 Epic Crystal", "🔥 VIP Pass (7 days)", "🎨 Custom Role Color"]
                    }
                },
                "icon": "💎",
                "color": discord.Color.gold()
            }
        }
    
    async def _get_user_balance(self, user_id: int) -> int:
        """Get user's token balance."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT broski_tokens FROM users WHERE discord_id = ?",
                (str(user_id),)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    def _roll_reward(self, box_type: str) -> tuple[str, str]:
        """Roll for a random reward."""
        box = self.box_types[box_type]
        
        # Weighted random selection
        reward_types = list(box["rewards"].keys())
        weights = [box["rewards"][r]["weight"] for r in reward_types]
        reward_type = random.choices(reward_types, weights=weights)[0]
        
        # Get specific reward
        if reward_type == "tokens":
            amount = random.choice(box["rewards"]["tokens"]["amounts"])
            return "tokens", str(amount)
        elif reward_type == "xp":
            amount = random.choice(box["rewards"]["xp"]["amounts"])
            return "xp", str(amount)
        elif reward_type == "rare_item":
            item = random.choice(box["rewards"]["rare_item"]["items"])
            return "rare_item", item
        
        return "tokens", "100"  # Fallback
    
    @app_commands.command(name="openbox", description="Open a mystery box for random rewards")
    @app_commands.describe(box_type="Type of box to open")
    async def openbox(
        self,
        interaction: discord.Interaction,
        box_type: Literal["basic", "premium", "legendary"]
    ):
        """Open a mystery box."""
        user_id = interaction.user.id
        
        if box_type not in self.box_types:
            await interaction.response.send_message(
                "❌ Invalid box type! Choose: basic, premium, or legendary",
                ephemeral=True
            )
            return
        
        box = self.box_types[box_type]
        price = box["price"]
        
        # Check balance
        balance = await self._get_user_balance(user_id)
        if balance < price:
            await interaction.response.send_message(
                f"❌ Insufficient funds!\n"
                f"{box['icon']} **{box_type.title()} Box** costs **{price} BROski$**\n"
                f"💳 Your balance: **{balance} BROski$**",
                ephemeral=True
            )
            return
        
        # Deduct cost
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET broski_tokens = broski_tokens - ? WHERE discord_id = ?",
                (price, str(user_id))
            )
            await db.commit()
        
        # Opening animation
        await interaction.response.send_message(
            f"{box['icon']} Opening **{box_type.title()} Mystery Box**... 🎲"
        )
        
        # Roll reward
        reward_type, reward_value = self._roll_reward(box_type)
        
        # Apply reward
        async with aiosqlite.connect(self.db_path) as db:
            if reward_type == "tokens":
                amount = int(reward_value)
                await db.execute(
                    "UPDATE users SET broski_tokens = broski_tokens + ? WHERE discord_id = ?",
                    (amount, str(user_id))
                )
            elif reward_type == "xp":
                amount = int(reward_value)
                await db.execute(
                    "UPDATE users SET total_xp = total_xp + ? WHERE discord_id = ?",
                    (amount, str(user_id))
                )
            elif reward_type == "rare_item":
                # Log rare drop
                await db.execute("""
                    INSERT INTO rare_drops (user_id, item_name, dropped_at)
                    VALUES (?, ?, ?)
                """, (user_id, reward_value, datetime.utcnow().isoformat()))
            
            # Record opening
            await db.execute("""
                INSERT INTO box_openings (user_id, box_type, reward_type, reward_value, opened_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, box_type, reward_type, reward_value, datetime.utcnow().isoformat()))
            
            await db.commit()
        
        # Get new balance
        new_balance = await self._get_user_balance(user_id)
        
        # Build result embed
        embed = discord.Embed(
            title=f"🎉 {box['icon']} {box_type.title()} Box Opened!",
            color=box["color"]
        )
        
        if reward_type == "tokens":
            amount = int(reward_value)
            net = amount - price
            embed.add_field(name="Reward", value=f"💰 **{amount} BROski$**", inline=True)
            embed.add_field(
                name="Net Profit",
                value=f"{'🟢' if net > 0 else '🔴'} {net:+} BROski$",
                inline=True
            )
            embed.add_field(name="New Balance", value=f"{new_balance} BROski$", inline=True)
        elif reward_type == "xp":
            amount = int(reward_value)
            embed.add_field(name="Reward", value=f"⭐ **{amount} XP**", inline=True)
            embed.add_field(name="Cost", value=f"{price} BROski$", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance} BROski$", inline=True)
        elif reward_type == "rare_item":
            embed.add_field(name="Reward", value=f"🎁 **{reward_value}**", inline=True)
            embed.add_field(name="Rarity", value="⭐ **RARE DROP!**", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance} BROski$", inline=True)
            embed.description = "🎊 Congratulations on the rare drop!"
        
        embed.set_footer(text="Use /boxhistory to see all your openings")
        
        await interaction.edit_original_response(content=None, embed=embed)
        logger.info(f"User {user_id} opened {box_type} box, got {reward_type}: {reward_value}")
    
    @app_commands.command(name="boxhistory", description="View your mystery box opening history")
    async def boxhistory(self, interaction: discord.Interaction):
        """Display box opening history."""
        user_id = interaction.user.id
        
        async with aiosqlite.connect(self.db_path) as db:
            # Get recent openings
            async with db.execute("""
                SELECT box_type, reward_type, reward_value, opened_at
                FROM box_openings
                WHERE user_id = ?
                ORDER BY opened_at DESC
                LIMIT 10
            """, (user_id,)) as cursor:
                recent = await cursor.fetchall()
            
            # Get statistics
            async with db.execute("""
                SELECT 
                    COUNT(*) as total_opens,
                    box_type,
                    SUM(CASE WHEN reward_type = 'tokens' THEN CAST(reward_value AS INTEGER) ELSE 0 END) as total_tokens,
                    COUNT(CASE WHEN reward_type = 'rare_item' THEN 1 END) as rare_drops
                FROM box_openings
                WHERE user_id = ?
                GROUP BY box_type
            """, (user_id,)) as cursor:
                stats = await cursor.fetchall()
        
        if not recent:
            await interaction.response.send_message(
                "📦 You haven't opened any boxes yet!\n💡 Use `/openbox <type>` to start!",
                ephemeral=True
            )
            return
        
        # Build embed
        embed = discord.Embed(
            title=f"📊 {interaction.user.display_name}'s Box History",
            color=discord.Color.blue()
        )
        
        # Recent openings
        recent_text = []
        for box_type, reward_type, reward_value, opened_at in recent[:5]:
            icon = self.box_types[box_type]["icon"]
            if reward_type == "tokens":
                reward_text = f"💰 {reward_value} BROski$"
            elif reward_type == "xp":
                reward_text = f"⭐ {reward_value} XP"
            else:
                reward_text = f"🎁 {reward_value}"
            
            recent_text.append(f"{icon} **{box_type.title()}** → {reward_text}")
        
        embed.add_field(
            name="📋 Recent Openings",
            value="\n".join(recent_text) if recent_text else "None",
            inline=False
        )
        
        # Statistics
        if stats:
            stats_text = []
            for total, box_type, tokens, rares in stats:
                icon = self.box_types[box_type]["icon"]
                stats_text.append(
                    f"{icon} **{box_type.title()}:** {total} opened | {tokens} tokens | {rares} rares"
                )
            
            embed.add_field(
                name="📈 Statistics",
                value="\n".join(stats_text),
                inline=False
            )
        
        embed.set_footer(text="Showing last 10 openings")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Load the mystery box cog."""
    await bot.add_cog(MysteryBox(bot))
