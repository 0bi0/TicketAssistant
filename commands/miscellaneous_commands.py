# Necessary imports
import discord
from discord import app_commands


def _build_help_embed() -> discord.Embed:
    embed = discord.Embed(
        title="Ticket Management Bot",
        color=0xb6b6b6
    )

    # First section of the Bot's output
    embed.add_field(name="📰  Information", value=(
        "The `Ticket Assistant` is a robust ticket management bot designed to help\n"
        "streamline the process of managing tickets and providing insights into their\n"
        "status. Currently running on SQLite version 3.51.3.\n"
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

    embed.set_footer(text="Ticket Assistant | Made by 0bi0")
    return embed


def _build_permissions_embed() -> discord.Embed:
    embed = discord.Embed(
        title="Information regarding Permissions",
        color=0xb6b6b6
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
    embed.set_footer(text="Ticket Assistant | Made by 0bi0")
    return embed


def _build_listcommands_embed() -> discord.Embed:
    embed = discord.Embed(
        title="Available Bot Commands",
        color=0xb6b6b6
    )

    embed.add_field(name="📋  Commands", value=(
        "All executable commands can be found in the list below.\n"
        "‎ \n"
    ), inline=False)

    embed.add_field(name="Ticket Stat commands", value=(
        "・`/ticketstats <category> <days>` - Shows stats for the specified category\n"
        "・`/tickethistory <category> <time>` - Shows all tickets in selected period\n"
        "・`/logchannelset <channel>` - Sets the channel for ticket event logs"
    ), inline=False)

    embed.add_field(name="Ticket DataBase commands", value=(
        "・`/wipestats` - Wipes the database of all information (System-Admin+)\n"
        "・`/wipehistory` - Brings up the audit log of the most recent DB wipes"
    ), inline=False)

    embed.add_field(name="User Permission commands", value=(
        "・`/maxpermsadd <user>` - Adds max permissions to the specified user\n"
        "・`/maxpermsremove <user>` - Removes max permissions from specified user\n"
        "・`/privilegedusers` - Displays all users with maximum permissions"
    ), inline=False)

    embed.add_field(name="Miscellaneous commands", value=(
        "・`/help` - General help about the bot and the features it provides\n"
        "––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––"
    ), inline=False)

    embed.set_footer(text="Ticket Assistant | Made by 0bi0")
    return embed


class CommandNavigationSelect(discord.ui.Select):
    def __init__(self, current_page: str):
        options = [
            discord.SelectOption(
                label="Help",
                value="help",
                description="General bot help and role overview",
                emoji="📰",
                default=current_page == "help"
            ),
            discord.SelectOption(
                label="Permissions",
                value="permissions",
                description="Role permissions and max-perms note",
                emoji="⚙️",
                default=current_page == "permissions"
            ),
            discord.SelectOption(
                label="Command List",
                value="listcommands",
                description="All available slash commands",
                emoji="📋",
                default=current_page == "listcommands"
            ),
        ]

        super().__init__(
            placeholder="Choose a section...",
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        selected_page = self.values[0]
        parent_view = self.view
        if isinstance(parent_view, CommandNavigationView):
            await parent_view.navigate_to(interaction, selected_page)


class CommandNavigationView(discord.ui.View):
    def __init__(self, current_page: str = "help"):
        super().__init__(timeout=180)
        self.current_page = current_page
        self._refresh_menu()

    def _refresh_menu(self):
        self.clear_items()
        self.add_item(CommandNavigationSelect(self.current_page))

    async def navigate_to(self, interaction: discord.Interaction, destination: str):
        self.current_page = destination
        self._refresh_menu()

        if destination == "permissions":
            embed = _build_permissions_embed()
        elif destination == "listcommands":
            embed = _build_listcommands_embed()
        else:
            embed = _build_help_embed()

        await interaction.response.edit_message(embed=embed, view=self)



# ===| Help command |===
#
# A generic help command that displays information
# about the bot and its features

# Creates the command
@app_commands.command(name="help", description="General assistance regarding this bot")
async def help(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.NotFound:
        return

    embed = _build_help_embed()
    try:
        await interaction.followup.send(embed=embed, view=CommandNavigationView(current_page="help"), ephemeral=True)
    except discord.NotFound:
        return



# ===| Command list command |===
#
# Displays every slash command the bot can execute

# Creates the command
@app_commands.command(name="listcommands", description="Lists all commands this bot can execute")
async def listcommands(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.NotFound:
        return

    embed = _build_listcommands_embed()
    try:
        await interaction.followup.send(
            embed=embed,
            view=CommandNavigationView(current_page="listcommands"),
            ephemeral=True
        )
    except discord.NotFound:
        return



# ===| Permissions command |===
#
# Displays the permissions of each role

# Creates the command
@app_commands.command(name="viewpermissions", description="Information regarding perms of each role")
async def viewpermissions(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.NotFound:
        return

    embed = _build_permissions_embed()
    try:
        await interaction.followup.send(embed=embed, view=CommandNavigationView(current_page="permissions"), ephemeral=True)
    except discord.NotFound:
        return