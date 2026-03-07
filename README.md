# Ticket Assistant

The Ticket Assistant is a lightweight, asynchronous Discord bot created in Python that provides real-time ticket analytics directly inside your server. While there is no central platform or website in which its hosted, you can very easily compile this code yourself and use it independently. This bot was originally created for the PvPHub Network.

![Bot banner](attachments/banner.png)


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
- Enable Privileged Gateway Intents
- Invite the bot to your server with proper permissions
- Configure the required environment variables


---


## 🔐 Environment Variables

In `../cogs/lists`, in your project root, configure the following:
- **DISCORD_TOKEN**="your_discord_bot_token"
- **SUPPORT_ROLES**="your_support_representatives"
- **STATS_ALLOWED_ROLES**="ticket_manager_roles"
- **DATABASE_PERMS**="databse_interaction_perms"
- **MANAGE_USER_PERMS**="manage_users_perms"
- **TICKET_CATEGORIES**="names_of_ticket_categories"
- **OPEN_MARKERS**="ticket_bot_opening_messages"


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


## License

The Ticket Assistant is licensed under the MIT License, meaning anyone is free to utilise, modify, or
redisribute the software as they please, with the only prerequisite being that they license it under
the MIT License as well.

This is not an official Discord product, nor is it affiliated with or endorsed by Discord Inc.