"""
BROski Bot — Pets Cog (BROskiPets dNFT)

/pet hatch       — mint your BROskiPet (Phase 1: 300 BROski$)
/pet status      — vitals, XP, next evolution
/pet brain-feed  — the Brain's most-connected note feeds your pet

Bot is a render adapter — pet state lives in broski-pets-bridge (:8098,
Redis DB 3). Brain-feed XP comes from live graph centrality (Phase 6 arc).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import discord
import httpx
from discord import app_commands
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)

_BRIDGE_URL = os.getenv("PETS_BRIDGE_URL", "http://broski-pets-bridge:8098").rstrip("/")
_AUTOFEED_HOUR = int(os.getenv("PETS_AUTOFEED_HOUR_UTC", "7"))


def _autofeed_enabled() -> bool:
    return os.getenv("PETS_AUTOFEED_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def _owner_id() -> int:
    raw = os.getenv("DIGEST_DM_USER_ID") or os.getenv("DISCORD_USER_ID") or "0"
    try:
        return int(raw)
    except ValueError:
        return 0

_RARITY_COLORS = {
    "Common": 0x888888,
    "Uncommon": 0x10B981,
    "Rare": 0x22D3EE,
    "Legendary": 0xF59E0B,
}


def _bridge_key() -> str:
    # shared ${API_KEY} via compose — the bridge compares against the same
    # expansion (per-agent _FILE keys were removed as dead config 2026-06-12)
    return os.getenv("PETS_BRIDGE_API_KEY", "").strip()


async def _bridge(method: str, path: str, json_body: dict | None = None) -> tuple[int, dict]:
    """Call broski-pets-bridge. Returns (status_code, payload)."""
    headers = {}
    key = _bridge_key()
    if key:
        headers["X-API-Key"] = key
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            resp = await client.request(method, f"{_BRIDGE_URL}{path}", json=json_body)
            try:
                payload = resp.json()
            except Exception:
                payload = {}
            return resp.status_code, payload
    except Exception as exc:
        logger.warning("Pets bridge unreachable: %s", exc)
        return 0, {}


def _offline_embed() -> discord.Embed:
    return discord.Embed(
        title="🐾 BROskiPets",
        description=(
            "Pets bridge offline.\n"
            "Check: `docker compose --profile pets up -d broski-pets-bridge`"
        ),
        color=0xE67E22,
    )


def _bar(value: int) -> str:
    filled = max(0, min(10, round(value / 10)))
    return "█" * filled + "░" * (10 - filled)


def _status_embed(pet: dict) -> discord.Embed:
    rarity = str(pet.get("rarity", "Common"))
    embed = discord.Embed(
        title=f"🐾 {pet.get('name', 'BROskiPet')}",
        description=f"**{pet.get('species', '?')}** · {rarity} · Stage {pet.get('level', 1)}",
        color=_RARITY_COLORS.get(rarity, 0x888888),
    )
    xp = int(pet.get("xp", 0))
    nxt = pet.get("next_evolution_xp")
    xp_line = f"**{xp}** XP"
    if isinstance(nxt, int):
        xp_line += f" · {nxt} to next stage"
    embed.add_field(name="⚡ XP", value=xp_line, inline=False)
    embed.add_field(
        name="Vitals",
        value=(
            f"🍖 Hunger    `{_bar(int(pet.get('hunger', 0)))}` {pet.get('hunger', 0)}/100\n"
            f"🔋 Energy    `{_bar(int(pet.get('energy', 0)))}` {pet.get('energy', 0)}/100\n"
            f"💜 Happiness `{_bar(int(pet.get('happiness', 0)))}` {pet.get('happiness', 0)}/100"
        ),
        inline=False,
    )
    fed_at = pet.get("last_brain_feed_at")
    if fed_at:
        embed.add_field(name="🧠 Last brain feed", value=str(fed_at)[:16], inline=False)
    embed.set_footer(text="BROskiPets · your Brain feeds your pet")
    return embed


def _feed_embed(payload: dict, *, title: str = "🧠➜🐾 Brain feed!") -> discord.Embed:
    fed_by = payload.get("fed_by") or {}
    graph = payload.get("graph") or {}
    result = payload.get("result") or {}
    embed = discord.Embed(
        title=title,
        description=payload.get("message", "Your Brain fed your pet!"),
        color=0xF59E0B,
    )
    embed.add_field(
        name="📎 Fed by",
        value=f"`{fed_by.get('note', '?')}` · {fed_by.get('links', '?')} links",
        inline=False,
    )
    embed.add_field(
        name="⚡ XP",
        value=f"+{payload.get('xp_awarded', 0)} → {result.get('new_xp', '?')} total",
        inline=True,
    )
    embed.add_field(
        name="🕸️ Graph",
        value=f"{graph.get('nodes', '?')} nodes · {graph.get('edges', '?')} edges",
        inline=True,
    )
    if result.get("evolved"):
        embed.add_field(
            name="🎉 EVOLVED!",
            value=result.get("evolution_message", "New stage unlocked!"),
            inline=False,
        )
    embed.set_footer(text="BROskiPets · write notes, link thoughts, evolve")
    return embed


class Pets(commands.Cog):
    """BROskiPets — dNFT pets fed by the BROski Brain graph."""

    pet = app_commands.Group(name="pet", description="🐾 Your BROskiPet")

    @pet.command(name="hatch", description="🥚 Hatch your BROskiPet (300 BROski$)")
    async def hatch(self, interaction: discord.Interaction):
        await interaction.response.defer()
        status, payload = await _bridge(
            "POST",
            "/provision",
            {"discord_id": str(interaction.user.id), "broski_to_spend": 300},
        )
        if status == 0:
            await interaction.followup.send(embed=_offline_embed())
            return
        if status == 409:
            await interaction.followup.send(
                "🐾 You already have a pet! Try `/pet status`.", ephemeral=True
            )
            return
        if status != 200:
            await interaction.followup.send(
                f"💀 Hatch failed: {payload.get('detail', status)}", ephemeral=True
            )
            return
        rarity = str(payload.get("rarity", "Common"))
        embed = discord.Embed(
            title=f"🥚➜🐾 {payload.get('name', 'Your pet')} has hatched!",
            description=f"**{payload.get('species', '?')}** · {rarity}",
            color=_RARITY_COLORS.get(rarity, 0x888888),
        )
        embed.set_footer(text="BROskiPets · feed it with your Brain: /pet brain-feed")
        await interaction.followup.send(embed=embed)

    @pet.command(name="status", description="📊 Your pet's vitals, XP and next evolution")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        status, payload = await _bridge(
            "GET", f"/pet/{interaction.user.id}/status"
        )
        if status == 0:
            await interaction.followup.send(embed=_offline_embed())
            return
        if status == 404:
            await interaction.followup.send(
                "🥚 No pet yet — hatch one with `/pet hatch`!", ephemeral=True
            )
            return
        if status != 200:
            await interaction.followup.send(
                f"💀 Status failed: {payload.get('detail', status)}", ephemeral=True
            )
            return
        await interaction.followup.send(embed=_status_embed(payload))

    @pet.command(
        name="brain-feed",
        description="🧠 Your Brain's most-connected note feeds your pet",
    )
    async def brain_feed(self, interaction: discord.Interaction):
        await interaction.response.defer()
        status, payload = await _bridge(
            "POST", f"/pet/{interaction.user.id}/brain-feed"
        )
        if status == 0:
            await interaction.followup.send(embed=_offline_embed())
            return
        if status == 404:
            await interaction.followup.send(
                "🥚 No pet yet — hatch one with `/pet hatch`!", ephemeral=True
            )
            return
        if status != 200:
            await interaction.followup.send(
                f"💀 Brain feed failed: {payload.get('detail', status)}", ephemeral=True
            )
            return

        if not payload.get("fed"):
            embed = discord.Embed(
                title="🧠 Brain not grown yet",
                description=payload.get(
                    "message", "Write a note, link a thought — then feed again."
                ),
                color=0x888888,
            )
            embed.set_footer(text="One feed per graph refresh · graph updates every 30 min")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        await interaction.followup.send(embed=_feed_embed(payload))

    # ── Daily auto brain-feed ────────────────────────────────────────────
    # Feeds every pet on the roster once a day at PETS_AUTOFEED_HOUR_UTC.
    # Bridge-side dedup (one feed per graph refresh) makes retries harmless.
    # DM goes to the owner only, and only when the pet was actually fed.

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_autofeed_date: str | None = None

    async def cog_load(self):
        if _autofeed_enabled():
            self.autofeed_loop.start()

    async def cog_unload(self):
        self.autofeed_loop.cancel()

    @tasks.loop(hours=1)
    async def autofeed_loop(self):
        now = datetime.now(timezone.utc)
        if now.hour != _AUTOFEED_HOUR:
            return
        today = now.strftime("%Y-%m-%d")
        if self._last_autofeed_date == today:
            return

        status, board = await _bridge("GET", "/leaderboard")
        if status != 200 or not isinstance(board, list):
            logger.warning("autofeed: pets bridge roster unavailable (%s)", status)
            return  # bridge down — hourly loop retries while still in the hour
        self._last_autofeed_date = today

        owner = _owner_id()
        for row in board:
            discord_id = str(row.get("discord_id", "")).strip()
            if not discord_id:
                continue
            st, payload = await _bridge("POST", f"/pet/{discord_id}/brain-feed")
            fed = bool(payload.get("fed")) if st == 200 else False
            # print, not logger.info — the bot has no logging config, INFO is dropped
            print(
                f"🧠 autofeed: pet={row.get('name', discord_id)} status={st} "
                f"fed={fed} duplicate={bool(payload.get('duplicate'))}"
            )
            if not (fed and owner and discord_id == str(owner)):
                continue
            user = self.bot.get_user(owner)
            if user is None:
                try:
                    user = await self.bot.fetch_user(owner)
                except discord.HTTPException:
                    continue
            try:
                await user.send(embed=_feed_embed(payload, title="🌅🧠 Daily brain feed"))
            except (discord.Forbidden, discord.HTTPException):
                pass

    @autofeed_loop.before_loop
    async def _before_autofeed(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Pets(bot))
