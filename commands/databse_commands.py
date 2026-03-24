# Necessary imports
import discord
from discord import app_commands
from discord import client
import time

from cogs.permissions import has_database_permission



# ===| Stat wipe command (USE WITH CAUTION) |===
#
# The wipe command can be useful for databse resets
# and for other miscellaneous reasons

@app_commands.command(name="wipestats", description="Permanently delete ticket data from the selected period")
@app_commands.describe(days="Wipe ticket data from the last this many days (e.g. 30)")
async def wipestats(interaction: discord.Interaction, days: int):
    # DataBase Permission check
    if not has_database_permission(interaction.user):
        await interaction.response.send_message("❌ You do not have permission to wipe data.", ephemeral=True)
        return

    if days <= 0:
        await interaction.response.send_message("❌ Days must be greater than 0.", ephemeral=True)
        return

    # Calculates the start timestamp for the requested period
    period_start = int(time.time()) - (days * 86400)

    try:
        count_cursor = await interaction.client.db.execute("""
            SELECT COUNT(*)
            FROM tickets
            WHERE opened_at >= ?
        """, (period_start,))
        count_row = await count_cursor.fetchone()
        deleted_count = count_row[0] if count_row else 0

        if deleted_count == 0:
            await interaction.response.send_message(
                f"ℹ️ No tickets found in the last **{days}** days. Nothing was deleted.",
                ephemeral=True,
            )
            return

        await interaction.client.db.execute("""
            DELETE FROM messages
            WHERE channel_id IN (
                SELECT channel_id
                FROM tickets
                WHERE opened_at >= ?
            )
        """, (period_start,))

        await interaction.client.db.execute("""
            DELETE FROM tickets
            WHERE opened_at >= ?
        """, (period_start,))

        # Logs the wipe action in the DB
        await interaction.client.db.execute("""
            INSERT INTO wipe_log(wiped_by, cutoff_days, deleted_tickets, timestamp)
            VALUES (?, ?, ?, ?)
        """, (
            interaction.user.id,
            days,
            deleted_count,
            int(time.time())
        ))

        await interaction.client.db.commit()

        # Output when a DB wipe is successfully completed 
        await interaction.response.send_message(
            f"✅ Database Wipe Successful!\n"
            f"Removed **{deleted_count}** tickets and associated messages "
            f"from the last **{days}** days.",
            ephemeral=True
        )

        # 💻 CONSOLE OUTPUT: Successfull DB wipe
        print(f"🧹[DB WIPE]: {interaction.user} cleared data older than {days} days.")

    # Exception argument in the event that a DB wipe can't be executed
    except Exception as e:
        await interaction.response.send_message(f"❌ Database error: {e}", ephemeral=True)



# ===| Wipe history command |===
#
# Shows recent DB wipes (simple audit log)

# Creates the command and sets its permissions
@app_commands.command(name="wipehistory", description="Show recent database wipe history")
async def wipehistory(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.NotFound:
        return

    # Permission check
    if not has_database_permission(interaction.user):
        try:
            await interaction.followup.send("❌ You do not have permission to view wipe history.", ephemeral=True)
        except discord.NotFound:
            return
        return

    cursor = await interaction.client.db.execute("""
        SELECT wiped_by, cutoff_days, deleted_tickets, timestamp
        FROM wipe_log
        ORDER BY timestamp DESC
        LIMIT 10
    """)
    rows = await cursor.fetchall()

    # If not DB wipes can be found, the following arguments will be sent as output
    if not rows:
        try:
            await interaction.followup.send("ℹ️ No wipe history found.", ephemeral=True)
        except discord.NotFound:
            return
        return

    lines = []
    for wiped_by, cutoff_days, deleted_tickets, ts in rows:
        user = interaction.guild.get_member(wiped_by)
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

        lines.append(
            f"・<@{wiped_by}> wiped ≥ **{cutoff_days}d** | "
            f"Deleted: **{deleted_tickets}** | `{time_str}`"
        )

    # Displays the most recent DB wipes
    embed = discord.Embed(
        title="Database Wipe History",
        description="\n".join(lines),
        color=discord.Color.orange()
    )

    # Footer + Send message argument
    embed.set_footer(text="Audit log | Last 10 wipes")
    try:
        await interaction.followup.send(embed=embed, ephemeral=True)
    except discord.NotFound:
        return

    log_line_wipe = f"[📋 WIPE HISTORY] {interaction.user} viewed the database wipe history"
    print(log_line_wipe)
    print("-" * len(log_line_wipe))