"""
🤖 BROski Discord Bot — HYPERFOCUS z0ne
Tier 1 MAX Features:
  ✅ BROski$ Economy (/earn /spend /balance)
  ✅ AI Chat (/ask /broski)
  ✅ Focus Tracker (/focus start/stop)
  ✅ Daily Missions (auto-post to #missions)

Connects to: HyperCode V2.4 FastAPI (internal Docker network)
DB: Supabase
"""

import os
import asyncio
import httpx
from datetime import datetime, time
import discord
from discord.ext import commands, tasks
from discord import app_commands
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# ── Config ──────────────────────────────────────────────────────────────
DISCORD_TOKEN      = os.getenv("DISCORD_TOKEN")
SUPABASE_URL       = os.getenv("SUPABASE_URL")
SUPABASE_KEY       = os.getenv("SUPABASE_KEY")
FASTAPI_BASE       = os.getenv("FASTAPI_BASE", "http://fastapi:8000")
MISSIONS_CHANNEL   = int(os.getenv("MISSIONS_CHANNEL_ID", "0"))
GUILD_ID           = int(os.getenv("GUILD_ID", "0"))

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Bot Setup ────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ── Helpers ──────────────────────────────────────────────────────────────
def get_or_create_member(discord_id: str, username: str) -> dict:
    """Get member from Supabase or create with defaults."""
    result = supabase.table("broski_members").select("*").eq("discord_id", discord_id).execute()
    if result.data:
        return result.data[0]
    new_member = {
        "discord_id": discord_id,
        "username": username,
        "broski_coins": 100,  # starter bonus 🎁
        "xp": 0,
        "focus_start": None,
        "total_focus_minutes": 0,
        "created_at": datetime.utcnow().isoformat()
    }
    supabase.table("broski_members").insert(new_member).execute()
    return new_member


def award_coins(discord_id: str, amount: int, reason: str = "") -> int:
    """Award BROski$ coins. Returns new balance."""
    member = supabase.table("broski_members").select("broski_coins").eq("discord_id", discord_id).execute()
    current = member.data[0]["broski_coins"] if member.data else 0
    new_balance = current + amount
    supabase.table("broski_members").update({"broski_coins": new_balance}).eq("discord_id", discord_id).execute()
    # log the transaction
    supabase.table("broski_transactions").insert({
        "discord_id": discord_id,
        "amount": amount,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat()
    }).execute()
    return new_balance


async def call_fastapi(endpoint: str, method: str = "GET", payload: dict = None) -> dict:
    """Hit the V2.4 FastAPI backend."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        url = f"{FASTAPI_BASE}{endpoint}"
        if method == "POST":
            resp = await client.post(url, json=payload)
        else:
            resp = await client.get(url, params=payload)
        resp.raise_for_status()
        return resp.json()


# ── Events ───────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"🤖 BROski Bot online as {bot.user}")
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    daily_missions_post.start()
    print("✅ Slash commands synced | Daily missions loop started")


@bot.event
async def on_member_join(member: discord.Member):
    """Auto-create DB record + send welcome."""
    get_or_create_member(str(member.id), member.name)
    embed = discord.Embed(
        title="🐶 Welcome to HYPERFOCUS z0ne, BROski!",
        description=(
            f"Hey {member.mention}! You've joined the most ADHD-friendly server ever built. 🧠⚡\n\n"
            "**Your starter pack:**\n"
            "🪙 **100 BROski$** added to your wallet\n"
            "🎯 Check `#missions` for today's tasks\n"
            "⚡ Use `/focus start` to begin a focus session\n\n"
            "Type `/broski` anytime to chat with me!"
        ),
        color=0x9B59B6
    )
    embed.set_footer(text="BROski♾️ — Built different, built for YOU")
    await member.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════════
# 💰 TIER 1 FEATURE 1: BROski$ Economy
# ══════════════════════════════════════════════════════════════════════════

@tree.command(name="balance", description="Check your BROski$ wallet 💰")
async def balance(interaction: discord.Interaction):
    member = get_or_create_member(str(interaction.user.id), interaction.user.name)
    embed = discord.Embed(
        title="💰 Your BROski$ Wallet",
        color=0xF1C40F
    )
    embed.add_field(name="BROski$", value=f"🪙 **{member['broski_coins']}**", inline=True)
    embed.add_field(name="XP", value=f"⚡ **{member['xp']}**", inline=True)
    embed.add_field(name="Focus Time", value=f"🎯 **{member['total_focus_minutes']} mins**", inline=True)
    embed.set_footer(text=f"Keep grinding, {interaction.user.name}! 🐶")
    await interaction.response.send_message(embed=embed)


@tree.command(name="earn", description="Earn BROski$ by completing a task 🏆")
@app_commands.describe(task="What did you complete?")
async def earn(interaction: discord.Interaction, task: str):
    discord_id = str(interaction.user.id)
    get_or_create_member(discord_id, interaction.user.name)
    coins_earned = 25  # base earn rate
    new_balance = award_coins(discord_id, coins_earned, reason=f"Task: {task}")
    embed = discord.Embed(
        title="🏆 NICE ONE BROski♾️!",
        description=f"You earned **+{coins_earned} BROski$** for:\n> *{task}*",
        color=0x2ECC71
    )
    embed.add_field(name="New Balance", value=f"🪙 {new_balance}")
    await interaction.response.send_message(embed=embed)


@tree.command(name="spend", description="Spend your BROski$ 🛒")
@app_commands.describe(amount="How many coins?", item="What are you buying?")
async def spend(interaction: discord.Interaction, amount: int, item: str):
    discord_id = str(interaction.user.id)
    member = get_or_create_member(discord_id, interaction.user.name)
    if member["broski_coins"] < amount:
        await interaction.response.send_message(
            f"❌ Not enough BROski$! You have **{member['broski_coins']}** but need **{amount}**.",
            ephemeral=True
        )
        return
    new_balance = award_coins(discord_id, -amount, reason=f"Spent on: {item}")
    embed = discord.Embed(
        title="🛒 Purchase Complete!",
        description=f"You spent **{amount} BROski$** on:\n> *{item}*",
        color=0xE74C3C
    )
    embed.add_field(name="Remaining Balance", value=f"🪙 {new_balance}")
    await interaction.response.send_message(embed=embed)


@tree.command(name="give", description="Gift BROski$ to a friend 🎁")
@app_commands.describe(member="Who to gift?", amount="How many coins?")
async def give(interaction: discord.Interaction, member: discord.Member, amount: int):
    sender_id = str(interaction.user.id)
    receiver_id = str(member.id)
    sender = get_or_create_member(sender_id, interaction.user.name)
    get_or_create_member(receiver_id, member.name)
    if sender["broski_coins"] < amount:
        await interaction.response.send_message(
            f"❌ You only have **{sender['broski_coins']} BROski$**!", ephemeral=True
        )
        return
    award_coins(sender_id, -amount, reason=f"Gift to {member.name}")
    new_balance = award_coins(receiver_id, amount, reason=f"Gift from {interaction.user.name}")
    embed = discord.Embed(
        title="🎁 Gift Sent!",
        description=f"{interaction.user.mention} gifted **{amount} BROski$** to {member.mention}!",
        color=0x9B59B6
    )
    embed.add_field(name=f"{member.name}'s New Balance", value=f"🪙 {new_balance}")
    await interaction.response.send_message(embed=embed)


# ══════════════════════════════════════════════════════════════════════════
# 🧠 TIER 1 FEATURE 2: AI Chat via FastAPI
# ══════════════════════════════════════════════════════════════════════════

@tree.command(name="broski", description="Chat with BROski AI 🧠")
@app_commands.describe(message="What do you want to ask?")
async def broski_chat(interaction: discord.Interaction, message: str):
    await interaction.response.defer(thinking=True)
    discord_id = str(interaction.user.id)
    get_or_create_member(discord_id, interaction.user.name)
    try:
        result = await call_fastapi("/ai/chat", method="POST", payload={
            "user_id": discord_id,
            "message": message,
            "context": "discord"
        })
        reply = result.get("reply", "Hmm, BROski brain glitched! Try again 🐶")
        # Award small coins for engaging
        award_coins(discord_id, 5, reason="AI chat interaction")
        embed = discord.Embed(
            title="🧠 BROski AI Says...",
            description=reply,
            color=0x3498DB
        )
        embed.set_footer(text="+5 BROski$ for chatting! Keep it up 🐶")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"⚠️ FastAPI unreachable: `{e}`\nIs V2.4 running? Check Docker! 🐳")


@tree.command(name="ask", description="Quick question to BROski ⚡")
@app_commands.describe(question="Your question")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer(thinking=True)
    discord_id = str(interaction.user.id)
    get_or_create_member(discord_id, interaction.user.name)
    try:
        result = await call_fastapi("/ai/quick", method="POST", payload={
            "user_id": discord_id,
            "question": question
        })
        answer = result.get("answer", "No answer returned 🤔")
        embed = discord.Embed(
            title=f"❓ {question[:80]}",
            description=answer,
            color=0x1ABC9C
        )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"⚠️ FastAPI error: `{e}`")


# ══════════════════════════════════════════════════════════════════════════
# 🎯 TIER 1 FEATURE 3: Focus Tracker
# ══════════════════════════════════════════════════════════════════════════

@tree.command(name="focus", description="Start or stop a focus session 🎯")
@app_commands.describe(action="start or stop")
@app_commands.choices(action=[
    app_commands.Choice(name="start", value="start"),
    app_commands.Choice(name="stop",  value="stop"),
])
async def focus(interaction: discord.Interaction, action: str):
    discord_id = str(interaction.user.id)
    member = get_or_create_member(discord_id, interaction.user.name)

    if action == "start":
        if member.get("focus_start"):
            await interaction.response.send_message(
                "⚡ You're already in a focus session! Use `/focus stop` when done.",
                ephemeral=True
            )
            return
        now = datetime.utcnow().isoformat()
        supabase.table("broski_members").update({"focus_start": now}).eq("discord_id", discord_id).execute()
        embed = discord.Embed(
            title="🎯 FOCUS MODE: ACTIVATED!",
            description=(
                "Lock in BROski! Your timer has started. 🧠\n\n"
                "**Tips:**\n"
                "- Put phone face-down 📵\n"
                "- One tab only 💻\n"
                "- Water bottle nearby 💧\n\n"
                "Type `/focus stop` when done to claim your XP + BROski$!"
            ),
            color=0xE67E22
        )
        await interaction.response.send_message(embed=embed)

    elif action == "stop":
        if not member.get("focus_start"):
            await interaction.response.send_message(
                "❌ No active focus session! Start one with `/focus start`.",
                ephemeral=True
            )
            return
        start_time = datetime.fromisoformat(member["focus_start"])
        elapsed = datetime.utcnow() - start_time
        minutes = max(1, int(elapsed.total_seconds() / 60))
        coins = min(minutes * 2, 200)  # 2 coins/min, capped at 200
        xp_gain = minutes

        total_focus = member.get("total_focus_minutes", 0) + minutes
        new_coins = award_coins(discord_id, coins, reason=f"Focus session: {minutes} mins")
        supabase.table("broski_members").update({
            "focus_start": None,
            "total_focus_minutes": total_focus,
            "xp": member.get("xp", 0) + xp_gain
        }).eq("discord_id", discord_id).execute()

        embed = discord.Embed(
            title="🏆 FOCUS SESSION COMPLETE — NICE ONE BROski♾️!",
            color=0x2ECC71
        )
        embed.add_field(name="⏱️ Duration",    value=f"**{minutes} minutes**", inline=True)
        embed.add_field(name="🪙 Coins Earned", value=f"**+{coins} BROski$**",  inline=True)
        embed.add_field(name="⚡ XP Gained",   value=f"**+{xp_gain} XP**",     inline=True)
        embed.add_field(name="💰 New Balance",  value=f"🪙 {new_coins}",         inline=True)
        embed.add_field(name="🎯 Total Focus",  value=f"{total_focus} mins lifetime", inline=True)
        embed.set_footer(text="Every minute counts. You're building something great. 🐶")
        await interaction.response.send_message(embed=embed)


@tree.command(name="focusstats", description="See your focus history 📊")
async def focus_stats(interaction: discord.Interaction):
    discord_id = str(interaction.user.id)
    member = get_or_create_member(discord_id, interaction.user.name)
    total = member.get("total_focus_minutes", 0)
    hours = total // 60
    mins  = total % 60
    embed = discord.Embed(
        title="📊 Your Focus Stats",
        color=0x9B59B6
    )
    embed.add_field(name="Total Focus Time", value=f"⏱️ **{hours}h {mins}m**", inline=True)
    embed.add_field(name="Total XP",         value=f"⚡ **{member.get('xp', 0)}**", inline=True)
    embed.add_field(name="BROski$",           value=f"🪙 **{member.get('broski_coins', 0)}**", inline=True)
    level = (member.get("xp", 0) // 100) + 1
    embed.add_field(name="Level", value=f"🏆 **Level {level}**", inline=True)
    await interaction.response.send_message(embed=embed)


# ══════════════════════════════════════════════════════════════════════════
# 📋 TIER 1 FEATURE 4: Daily Missions
# ══════════════════════════════════════════════════════════════════════════

DAILY_MISSIONS = [
    {"title": "🎯 Focus Block",      "desc": "Complete a 25-min focus session",       "reward": 50,  "command": "/focus start"},
    {"title": "🧠 Ask BROski",       "desc": "Use /broski to get help with something",  "reward": 15,  "command": "/broski"},
    {"title": "💪 Task Crusher",     "desc": "Complete 3 tasks using /earn",            "reward": 75,  "command": "/earn"},
    {"title": "🎁 Spread the Love",  "desc": "Gift coins to a fellow BROski",           "reward": 20,  "command": "/give"},
    {"title": "💬 Community Drop",   "desc": "Post something helpful in #general",      "reward": 30,  "command": "Chat!"},
    {"title": "🔥 Hyperfocus Boss",  "desc": "Complete a 60-min focus session",         "reward": 120, "command": "/focus start"},
    {"title": "📚 Level Up",         "desc": "Check your stats and set a goal for today","reward": 10,  "command": "/focusstats"},
]


@tasks.loop(time=time(hour=8, minute=0))  # 8am UTC = 9am BST 🏴󠁧󠁢󠁷󠁬󠁳󠁿
async def daily_missions_post():
    """Auto-post daily missions to the missions channel."""
    channel = bot.get_channel(MISSIONS_CHANNEL)
    if not channel:
        print(f"⚠️ Missions channel {MISSIONS_CHANNEL} not found!")
        return

    today = datetime.utcnow().strftime("%A %d %B")
    day_index = datetime.utcnow().weekday()  # 0=Mon, 6=Sun
    # Pick 3 missions per day based on day index
    selected = [DAILY_MISSIONS[day_index % len(DAILY_MISSIONS)],
                DAILY_MISSIONS[(day_index + 2) % len(DAILY_MISSIONS)],
                DAILY_MISSIONS[(day_index + 4) % len(DAILY_MISSIONS)]]

    embed = discord.Embed(
        title=f"🌅 Daily Missions — {today}",
        description="Complete these missions to earn BROski$ and XP! 🏆",
        color=0xF39C12
    )
    total_possible = sum(m["reward"] for m in selected)
    for m in selected:
        embed.add_field(
            name=f"{m['title']} — 🪙 {m['reward']} BROski$",
            value=f"{m['desc']}\n`{m['command']}`",
            inline=False
        )
    embed.add_field(
        name="💰 Max Earnings Today",
        value=f"🪙 **{total_possible} BROski$** if you crush all 3!",
        inline=False
    )
    embed.set_footer(text="BROski♾️ — Built for the neurodivergent legends 🧠🏴󠁧󠁢󠁷󠁬󠁳󠁿")
    await channel.send(embed=embed)


@tree.command(name="missions", description="See today's missions 📋")
async def missions(interaction: discord.Interaction):
    """Manual trigger to see missions anytime."""
    today = datetime.utcnow().strftime("%A %d %B")
    day_index = datetime.utcnow().weekday()
    selected = [DAILY_MISSIONS[day_index % len(DAILY_MISSIONS)],
                DAILY_MISSIONS[(day_index + 2) % len(DAILY_MISSIONS)],
                DAILY_MISSIONS[(day_index + 4) % len(DAILY_MISSIONS)]]
    embed = discord.Embed(
        title=f"📋 Today's Missions — {today}",
        description="Your BROski$ awaits! Complete these to level up:",
        color=0xF39C12
    )
    for m in selected:
        embed.add_field(
            name=f"{m['title']} — 🪙 {m['reward']}",
            value=f"{m['desc']}\n`{m['command']}`",
            inline=False
        )
    await interaction.response.send_message(embed=embed)


# ── Run ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
