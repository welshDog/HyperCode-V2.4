"""
🤖 BROski-Bot — THE ONE TRUE BOT for HYPERFOCUS z0ne
Lives in: agents/broski-bot/
Profile:  discord (--profile discord to start)

Tier 1 Features:
  ✅ BROski$ Economy  — /balance /earn /spend /give
  ✅ AI Chat          — /broski /ask (via FastAPI hypercode-core)
  ✅ Focus Tracker    — /focus start|stop + /focusstats
  ✅ Daily Missions   — /missions + auto-post 8am UTC

Persistence:
  - Economy + XP stored in Supabase
  - Logs bound to HC_DATA_ROOT/broski-bot/logs
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

# ── Config ─────────────────────────────────────────────────────────────
DISCORD_TOKEN    = os.getenv("DISCORD_TOKEN")
SUPABASE_URL     = os.getenv("SUPABASE_URL")
SUPABASE_KEY     = os.getenv("SUPABASE_KEY")
FASTAPI_BASE     = os.getenv("FASTAPI_BASE", "http://hypercode-core:8000")
MISSIONS_CHANNEL = int(os.getenv("MISSIONS_CHANNEL_ID", "0"))
GUILD_ID         = int(os.getenv("GUILD_ID", "0"))
LOGS_PATH        = os.getenv("BOT_LOGS_PATH", "/opt/hypercode/data/broski-bot/logs")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Bot Setup ────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=os.getenv("DISCORD_COMMAND_PREFIX", "/"), intents=intents)
tree = bot.tree


# ── Helpers ────────────────────────────────────────────────────────────
def get_or_create_member(discord_id: str, username: str) -> dict:
    result = supabase.table("broski_members").select("*").eq("discord_id", discord_id).execute()
    if result.data:
        return result.data[0]
    new_member = {
        "discord_id": discord_id,
        "username": username,
        "broski_coins": 100,
        "xp": 0,
        "focus_start": None,
        "total_focus_minutes": 0,
        "created_at": datetime.utcnow().isoformat()
    }
    supabase.table("broski_members").insert(new_member).execute()
    return new_member


def award_coins(discord_id: str, amount: int, reason: str = "") -> int:
    member = supabase.table("broski_members").select("broski_coins").eq("discord_id", discord_id).execute()
    current = member.data[0]["broski_coins"] if member.data else 0
    new_balance = current + amount
    supabase.table("broski_members").update({"broski_coins": new_balance}).eq("discord_id", discord_id).execute()
    supabase.table("broski_transactions").insert({
        "discord_id": discord_id,
        "amount": amount,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat()
    }).execute()
    return new_balance


async def call_fastapi(endpoint: str, method: str = "GET", payload: dict = None) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        url = f"{FASTAPI_BASE}{endpoint}"
        resp = await client.post(url, json=payload) if method == "POST" else await client.get(url, params=payload)
        resp.raise_for_status()
        return resp.json()


# ── Events ─────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"🤖 broski-bot ONLINE as {bot.user}")
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    daily_missions_post.start()
    print("✅ Slash commands synced | Daily missions loop running")


@bot.event
async def on_member_join(member: discord.Member):
    get_or_create_member(str(member.id), member.name)
    embed = discord.Embed(
        title="🐶 Welcome to HYPERFOCUS z0ne, BROski!",
        description=(
            f"Hey {member.mention}! You've joined the most ADHD-friendly server ever. 🧠⚡\n\n"
            "🪙 **100 BROski$** in your wallet\n"
            "🎯 `/focus start` to begin a focus session\n"
            "📋 Check `/missions` for today's tasks\n\n"
            "Type `/broski` anytime to chat with me!"
        ),
        color=0x9B59B6
    )
    embed.set_footer(text="BROski♾️ — Built different, built for YOU")
    await member.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════════
# 💰 ECONOMY
# ══════════════════════════════════════════════════════════════════════════

@tree.command(name="balance", description="Check your BROski$ wallet 💰")
async def balance(interaction: discord.Interaction):
    member = get_or_create_member(str(interaction.user.id), interaction.user.name)
    embed = discord.Embed(title="💰 Your BROski$ Wallet", color=0xF1C40F)
    embed.add_field(name="BROski$",    value=f"🪙 **{member['broski_coins']}**",           inline=True)
    embed.add_field(name="XP",         value=f"⚡ **{member['xp']}**",                     inline=True)
    embed.add_field(name="Focus Time", value=f"🎯 **{member['total_focus_minutes']} mins**", inline=True)
    embed.set_footer(text=f"Keep grinding, {interaction.user.name}! 🐶")
    await interaction.response.send_message(embed=embed)


@tree.command(name="earn", description="Earn BROski$ by completing a task 🏆")
@app_commands.describe(task="What did you complete?")
async def earn(interaction: discord.Interaction, task: str):
    discord_id = str(interaction.user.id)
    get_or_create_member(discord_id, interaction.user.name)
    new_balance = award_coins(discord_id, 25, reason=f"Task: {task}")
    embed = discord.Embed(
        title="🏆 NICE ONE BROski♾️!",
        description=f"You earned **+25 BROski$** for:\n> *{task}*",
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
            f"❌ Only **{member['broski_coins']} BROski$** in your wallet!", ephemeral=True
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
    sender_id   = str(interaction.user.id)
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
# 🧠 AI CHAT
# ══════════════════════════════════════════════════════════════════════════

@tree.command(name="broski", description="Chat with BROski AI 🧠")
@app_commands.describe(message="What do you want to ask?")
async def broski_chat(interaction: discord.Interaction, message: str):
    await interaction.response.defer(thinking=True)
    discord_id = str(interaction.user.id)
    get_or_create_member(discord_id, interaction.user.name)
    try:
        result = await call_fastapi("/ai/chat", method="POST", payload={
            "user_id": discord_id, "message": message, "context": "discord"
        })
        reply = result.get("reply", "BROski brain glitched! Try again 🐶")
        award_coins(discord_id, 5, reason="AI chat interaction")
        embed = discord.Embed(title="🧠 BROski AI Says...", description=reply, color=0x3498DB)
        embed.set_footer(text="+5 BROski$ for chatting! 🐶")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"⚠️ FastAPI unreachable: `{e}`\nIs hypercode-core running?")


@tree.command(name="ask", description="Quick question to BROski ⚡")
@app_commands.describe(question="Your question")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer(thinking=True)
    discord_id = str(interaction.user.id)
    get_or_create_member(discord_id, interaction.user.name)
    try:
        result = await call_fastapi("/ai/quick", method="POST", payload={
            "user_id": discord_id, "question": question
        })
        answer = result.get("answer", "No answer returned 🤔")
        embed = discord.Embed(title=f"❓ {question[:80]}", description=answer, color=0x1ABC9C)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"⚠️ FastAPI error: `{e}`")


# ══════════════════════════════════════════════════════════════════════════
# 🎯 FOCUS TRACKER
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
                "⚡ Already in a focus session! Use `/focus stop` when done.", ephemeral=True
            )
            return
        supabase.table("broski_members").update(
            {"focus_start": datetime.utcnow().isoformat()}
        ).eq("discord_id", discord_id).execute()
        embed = discord.Embed(
            title="🎯 FOCUS MODE: ACTIVATED!",
            description=(
                "Lock in BROski! Timer started. 🧠\n\n"
                "- Phone face-down 📵\n- One tab only 💻\n- Water nearby 💧\n\n"
                "Type `/focus stop` when done!"
            ),
            color=0xE67E22
        )
        await interaction.response.send_message(embed=embed)

    elif action == "stop":
        if not member.get("focus_start"):
            await interaction.response.send_message(
                "❌ No active session! Start one with `/focus start`.", ephemeral=True
            )
            return
        elapsed  = datetime.utcnow() - datetime.fromisoformat(member["focus_start"])
        minutes  = max(1, int(elapsed.total_seconds() / 60))
        coins    = min(minutes * 2, 200)
        total    = member.get("total_focus_minutes", 0) + minutes
        new_bal  = award_coins(discord_id, coins, reason=f"Focus: {minutes} mins")
        supabase.table("broski_members").update({
            "focus_start": None,
            "total_focus_minutes": total,
            "xp": member.get("xp", 0) + minutes
        }).eq("discord_id", discord_id).execute()
        embed = discord.Embed(title="🏆 FOCUS COMPLETE — NICE ONE BROski♾️!", color=0x2ECC71)
        embed.add_field(name="⏱️ Duration",    value=f"**{minutes} mins**",  inline=True)
        embed.add_field(name="🪙 Coins",        value=f"**+{coins}**",        inline=True)
        embed.add_field(name="⚡ XP",            value=f"**+{minutes}**",      inline=True)
        embed.add_field(name="💰 Balance",      value=f"🪙 {new_bal}",       inline=True)
        embed.add_field(name="🎯 Lifetime",    value=f"{total} mins",      inline=True)
        embed.set_footer(text="Every minute builds something great. 🐶")
        await interaction.response.send_message(embed=embed)


@tree.command(name="focusstats", description="See your focus history 📊")
async def focus_stats(interaction: discord.Interaction):
    member = get_or_create_member(str(interaction.user.id), interaction.user.name)
    total  = member.get("total_focus_minutes", 0)
    level  = (member.get("xp", 0) // 100) + 1
    embed  = discord.Embed(title="📊 Your Focus Stats", color=0x9B59B6)
    embed.add_field(name="Total Focus", value=f"⏱️ **{total//60}h {total%60}m**",    inline=True)
    embed.add_field(name="Total XP",    value=f"⚡ **{member.get('xp', 0)}**",           inline=True)
    embed.add_field(name="BROski$",     value=f"🪙 **{member.get('broski_coins', 0)}**", inline=True)
    embed.add_field(name="Level",       value=f"🏆 **Level {level}**",                  inline=True)
    await interaction.response.send_message(embed=embed)


# ══════════════════════════════════════════════════════════════════════════
# 📋 DAILY MISSIONS
# ══════════════════════════════════════════════════════════════════════════

DAILY_MISSIONS = [
    {"title": "🎯 Focus Block",     "desc": "Complete a 25-min focus session",        "reward": 50,  "cmd": "/focus start"},
    {"title": "🧠 Ask BROski",      "desc": "Use /broski to get help with something",  "reward": 15,  "cmd": "/broski"},
    {"title": "💪 Task Crusher",    "desc": "Complete 3 tasks using /earn",            "reward": 75,  "cmd": "/earn"},
    {"title": "🎁 Spread the Love", "desc": "Gift coins to a fellow BROski",           "reward": 20,  "cmd": "/give"},
    {"title": "💬 Community Drop",  "desc": "Post something helpful in #general",      "reward": 30,  "cmd": "Chat!"},
    {"title": "🔥 Hyperfocus Boss", "desc": "Complete a 60-min focus session",         "reward": 120, "cmd": "/focus start"},
    {"title": "📚 Level Up",        "desc": "Check your stats + set a goal for today", "reward": 10,  "cmd": "/focusstats"},
]


@tasks.loop(time=time(hour=8, minute=0))  # 8am UTC = 9am BST
async def daily_missions_post():
    channel = bot.get_channel(MISSIONS_CHANNEL)
    if not channel:
        return
    today = datetime.utcnow().strftime("%A %d %B")
    idx   = datetime.utcnow().weekday()
    picks = [DAILY_MISSIONS[idx % 7], DAILY_MISSIONS[(idx+2) % 7], DAILY_MISSIONS[(idx+4) % 7]]
    embed = discord.Embed(
        title=f"🌅 Daily Missions — {today}",
        description="Complete these to earn BROski$ and XP! 🏆",
        color=0xF39C12
    )
    for m in picks:
        embed.add_field(
            name=f"{m['title']} — 🪙 {m['reward']}",
            value=f"{m['desc']}\n`{m['cmd']}`",
            inline=False
        )
    embed.add_field(
        name="💰 Max Today",
        value=f"🪙 **{sum(m['reward'] for m in picks)} BROski$** if you crush all 3!",
        inline=False
    )
    embed.set_footer(text="BROski♾️ — Built for the neurodivergent legends 🧠🏴󠁧󠁢󠁷󠁬󠁳󠁿")
    await channel.send(embed=embed)


@tree.command(name="missions", description="See today's missions 📋")
async def missions(interaction: discord.Interaction):
    today = datetime.utcnow().strftime("%A %d %B")
    idx   = datetime.utcnow().weekday()
    picks = [DAILY_MISSIONS[idx % 7], DAILY_MISSIONS[(idx+2) % 7], DAILY_MISSIONS[(idx+4) % 7]]
    embed = discord.Embed(
        title=f"📋 Today's Missions — {today}",
        description="Your BROski$ awaits! Crush these:",
        color=0xF39C12
    )
    for m in picks:
        embed.add_field(
            name=f"{m['title']} — 🪙 {m['reward']}",
            value=f"{m['desc']}\n`{m['cmd']}`",
            inline=False
        )
    await interaction.response.send_message(embed=embed)


# ── Run
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
