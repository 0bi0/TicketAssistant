# Necessary imports
import discord

from cogs.permissions import (
    PERMISSION_ROLE_CATEGORY_LABELS,
    add_permission_role_to_category,
    get_default_permission_roles_for_category,
    get_permission_roles_for_category,
    remove_permission_role_from_category,
)

from development.maintenance import MAINTENANCE_NOTICE, is_maintenance_enabled
from development.dev.state import ACTIVE_PERMS_PANELS
from main.bot import client



# ===| Embed and role resolution helpers |===
#
# Build and maintain the runtime permissions panel presentation

def build_perms_embed(guild: discord.Guild, category: str) -> discord.Embed:
    category_label = PERMISSION_ROLE_CATEGORY_LABELS.get(category, category)
    roles = get_permission_roles_for_category(category)

    role_by_name = {role_obj.name: role_obj for role_obj in guild.roles}
    ordered_roles = sorted(
        roles,
        key=lambda name: (
            role_by_name[name].position if name in role_by_name else -1,
            name.casefold(),
        ),
        reverse=True,
    )

    lines = "\n".join(f"・`{name}`" for name in ordered_roles) if ordered_roles else "No roles configured."

    embed = discord.Embed(
        title="Developer Permissions Panel",
        description="Manage role-based permission lists from the dashboard.",
        color=discord.Color.from_rgb(182, 182, 182),
    )
    embed.add_field(name="Category", value=f"`{category}` - {category_label}", inline=False)
    embed.add_field(name="Current Roles", value=lines, inline=False)
    embed.set_footer(text="Changes persist in database")
    return embed



# Helper to resolve a role from user input
def resolve_role_from_input(guild: discord.Guild, value: str) -> discord.Role | None:
    raw = value.strip()
    if not raw:
        return None

    if raw.startswith("<@&") and raw.endswith(">"):
        raw = raw[3:-1]

    if raw.isdigit():
        role_obj = guild.get_role(int(raw))
        if role_obj:
            return role_obj

    lowered = raw.casefold()
    for role_obj in guild.roles:
        if role_obj.name.casefold() == lowered:
            return role_obj

    return None


# Persists per-category role additions/removals relative to defaults
async def persist_permission_overrides_for_category(category: str) -> None:
    if not hasattr(client, "db"):
        return

    default_values = get_default_permission_roles_for_category(category)
    current_values = set(get_permission_roles_for_category(category))

    additions = sorted(current_values - default_values)
    removals = sorted(default_values - current_values)

    await client.db.execute(
        "DELETE FROM dev_permission_role_overrides WHERE category = ?",
        (category,),
    )

    for role_name in additions:
        await client.db.execute(
            "INSERT INTO dev_permission_role_overrides(category, role_name, action) VALUES (?, ?, 'add')",
            (category, role_name),
        )

    for role_name in removals:
        await client.db.execute(
            "INSERT INTO dev_permission_role_overrides(category, role_name, action) VALUES (?, ?, 'remove')",
            (category, role_name),
        )

    await client.db.commit()



# ===| UI Components |===
#
# Select menu for choosing permission categories, with dynamic options and 
# state management to reflect current selection and update the embed accordingly
#
class PermissionCategorySelect(discord.ui.Select):
    def __init__(self, current_category: str):
        options = [
            discord.SelectOption(
                label=label,
                value=key,
                default=(key == current_category),
            )
            for key, label in PERMISSION_ROLE_CATEGORY_LABELS.items()
        ]
        super().__init__(
            placeholder="Choose a permission category...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    # Handles category selection changes by updating the embed with the new category's role list and refreshing the select menu to reflect the current selection
    async def callback(self, interaction: discord.Interaction):
        parent_view = self.view
        if not isinstance(parent_view, PermissionsPanelView):
            return

        if parent_view.maintenance_blocked(interaction):
            await interaction.response.send_message(MAINTENANCE_NOTICE, ephemeral=True)
            return

        if not parent_view.is_allowed(interaction):
            await interaction.response.send_message("Only the panel creator can use this panel.", ephemeral=True)
            return

        selected = self.values[0]
        parent_view.selected_category = selected
        parent_view.refresh_select()
        updated_embed = build_perms_embed(interaction.guild, selected) if interaction.guild else None
        await interaction.response.edit_message(embed=updated_embed, view=parent_view)


# Modal for adding/removing roles from categories, with shared logic for both actions
class PermissionRoleModal(discord.ui.Modal):
    def __init__(self, panel_view: "PermissionsPanelView", action: str):
        super().__init__(title=f"{action.title()} Role")
        self.panel_view = panel_view
        self.action = action
        self.role_input = discord.ui.TextInput(
            label="Role mention, ID, or exact name",
            placeholder="@Administrator or 1234567890 or Administrator",
            required=True,
            max_length=100,
        )
        self.add_item(self.role_input)

    # Handles both add and remove role actions based on initialization parameter
    async def on_submit(self, interaction: discord.Interaction):
        if self.panel_view.maintenance_blocked(interaction):
            await interaction.response.send_message(MAINTENANCE_NOTICE, ephemeral=True)
            return

        if not self.panel_view.is_allowed(interaction):
            await interaction.response.send_message("Only the panel creator can use this panel.", ephemeral=True)
            return

        if not interaction.guild:
            await interaction.response.send_message("This control can only run inside a server.", ephemeral=True)
            return

        category = self.panel_view.selected_category
        role_obj = resolve_role_from_input(interaction.guild, self.role_input.value)
        if role_obj is None:
            await interaction.response.send_message("Role not found. Use mention, role ID, or exact role name.", ephemeral=True)
            return

        if self.action == "add":
            changed = add_permission_role_to_category(category, role_obj.name)
        else:
            changed = remove_permission_role_from_category(category, role_obj.name)

        if not changed:
            await interaction.response.send_message("No changes applied for that role.", ephemeral=True)
            return

        await persist_permission_overrides_for_category(category)

        # Log the change with a clear message indicating the action, role, category, and user responsible
        action_label = "ADD" if self.action == "add" else "REMOVE"
        verb = "added" if self.action == "add" else "removed"
        log_line = f"[🧰 PERMS {action_label}] {interaction.user} {verb} role '{role_obj.name}' in category '{category}'"
        print(log_line)
        print("-" * len(log_line))

        # Refresh the select menu to reflect the updated state and update the embed with the new role list
        self.panel_view.refresh_select()
        updated_embed = build_perms_embed(interaction.guild, category)
        await interaction.response.edit_message(embed=updated_embed, view=self.panel_view)



# Main panel view for permission handling
class PermissionsPanelView(discord.ui.View):
    def __init__(self, guild_id: int, creator_id: int, selected_category: str = "stats"):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.creator_id = creator_id
        self.selected_category = selected_category
        self.refresh_select()

    # Checks if the interaction is from the original panel creator
    def is_allowed(self, interaction: discord.Interaction) -> bool:
        return bool(
            interaction.guild
            and interaction.guild.id == self.guild_id
            and isinstance(interaction.user, discord.Member)
            and interaction.user.id == self.creator_id
        )

    # If maintenance mode is enabled, restrict access to owner only
    def maintenance_blocked(self, interaction: discord.Interaction) -> bool:
        return bool(
            interaction.guild
            and is_maintenance_enabled(interaction.guild.id)
            and interaction.user.id != interaction.guild.owner_id
        )

    # Rebuilds panel controls so current state is updated
    def refresh_select(self) -> None:
        self.clear_items()
        self.add_item(PermissionCategorySelect(self.selected_category))
        self.add_item(self.add_role_button)
        self.add_item(self.remove_role_button)
        self.add_item(self.exit_session_button)



    # Exit button
    @discord.ui.button(label="Exit Session", style=discord.ButtonStyle.secondary, row=1)
    async def exit_session_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if self.maintenance_blocked(interaction):
            await interaction.response.send_message(MAINTENANCE_NOTICE, ephemeral=True)
            return

        if not self.is_allowed(interaction):
            await interaction.response.send_message("Only the panel creator can use this panel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        ACTIVE_PERMS_PANELS.pop(self.guild_id, None)

        try:
            await interaction.message.delete()
        except (discord.Forbidden, discord.HTTPException, AttributeError):
            await interaction.followup.send("Session lock released, but I could not delete the permissions panel message.", ephemeral=True)
            return

        await interaction.followup.send("Permissions session closed.", ephemeral=True)



    # Add role button
    @discord.ui.button(label="Add Role", style=discord.ButtonStyle.success, row=1)
    async def add_role_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if self.maintenance_blocked(interaction):
            await interaction.response.send_message(MAINTENANCE_NOTICE, ephemeral=True)
            return

        if not self.is_allowed(interaction):
            await interaction.response.send_message("Only the panel creator can use this panel.", ephemeral=True)
            return

        await interaction.response.send_modal(PermissionRoleModal(self, "add"))



    # Remove role button
    @discord.ui.button(label="Remove Role", style=discord.ButtonStyle.danger, row=1)
    async def remove_role_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if self.maintenance_blocked(interaction):
            await interaction.response.send_message(MAINTENANCE_NOTICE, ephemeral=True)
            return

        if not self.is_allowed(interaction):
            await interaction.response.send_message("Only the panel creator can use this panel.", ephemeral=True)
            return

        await interaction.response.send_modal(PermissionRoleModal(self, "remove"))