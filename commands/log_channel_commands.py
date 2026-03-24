# Necessary imports
import discord
from discord import app_commands

from cogs.permissions import has_manage_perms_permission, LOG_CHANNEL_ID



# ===| Log channel set command |===
#
# Registers a text channel as the destination for all ticket event logs
# Only privileged users or users with MANAGE_USER_PERMS perms can use this

@app_commands.command(name="logchannelset", description="Set the channel where ticket events are logged")
@app_commands.describe(channel="Channel to send ticket open/close logs to")
async def logchannelset(interaction: discord.Interaction, channel: discord.TextChannel):
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.NotFound:
        return

    # Permission check: Only users with manage perms permission can set the log channel
    if not has_manage_perms_permission(interaction.user):
        try:
            await interaction.followup.send("❌ No permission to set the log channel.", ephemeral=True)
        except discord.NotFound:
            return
        return

    await interaction.client.db.execute(
        "INSERT OR REPLACE INTO log_channel(id, channel_id) VALUES (1, ?)",
        (channel.id,)
    )
    await interaction.client.db.commit()

    LOG_CHANNEL_ID[0] = channel.id

    try:
        await interaction.followup.send(
            f"✅ Ticket log channel set to {channel.mention}.",
            ephemeral=True
        )
    except discord.NotFound:
        return

    # 💻 CONSOLE OUTPUT: Set ticket logging channel
    log_line = f"[📋 LOG CHANNEL SET] {interaction.user} set log channel to #{channel.name} ({channel.id})"
    print(log_line)
    print("-" * len(log_line))