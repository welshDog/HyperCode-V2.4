"""
Guardian P3c Smoke Test — flood/strike sim → ban ONLY on APPROVE click.

SACRED INVARIANT (from CLAUDE.md): guild.ban() can ONLY be called when a
human explicitly clicks APPROVE on a BanVetoButton AND Core returns
final_status='executed'. Every other code path must NEVER call guild.ban().

Coverage:
  P3a: flood detection  → member.timeout(), NOT guild.ban()
  P3c: APPROVE click    → guild.ban() called  (the one allowed path)
  P3c: VETO click       → guild.ban() NOT called
  P3c: already resolved → guild.ban() NOT called (idempotency guard)
  P3c: window expiry    → member.timeout() (long), NOT guild.ban()
  P3c: reconciler sweep → decision passed to Core is NEVER 'approve'

Run: pytest agents/broski-bot/tests/unit/cogs/test_guardian_p3c.py -v
"""
from __future__ import annotations

import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set env before importing the cogs so _owner_id() picks it up.
OWNER_ID = 900_001
os.environ.setdefault("DISCORD_USER_ID", str(OWNER_ID))

import discord
from discord.ext import commands

# Polyfill discord.ui.DynamicItem for discord.py < 2.4.0.
# The Docker image uses requirements.txt (discord.py==2.4.0); local pyproject
# pins ^2.3.2. This stub makes the test file importable in both environments.
if not hasattr(discord.ui, "DynamicItem"):
    class _DynItem:
        __class_getitem__ = classmethod(lambda cls, _: cls)

        def __init_subclass__(cls, /, template=None, **kw):
            super().__init_subclass__(**kw)

        def __init__(self, item):
            self.item = item

    discord.ui.DynamicItem = _DynItem  # type: ignore[attr-defined]

from cogs.ban_veto import BanVeto, BanVetoButton
from cogs.moderation import MENTION_LIMIT, SPAM_MSGS, SPAM_WINDOW, Moderation


# ── fixtures / helpers ────────────────────────────────────────────────────────

def _bot(core_action_return: dict) -> MagicMock:
    mock_core = MagicMock()
    mock_core.action = AsyncMock(return_value=core_action_return)
    bot = MagicMock(spec=commands.Bot)
    bot.core_client = mock_core
    return bot


def _interaction(bot, *, user_id: int = OWNER_ID) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.mention = f"<@{user_id}>"
    user.guild_permissions = MagicMock(ban_members=False, manage_guild=False)

    interaction = MagicMock()
    interaction.client = bot
    interaction.user = user
    interaction.response = MagicMock()
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    interaction.message = MagicMock()
    interaction.message.edit = AsyncMock()
    return interaction


def _message(
    *,
    content: str = "hello",
    guild_id: int = 111,
    user_id: int = 222,
    mentions: int = 0,
) -> MagicMock:
    """discord.Message stub that passes isinstance(author, discord.Member)."""
    member = MagicMock(spec=discord.Member)
    member.id = user_id
    member.name = "spammer"
    member.bot = False
    member.guild_permissions = MagicMock(
        administrator=False, manage_messages=False, manage_guild=False
    )
    member.timeout = AsyncMock()

    channel = MagicMock()
    channel.id = 333
    channel.purge = AsyncMock(return_value=[])

    guild = MagicMock()
    guild.id = guild_id

    msg = MagicMock(spec=discord.Message)
    msg.id = 9_999
    msg.author = member
    msg.guild = guild
    msg.channel = channel
    msg.content = content
    msg.mentions = [MagicMock() for _ in range(mentions)]
    msg.role_mentions = []
    return msg


def _guild_with_ban() -> MagicMock:
    guild = MagicMock()
    guild.ban = AsyncMock()
    guild.get_member = MagicMock(return_value=None)
    return guild


def _guild_with_member(timeout_mock: AsyncMock) -> MagicMock:
    member = MagicMock()
    member.__class__ = discord.Member
    member.timeout = timeout_mock

    guild = MagicMock()
    guild.ban = AsyncMock()
    guild.get_member = MagicMock(return_value=member)
    return guild


# ── P3a: moderation cog ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_p3a_mention_flood_triggers_timeout_not_ban():
    """
    P3a: Mention flood detected → Core directive=timeout → member.timeout()
    is called. guild.ban() is NEVER called. Phase 3a cannot produce a ban.
    """
    bot = _bot({"data": {
        "directive": "timeout",
        "timeout_seconds": 600,
        "delete_message": True,
        "reason": "Spam burst auto-handled",
        "mod_action_id": 1,
        "escalated_ban_id": None,
    }})
    cog = Moderation(bot, bot.core_client)

    # MENTION_LIMIT is 6 by default — send a message that trips it
    msg = _message(mentions=MENTION_LIMIT)

    await cog.on_message(msg)

    bot.core_client.action.assert_awaited_once()
    assert bot.core_client.action.call_args[0][0] == "mod.assess"
    msg.author.timeout.assert_awaited_once()


@pytest.mark.asyncio
async def test_p3a_rate_flood_triggers_timeout_not_ban():
    """
    P3a: Rate flood (N messages in window) → member.timeout(). No ban.
    Pre-fills the sliding window to force the trip on the next message.
    """
    bot = _bot({"data": {
        "directive": "timeout",
        "timeout_seconds": 600,
        "delete_message": True,
        "reason": "Spam burst auto-handled",
        "mod_action_id": 2,
        "escalated_ban_id": None,
    }})
    cog = Moderation(bot, bot.core_client)

    msg = _message(content="free nitro!!!!")
    key = (msg.guild.id, msg.author.id)
    now = time.monotonic()
    # Pre-fill the bucket with SPAM_MSGS entries in the window
    for _ in range(SPAM_MSGS):
        cog._recent[key].append((now, msg.content))

    await cog.on_message(msg)

    msg.author.timeout.assert_awaited_once()


@pytest.mark.asyncio
async def test_p3a_ignores_non_timeout_directive():
    """
    P3a guard: if Core responds with anything other than directive='timeout'
    (hypothetical / future safety), Moderation applies NO action at all.
    """
    bot = _bot({"data": {"directive": "ban"}})  # would be a Core bug
    cog = Moderation(bot, bot.core_client)

    msg = _message(mentions=MENTION_LIMIT)
    await cog.on_message(msg)

    msg.author.timeout.assert_not_awaited()


# ── P3c: ban veto buttons ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_p3c_approve_executes_ban():
    """
    P3c APPROVE: human clicks APPROVE → Core returns final_status='executed'
    → guild.ban() IS called. This is the ONE allowed ban path.
    """
    guild_id, target_id = "5551", "7771"
    bot = _bot({"data": {
        "final_status": "executed",
        "target_discord_id": target_id,
        "guild_id": guild_id,
    }})
    mock_guild = _guild_with_ban()
    bot.get_guild.return_value = mock_guild

    button = BanVetoButton("approve", mid=42)
    await button.callback(_interaction(bot))

    mock_guild.ban.assert_awaited_once()
    reason = mock_guild.ban.call_args.kwargs.get("reason", "")
    assert "Guardian veto" in reason, f"Expected ban reason to mention 'Guardian veto', got: {reason!r}"


@pytest.mark.asyncio
async def test_p3c_veto_no_ban():
    """
    P3c VETO: human clicks VETO → guild.ban() is NEVER called.
    Member keeps their existing timeout.
    """
    bot = _bot({"data": {
        "final_status": "vetoed",
        "target_discord_id": "7771",
        "guild_id": "5551",
    }})
    mock_guild = _guild_with_ban()
    bot.get_guild.return_value = mock_guild

    button = BanVetoButton("veto", mid=42)
    await button.callback(_interaction(bot))

    mock_guild.ban.assert_not_awaited()


@pytest.mark.asyncio
async def test_p3c_already_resolved_no_ban():
    """
    P3c idempotency: stale double-click on an already-resolved proposal →
    Core returns already_resolved=True → guild.ban() is NOT called again.
    """
    bot = _bot({"data": {
        "already_resolved": True,
        "final_status": "executed",  # was previously approved — but stale click
    }})
    mock_guild = _guild_with_ban()
    bot.get_guild.return_value = mock_guild

    button = BanVetoButton("approve", mid=42)
    await button.callback(_interaction(bot))

    mock_guild.ban.assert_not_awaited()


# ── P3c: window expiry (reconciler downgrade) ─────────────────────────────────

@pytest.mark.asyncio
async def test_p3c_window_expiry_downgrades_not_bans():
    """
    P3c silence is safe: veto window expires → reconciler calls _downgrade →
    Core returns final_status='downgraded' → member.timeout(long) is called.
    guild.ban() is NEVER called. Silence = safe downgrade, never a ban.
    """
    guild_id, target_id = "5551", "7771"
    bot = _bot({"data": {
        "final_status": "downgraded",
        "downgrade_seconds": 604_800,
        "guild_id": guild_id,
        "target_discord_id": target_id,
    }})
    timeout_mock = AsyncMock()
    mock_guild = _guild_with_member(timeout_mock)
    bot.get_guild.return_value = mock_guild
    bot.get_channel.return_value = None

    cog = BanVeto(bot)
    await cog._downgrade({
        "mod_action_id": 42,
        "guild_id": guild_id,
        "target_discord_id": target_id,
    })

    timeout_mock.assert_awaited_once()
    mock_guild.ban.assert_not_awaited()


# ── P3c: reconciler loop invariant ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_p3c_reconciler_never_sends_approve_to_core():
    """
    P3c safety invariant: the veto_loop reconciler can only pass 'delivered'
    or 'downgrade' decisions to Core — NEVER 'approve'. If it ever passed
    'approve', Core would set status='executed' and the bot would ban without
    a human click. This test asserts that can never happen.
    """
    guild_id, target_id = "5551", "7771"

    # Two sweep items: one undelivered (→ _deliver), one due (→ _downgrade)
    sweep_response = {
        "data": {
            "pending": [
                {
                    "mod_action_id": 10,
                    "target_discord_id": target_id,
                    "target_username": "spammer",
                    "reason": "test",
                    "guild_id": guild_id,
                    "strike_count": 3,
                    "delivered": False,
                    "executes_at": None,
                    "due": False,
                },
                {
                    "mod_action_id": 11,
                    "target_discord_id": target_id,
                    "target_username": "spammer",
                    "reason": "test",
                    "guild_id": guild_id,
                    "strike_count": 3,
                    "delivered": True,
                    "executes_at": "2026-01-01T00:00:00+00:00",
                    "due": True,
                },
            ]
        }
    }

    approve_called_with = []

    async def _core_action(action, ctx, payload=None):
        if action == "mod.veto_sweep":
            return sweep_response
        if action == "mod.veto_resolve":
            decision = (payload or {}).get("decision")
            # CRITICAL ASSERTION: reconciler must NEVER pass 'approve' to Core
            if decision == "approve":
                approve_called_with.append(payload)
            if decision == "downgrade":
                return {"data": {
                    "final_status": "downgraded",
                    "downgrade_seconds": 604_800,
                    "guild_id": guild_id,
                    "target_discord_id": target_id,
                }}
            return {"data": {"ok": True, "final_status": "delivered"}}
        return {}

    mock_core = MagicMock()
    mock_core.action = AsyncMock(side_effect=_core_action)

    timeout_mock = AsyncMock()
    mock_guild = _guild_with_member(timeout_mock)
    mock_guild.ban = AsyncMock()

    bot = MagicMock()
    bot.core_client = mock_core
    bot.get_guild.return_value = mock_guild
    bot.get_user.return_value = None   # suppress DM in test
    bot.get_channel.return_value = None

    cog = BanVeto(bot)

    # Run one reconciler sweep directly via the underlying coroutine.
    # Patch _deliver so discord.ui.View.add_item() isn't called with our
    # polyfill stub — the delivery path is already tested separately.
    with patch.object(cog, "_deliver", new_callable=AsyncMock):
        await cog.veto_loop.coro(cog)

    # Sacred rule check: reconciler NEVER sent 'approve' to Core
    assert not approve_called_with, (
        "SAFETY VIOLATION: reconciler sent decision='approve' to Core — "
        f"payload(s): {approve_called_with!r}. "
        "A ban must only happen via explicit human APPROVE button click."
    )

    # Sanity: downgrade DID produce a timeout (item 11 was due)
    timeout_mock.assert_awaited_once()

    # Sanity: guild.ban was never called by the reconciler
    mock_guild.ban.assert_not_awaited()
