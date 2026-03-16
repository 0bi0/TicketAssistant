# Ticket Assistant Setup Guide

This guide explains how to set up this bot from scratch for your own Discord server.

## What this bot does

This project is not a ticket system by itself. It watches ticket activity from another ticket bot, stores ticket data in a local SQLite database, and exposes slash commands for stats, history, permissions, and log-channel management.

By default, it is configured to work with TicketsBot/TicketsV2-style embeds and transcript URLs.



## 1. Install the prerequisites

You need:

- Python 3.11 or newer
- A Discord server where you have permission to add bots and manage roles/channels
- A Discord bot application created in the Discord Developer Portal
- An existing ticket bot in your server that creates ticket channels and posts ticket open/close embeds



## 2. Clone or download this project

Place the project somewhere permanent on the machine that will run it.

Example:

```powershell
git clone https://github.com/0bi0/TicketAssistant.git
cd TicketAssistant
```

If you downloaded a ZIP instead, extract it and open the project root in a terminal.



## 3. Create a Python virtual environment

From the project root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If `py -3.11` is not available, use the Python launcher/version installed on your machine.



## 4. Install the Python dependencies

With the virtual environment active:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

This project depends on:

- `discord.py`
- `matplotlib`
- `aiosqlite`
- `python-dotenv`



## 5. Create the `.env` file in the project root

Create a file named `.env` in the main project root, on the same level as `README.md` and `requirements.txt`.

Add this:

```env
DISCORD_BOT_TOKEN=your_bot_token_here
```

Important:

- The code looks specifically for `DISCORD_BOT_TOKEN`
- The `.env` file must be in the project root
- Do not commit your token to Git



## 6. Create your Discord bot application

Go to the Discord Developer Portal:

https://discord.com/developers/applications

Then:

1. Create a new application.
2. Open the `Bot` section.
3. Create the bot user.
4. Copy the bot token and place it in the `.env` file.
5. Enable these Privileged Gateway Intents:
   - `Server Members Intent`
   - `Message Content Intent`

This repository also uses guild data, so the bot must be able to access server and channel information normally.



## 7. Invite the bot to your server

When generating the invite URL, give the bot the permissions it needs to function in your server.

At minimum, make sure it can:

- View channels
- Read message history
- Send messages
- Embed links
- Use application commands

Depending on how your server is configured, you may also need to allow it to view private ticket channels/categories.



## 8. Configure the ticket categories and role names

This project does not store most role/category configuration in `.env`. It reads those values directly from Python files in `cogs/lists/`.

Edit these files so the names exactly match your Discord server:

- `cogs/lists/ticket_categories.py`
  - Maps slash-command category keys to actual Discord category names
- `cogs/lists/support_roles.py`
  - Roles treated as support staff for message tracking and ticket history
- `cogs/lists/allowed_roles.py`
  - Roles allowed to run ticket stats commands
- `cogs/lists/database_perms.py`
  - Roles allowed to wipe the database and view wipe history
- `cogs/lists/manage_user_perms.py`
  - Roles allowed to manage privileged users and set the ticket log channel
- `cogs/lists/opening_messages.py`
  - Text markers used to detect ticket-open embeds
- `cogs/lists/closing_messages.py`
  - Text markers used to detect ticket-close embeds

Notes:

- The names must match your Discord role names and category names exactly.
- `VARIABLES.md` is only a reference document. Editing it does not change runtime behavior.



## 9. If needed, change the tracked ticket bot ID

Open `main/bot.py`.

By default, this project is configured with:

```python
TICKETS_BOT_ID = 1325579039888511056
```

If your server uses a different ticket bot, replace that ID with the bot user ID of the system that creates the ticket embeds/channels you want to track.

If you use a different ticket bot, you may also need to update:

- `cogs/lists/opening_messages.py`
- `cogs/lists/closing_messages.py`
- Any transcript URL assumptions in the event handlers



## 10. Start the bot

From the project root, with the virtual environment active:

```powershell
python -m main.main
```

What happens on startup:

- The bot loads `.env`
- It creates or updates `tickets.db`
- It creates a `.bot.lock` file to prevent multiple instances from running at once
- It syncs the slash commands to Discord

If the token is missing, startup stops immediately.



## 11. Wait for slash commands to sync

On startup, the bot registers and syncs its slash commands. Give Discord a short time to reflect them in your server.

The available commands include:

- `/ticketstats`
- `/tickethistory`
- `/logchannelset`
- `/wipestats`
- `/wipehistory`
- `/maxpermsadd`
- `/maxpermsremove`
- `/privilegedusers`
- `/help`



## 12. Set the ticket log channel

After the bot is online, run this in your Discord server:

```text
/logchannelset
```

Select the text channel where ticket open/close logs should be sent.

Only users with the configured manage-permissions role, or users added as privileged users, can run this command.



## 13. Test the setup

Run these checks:

1. Open a test ticket using your ticket bot.
2. Confirm the analytics bot stays online with no startup errors.
3. Send a few messages in the ticket.
4. Close the ticket.
5. Confirm a row is written into `tickets.db`.
6. Confirm the configured log channel receives a close/open log when applicable.
7. Run `/ticketstats` and `/tickethistory` to verify data is visible.

## 14. Keep in mind how this bot detects tickets

This project relies on message/embed pattern matching and channel deletion events.

That means:

- Your ticket system must post recognizable open/close embeds
- Ticket categories must match the configured names
- If your ticket bot uses different embed wording, you must update the marker lists
- Closing is ultimately tracked from channel deletion events, so behavior depends on how your ticket system closes tickets



## 15. Common problems

### Bot exits immediately with a token error

Cause:

- `.env` is missing
- The variable name is wrong
- The token is empty

Fix:

- Make sure the root `.env` file contains `DISCORD_BOT_TOKEN=...`

### Commands do not show up

Cause:

- The bot is not online
- The invite is missing application command scope/permissions
- Discord has not finished syncing yet

Fix:

- Restart the bot and wait a minute
- Re-invite the bot with the correct scopes and permissions

### No ticket data is being recorded

Cause:

- The wrong ticket bot ID is configured
- The open/close marker text does not match your ticket bot's embeds
- The category names do not match your actual Discord categories
- The bot cannot see the ticket channels

Fix:

- Update `main/bot.py`
- Update the marker lists in `cogs/lists/`
- Verify category and role names
- Check the bot's server permissions and channel access

### The bot says another instance is already running

Cause:

- Another copy of the bot is still running
- The previous process did not shut down cleanly

Fix:

- Stop the other process
- If no process is running, delete `.bot.lock` and start the bot again



## 16. Recommended production setup

For long-term use, run this bot on a machine or VPS that stays online and keep these files backed up:

- `.env`
- `tickets.db`

If you change role names, category names, or ticket bot behavior in your server, update the corresponding files in `cogs/lists/` and restart the bot.