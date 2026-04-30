# Necessary imports
import discord
from discord import app_commands

from cogs.permissions import (
    PRIVILEGED_USERS,
    has_manage_perms_permission,
)
from development.maintenance import set_maintenance_password


# Helper function to refresh the in-memory privileged user cache from the database
async def _refresh_privileged_users_from_db(interaction: discord.Interaction) -> None:
    """Refresh in-memory privileged user cache from DB to avoid stale state."""
    cursor = await interaction.client.db.execute(
        "SELECT user_id FROM privileged_users WHERE user_id > 0"
    )
    rows = await cursor.fetchall()

    PRIVILEGED_USERS.clear()
    for row in rows:
        PRIVILEGED_USERS.add(row[0])




# ===| Max perms add command |===
#
# Adds max permissions to a user

@app_commands.command(name="maxpermsadd", description="Give a user max permissions")
@app_commands.describe(user="User to grant max perms")
async def maxpermsadd(interaction: discord.Interaction, user: discord.User):
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.NotFound:
        return

    # Refresh privileged users from DB to ensure only the latest state is used
    await _refresh_privileged_users_from_db(interaction)

    if not interaction.guild:
        try:
            await interaction.followup.send("❌ This command can only be used in a server.", ephemeral=True)
        except discord.NotFound:
            return
        return

    # Only server owner can use this command
    if interaction.user.id != interaction.guild.owner_id:
        try:
            await interaction.followup.send("❌ Only the server owner can add max perms.", ephemeral=True)
        except discord.NotFound:
            return
        return

    guild_owner_id = interaction.guild.owner_id if interaction.guild else None
    if user.id in PRIVILEGED_USERS or user.id == guild_owner_id:
        try:
            await interaction.followup.send(f"⚠️ {user.mention} already has max perms.", ephemeral=True)
        except discord.NotFound:
            return
        return

    await interaction.client.db.execute(
        "INSERT OR IGNORE INTO privileged_users(user_id) VALUES (?)",
        (user.id,),
    )
    await interaction.client.db.commit()
    await _refresh_privileged_users_from_db(interaction)

    try:
        await interaction.followup.send(f"✅ {user.mention} now has max permissions.", ephemeral=True)
    except discord.NotFound:
        return

    log_line_add = f"[🟢 MAX PERMS ADD] {interaction.user} granted max perms to {user}"
    print(log_line_add)
    print("-" * len(log_line_add))



# ===| Max perms remove command |===
#
# Removes max permissions from a user

@app_commands.command(name="maxpermsremove", description="Remove max permissions from a user")
@app_commands.describe(user="User to revoke max perms")
async def maxpermsremove(interaction: discord.Interaction, user: discord.User):
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.NotFound:
        return

    await _refresh_privileged_users_from_db(interaction)

    if not interaction.guild:
        try:
            await interaction.followup.send("❌ This command can only be used in a server.", ephemeral=True)
        except discord.NotFound:
            return
        return

    # Only server owner can use command
    if interaction.user.id != interaction.guild.owner_id:
        try:
            await interaction.followup.send("❌ Only the server owner can remove max perms.", ephemeral=True)
        except discord.NotFound:
            return
        return

    guild_owner_id = interaction.guild.owner_id if interaction.guild else None
    if user.id == guild_owner_id:
        try:
            await interaction.followup.send(
                "⚠️ Server owners always have max perms and cannot be removed.",
                ephemeral=True,
            )
        except discord.NotFound:
            return
        return

    if user.id not in PRIVILEGED_USERS:
        try:
            await interaction.followup.send(f"⚠️ {user.mention} does not have max perms.", ephemeral=True)
        except discord.NotFound:
            return
        return

    if user.id == interaction.user.id:
        try:
            await interaction.followup.send("You cannot remove max perms from yourself!", ephemeral=True)
        except discord.NotFound:
            return
        return

    await interaction.client.db.execute("DELETE FROM privileged_users WHERE user_id=?", (user.id,))
    await interaction.client.db.commit()
    await _refresh_privileged_users_from_db(interaction)

    try:
        await interaction.followup.send(f"✅ {user.mention} max permissions removed.", ephemeral=True)
    except discord.NotFound:
        return

    log_line_remove = f"[🔴 MAX PERMS REMOVE] {interaction.user} removed max perms from {user}"
    print(log_line_remove)
    print("-" * len(log_line_remove))



# ===| Privileged users list command |===
#
# Displays all users with max permissions

@app_commands.command(name="privilegedusers", description="List all users with max permissions")
async def privilegedusers(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.NotFound:
        return

    await _refresh_privileged_users_from_db(interaction)

    if not has_manage_perms_permission(interaction.user):
        try:
            await interaction.followup.send(
                "❌ You do not have permission to view privileged users.",
                ephemeral=True,
            )
        except discord.NotFound:
            return
        return

    if not interaction.guild:
        try:
            await interaction.followup.send("❌ This command can only be used in a server.", ephemeral=True)
        except discord.NotFound:
            return
        return

    visible_privileged_user_ids = set(PRIVILEGED_USERS)
    visible_privileged_user_ids.add(interaction.guild.owner_id)

    if not visible_privileged_user_ids:
        try:
            await interaction.followup.send(
                "ℹ️ No privileged users are currently registered.",
                ephemeral=True,
            )
        except discord.NotFound:
            return
        return

    lines = []
    for user_id in sorted(visible_privileged_user_ids):
        member = interaction.guild.get_member(user_id)
        suffix = " (Server Owner)" if user_id == interaction.guild.owner_id else ""
        if member:
            lines.append(f"- {member.mention} - `{user_id}`{suffix}")
        else:
            lines.append(f"- <@{user_id}> - `{user_id}` (Not in Server){suffix}")

    embed = discord.Embed(
        title="Privileged Users (Max Permissions)",
        description="\n".join(lines),
        color=discord.Color.gold(),
    )
    embed.set_footer(text=f"Total: {len(visible_privileged_user_ids)} users")

    try:
        await interaction.followup.send(embed=embed, ephemeral=True)
    except discord.NotFound:
        return

    # 💻 CONSOLE OUTPUT: View privileged users list
    log_line_priv = f"[👑 PRIV USERS VIEW] {interaction.user} viewed privileged users list"
    print(log_line_priv)
    print("-" * len(log_line_priv))


class PasswordSetModal(discord.ui.Modal, title="Set Maintenance Password"):
    password = discord.ui.TextInput(
        label="New password",
        placeholder="Enter a strong password",
        style=discord.TextStyle.short,
        min_length=8,
        max_length=128,
        required=True,
    )
    confirm_password = discord.ui.TextInput(
        label="Confirm password",
        placeholder="Re-enter the same password",
        style=discord.TextStyle.short,
        min_length=8,
        max_length=128,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ Only the server owner can set this password.", ephemeral=True)
            return

        if self.password.value != self.confirm_password.value:
            await interaction.response.send_message("❌ Passwords do not match.", ephemeral=True)
            return

        await set_maintenance_password(
            interaction.client.db,
            guild_id=interaction.guild.id,
            password=self.password.value,
            updated_by=interaction.user.id,
        )

        await interaction.response.send_message("✅ Maintenance password has been updated.", ephemeral=True)

        log_line_password = f"[🔐 MAINT PASSWORD SET] {interaction.user} updated maintenance password in guild {interaction.guild.id}"
        print("-" * len(log_line_password))


@app_commands.command(name="passwordset", description="Set maintenance password (owner only)")
async def passwordset(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
        return

    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Only the server owner can set this password.", ephemeral=True)
        return

    await interaction.response.send_modal(PasswordSetModal())