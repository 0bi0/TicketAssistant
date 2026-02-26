# Necessary imports
import discord
from discord import app_commands
from discord import client
import time

from cogs.permissions import (
    has_database_permission,
)



# ===| Stat wipe command (USE WITH CAUTION) |===
#
# The wipe command can be useful for databse resets
# and for other miscellaneous reasons

@app_commands.command(name="wipestats", description="Permanently delete ticket data from a specific period")
@app_commands.describe(days="Wipe data older than this many days (e.g. 30d)")
async def wipestats(interaction: discord.Interaction, days: int):
    # DataBase Permission check
    if not has_database_permission(interaction.user):
        await interaction.response.send_message("❌ You do not have permission to wipe data.", ephemeral=True)
        return

    # Calculates the cutoff timestamp
    cutoff_time = int(time.time()) - (days * 86400)

    try:
        await interaction.client.db.execute("""
            DELETE FROM messages 
            WHERE timestamp <= ?
        """, (cutoff_time,))

        cursor = await interaction.client.db.execute("""
            DELETE FROM tickets 
            WHERE opened_at <= ?
        """, (cutoff_time,))
        
        deleted_count = cursor.rowcount

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
            f"older than **{days}** days.",
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
    # Permission check
    if not has_database_permission(interaction.user):
        await interaction.response.send_message("❌ You do not have permission to view wipe history.", ephemeral=True)
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
        await interaction.response.send_message("ℹ️ No wipe history found.", ephemeral=True)
        return

    lines = []
    for wiped_by, cutoff_days, deleted_tickets, ts in rows:
        user = interaction.guild.get_member(wiped_by)
        user_name = user.display_name if user else f"User ID {wiped_by}"
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

        lines.append(
            f"・**{user_name}** wiped ≥ **{cutoff_days}d** | "
            f"Deleted: **{deleted_tickets}** | `{time_str}`"
        )

    # Displays the most recent DB wipes
    embed = discord.Embed(
        title="🧹 Database Wipe History",
        description="\n".join(lines),
        color=discord.Color.orange()
    )

    # Footer + Send message argument
    embed.set_footer(text="Audit log | Last 10 wipes")
    await interaction.response.send_message(embed=embed, ephemeral=True)