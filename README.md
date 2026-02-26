# Ticket Assistant

The Ticket Assistant is a lightweight, asynchronous Discord bot created in Python that provides real-time ticket analytics directly inside your server. While there is no central platform or website in which its hosted, you can very easily compile this code yourself and use it independently. This bot was originally created for the PvPHub Network.


---


## Features

- Ticket creation & closure logging
- Response time tracking
- Ticket duration analytics
- Automatic management notifications
- Slash command support
- Clean embed-based summaries


## What It Tracks

The bot collects and organizes:
- Total tickets opened
- Peak concurrent tickets
- Average initial response time
- Average ticket resolution time
- Average message count

This allows Management to easily identify inefficiencies, overload situations, or performance inconsistencies.


## Setup Requirements

To run the bot, you must create your own Discord application:
- Discord Developer Portal: https://discord.com/developers/applications

**After creating your bot:**
- Enable Privileged Gateway Intents (if required).
- Invite the bot to your server with proper permissions.
- Configure the required environment variables.


---


## 🔐 Environment Variables

In `permissions.py`, in your project root, configure the following:
- **DISCORD_TOKEN**="your_discord_bot_token"
- **SUPPORT_ROLES**="your_support_representatives"
- **STATS_ALLOWED_ROLES**="ticket_manager_roles"
- **DATABASE_PERMS**="databse_interaction_perms"
- **MANAGE_USER_PERMS**="manage_users_perms"
- **TICKET_CATEGORIES**="names_of_ticket_categories"


---


## 💻 Commands

**Ticket Stat commands:**
- `/ticketstats <category> <days>` - Shows stats for the specified category

**Ticket DataBase commands:**
- `/wipestats` - Wipes the database of all information (System-Admin+ default)
- `/wipehistory` - Brings up the audit log of the most recent DB wipes

**User Permission commands:**
- `/maxpermsadd <user>` - Adds max permissions to the specified user
- `/maxpermsremove <user>` - Removes max permissions from specified user
- `/privilegedusers` - Displays all users with maximum permissions

**Miscellaneous commands:**
- `/viewpermissions` - Lists all of the permissions that each roles has
- `/help` - General help about the bot and the features it provides

---


## Purpose

The Ticket Assistant is designed to increase transparency, accountability, and efficiency within structured support environments. 

By providing automated tracking and statistical insight, it ensures that no ticket is overlooked and that management remains fully informed at all times.