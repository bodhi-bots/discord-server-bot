"""
Discord Server Bot - welcome messages, auto-role and a ticket system.

Slash commands (admins only):
  /setup-welcome <channel>   - channel where new members are welcomed
  /setup-autorole <role>     - role every new member gets automatically
  /setup-staffrole <role>    - role that can see all tickets
  /ticket-panel              - posts the "Open ticket" button in this channel
  /settings                  - show the current configuration
"""

import asyncio
import json
import logging
import os
from pathlib import Path

import discord
from discord import app_commands

TOKEN = os.environ["DISCORD_TOKEN"]  # from the Developer Portal - never put it in code or on GitHub
CONFIG_FILE = Path(__file__).with_name("config.json")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)


# ---------- Config (saved to disk, so it survives restarts) ----------

def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}


def save_config() -> None:
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def guild_config(guild_id: int) -> dict:
    return config.setdefault(str(guild_id), {})


config = load_config()


# ---------- Ticket buttons ----------

class OpenTicketView(discord.ui.View):
    """Panel with an 'Open ticket' button. timeout=None + custom_id keeps it working after a restart."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open ticket", emoji="🎫", style=discord.ButtonStyle.primary, custom_id="ticket:open")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # One open ticket per member
        existing = discord.utils.find(
            lambda c: c.topic == f"ticket-owner:{user.id}", guild.text_channels
        )
        if existing:
            await interaction.response.send_message(
                f"You already have an open ticket: {existing.mention}", ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        staff_id = guild_config(guild.id).get("staff_role")
        staff_role = guild.get_role(staff_id) if staff_id else None
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        try:
            channel = await guild.create_text_channel(
                name=f"ticket-{user.name}",
                overwrites=overwrites,
                topic=f"ticket-owner:{user.id}",
                category=interaction.channel.category,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to create channels. Ask an admin to check my role.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Ticket opened",
            description=f"Hi {user.mention}, describe your question and the team will help you soon.\n"
                        f"Press the button below when you're done.",
            color=discord.Color.blurple(),
        )
        mention = staff_role.mention if staff_role else ""
        await channel.send(content=mention, embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"Your ticket: {channel.mention}", ephemeral=True)


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close ticket", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="ticket:close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("This ticket will be closed in 5 seconds...")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to delete this channel.")


# ---------- Bot ----------

class ServerBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True  # needed for welcome messages and auto-role
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Register the buttons so old panels keep working after a restart
        self.add_view(OpenTicketView())
        self.add_view(CloseTicketView())

    async def sync_commands(self, guild: discord.Guild):
        # Syncing per server makes new commands show up instantly
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_ready(self):
        for guild in self.guilds:
            await self.sync_commands(guild)
        log.info("Logged in as %s in %d server(s)", self.user, len(self.guilds))

    async def on_guild_join(self, guild: discord.Guild):
        await self.sync_commands(guild)

    async def on_member_join(self, member: discord.Member):
        cfg = guild_config(member.guild.id)

        role_id = cfg.get("autorole")
        role = member.guild.get_role(role_id) if role_id else None
        if role:
            try:
                await member.add_roles(role, reason="Auto-role")
            except discord.Forbidden:
                log.warning("Can't give role %s: move the bot's role above it", role.name)

        channel_id = cfg.get("welcome_channel")
        channel = member.guild.get_channel(channel_id) if channel_id else None
        if channel:
            embed = discord.Embed(
                title=f"Welcome to {member.guild.name}!",
                description=f"Hey {member.mention}, great to have you here. "
                            f"You are member #{member.guild.member_count}.",
                color=discord.Color.green(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)


bot = ServerBot()
admin_only = app_commands.default_permissions(administrator=True)


@bot.tree.command(name="setup-welcome", description="Set the channel for welcome messages")
@admin_only
async def setup_welcome(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_config(interaction.guild_id)["welcome_channel"] = channel.id
    save_config()
    await interaction.response.send_message(f"✅ Welcome messages will be posted in {channel.mention}", ephemeral=True)


@bot.tree.command(name="setup-autorole", description="Set the role new members get automatically")
@admin_only
async def setup_autorole(interaction: discord.Interaction, role: discord.Role):
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            f"⚠️ My role must be above {role.mention}. Drag my role higher in Server Settings → Roles, then try again.",
            ephemeral=True,
        )
        return
    guild_config(interaction.guild_id)["autorole"] = role.id
    save_config()
    await interaction.response.send_message(f"✅ New members will get {role.mention}", ephemeral=True)


@bot.tree.command(name="setup-staffrole", description="Set the role that can see and answer tickets")
@admin_only
async def setup_staffrole(interaction: discord.Interaction, role: discord.Role):
    guild_config(interaction.guild_id)["staff_role"] = role.id
    save_config()
    await interaction.response.send_message(f"✅ {role.mention} can now see all tickets", ephemeral=True)


@bot.tree.command(name="ticket-panel", description="Post the ticket button in this channel")
@admin_only
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Need help?",
        description="Click the button below to open a private ticket with the team.",
        color=discord.Color.blurple(),
    )
    await interaction.channel.send(embed=embed, view=OpenTicketView())
    await interaction.response.send_message("✅ Ticket panel posted", ephemeral=True)


@bot.tree.command(name="settings", description="Show the current bot settings")
@admin_only
async def settings(interaction: discord.Interaction):
    cfg = guild_config(interaction.guild_id)
    g = interaction.guild

    def show(kind: str, key: str) -> str:
        item_id = cfg.get(key)
        item = (g.get_channel(item_id) if kind == "channel" else g.get_role(item_id)) if item_id else None
        return item.mention if item else "not set"

    await interaction.response.send_message(
        f"**Welcome channel:** {show('channel', 'welcome_channel')}\n"
        f"**Auto-role:** {show('role', 'autorole')}\n"
        f"**Staff role:** {show('role', 'staff_role')}",
        ephemeral=True,
    )


if __name__ == "__main__":
    bot.run(TOKEN, log_handler=None)
