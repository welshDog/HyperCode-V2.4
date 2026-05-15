"""
BROski Bot — Economy Cog
Commands: /balance /daily /give /rich
Wired to: broski_members + broski_transactions (Supabase)
"""
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
DAILY_AMOUNT = int(os.getenv("DAILY_TOKEN_AMOUNT", "50"))
DAILY_COOLDOWN_HOURS = 20


def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _get_or_create_member(sb: Client, member: discord.Member) -> dict:
    res = sb.table("broski_members").upsert({
        "discord_id": str(member.id),
        "username": member.name,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="discord_id").execute()
    return res.data[0] if res.data else {}


def _progress_bar(current: int, maximum: int, length: int = 10) -> str:
    filled = int((current / max(maximum, 1)) * length)
    return "█" * filled + "░" * (length - filled)


class Economy(commands.Cog):
    """BROski$ token economy commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your BROski$ token balance 💰")
    async def balance(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        sb = get_supabase()
        row = _get_or_create_member(sb, interaction.user)

        tokens = row.get("broski_tokens", 0)
        xp = row.get("xp", 0)
        level = row.get("level", 1)
        streak = row.get("streak_days", 0)
        xp_next = level * 100
        bar = _progress_bar(xp % xp_next, xp_next)

        embed = discord.Embed(
            title=f"💰 {interaction.user.display_name}'s Wallet",
            colour=discord.Colour.gold(),
        )
        embed.add_field(name="BROski$ Balance", value=f"**{tokens:,}** tokens", inline=True)
        embed.add_field(name="🔥 Streak", value=f"{streak} days", inline=True)
        embed.add_field(name=f"⚡ Level {level} XP", value=f"{bar} {xp % xp_next}/{xp_next}", inline=False)
        embed.set_footer(text="Earn more with /daily and /quests")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="daily", description="Claim your daily BROski$ tokens 🌅")
    async def daily(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        sb = get_supabase()
        row = _get_or_create_member(sb, interaction.user)
        did = str(interaction.user.id)
        now = datetime.now(timezone.utc)

        last = row.get("last_active")
        if last:
            last_dt = datetime.fromisoformat(last)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            diff = now - last_dt
            if diff < timedelta(hours=DAILY_COOLDOWN_HOURS):
                remaining = timedelta(hours=DAILY_COOLDOWN_HOURS) - diff
                hrs, rem = divmod(int(remaining.total_seconds()), 3600)
                mins = rem // 60
                embed = discord.Embed(
                    title="⏳ Already claimed!",
                    description=f"Next daily in **{hrs}h {mins}m** — you've got this bro! 🔥",
                    colour=discord.Colour.orange(),
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

        streak = row.get("streak_days", 0)
        if last:
            last_dt = datetime.fromisoformat(last)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            if (now - last_dt) < timedelta(hours=36):
                streak += 1
            else:
                streak = 1
        else:
            streak = 1

        bonus = min(streak * 5, 100)
        total = DAILY_AMOUNT + bonus

        sb.table("broski_members").update({
            "broski_tokens": row.get("broski_tokens", 0) + total,
            "streak_days": streak,
            "last_active": now.isoformat(),
            "updated_at": now.isoformat(),
        }).eq("discord_id", did).execute()

        sb.table("broski_transactions").insert({
            "discord_id": did,
            "amount": total,
            "reason": f"daily_claim_streak_{streak}",
        }).execute()

        streak_emoji = "🔥" if streak >= 7 else "✨" if streak >= 3 else "⚡"
        embed = discord.Embed(
            title=f"{streak_emoji} Daily Claimed!",
            description=f"You earned **+{total} BROski$** {'(+'+str(bonus)+' streak bonus!)' if bonus else ''}",
            colour=discord.Colour.green(),
        )
        embed.add_field(name="🔥 Streak", value=f"{streak} days", inline=True)
        embed.add_field(name="💰 New Total", value=f"{row.get('broski_tokens', 0) + total:,}", inline=True)
        if streak == 1 and last:
            embed.set_footer(text="Welcome back! Streak restarted — comeback counts too 💪")
        else:
            embed.set_footer(text="Back tomorrow for more! Try /quests for bonus XP.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="give", description="Send BROski$ tokens to another member 🎁")
    @app_commands.describe(member="Who to send to", amount="How many BROski$ to send")
    async def give(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        await interaction.response.defer(ephemeral=True)
        if amount <= 0:
            await interaction.followup.send("❌ Amount must be positive bro!", ephemeral=True)
            return
        if member.id == interaction.user.id:
            await interaction.followup.send("❌ Can't send to yourself!", ephemeral=True)
            return

        sb = get_supabase()
        giver = _get_or_create_member(sb, interaction.user)
        if giver.get("broski_tokens", 0) < amount:
            await interaction.followup.send(f"❌ Not enough BROski$! You have **{giver.get('broski_tokens', 0):,}**", ephemeral=True)
            return

        sb.table("broski_members").update({
            "broski_tokens": giver["broski_tokens"] - amount,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("discord_id", str(interaction.user.id)).execute()

        recv = _get_or_create_member(sb, member)
        sb.table("broski_members").update({
            "broski_tokens": recv.get("broski_tokens", 0) + amount,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("discord_id", str(member.id)).execute()

        now = datetime.now(timezone.utc).isoformat()
        sb.table("broski_transactions").insert([
            {"discord_id": str(interaction.user.id), "amount": -amount, "reason": f"give_to_{member.id}"},
            {"discord_id": str(member.id), "amount": amount, "reason": f"gift_from_{interaction.user.id}"},
        ]).execute()

        embed = discord.Embed(
            title="🎁 BROski$ Sent!",
            description=f"You sent **{amount:,} BROski$** to {member.mention} — legend move! 🔥",
            colour=discord.Colour.purple(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)

    @app_commands.command(name="rich", description="See the top BROski$ holders 🏦")
    async def rich(self, interaction: discord.Interaction):
        await interaction.response.defer()
        sb = get_supabase()
        res = sb.table("broski_members").select("username,broski_tokens").order("broski_tokens", desc=True).limit(10).execute()
        rows = res.data or []

        medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 7
        lines = [f"{medals[i]} **{r['username']}** — {r['broski_tokens']:,} BROski$" for i, r in enumerate(rows)]

        embed = discord.Embed(
            title="🏦 BROski$ Rich List",
            description="\n".join(lines) or "No members yet — be first!",
            colour=discord.Colour.gold(),
        )
        embed.set_footer(text="Earn with /daily, /quests, and community events!")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
