"""
Admin Cog — Full server administration for BROski World.
Grants admins/owner complete control over the server environment.
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)

# Permission guard — only guild admins or bot owner
def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        app = await interaction.client.application_info()
        return interaction.user.id == app.owner.id
    return app_commands.check(predicate)


class AdminCog(commands.Cog, name="Admin"):
    """Full server administration tools for BROski World."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─── MODERATION ───────────────────────────────────────────────

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(member="Member to ban", reason="Reason for ban", delete_days="Days of messages to delete (0-7)")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided", delete_days: int = 0):
        await interaction.response.defer(ephemeral=True)
        try:
            await member.ban(reason=f"[BROski Admin] {reason}", delete_message_days=min(delete_days, 7))
            embed = discord.Embed(title="🔨 Member Banned", color=0xe74c3c)
            embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=True)
            embed.add_field(name="By", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await interaction.followup.send(embed=embed)
            logger.info("Ban", user=str(member), by=str(interaction.user), reason=reason)
        except discord.Forbidden:
            await interaction.followup.send("❌ Missing permissions to ban this member.")

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="Member to kick", reason="Reason for kick")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await interaction.response.defer(ephemeral=True)
        try:
            await member.kick(reason=f"[BROski Admin] {reason}")
            embed = discord.Embed(title="👢 Member Kicked", color=0xe67e22)
            embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=True)
            embed.add_field(name="By", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await interaction.followup.send(embed=embed)
        except discord.Forbidden:
            await interaction.followup.send("❌ Missing permissions to kick this member.")

    @app_commands.command(name="timeout", description="Timeout (mute) a member")
    @app_commands.describe(member="Member to timeout", minutes="Duration in minutes (max 40320 = 28 days)", reason="Reason")
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int = 10, reason: str = "No reason provided"):
        await interaction.response.defer(ephemeral=True)
        duration = timedelta(minutes=min(minutes, 40320))
        try:
            await member.timeout(duration, reason=f"[BROski Admin] {reason}")
            embed = discord.Embed(title="🔇 Member Timed Out", color=0xf39c12)
            embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=True)
            embed.add_field(name="Duration", value=f"{minutes} min", inline=True)
            embed.add_field(name="By", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await interaction.followup.send(embed=embed)
        except discord.Forbidden:
            await interaction.followup.send("❌ Missing permissions to timeout this member.")

    @app_commands.command(name="untimeout", description="Remove timeout from a member")
    @app_commands.describe(member="Member to untimeout")
    @app_commands.default_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        try:
            await member.timeout(None)
            await interaction.followup.send(f"✅ Timeout removed from **{member}**.")
        except discord.Forbidden:
            await interaction.followup.send("❌ Missing permissions.")

    @app_commands.command(name="warn", description="Issue a warning to a member (sends DM)")
    @app_commands.describe(member="Member to warn", reason="Warning reason")
    @app_commands.default_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        await interaction.response.defer(ephemeral=True)
        try:
            embed_dm = discord.Embed(
                title=f"⚠️ Warning from {interaction.guild.name}",
                description=f"**Reason:** {reason}",
                color=0xf1c40f,
            )
            embed_dm.set_footer(text="Please follow server rules.")
            try:
                await member.send(embed=embed_dm)
                dm_status = "DM sent"
            except discord.Forbidden:
                dm_status = "DM blocked by user"

            embed = discord.Embed(title="⚠️ Warning Issued", color=0xf1c40f)
            embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=True)
            embed.add_field(name="By", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=dm_status)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

    @app_commands.command(name="purge", description="Bulk delete messages in a channel")
    @app_commands.describe(amount="Number of messages to delete (1-500)")
    @app_commands.default_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int = 10):
        await interaction.response.defer(ephemeral=True)
        amount = max(1, min(amount, 500))
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🗑️ Deleted **{len(deleted)}** messages.", ephemeral=True)

    # ─── ROLES ────────────────────────────────────────────────────

    @app_commands.command(name="role_add", description="Add a role to a member")
    @app_commands.describe(member="Target member", role="Role to add")
    @app_commands.default_permissions(manage_roles=True)
    async def role_add(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        try:
            await member.add_roles(role, reason=f"Added by {interaction.user}")
            await interaction.followup.send(f"✅ Added **{role.name}** to **{member}**.")
        except discord.Forbidden:
            await interaction.followup.send("❌ Missing permissions to manage roles.")

    @app_commands.command(name="role_remove", description="Remove a role from a member")
    @app_commands.describe(member="Target member", role="Role to remove")
    @app_commands.default_permissions(manage_roles=True)
    async def role_remove(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        try:
            await member.remove_roles(role, reason=f"Removed by {interaction.user}")
            await interaction.followup.send(f"✅ Removed **{role.name}** from **{member}**.")
        except discord.Forbidden:
            await interaction.followup.send("❌ Missing permissions to manage roles.")

    @app_commands.command(name="role_create", description="Create a new role")
    @app_commands.describe(name="Role name", colour="Hex colour e.g. ff5500", hoist="Show separately in member list")
    @app_commands.default_permissions(manage_roles=True)
    async def role_create(self, interaction: discord.Interaction, name: str, colour: str = "99aab5", hoist: bool = False):
        await interaction.response.defer(ephemeral=True)
        try:
            colour_val = int(colour.lstrip("#"), 16)
            role = await interaction.guild.create_role(
                name=name,
                colour=discord.Colour(colour_val),
                hoist=hoist,
                reason=f"Created by {interaction.user}",
            )
            await interaction.followup.send(f"✅ Created role {role.mention}.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error creating role: {e}")

    # ─── CHANNELS ─────────────────────────────────────────────────

    @app_commands.command(name="channel_lock", description="Lock a channel (prevent @everyone from sending)")
    @app_commands.default_permissions(manage_channels=True)
    async def channel_lock(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.followup.send(f"🔒 Channel **{interaction.channel.name}** locked.")

    @app_commands.command(name="channel_unlock", description="Unlock a channel")
    @app_commands.default_permissions(manage_channels=True)
    async def channel_unlock(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = True
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.followup.send(f"🔓 Channel **{interaction.channel.name}** unlocked.")

    @app_commands.command(name="slowmode", description="Set slowmode delay on a channel")
    @app_commands.describe(seconds="Seconds between messages (0 = off, max 21600)")
    @app_commands.default_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int = 0):
        await interaction.response.defer(ephemeral=True)
        seconds = max(0, min(seconds, 21600))
        await interaction.channel.edit(slowmode_delay=seconds)
        status = f"{seconds}s" if seconds > 0 else "disabled"
        await interaction.followup.send(f"⏱️ Slowmode **{status}** in {interaction.channel.mention}.")

    # ─── ANNOUNCEMENTS ────────────────────────────────────────────

    @app_commands.command(name="announce", description="Send an announcement embed to a channel")
    @app_commands.describe(channel="Target channel", title="Announcement title", message="Announcement body", colour="Hex colour (default 3498db)")
    @app_commands.default_permissions(manage_messages=True)
    async def announce(self, interaction: discord.Interaction, channel: discord.TextChannel, title: str, message: str, colour: str = "3498db"):
        await interaction.response.defer(ephemeral=True)
        try:
            colour_val = int(colour.lstrip("#"), 16)
            embed = discord.Embed(title=title, description=message, color=colour_val)
            embed.set_footer(text=f"Announced by {interaction.user.display_name}")
            await channel.send(embed=embed)
            await interaction.followup.send(f"✅ Announcement sent to {channel.mention}.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

    # ─── SERVER INFO ──────────────────────────────────────────────

    @app_commands.command(name="serverinfo", description="Display detailed server statistics")
    async def serverinfo(self, interaction: discord.Interaction):
        g = interaction.guild
        embed = discord.Embed(title=f"📊 {g.name}", color=0x3498db)
        embed.set_thumbnail(url=g.icon.url if g.icon else None)
        embed.add_field(name="Owner", value=g.owner.mention if g.owner else "Unknown", inline=True)
        embed.add_field(name="Members", value=f"👥 {g.member_count}", inline=True)
        embed.add_field(name="Channels", value=f"💬 {len(g.text_channels)} text | 🔊 {len(g.voice_channels)} voice", inline=True)
        embed.add_field(name="Roles", value=f"🎭 {len(g.roles)}", inline=True)
        embed.add_field(name="Emojis", value=f"😀 {len(g.emojis)}", inline=True)
        embed.add_field(name="Boosts", value=f"🚀 {g.premium_subscription_count} (Level {g.premium_tier})", inline=True)
        embed.add_field(name="Created", value=f"<t:{int(g.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Verification", value=str(g.verification_level).title(), inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Display detailed info about a member")
    @app_commands.describe(member="Member to inspect (default: yourself)")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        embed = discord.Embed(title=f"👤 {member}", color=member.colour)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
        embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown", inline=True)
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"]
        embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles[:10]) or "None", inline=False)
        top_perms = [p.replace("_", " ").title() for p, v in member.guild_permissions if v and p in ("administrator", "manage_guild", "manage_roles", "ban_members", "kick_members")]
        if top_perms:
            embed.add_field(name="Key Permissions", value=", ".join(top_perms), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="adminhelp", description="List all admin commands")
    @app_commands.default_permissions(manage_messages=True)
    async def adminhelp(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🛡️ BROski Admin Commands", color=0x9b59b6)
        commands_list = {
            "Moderation": "/ban /kick /timeout /untimeout /warn /purge",
            "Roles": "/role_add /role_remove /role_create",
            "Channels": "/channel_lock /channel_unlock /slowmode",
            "Announcements": "/announce",
            "Info": "/serverinfo /userinfo /adminhelp",
        }
        for category, cmds in commands_list.items():
            embed.add_field(name=category, value=f"`{cmds}`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
