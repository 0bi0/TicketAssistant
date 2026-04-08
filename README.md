<div align="center">


# Ticket Assistant

![GitHub Release](https://img.shields.io/github/v/release/0bi0/TicketAssistant)
![Code Coverage](https://img.shields.io/badge/coverage-98%25-darkgreen)
![GitHub Commit Activity](https://img.shields.io/github/commit-activity/m/0bi0/TicketAssistant)
![Support Email](https://img.shields.io/badge/Disc._Support-@0bi0-red)


</div>



The Ticket Assistant is a lightweight, asynchronous, and customizable Discord bot created in Python that provides real-time ticket analytics directly inside your server. While there is no central platform or website in which its hosted, you can easily compile this code yourself and use it independently. This bot was originally created for the [PvPHub Network](https://discord.gg/pvphub). 

![Bot banner](attachments/banner.png)


> [!IMPORTANT]
> Due to the bot not being hosted on a central platform,
> **it ought to be run on a VPS or any other server.**
> For more information regarding how you can set the bot up for your personal usage, 
> please consult [this](https://www.cherryservers.com/blog/host-discord-bot-on-vps) article.


---


## Features

- 🗂️ | **Ticket creation & closure logging** - Records when tickets are opened and closed
- ⏱️ | **Response time tracking** - Measures how quickly staff respond after a ticket is created
- 📊 | **Ticket duration analytics** - Calculates how long tickets stay open from creation to closure
- 🔔 | **Automatic management notifications** - Sends alerts to management channels when key ticket events occur
- 🧭 | **Slash command support** - Provides easy-to-use Discord slash commands for analytics and workflows
- 🧾 | **Clean embed-based summaries** - Presents ticket metrics and logs in structured, readable embed messages
- 💾 | **Developer command integration** - Provides developer commands for bot debugging and maintenance


---


## Setup Requirements

To run the bot, you must create your own Discord application:
- Discord Developer Portal: https://discord.com/developers/applications

**After creating your bot:**
- Enable Privileged Gateway Intents
- Invite the bot to your server with proper permissions
- Configure the required environment variables

For more information regarding bot setup, please read `SETUP.md`


---


## 🔐 Environment Variables

In `../cogs/lists` and `../.env`, in your project root, configure the following:
- **DISCORD_TOKEN**="your_discord_bot_token"
- **OPEN_MARKERS**="ticket_bot_opening_messages"
- **CLOSE_MARKERS**="ticket_bot_closing_messages"


---
## 💻 Commands

All of the bot's commands can be listed by pressing the button below.

<details>
  <summary>Show commands</summary>

  ## 📋 Standard Commands

  | Category | Command | Description |
  |--------|--------|--------|
  | **Ticket Statistics** | `/ticketstats <category> <days>` | Shows ticket statistics for the specified category |
  | **Ticket Statistics** | `/tickethistory <category> <days>` | Shows ticket logs for specified time period |
  | **Database Management** | `/wipestats` | Wipes all stored ticket statistics |
  | **Database Management** | `/wipehistory` | Shows history of database wipes |
  | **Ticket Summaries** | `/summarychannel` | Sets the channel for automated reports |
  | **Ticket Summaries** | `/summaryfrequency` | Sets the frequency between each report |
  | **User Permissions** | `/maxpermsadd <user>` | Grants maximum permissions |
  | **User Permissions** | `/maxpermsremove <user>` | Removes maximum permissions |
  | **User Permissions** | `/privilegedusers` | Lists all privileged users |
  | **Miscellaneous** | `/logchannelset <channel>` | Sets logging channel for ticket |
  | **Miscellaneous** | `/passwordset` | Sets the PW for maintenance |
  | **Miscellaneous** | `/help` | Displays help information |


  ## 🧩 Developer Commands

  | Category | Command | Description |
  |--------|--------|--------|
  | **System Administration** | `dev!panel` | Opens up the developer interface for necessary utilites |
  | **System Administration** | `dev!perms` | Opens role permissions management panel |
  | **Developer Access** | `dev!whitelist <@user>` | Adds a developer (owner only) |
  | **Developer Access** | `dev!unwhitelist <@user>` | Removes a developer (owner only) |
  | **User Messaging** | `dev!dm <@user> <message>` | Sends a DM as the bot |
  | **User Messaging** | `dev!dmall <message>` | Sends a DM to all non-bot members |
  | **Miscellaneous** | `dev!list` | Lists all registered developers in the server |
  | **Miscellaneous** | `dev!help` | Displays all available developer commands |

</details>


---


## License

The Ticket Assistant is licensed under the MIT License, meaning anyone is free to utilise, modify, or
redisribute the software as they please, with the only prerequisite being that they license it under
the MIT License as well.

This is not an official Discord product, nor is it affiliated with or endorsed by Discord Inc.


---


For any potential inquiries, please contact [admin@ticketassistant.dev](mailto:admin@ticketassistant.dev).
