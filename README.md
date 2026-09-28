# Discord Server Bot

A Discord bot that handles the three things almost every server needs: welcome messages, automatic roles and a private ticket system with buttons.

## Features

**Welcome messages**: new members get a welcome embed with their avatar and member number.

**Auto-role**: every new member automatically gets a role you choose.

**Ticket system**: members click a button to open a private support channel that only they and your staff can see. One open ticket per member, and tickets are closed with one click.

- Settings are saved per server and survive restarts
- Ticket buttons keep working after the bot restarts
- Checks role order and permissions, and explains what to fix instead of failing silently
- Setup commands are visible to admins only

## Commands

| Command | What it does |
|---|---|
| `/setup-welcome <channel>` | Channel for welcome messages |
| `/setup-autorole <role>` | Role new members get automatically |
| `/setup-staffrole <role>` | Role that can see and answer all tickets |
| `/ticket-panel` | Post the "Open ticket" button in the current channel |
| `/settings` | Show the current configuration |

## Setup

1. Create an application in the [Discord Developer Portal](https://discord.com/developers/applications)
2. Under **Bot**, enable **Server Members Intent**
3. Invite the bot with the `bot` and `applications.commands` scopes and the permissions *Manage Roles*, *Manage Channels*, *View Channels*, *Send Messages*, *Embed Links* and *Read Message History*
4. Make sure the bot's role is above the role you use for auto-role

```
pip install -r requirements.txt
```

```
# Windows (PowerShell)
$env:DISCORD_TOKEN="your_token"
python serverbot.py
```

```
# Mac/Linux
export DISCORD_TOKEN="your_token"
python serverbot.py
```

## Tech

- Python 3.10+
- [discord.py](https://discordpy.readthedocs.io/) 2.x with slash commands and persistent button views
- JSON storage for per-server settings

## Custom bots

Need a bot for your community? Moderation, leveling, giveaways, verification, or integrations with your own tools. Get in touch via GitHub.
