"""
BROski Bot — Moderation Cog (Server Guardian Phase 3a)

Reversible auto-mod only: structural spam detection (rate / duplicate /
mention flood) + optional content blocklist. On a trip the bot asks Core
(`mod.assess`) for the directive, then applies a reversible action
(delete message + timeout). Core owns the decision + audit log.

Phase 3a NEVER bans or kicks — that's Phase 3c (veto-gated).
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from datetime import timedelta

import discord
from discord.ext import commands

from core_client import CoreClient, CoreError, render_to_embed


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _blocklist() -> list[str]:
    raw = os.getenv("MOD_BLOCKLIST", "")
    return [w.strip().lower() for w in raw.split(",") if w.strip()]


SPAM_MSGS = _int_env("MOD_SPAM_MSGS", 6)
SPAM_WINDOW = _int_env("MOD_SPAM_WINDOW", 8)
MENTION_LIMIT = _int_env("MOD_MENTION_LIMIT", 6)
DUP_LIMIT = _int_env("MOD_DUPLICATE_LIMIT", 4)
MOD_LOG_CHANNEL_ID = _int_env("MOD_LOG_CHANNEL_ID", 0)


class Moderation(commands.Cog):
    """Reversible auto-mod. Detection bot-side, decision + audit Core-side."""

    def __init__(self, bot: commands.Bot, core: CoreClient):
        self.bot = bot
        self.core = core
        self._blocklist = _blocklist()
        # (guild_id, user_id) -> deque[(ts, content)]
        self._recent: dict[tuple[int, int], deque] = defaultdict(
            lambda: deque(maxlen=max(SPAM_MSGS, DUP_LIMIT) + 2)
        )
        self._handled: set[int] = set()  # message ids already actioned

    def _detect(self, message: discord.Message) -> tuple[str, dict] | None:
        """Return (kind, evidence) if message trips a rule, else None."""
        content = (message.content or "").strip()

        # Mention flood — single message, content-neutral
        mention_count = len(message.mentions) + len(message.role_mentions)
        if mention_count >= MENTION_LIMIT:
            return "spam", {"rule": "mention_flood", "mentions": mention_count}

        # Blocklist (opt-in, empty by default)
        low = content.lower()
        for word in self._blocklist:
            if word and word in low:
                return "blocklist", {"rule": "blocklist", "match": word}

        key = (message.guild.id, message.author.id)
        now = time.monotonic()
        bucket = self._recent[key]
        bucket.append((now, content))

        # Rate flood
        recent = [t for (t, _c) in bucket if now - t <= SPAM_WINDOW]
        if len(recent) >= SPAM_MSGS:
            return "spam", {
                "rule": "rate_flood",
                "count": len(recent),
                "window_s": SPAM_WINDOW,
            }

        # Duplicate flood
        if content:
            same = [c for (t, c) in bucket if c == content and now - t <= SPAM_WINDOW * 3]
            if len(same) >= DUP_LIMIT:
                return "spam", {"rule": "duplicate_flood", "count": len(same)}

        return None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.id in self._handled:
            return

        member = message.author
        if isinstance(member, discord.Member):
            perms = member.guild_permissions
            if perms.administrator or perms.manage_messages or perms.manage_guild:
                return  # never auto-mod staff

        hit = self._detect(message)
        if hit is None:
            return

        kind, evidence = hit
        self._handled.add(message.id)
        evidence = {**evidence, "channel_id": str(message.channel.id)}

        ctx = {
            "user_id": str(message.author.id),
            "username": message.author.name,
            "guild_id": str(message.guild.id),
            "channel_id": str(message.channel.id),
            "interaction_id": f"mod-{message.id}",
        }
        payload = {
            "kind": kind,
            "target_discord_id": str(message.author.id),
            "target_username": message.author.name,
            "channel_id": str(message.channel.id),
            "evidence": evidence,
        }

        try:
            resp = await self.core.action("mod.assess", ctx, payload)
        except CoreError:
            return  # Core down — fail safe: do nothing rather than mis-mod

        data = resp.get("data") or {}
        directive = data.get("directive")
        if directive != "timeout":
            return

        # Apply reversible actions with safe fallbacks.
        if data.get("delete_message"):
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                pass

        if isinstance(member, discord.Member):
            secs = int(data.get("timeout_seconds", 600))
            try:
                await member.timeout(
                    timedelta(seconds=secs),
                    reason=str(data.get("reason", "BROski auto-mod")),
                )
            except (discord.Forbidden, discord.HTTPException):
                pass

        if MOD_LOG_CHANNEL_ID and resp.get("render"):
            channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
            if channel is not None:
                try:
                    await channel.send(embed=render_to_embed(resp["render"]))
                except discord.HTTPException:
                    pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot, bot.core_client))
