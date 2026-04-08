#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BROski-Bot Shop System
Purchase items, manage inventory, and customize your experience

Commands:
- /shop - Browse all available items
- /buy <item_id> - Purchase an item
- /inventory - View your owned items
"""

import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

DB_PATH = "database/broski_main.db"


class ShopSystem(commands.Cog):
    """Shop system for purchasing items with BROski tokens."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = DB_PATH
    
    async def _get_user_balance(self, user_id: int) -> int:
        """Get user's token balance."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT broski_tokens FROM users WHERE discord_id = ?",
                (str(user_id),)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    async def _deduct_tokens(self, user_id: int, amount: int):
        """Deduct tokens from user balance."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET broski_tokens = broski_tokens - ? WHERE discord_id = ?",
                (amount, str(user_id))
            )
            await db.execute(
                "INSERT INTO economy_transactions (discord_id, amount, direction, reason) VALUES (?, ?, 'spend', 'Shop purchase')",
                (str(user_id), amount)
            )
            await db.commit()
    
    @app_commands.command(name="shop", description="Browse items available for purchase")
    async def shop(self, interaction: discord.Interaction):
        """Display shop items."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT item_id, name, description, price, icon, category, stock
                FROM shop_items WHERE active = 1
                ORDER BY category, price
            """) as cursor:
                items = await cursor.fetchall()
        
        if not items:
            await interaction.response.send_message(
                "🛒 The shop is currently empty! Check back later.",
                ephemeral=True
            )
            return
        
        # Build shop embed
        embed = discord.Embed(
            title="🛒 BROski Shop",
            description="Purchase items with your BROski$ tokens!",
            color=discord.Color.gold()
        )
        
        # Group by category
        categories = {}
        for item in items:
            item_id, name, desc, price, icon, category, stock = item
            if category not in categories:
                categories[category] = []
            
            stock_text = f" (Stock: {stock})" if stock != -1 else ""
            categories[category].append(
                f"{icon} **#{item_id} {name}** - {price} BROski${stock_text}\n{desc}"
            )
        
        # Add fields by category
        for category, items_list in categories.items():
            embed.add_field(
                name=f"📂 {category.title()}",
                value="\n\n".join(items_list),
                inline=False
            )
        
        embed.set_footer(text="Use /buy <item_id> to purchase | /inventory to view owned items")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="buy", description="Purchase an item from the shop")
    @app_commands.describe(item_id="Item ID number from /shop")
    async def buy(self, interaction: discord.Interaction, item_id: int):
        """Purchase an item."""
        user_id = interaction.user.id
        
        # Get item details
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT name, description, price, stock, duration_minutes, usable
                FROM shop_items WHERE item_id = ? AND active = 1
            """, (item_id,)) as cursor:
                item = await cursor.fetchone()
        
        if not item:
            await interaction.response.send_message(
                f"❌ Item #{item_id} not found or unavailable!",
                ephemeral=True
            )
            return
        
        name, description, price, stock, duration_minutes, usable = item
        
        # Check stock
        if stock == 0:
            await interaction.response.send_message(
                f"❌ **{name}** is out of stock!",
                ephemeral=True
            )
            return
        
        # Check balance
        balance = await self._get_user_balance(user_id)
        if balance < price:
            await interaction.response.send_message(
                f"❌ Insufficient funds!\n"
                f"💰 Price: **{price} BROski$**\n"
                f"💳 Your balance: **{balance} BROski$**\n"
                f"💸 Need: **{price - balance} more**",
                ephemeral=True
            )
            return
        
        # Process purchase
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Deduct tokens
                await db.execute(
                    "UPDATE users SET broski_tokens = broski_tokens - ? WHERE discord_id = ?",
                    (price, str(user_id))
                )
                
                # Calculate expiration if item has duration
                expires_at = None
                if duration_minutes:
                    expires_at = (datetime.utcnow() + timedelta(minutes=duration_minutes)).isoformat()
                
                # Add to inventory
                await db.execute("""
                    INSERT INTO user_inventory (user_id, item_id, quantity, purchased_at, expires_at)
                    VALUES (?, ?, 1, ?, ?)
                """, (user_id, item_id, datetime.utcnow().isoformat(), expires_at))
                
                # Update stock if limited
                if stock != -1:
                    await db.execute(
                        "UPDATE shop_items SET stock = stock - 1 WHERE item_id = ?",
                        (item_id,)
                    )
                
                # Log transaction
                await db.execute("""
                    INSERT INTO economy_transactions (discord_id, amount, direction, reason)
                    VALUES (?, ?, 'spend', ?)
                """, (str(user_id), price, f"Purchased {name}"))
                
                await db.commit()
            
            # Success message
            embed = discord.Embed(
                title="✅ Purchase Successful!",
                description=f"You bought **{name}**!",
                color=discord.Color.green()
            )
            
            embed.add_field(name="Item", value=description, inline=False)
            embed.add_field(name="Price", value=f"{price} BROski$", inline=True)
            embed.add_field(name="New Balance", value=f"{balance - price} BROski$", inline=True)
            
            if expires_at:
                embed.add_field(
                    name="Expires",
                    value=f"<t:{int(datetime.fromisoformat(expires_at).timestamp())}:R>",
                    inline=True
                )
            
            if usable:
                embed.set_footer(text="Use /inventory to use this item")
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"User {user_id} purchased item #{item_id} ({name}) for {price} tokens")
            
        except Exception as e:
            logger.error(f"Purchase error for user {user_id}: {e}")
            await interaction.response.send_message(
                "❌ Purchase failed! Please try again.",
                ephemeral=True
            )
    
    @app_commands.command(name="inventory", description="View your owned items")
    async def inventory(self, interaction: discord.Interaction):
        """Display user's inventory."""
        user_id = interaction.user.id
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT si.name, si.icon, si.description, ui.quantity, ui.purchased_at, ui.expires_at, ui.used
                FROM user_inventory ui
                JOIN shop_items si ON ui.item_id = si.item_id
                WHERE ui.user_id = ?
                ORDER BY ui.purchased_at DESC
            """, (user_id,)) as cursor:
                items = await cursor.fetchall()
        
        if not items:
            await interaction.response.send_message(
                "📦 Your inventory is empty!\n💡 Use `/shop` to browse items.",
                ephemeral=True
            )
            return
        
        # Build inventory embed
        embed = discord.Embed(
            title=f"📦 {interaction.user.display_name}'s Inventory",
            color=discord.Color.blue()
        )
        
        for name, icon, desc, quantity, purchased_at, expires_at, used in items:
            status = ""
            if used:
                status = " ✅ (Used)"
            elif expires_at:
                expire_dt = datetime.fromisoformat(expires_at)
                if expire_dt < datetime.utcnow():
                    status = " ⏰ (Expired)"
                else:
                    status = f" ⏳ (Expires <t:{int(expire_dt.timestamp())}:R>)"
            
            embed.add_field(
                name=f"{icon} {name} x{quantity}{status}",
                value=desc,
                inline=False
            )
        
        embed.set_footer(text=f"Total items: {len(items)}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Load the shop system cog."""
    await bot.add_cog(ShopSystem(bot))
