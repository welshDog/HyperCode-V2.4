"""
BROski Bot — Raid Guard (Server Guardian Phase 3b)

Detects join-floods and auto-locks channels (reversible). Bot detects,
Core decides + audits to mod_actions, bot performs the Discord ops.

Restart-safe: the authoritative unlock trigger is Core's `due` flag read
by a 60s reconciler — no in-memory timers. State lives in Postgres.

Fully reversible (matches the agreed risk model — full auto is OK here).
"""
from __future__ import annotations

import os
import time
import uuid
from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core_client import CoreClient, CoreError, render_to_embed


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


RAID_JOIN_THRESHOLD = _int_env("RAID_JOIN_THRESHOLD", 5)
RAID_WINDOW_SECONDS = _int_env("RAID_WINDOW_SECONDS", 10)
MOD_LOG_CHANNEL_ID = _int_env("MOD_LOG_CHANNEL_ID", 0)


class RaidGuard(commands.Cog):
    """Join-flood → reversible channel lockdown. Core owns the decision + audit."""

    def __init__(self, bot: commands.Bot, core: CoreClient):
        self.bot = bot
        self.core = core
        self._joins: dict[int, deque] = defaultdict(
            lambda: deque(maxlen=RAID_JOIN_THRESHOLD * 3 + 2)
        )
        # guild_id -> {"mod_action_id": int, "channel_ids": [int, ...]}
        self._locked: dict[int, dict] = {}

    async def cog_load(self):
        self.reconcile_loop.start()

    async def cog_unload(self):
        self.reconcile_loop.cancel()

    def _ctx(self, tag: str) -> dict:
        return {
            "user_id": "system",
            "username": "raid-guard",
            "guild_id": None,
            "channel_id": None,
            "interaction_id": f"raid-{tag}-{uuid.uuid4().hex[:10]}",
        }

    # ── Detection ────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        if guild is None or guild.id in self._locked:
            return
        now = time.monotonic()
        bucket = self._joins[guild.id]
        bucket.append(now)
        recent = [t for t in bucket if now - t <= RAID_WINDOW_SECONDS]
        if len(recent) >= RAID_JOIN_THRESHOLD:
            await self._engage(guild, len(recent), RAID_WINDOW_SECONDS)

    # ── Lock ─────────────────────────────────────────────────────────────────
    async def _engage(self, guild: discord.Guild, join_count: int, window_s: int):
        try:
            resp = await self.core.action(
                "mod.raid_lockdown",
                self._ctx("open"),
                {
                    "phase": "open",
                    "join_count": join_count,
                    "window_s": window_s,
                    "guild_id": str(guild.id),
                },
            )
        except CoreError:
            return  # Core down — fail safe, do not lock blind

        data = resp.get("data") or {}
        if not data.get("locked"):
            return
        mod_action_id = data.get("mod_action_id")

        locked_ids: list[int] = []
        everyone = guild.default_role
        for ch in guild.text_channels:
            ow = ch.overwrites_for(everyone)
            if ow.send_messages in (None, True):
                ow.send_messages = False
                try:
                    await ch.set_permissions(
                        everyone, overwrite=ow, reason="BROski raid lockdown"
                    )
                    locked_ids.append(ch.id)
                except (discord.Forbidden, discord.HTTPException):
                    continue

        self._locked[guild.id] = {
            "mod_action_id": mod_action_id,
            "channel_ids": locked_ids,
        }

        try:
            await self.core.action(
                "mod.raid_lockdown",
                self._ctx("locked"),
                {
                    "phase": "locked",
                    "mod_action_id": mod_action_id,
                    "locked_channel_ids": [str(i) for i in locked_ids],
                },
            )
        except CoreError:
            pass  # audit attach best-effort; reconciler still works off the row

        await self._alert(guild, resp.get("render"))

    # ── Unlock ───────────────────────────────────────────────────────────────
    async def _lift(self, guild: discord.Guild, mod_action_id, channel_ids: list[int]):
        everyone = guild.default_role
        for cid in channel_ids:
            ch = guild.get_channel(int(cid))
            if ch is None:
                continue
            ow = ch.overwrites_for(everyone)
            ow.send_messages = None  # restore inherit
            try:
                await ch.set_permissions(
                    everyone, overwrite=ow, reason="BROski raid lockdown lifted"
                )
            except (discord.Forbidden, discord.HTTPException):
                continue

        try:
            await self.core.action(
                "mod.raid_lockdown",
                self._ctx("resolve"),
                {"phase": "resolve", "mod_action_id": mod_action_id},
            )
        except CoreError:
            pass

        self._locked.pop(guild.id, None)
        self._joins.pop(guild.id, None)

    async def _alert(self, guild: discord.Guild, render):
        if not MOD_LOG_CHANNEL_ID or not render:
            return
        channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
        if channel is not None:
            try:
                await channel.send(embed=render_to_embed(render))
            except discord.HTTPException:
                pass

    # ── Reconciler (restart-safe, authoritative unlock) ──────────────────────
    @tasks.loop(seconds=60)
    async def reconcile_loop(self):
        try:
            resp = await self.core.action("mod.raid_sweep", self._ctx("sweep"))
        except CoreError:
            return
        for item in (resp.get("data") or {}).get("active", []):
            gid = item.get("guild_id")
            if not gid:
                continue
            guild = self.bot.get_guild(int(gid))
            if guild is None:
                continue
            mod_action_id = item.get("mod_action_id")
            channel_ids = [int(c) for c in (item.get("locked_channel_ids") or [])]

            if item.get("due"):
                await self._lift(guild, mod_action_id, channel_ids)
            else:
                # Re-arm in-memory guard after a restart so we don't double-lock.
                self._locked.setdefault(
                    guild.id,
                    {"mod_action_id": mod_action_id, "channel_ids": channel_ids},
                )

    @reconcile_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    # ── Admin commands ───────────────────────────────────────────────────────
    @app_commands.command(name="raid-unlock", description="🔓 Lift an active raid lockdown now (admin)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def raid_unlock(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        info = self._locked.get(guild.id) if guild else None
        if not guild or not info:
            await interaction.followup.send("No active lockdown here.", ephemeral=True)
            return
        await self._lift(guild, info["mod_action_id"], info["channel_ids"])
        await interaction.followup.send("🔓 Lockdown lifted.", ephemeral=True)

    @app_commands.command(name="raid-status", description="🛡️ Show raid lockdown status (admin)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def raid_status(self, interaction: discord.Interaction):
        guild = interaction.guild
        info = self._locked.get(guild.id) if guild else None
        if info:
            msg = f"🚨 LOCKED — {len(info['channel_ids'])} channels (action #{info['mod_action_id']})"
        else:
            msg = "🟢 No active lockdown."
        await interaction.response.send_message(msg, ephemeral=True)

    @raid_unlock.error
    @raid_status.error
    async def _on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "🔒 Manage Server permission required.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(RaidGuard(bot, bot.core_client))
