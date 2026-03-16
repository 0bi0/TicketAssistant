# Necessary imports
import discord
from discord import app_commands

from commands.databse_commands import wipestats, wipehistory
from commands.history_comands import tickethistory
from commands.miscellaneous_commands import help, listcommands, viewpermissions
from commands.privileged_user_commands import maxpermsadd, maxpermsremove, privilegedusers
from commands.log_channel_commands import logchannelset



# Registers all standalone slash commands onto the command tree
def register_commands(tree: app_commands.CommandTree[discord.Client]) -> None:
    tree.add_command(wipestats)
    tree.add_command(wipehistory)
    tree.add_command(tickethistory)
    tree.add_command(help)
    # tree.add_command(viewpermissions)
    tree.add_command(maxpermsadd)
    tree.add_command(maxpermsremove)
    tree.add_command(privilegedusers)
    tree.add_command(logchannelset)
    # tree.add_command(listcommands)