# Necessary imports
import discord
from discord import app_commands

from cogs.permissions import PRIVILEGED_USERS, has_manage_perms_permission


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

    await _refresh_privileged_users_from_db(interaction)

    # Only owner/privileged users can use this
    if not has_manage_perms_permission(interaction.user):
        try:
            await interaction.followup.send("❌ No permission to add max perms.", ephemeral=True)
        except discord.NotFound:
            return
        return

    if user.id in PRIVILEGED_USERS:
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

    print(f"[MAX PERMS ADD] {interaction.user} granted max perms to {user}")



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

    if not has_manage_perms_permission(interaction.user):
        try:
            await interaction.followup.send("❌ No permission to remove max perms.", ephemeral=True)
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

    print(f"[MAX PERMS REMOVE] {interaction.user} removed max perms from {user}")



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

    if not PRIVILEGED_USERS:
        try:
            await interaction.followup.send(
                "ℹ️ No privileged users are currently registered.",
                ephemeral=True,
            )
        except discord.NotFound:
            return
        return

    lines = []
    for user_id in sorted(PRIVILEGED_USERS):
        member = interaction.guild.get_member(user_id)
        if member:
            lines.append(f"- {member.mention} - `{user_id}`")
        else:
            lines.append(f"- <@{user_id}> - `{user_id}` (Not in Server)")

    embed = discord.Embed(
        title="Privileged Users (Max Permissions)",
        description="\n".join(lines),
        color=discord.Color.gold(),
    )
    embed.set_footer(text=f"Total: {len(PRIVILEGED_USERS)} users")

    try:
        await interaction.followup.send(embed=embed, ephemeral=True)
    except discord.NotFound:
        return

    print(f"[👑 PRIV USERS VIEW] {interaction.user} viewed privileged users list")