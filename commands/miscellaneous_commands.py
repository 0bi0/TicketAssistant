# Necessary imports
import discord
from discord import app_commands



# ===| Help command |===
#
# A generic help command that displays information
# about the bot and its features

# Creates the command
@app_commands.command(name="help", description="General assistance regarding this bot")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Ticket Management Bot",
        color=0x00ffcc
    )

    # First section of the Bot's output
    embed.add_field(name="📰  Information", value=(
        "The 'Ticket Assistant' is a simple Python bot that tracks ticket activity in order to\n"
        "ensure that the Management Team is up-to-date with all of the latest updates\n" 
        "regarding the tickets' situation.\n"
        "––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––"
    ), inline=False)

    # Second section of the Bot's output
    embed.add_field(name="🛡️  Required Roles", value=(
        "In order to interact with the bot, you need to either hold one of the following\n"
        "positions, or be a user with max permissions (see note in `/viewpermissions`).\n"
        "・`Owner`\n"
        "・`System-Admin`\n"
        "・`Administrator`\n"
        "・`Appeals Manager`\n"
        "・`Reports Manager`\n"
        "・`General Tickets Manager`\n"
        "––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––"
    ), inline=False)

    # Third section of the Bot's output
    embed.add_field(name="📋  Commands", value=(
        "All executable commands can be found in the list below.\n"
        "\n"
        "Ticket Stat commands:\n"
        "・`/ticketstats all <days>` - Shows stats for all ticket categories in last X days\n"
        "・`/ticketstats <category> <days>` - Shows stats for the specified category\n"
        "Ticket DataBase commands:\n"
        "・`/wipestats` - Wipes the database of all information (System-Admin+)\n"
        "・`/wipehistory` - Brings up the audit log of the most recent DB wipes\n"
        "User Permission commands:\n"
        "・`/maxpermsadd <user>` - Adds max permissions to the specified user\n"
        "・`/maxpermsremove <user>` - Removes max permissions from specified user\n"
        "・`/privilegedusers` - Displays all users with maximum permissions\n"
        "Miscellaneous commands:\n"
        "・`/viewpermissions` - Lists all of the permissions that each roles has\n"
        "・`/help` - General help about the bot and the features it provides\n"
        "––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––"
    ), inline=False)

    # Footer + Send message argument
    embed.set_footer(text="PvPHub | Made by 0bi0")
    await interaction.response.send_message(embed=embed, ephemeral=True)



# ===| Permissions command |===
#
# Displays the permissions of each role

# Creates the command
@app_commands.command(name="viewpermissions", description="Information regarding perms of each role")
async def viewpermissions(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Information regarding Permissions",
        color=0x00ffcc
    )

    # NOTE: Privileged users will always have max perms regardless
    #       of which roles they have equipped!

    # First section of the Bot's output
    embed.add_field(name="⚙️  Permissions", value=(
        "・Owner - `/ticketstats`, `/maxpermsadd`, `/wipestats`, `/wipehistory`\n"
        "・Sys-Admins - `/ticketstats`, `/wipestats`, `/wipehistory`\n"
        "・Administrators - `/ticketstats`\n"
        "・Ticket Managers - `/ticketstats`\n"
        "––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––\n"
    ), inline=False)

    # Second section of the Bot's output
    embed.add_field(name="📝  Note", value=(
        "Certain users are automatically granted maximum permissions, regardless of their\n"
        "roles. Users can be granted max perms only at the discretion of the server owner.\n"
        "––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––"
    ), inline=False)

    # Footer + Send message argument
    embed.set_footer(text="PvPHub | Made by 0bi0")
    await interaction.response.send_message(embed=embed, ephemeral=True)