# Necessary imports
import discord
from discord import app_commands
import aiosqlite
import importlib
import time
import os


from cogs.permissions import (
    PRIVILEGED_USERS,
    TICKET_CATEGORIES,

    has_stats_permission,
)


# Loads commands from files
from commands.databse_commands import wipestats, wipehistory
from commands.miscellaneous_commands import help, viewpermissions
from commands.privileged_user_commands import maxpermsadd, maxpermsremove, privilegedusers


# Enables necessary Discord intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# Initialize Discord client and command tree
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Imports (adds) commands from their perspective file to main.py
tree.add_command(wipestats)
tree.add_command(wipehistory)
tree.add_command(help)
tree.add_command(viewpermissions)
tree.add_command(maxpermsadd)
tree.add_command(maxpermsremove)
tree.add_command(privilegedusers)



# Your bot token
TOKEN = "your_token_goes_here"

# TicketsV2 UserID
TICKETS_BOT_ID = 1325579039888511056
# NOTE: You can replace this ID with any other Discord Ticket bot's ID if you
#       wish to use another bot, rather than the TicketsV2 



# Sequence for when bot starts
@client.event
async def on_ready():
    
    commands_path = os.path.join(os.path.dirname(__file__), "..", "commands")

    for filename in os.listdir(commands_path):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"commands.{filename[:-3]}"
            importlib.import_module(module_name)
            client.db = await aiosqlite.connect("tickets.db")

    # Base table
    await client.db.execute("""
        CREATE TABLE IF NOT EXISTS tickets(
            channel_id INTEGER PRIMARY KEY,
            opened_at INTEGER,
            closed_at INTEGER
        )
    """)

    # Table for database wipe audit log
    await client.db.execute("""
        CREATE TABLE IF NOT EXISTS wipe_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wiped_by INTEGER,
            cutoff_days INTEGER,
            deleted_tickets INTEGER,
            timestamp INTEGER
        )
    """)

    # Ensure category column exists (migration-safe)
    cursor = await client.db.execute("PRAGMA table_info(tickets)")
    columns = [row[1] for row in await cursor.fetchall()]

    if "category" not in columns:

        # 💻 CONSOLE OUTPUT: DB migration
        print("Migrating DB: adding category column")

        await client.db.execute("ALTER TABLE tickets ADD COLUMN category TEXT")

    await client.db.execute("""
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER,
            author_id INTEGER,
            is_staff INTEGER,
            timestamp INTEGER
        )
    """)

    # Table for privileged users (max perms)
    await client.db.execute("""
        CREATE TABLE IF NOT EXISTS privileged_users(
            user_id INTEGER PRIMARY KEY
        )
    """)

    # Load IDs into memory
    cursor = await client.db.execute("SELECT user_id FROM privileged_users")
    rows = await cursor.fetchall()
    for row in rows:
        PRIVILEGED_USERS.add(row[0])

    await client.db.commit()
    await tree.sync()

    # 💻 CONSOLE OUTPUT: Successful bot startup
    print(f"Bot logged in successfully as {client.user}")



# Creates the definition related to the total, peak concurrent amount of tickets
def compute_peak_concurrent(tickets: list[tuple[int, int | None]]) -> int:
    """
    tickets = [(opened_at, closed_at), ...]
    Returns max number of simultaneously open tickets.
    """
    events: list[tuple[int, int]] = []

    for opened_at, closed_at in tickets:
        events.append((opened_at, +1))
        if closed_at is not None:
            events.append((closed_at, -1))

    # Sort by time, with closes processed before opens at the same timestamp
    events.sort(key=lambda x: (x[0], -x[1]))

    current = 0
    peak = 0

    for _, delta in events:
        current += delta
        if current > peak:
            peak = current

    return peak


# DataBase-related section of code
#
# DO NOT TOUCH

# Creates the definition for DB handling
async def run_ticket_stats(interaction: discord.Interaction, days: int, category_key: str | None):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("❌ Server only.", ephemeral=True)
        return

    # Permission check
    if not has_stats_permission(interaction.user):
        await interaction.response.send_message("❌ No permission.", ephemeral=True)
        return

    since = int(time.time()) - days * 86400

    if category_key is None:
        query = """
            SELECT channel_id, opened_at, closed_at, category
            FROM tickets
            WHERE opened_at >= ?
        """
        params = (since,)
        label = "all categories"
    else:
        category_name = TICKET_CATEGORIES[category_key]
        query = """
            SELECT channel_id, opened_at, closed_at, category
            FROM tickets
            WHERE opened_at >= ?
              AND category = ?
        """
        params = (since, category_name)
        label = category_name

    cursor = await client.db.execute(query, params)
    rows = await cursor.fetchall()

    if not rows:
        await interaction.response.send_message(
            f"No **{label}** tickets in that period.",
            ephemeral=True
        )
        return

    # Defines the `ticket` value, must detect them opening and closing in order to do so though
    tickets = [(opened_at, closed_at) for _, opened_at, closed_at, _ in rows]

    # Computes statistics
    peak_open = compute_peak_concurrent(tickets)

    first_response_times = []
    handling_times = []
    rep_response_times = []

    for channel_id, opened_at, closed_at, _ in rows:
        cursor = await client.db.execute("""
            SELECT timestamp
            FROM messages
            WHERE channel_id=? AND is_staff=1 AND timestamp>=?
            ORDER BY timestamp ASC LIMIT 1
        """, (channel_id, opened_at))

        row = await cursor.fetchone()
        if row:
            first_response_times.append(row[0] - opened_at)

        if closed_at:
            handling_times.append(closed_at - opened_at)

        
        # Average response times between representatives
        cursor = await client.db.execute("""
            SELECT timestamp
            FROM messages
            WHERE channel_id=? AND is_staff=1
            ORDER BY timestamp ASC
        """, (channel_id,))

        staff_rows = await cursor.fetchall()

        if len(staff_rows) >= 2:
            staff_timestamps = [row[0] for row in staff_rows]

            for i in range(1, len(staff_timestamps)):
                delta = staff_timestamps[i] - staff_timestamps[i - 1]
                if delta > 0:
                    rep_response_times.append(delta)


    # Average value calculations
    avg_first = sum(first_response_times) / len(first_response_times) if first_response_times else 0
    avg_handle = sum(handling_times) / len(handling_times) if handling_times else 0
    avg_rep_response = (sum(rep_response_times) / len(rep_response_times) if rep_response_times else 0)


    # Defines the units of measurement
    def fmt(seconds):
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h}h {m}m {s}s"

    # Header for the `/ticketstatistics <category>` command
    description_content = (
        f"# 📊 Ticket Statistics\n"
        f"-# Showing stats for {label} over the past {days} day(s)\n\n"
        f"**•ㅤTotal Tickets**: `{len(tickets)}`\n"
    )

    # Only adds the breakdown if not filtering by a specific category
    if category_key is None:
        counts = {"General Tickets": 0, "Player-Reports": 0, "Appeals": 0, "Unknown": 0}
        for _, _, _, cat in rows:
            cat = cat or "Unknown"
            counts[cat] = counts.get(cat, 0) + 1

        # Displays the first set of information for tickets
        description_content += (
            f"**•ㅤGeneral**: `{counts.get('General Tickets', 0)}`\n"
            f"**•ㅤReports**: `{counts.get('Player-Reports', 0)}`\n"
            f"**•ㅤAppeals**: `{counts.get('Appeals', 0)}`\n"
        )

    # Displays the second set of information for tickets
    description_content += (
        f"**•ㅤPeak Concurrent**: `{peak_open}`\n"
        f"**•ㅤAverage Initial Response**: `{fmt(avg_first)}`\n"
        f"**•ㅤAverage Response Time**: `{fmt(avg_rep_response)}`\n"
        f"**•ㅤAverage Duration**: `{fmt(avg_handle)}`"
    )

    embed = discord.Embed(description=description_content,color=discord.Color.from_rgb(0, 189, 247))

    # Sends message
    await interaction.response.send_message(embed=embed)


# ===| Slash command group |===
#
# Main command plus subcommands for `/ticketstats <category>`
# everything related to them is handled here
#
@tree.command(
    name="ticketstats",
    description="Show ticket statistics",
)
@app_commands.describe(
    category="Category: all, appeals, general, or reports",
    period="Period like 12h (hours) or 14d (days)",
)
@app_commands.choices(
    category=[
        app_commands.Choice(name="All", value="all"),
        app_commands.Choice(name="Appeals", value="appeals"),
        app_commands.Choice(name="General", value="general"),
        app_commands.Choice(name="Reports", value="reports"),
    ]
)
async def ticketstats(
    interaction: discord.Interaction,
    category: app_commands.Choice[str],
    period: str
):
    # Normalize category
    cat = category.value.lower()

    # Parse period
    try:
        num = int(period[:-1])
        unit = period[-1].lower()
        days = num / 24 if unit == "h" else num if unit == "d" else None
        if days is None:
            await interaction.response.send_message("❌ Invalid period unit, use 'h' or 'd'.", ephemeral=True)
            return
    except:
        await interaction.response.send_message("❌ Invalid period format, e.g., 12h or 14d.", ephemeral=True)
        return

    # Map category to key for function
    cat_key = None if cat == "all" else cat

    await run_ticket_stats(interaction, days, cat_key)



# Runs the bot with the selected token
client.run(TOKEN)