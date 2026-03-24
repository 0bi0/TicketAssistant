# Necessary imports
import discord
from discord import app_commands

from cogs.permissions import PERMISSION_ROLE_CATEGORY_LABELS, get_permission_roles_for_category



EMBED_DIVIDER = "––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––"

DEV_COMMAND_GROUPS: dict[str, tuple[tuple[str, str], ...]] = {
    "Utility commands": (
        ("dev!help", "General help for developer commands"),
        ("dev!list", "Lists all registered developers in the server"),
    ),
    "Panel commands": (
        ("dev!panel", "Opens the live developer control panel"),
        ("dev!perms", "Opens role permissions management panel"),
    ),
    "Access commands": (
        ("dev!whitelist <@user>", "Adds a developer (owner only)"),
        ("dev!unwhitelist <@user>", "Removes a developer (owner only)"),
    ),
    "Messaging commands": (
        ("dev!dm <@user> <message>", "Sends a DM as the bot"),
        ("dev!dmall <message>", "Sends a DM to all non-bot members"),
    ),
}

SLASH_COMMAND_GROUPS: dict[str, tuple[str, ...]] = {
    "Ticket Stat commands": (
        "ticketstats",
        "tickethistory",
    ),
    "Ticket Database commands": (
        "wipestats",
        "wipehistory",
    ),
    "User Permission commands": (
        "maxpermsadd",
        "maxpermsremove",
        "privilegedusers",
    ),
    "Miscellaneous commands": (
        "help",
        "passwordset",
        "logchannelset",
        "summarychannel",
        "summaryfrequency",
    ),
}


def _safe_role_lines(category: str) -> list[str]:
    roles = sorted(set(get_permission_roles_for_category(category)), key=str.casefold)
    if not roles:
        return ["・`No roles configured`"]
    return [f"・`{role_name}`" for role_name in roles]


def _build_required_roles_text() -> str:
    return "\n".join([
        "Role requirements are managed dynamically when permissions are updated.",
        "Privileged users and the server owner are always have maximum permissions.",
        "Note that devs do not automatically have max perms or vice versa.",
        "‎"
    ])

def _build_sections_text() -> str:
    return "\n".join([
        "- Privileged users: Users with maximum permissions, but not necessarily devs",
        "- Developers: Users with access to dev commands, but not max perms per se",
        f"{EMBED_DIVIDER}",
    ])


def _format_concise_roles(
    category: str,
    *,
    guild: discord.Guild | None,
    max_visible: int = 3,
) -> str:
    roles = sorted(set(get_permission_roles_for_category(category)), key=str.casefold)
    if not roles:
        return "`No roles configured`"

    if guild is not None:
        role_by_name = {role_obj.name: role_obj for role_obj in guild.roles}
        roles = sorted(
            roles,
            key=lambda name: (
                role_by_name[name].position if name in role_by_name else -1,
                name.casefold(),
            ),
            reverse=True,
        )

    visible = roles[:max_visible]
    rendered = ", ".join(f"`{name}`" for name in visible)
    remaining = len(roles) - len(visible)
    if remaining > 0:
        rendered = f"{rendered}, +{remaining} more"

    return rendered


# Helper functions to build the content of the embeds
def _build_permissions_text(guild: discord.Guild | None) -> str:
    section_lines = [
        "Current permission-role mapping:\n",
    ]

    for category, label in PERMISSION_ROLE_CATEGORY_LABELS.items():
        section_lines.append(
            f"- **{label}**: {_format_concise_roles(category, guild=guild)}"
        )

    section_lines.append("\nOwner-only actions: `dev!whitelist`, `dev!unwhitelist`")
    section_lines.append(f"{EMBED_DIVIDER}")
    return "\n".join(section_lines)


def _build_command_lookup(tree: app_commands.CommandTree[discord.Client]) -> dict[str, app_commands.Command]:
    command_lookup: dict[str, app_commands.Command] = {}
    for command_obj in tree.get_commands(guild=None):
        command_lookup[command_obj.name] = command_obj
    return command_lookup


def _get_shared_tree() -> app_commands.CommandTree[discord.Client]:
    # Import lazily to avoid module import cycles during startup
    from main.bot import tree

    return tree


def _format_slash_command(command_obj: app_commands.Command) -> str:
    description = command_obj.description.strip() if command_obj.description else "No description"
    return f"・`/{command_obj.name}` - {description}"


def _build_listcommands_embed(tree: app_commands.CommandTree[discord.Client]) -> discord.Embed:
    command_lookup = _build_command_lookup(tree)
    shown_commands: set[str] = set()


    embed = discord.Embed(
        title="Available Bot Commands",
        color=0xb6b6b6
    )

    embed.add_field(name="📋  Standard Commands", value=(
        "Standard commands and general bot utilities.\n"
        "‎\n"
    ), inline=False)

    for group_name, group_commands in SLASH_COMMAND_GROUPS.items():
        lines: list[str] = []
        for command_name in group_commands:
            command_obj = command_lookup.get(command_name)
            if command_obj is None:
                continue
            shown_commands.add(command_name)
            lines.append(_format_slash_command(command_obj))

        if lines:
            embed.add_field(name=group_name, value="\n".join(lines), inline=False)

    uncategorized = [
        _format_slash_command(command_obj)
        for name, command_obj in sorted(command_lookup.items())
        if name not in shown_commands
    ]
    if uncategorized:
        embed.add_field(name="Other slash commands", value="\n".join(uncategorized), inline=False)

    if DEV_COMMAND_GROUPS:
        embed.add_field(name=" ", value=EMBED_DIVIDER, inline=False)
        embed.add_field(
            name="🧩  Developer Commands",
            value=(
                "Developer-prefixed maintenance and development commands.\n"
                "‎\n"
            ),
            inline=False,
        )

        for group_name, group_commands in DEV_COMMAND_GROUPS.items():
            lines = [f"・ `{usage}` - {description}" for usage, description in group_commands]
            embed.add_field(name=group_name, value="\n".join(lines), inline=False)

    embed.add_field(name=" ", value=EMBED_DIVIDER, inline=False)
    embed.set_footer(text="Ticket Assistant | Made by 0bi0")
    return embed


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
        f"{EMBED_DIVIDER}"
    ), inline=False)

    # Second section of the Bot's output
    embed.add_field(name="🛡️  Required Roles", value=_build_required_roles_text(), inline=False)

    # Third section of the Bot's output
    embed.add_field(name="🌐  Sections", value=_build_sections_text(), inline=False)

    embed.set_footer(text="Ticket Assistant | Made by 0bi0")
    return embed


def _build_permissions_embed(guild: discord.Guild | None) -> discord.Embed:
    embed = discord.Embed(
        title="Information regarding Permissions",
        color=0xb6b6b6
    )

    # NOTE: Privileged users will always have max perms regardless
    #       of which roles they have equipped!

    # First section of the Bot's output
    embed.add_field(name="⚙️  Permissions", value=_build_permissions_text(guild), inline=False)

    # Second section of the Bot's output
    embed.add_field(name="📝  Note", value=(
        "Certain users are automatically granted maximum permissions, regardless of their\n"
        "roles. Users can be granted max perms only at the discretion of the server owner.\n"
        f"{EMBED_DIVIDER}"
    ), inline=False)

    # Footer + Send message argument
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
    def __init__(self, tree: app_commands.CommandTree[discord.Client], current_page: str = "help"):
        super().__init__(timeout=180)
        self.tree = tree
        self.current_page = current_page
        self._refresh_menu()

    def _refresh_menu(self):
        self.clear_items()
        self.add_item(CommandNavigationSelect(self.current_page))

    async def navigate_to(self, interaction: discord.Interaction, destination: str):
        self.current_page = destination
        self._refresh_menu()

        if destination == "permissions":
            embed = _build_permissions_embed(interaction.guild)
        elif destination == "listcommands":
            embed = _build_listcommands_embed(self.tree)
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

    shared_tree = _get_shared_tree()
    embed = _build_help_embed()
    try:
        await interaction.followup.send(
            embed=embed,
            view=CommandNavigationView(shared_tree, current_page="help"),
            ephemeral=True,
        )
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

    shared_tree = _get_shared_tree()
    embed = _build_listcommands_embed(shared_tree)
    try:
        await interaction.followup.send(
            embed=embed,
            view=CommandNavigationView(shared_tree, current_page="listcommands"),
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

    shared_tree = _get_shared_tree()
    embed = _build_permissions_embed(interaction.guild)
    try:
        await interaction.followup.send(
            embed=embed,
            view=CommandNavigationView(shared_tree, current_page="permissions"),
            ephemeral=True,
        )
    except discord.NotFound:
        return