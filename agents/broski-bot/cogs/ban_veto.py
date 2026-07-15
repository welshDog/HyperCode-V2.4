"""
BROski Bot — Ban Veto (Server Guardian Phase 3c)

The ONLY path to an autonomous-proposed ban. SPEC LOCKED & BINDING:

  • Trigger: Core escalates after 3 auto-mod timeouts / 7d (handled in Core).
  • Delivery: this cog posts a persistent-button proposal to BOTH a DM to the
    owner AND the mod-log channel. Buttons survive bot restarts (DynamicItem).
  • Resolution:
      ✅ APPROVE click  → ban executes (the ONLY way a ban ever happens)
      🛑 VETO click     → no ban, member keeps existing timeout
      ⏱ window expires  → DOWNGRADE to a long timeout. NEVER a ban.

  SAFETY INVARIANT (enforced here in code, not just intent):
  The reconciler can ONLY deliver or downgrade. It can NEVER approve.
  A ban happens IFF a human clicked APPROVE and Core returned 'executed'.
  Silence is downgrade. No autonomous irreversible action. Ever.
"""
from __future__ import annotations

import os
import re
import uuid
from datetime import timedelta

import discord
from discord.ext import commands, tasks

from core_client import CoreClient, CoreError, render_to_embed

# Discord hard limit on member timeout is 28 days.
_DISCORD_MAX_TIMEOUT_SECONDS = 28 * 24 * 3600


def _owner_id() -> int:
    raw = os.getenv("DIGEST_DM_USER_ID") or os.getenv("DISCORD_USER_ID") or "0"
    try:
        return int(raw)
    except ValueError:
        return 0


def _mod_log_channel_id() -> int:
    try:
        return int(os.getenv("MOD_LOG_CHANNEL_ID", "0"))
    except ValueError:
        return 0


def _core(bot: commands.Bot) -> CoreClient:
    return bot.core_client


def _sys_ctx(tag: str) -> dict:
    return {
        "user_id": "system",
        "username": "ban-veto",
        "guild_id": None,
        "channel_id": None,
        "interaction_id": f"veto-{tag}-{uuid.uuid4().hex[:10]}",
    }


async def _resolve(bot: commands.Bot, mod_action_id: int, decision: str, actor: str) -> dict:
    resp = await _core(bot).action(
        "mod.veto_resolve",
        _sys_ctx(decision),
        {"mod_action_id": mod_action_id, "decision": decision, "actor": actor},
    )
    return resp.get("data") or {}


class BanVetoButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"banveto:(?P<action>approve|veto):(?P<mid>[0-9]+)",
):
    """Persistent button. custom_id carries the mod_action_id so the buttons
    keep working across bot restarts (registered via add_dynamic_items)."""

    def __init__(self, action: str, mid: int):
        self.action = action
        self.mid = mid
        approve = action == "approve"
        super().__init__(
            discord.ui.Button(
                label="APPROVE BAN" if approve else "VETO",
                style=discord.ButtonStyle.danger if approve else discord.ButtonStyle.secondary,
                emoji="✅" if approve else "🛑",
                custom_id=f"banveto:{action}:{mid}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item, match: re.Match, /):
        return cls(match["action"], int(match["mid"]))

    async def _authorised(self, interaction: discord.Interaction) -> bool:
        # Owner (DM recipient) is always allowed; otherwise need ban perms.
        if interaction.user.id == _owner_id():
            return True
        perms = getattr(interaction.user, "guild_permissions", None)
        return bool(perms and (perms.ban_members or perms.manage_guild))

    async def callback(self, interaction: discord.Interaction):
        bot: commands.Bot = interaction.client  # type: ignore[assignment]

        if not await self._authorised(interaction):
            await interaction.response.send_message(
                "🔒 You need Ban Members permission to decide this.", ephemeral=True
            )
            return

        await interaction.response.defer()
        actor = f"{interaction.user} ({interaction.user.id})"

        try:
            data = await _resolve(bot, self.mid, self.action, actor)
        except CoreError:
            await interaction.followup.send(
                "⚠️ Core unavailable — try again.", ephemeral=True
            )
            return

        final = data.get("final_status")

        # Already resolved (stale duplicate message / double click) — never re-act.
        if data.get("already_resolved"):
            await self._finalise(interaction, f"ℹ️ Already **{final}** — no action taken.")
            return

        if self.action == "veto" and final == "vetoed":
            await self._finalise(
                interaction,
                f"🛑 **VETOED** by {interaction.user.mention}. "
                "Member keeps their existing timeout. No ban.",
            )
            return

        if self.action == "approve" and final == "executed":
            await self._do_ban(bot, interaction, data)
            return

        await self._finalise(interaction, f"State: **{final}** — no action taken.")

    async def _do_ban(self, bot, interaction, data: dict):
        gid = data.get("guild_id")
        target_id = data.get("target_discord_id")
        guild = bot.get_guild(int(gid)) if gid else None
        banned = False
        if guild and target_id:
            try:
                await guild.ban(
                    discord.Object(id=int(target_id)),
                    reason=f"Guardian veto APPROVED by {interaction.user}",
                    delete_message_seconds=0,
                )
                banned = True
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                banned = False
        msg = (
            f"✅ **BAN EXECUTED** — approved by {interaction.user.mention}."
            if banned
            else "⚠️ Approved, but the ban call failed (perms? already gone?). "
            "Core marked it executed — verify manually."
        )
        await self._finalise(interaction, msg)

    async def _finalise(self, interaction: discord.Interaction, text: str):
        try:
            await interaction.message.edit(content=text, view=None)
        except (discord.HTTPException, AttributeError):
            pass
        try:
            await interaction.followup.send(text, ephemeral=True)
        except discord.HTTPException:
            pass


def _veto_view(mid: int) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    v.add_item(BanVetoButton("approve", mid))
    v.add_item(BanVetoButton("veto", mid))
    return v


def _proposal_embed(item: dict, window_note: str) -> discord.Embed:
    e = discord.Embed(
        title="🚨 BAN PROPOSAL — veto window open",
        description=(
            f"**Target:** <@{item.get('target_discord_id')}> "
            f"(`{item.get('target_username') or item.get('target_discord_id')}`)\n"
            f"**Why:** {item.get('reason')}\n"
            f"**Strikes:** {item.get('strike_count')}\n\n"
            f"⏱ {window_note}\n"
            "🛑 **VETO** → no ban, member keeps timeout\n"
            "✅ **APPROVE BAN** → ban now (the ONLY way a ban happens)\n"
            "🤫 **No response** → auto-**downgrade** to a long timeout. *Never a ban.*"
        ),
        colour=0xED4245,
    )
    e.set_footer(text="BROski Guardian • Phase 3c • silence is safe")
    return e


class BanVeto(commands.Cog):
    """Phase 3c veto-gated ban. Reconciler can only deliver/downgrade — never ban."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._owner_id = _owner_id()
        self._mod_log_id = _mod_log_channel_id()

    async def cog_load(self):
        self.bot.add_dynamic_items(BanVetoButton)  # restore buttons after restart
        self.veto_loop.start()

    async def cog_unload(self):
        self.veto_loop.cancel()

    async def _deliver(self, item: dict):
        mid = item["mod_action_id"]
        embed = _proposal_embed(item, "Decide within the veto window.")
        view = _veto_view(mid)

        sent_any = False
        if self._owner_id:
            user = self.bot.get_user(self._owner_id) or await self._safe_fetch_user(self._owner_id)
            if user is not None:
                try:
                    await user.send(embed=embed, view=view)
                    sent_any = True
                except discord.HTTPException:
                    pass
        if self._mod_log_id:
            ch = self.bot.get_channel(self._mod_log_id)
            if ch is not None:
                try:
                    await ch.send(embed=embed, view=_veto_view(mid))
                    sent_any = True
                except discord.HTTPException:
                    pass

        if sent_any:
            try:
                await _resolve(self.bot, mid, "delivered", "system")
            except CoreError:
                pass  # next sweep retries delivery

    async def _safe_fetch_user(self, uid: int):
        try:
            return await self.bot.fetch_user(uid)
        except discord.HTTPException:
            return None

    async def _downgrade(self, item: dict):
        mid = item["mod_action_id"]
        try:
            data = await _resolve(self.bot, mid, "downgrade", "system(window-expired)")
        except CoreError:
            return
        if data.get("final_status") != "downgraded":
            return  # someone resolved it first — fine, never a ban

        secs = min(
            int(data.get("downgrade_seconds", 604800)),
            _DISCORD_MAX_TIMEOUT_SECONDS,
        )
        gid = data.get("guild_id")
        target_id = data.get("target_discord_id")
        guild = self.bot.get_guild(int(gid)) if gid else None
        note = "no member object — timeout skipped"
        if guild and target_id:
            member = guild.get_member(int(target_id))
            if member is not None:
                try:
                    await member.timeout(
                        timedelta(seconds=secs),
                        reason="Guardian: veto window expired — downgraded (NO ban)",
                    )
                    note = f"timed out {secs // 86400}d"
                except (discord.Forbidden, discord.HTTPException):
                    note = "timeout failed (perms?)"

        if self._mod_log_id:
            ch = self.bot.get_channel(self._mod_log_id)
            if ch is not None:
                try:
                    await ch.send(
                        f"⏱ Ban proposal #{mid} window expired → **DOWNGRADED** "
                        f"to long timeout ({note}). **No ban.** "
                        f"<@{target_id}>"
                    )
                except discord.HTTPException:
                    pass

    @tasks.loop(seconds=60)
    async def veto_loop(self):
        try:
            resp = await self.bot.core_client.action("mod.veto_sweep", _sys_ctx("sweep"))
        except CoreError:
            return
        for item in (resp.get("data") or {}).get("pending", []):
            if not item.get("delivered"):
                await self._deliver(item)
            elif item.get("due"):
                await self._downgrade(item)

    @veto_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(BanVeto(bot))
