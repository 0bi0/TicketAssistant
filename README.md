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

For more information regarding bot setup, please consult `SETUP.md`


---


## 🔐 Environment Variables

In `../cogs/lists` and `../.env`, in your project root, configure the following:
- **DISCORD_TOKEN**="your_discord_bot_token"
- **OPEN_MARKERS**="ticket_bot_opening_messages"
- **CLOSE_MARKERS**="ticket_bot_closing_messages"


---


## 💻 Commands

| Category | Command | Description |
|--------|--------|--------|
| **Ticket Statistics** | `/ticketstats <category> <days>` | Shows ticket statistics for the specified category |
| **Ticket Statistics** | `/tickethistory <category> <days>` | Shows ticket logs for specified time period |
| **Ticket Statistics** | `/logchannelset <channel>` | Sets logging channel for ticket
| **Database Management** | `/wipestats` | Wipes all stored ticket statistics |
| **Database Management** | `/wipehistory` | Shows history of database wipes |
| **User Permissions** | `/maxpermsadd <user>` | Grants maximum permissions |
| **User Permissions** | `/maxpermsremove <user>` | Removes maximum permissions |
| **User Permissions** | `/privilegedusers` | Lists all privileged users |
| **Miscellaneous** | `/logchannelset` | Sets the ticket logging channel |
| **Miscellaneous** | `/passwordset` | Sets the PW for maintenance |
| **Miscellaneous** | `/help` | Displays help information |


---


## License

The Ticket Assistant is licensed under the MIT License, meaning anyone is free to utilise, modify, or
redisribute the software as they please, with the only prerequisite being that they license it under
the MIT License as well.

This is not an official Discord product, nor is it affiliated with or endorsed by Discord Inc.