import discord
from discord import app_commands

from commands.databse_commands import wipestats, wipehistory
from commands.miscellaneous_commands import help, viewpermissions
from commands.privileged_user_commands import (maxpermsadd, maxpermsremove, privilegedusers,)

# Registers all standalone slash commands onto the command tree
def register_commands(tree: app_commands.CommandTree[discord.Client]) -> None:
    tree.add_command(wipestats)
    tree.add_command(wipehistory)
    tree.add_command(help)
    tree.add_command(viewpermissions)
    tree.add_command(maxpermsadd)
    tree.add_command(maxpermsremove)
    tree.add_command(privilegedusers)