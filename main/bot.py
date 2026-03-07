# Necessary imports
import discord
from discord import app_commands

# Enables necessary Discord intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# Initialize Discord client and command tree
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# TicketsV2 UserID
TICKETS_BOT_ID = 1325579039888511056
# NOTE: You can replace this ID with any other Discord Ticket bot's ID if you
#       wish to use another bot, rather than the TicketsV2 