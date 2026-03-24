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
# NOTE: As of v1.3.0, this ID cannot be changed, as in doing so, you would be breaking the
#       dashboard linking - which is hard-coded - in message_detection.py. This is subject
#       to be fixed in a future update, but for now, please do not change this ID.