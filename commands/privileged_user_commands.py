# Necessary imports
import discord
from discord import app_commands
from discord import client

from cogs.permissions import (
    PRIVILEGED_USERS,

    has_manage_perms_permission,
)




# ===| Max perms add command |===
#
# Adds max permissions to a user

# Creates the command and sets its permissions
@app_commands.command(name="maxpermsadd", description="Give a user max permissions")
@app_commands.describe(user="User to grant max perms")
async def maxpermsadd(interaction: discord.Interaction, user: discord.Member):
    # Only Matt and privileged users can use this
    if not has_manage_perms_permission(interaction.user):
        await interaction.response.send_message("❌ No permission to add max perms.", ephemeral=True)
        return

    # Exception argument in case a user neither has the required roles, nor is a privileged user
    if user.id in PRIVILEGED_USERS:
        await interaction.response.send_message(f"⚠️ {user.mention} already has max perms.", ephemeral=True)
        return

    # Adds max perms to the stated user
    PRIVILEGED_USERS.add(user.id)
    await interaction.client.db.execute("INSERT OR IGNORE INTO privileged_users(user_id) VALUES (?)", (user.id,))
    await interaction.client.db.commit()

    # Confirms that that the permissions have been added to the stated user
    await interaction.response.send_message(f"✅ {user.mention} now has max permissions.", ephemeral=True)

    # 💻 CONSOLE OUTPUT: Added max perms to a user
    print(f"🟢 [MAX PERMS ADD] {interaction.user} granted max perms to {user}")



# ===| Max perms remove command |===
#
# Removes max permissions from a user

# Creates the command and sets its permissions
@app_commands.command(name="maxpermsremove", description="Remove max permissions from a user")
@app_commands.describe(user="User to revoke max perms")
async def maxpermsremove(interaction: discord.Interaction, user: discord.Member):
    # Only Matt and privileged users can use this
    if not has_manage_perms_permission(interaction.user):
        await interaction.response.send_message("❌ No permission to remove max perms.", ephemeral=True)
        return

    # Exception argument in case a user neither has the required roles, nor is a privileged user
    if user.id not in PRIVILEGED_USERS:
        await interaction.response.send_message(f"⚠️ {user.mention} does not have max perms.", ephemeral=True)
        return

    # Removes max perms from the stated user + Blocks user from removing the permissions from themselves
    if user.id == interaction.user.id:
        await interaction.response.send_message("You cannot remove max perms from yourself!", ephemeral=True)
        return
    else:
        PRIVILEGED_USERS.remove(user.id)
        interaction.client.db.execute("DELETE FROM privileged_users WHERE user_id=?", (user.id,))
        await interaction.client.db.commit()

    # Confirms that that the permissions have been removed from the stated user
    await interaction.response.send_message(f"✅ {user.mention} max permissions removed.", ephemeral=True)

    # 💻 CONSOLE OUTPUT: Removed max perms from a user
    print(f"🔴 [MAX PERMS REMOVE] {interaction.user} removed max perms from {user}")



# ===| Privileged users list command |===
#
# Displays all users with max permissions

@app_commands.command(name="privilegedusers", description="List all users with max permissions")
async def privilegedusers(interaction: discord.Interaction):

    # Permission check
    if not has_manage_perms_permission(interaction.user):
        await interaction.response.send_message(
            "❌ You do not have permission to view privileged users.",
            ephemeral=True
        )
        return

    # If no privileged users exist, this will be displayed
    if not PRIVILEGED_USERS:
        await interaction.response.send_message(
            "ℹ️ No privileged users are currently registered.",
            ephemeral=True
        )
        return

    lines = []

    # If a user has max perms, they will be able to execute this cimmand
    for user_id in sorted(PRIVILEGED_USERS):
        member = interaction.guild.get_member(user_id)

        if member:
            lines.append(f"・{member.mention} — `{user_id}`")
        else:
            lines.append(f"・<@{user_id}> — `{user_id}` (Not in Server)")

    embed = discord.Embed(
        title="👑 Privileged Users (Max Permissions)",
        description="\n".join(lines),
        color=discord.Color.gold()
    )

    # Footer + Send message argument
    embed.set_footer(text=f"Total: {len(PRIVILEGED_USERS)} users")
    await interaction.response.send_message(embed=embed, ephemeral=True)

    # 💻 CONSOLE OUTPUT
    print(f"👑 [PRIV USERS VIEW] {interaction.user} viewed privileged users list")