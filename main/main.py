# Necessary imports
import asyncio
import discord
from discord import app_commands
import aiosqlite
import time
import os
import atexit
import sys
import io
from datetime import datetime, timedelta
from collections import Counter
from dotenv import load_dotenv


# Windows compatibility
try:
    import msvcrt
except ImportError:
    msvcrt = None


# Linux compatibility
try:
    import fcntl
except ImportError:
    fcntl = None


try:
    import matplotlib  # type: ignore[reportMissingImports]

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore[reportMissingImports]
    from matplotlib.ticker import MaxNLocator  # type: ignore[reportMissingImports]
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


from cogs.permissions import (
    PRIVILEGED_USERS,
    TICKET_CATEGORIES,
    LOG_CHANNEL_ID,
    apply_permission_role_overrides,

    has_stats_permission,
)

from development.dev_auth import refresh_dev_users
from development.maintenance import MAINTENANCE_NOTICE, is_maintenance_enabled, load_maintenance_state_cache
from development.runtime_logs import install_print_hook

from main.command_registry import register_commands
from main.bot import client, tree, TICKETS_BOT_ID
from commands.summary_commands import initialize_summary_reporting


async def _maintenance_interaction_check(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return True

    if interaction.user.id == interaction.guild.owner_id:
        return True

    if not is_maintenance_enabled(interaction.guild.id):
        return True

    if not interaction.response.is_done():
        await interaction.response.send_message(MAINTENANCE_NOTICE, ephemeral=True)
    else:
        await interaction.followup.send(MAINTENANCE_NOTICE, ephemeral=True)
    return False



# Defines paths for database and lock file
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "tickets.db")
LOCK_PATH = os.path.join(BASE_DIR, ".bot.lock")

# Load environment variables from the project root .env file.
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Mirror console output into runtime log buffer for dev panel log viewing.
install_print_hook()



# Single instance enforcement using file locking
def enforce_single_instance() -> None:
    # Prevent running multiple bot instances in the same project directory.
    lock_file = open(LOCK_PATH, "w+")
    try:
        lock_file.write("0")
        lock_file.flush()
        lock_file.seek(0)
        if msvcrt is not None:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            if fcntl is None:
                raise OSError("No supported file locking module available")
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("Another bot instance is already running. Stop it before starting a new one.")
        sys.exit(1)

    # Ensure lock is released on exit
    def _release_lock() -> None:
        try:
            lock_file.seek(0)
            if msvcrt is not None:
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        lock_file.close()

    # Register the cleanup function to release the lock on exit
    atexit.register(_release_lock)



# Enforce single instance at startup (cause sometimes the dumbass bot duplicates user permissions for some god-forsaken reason and I can't do shit to debug that)
enforce_single_instance()

# Register standalone commands in one place.
register_commands(tree)



# Your bot token
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    print("Missing DISCORD_BOT_TOKEN in .env or environment variables.")
    sys.exit(1)



# Sequence for when bot starts
@client.event
async def on_ready():
    activity = discord.CustomActivity(name="Watching the gears turn")
    await client.change_presence(status=discord.Status.online, activity=activity)
    if getattr(client, "_startup_complete", False):
        print(f"Bot reconnected as {client.user}")
        return

    # Flag to prevent multiple on_ready executions during startup (this shit really pisses me off)
    client._startup_complete = True
    client._started_at = int(time.time())

    # Connect ONCE
    client.db = await aiosqlite.connect(DB_PATH)

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

    if "opened_by" not in columns:
        print("Migrating DB: adding opened_by column")
        await client.db.execute("ALTER TABLE tickets ADD COLUMN opened_by INTEGER")

    if "closed_by" not in columns:
        print("Migrating DB: adding closed_by column")
        await client.db.execute("ALTER TABLE tickets ADD COLUMN closed_by INTEGER")

    if "close_reason" not in columns:
        print("Migrating DB: adding close_reason column")
        await client.db.execute("ALTER TABLE tickets ADD COLUMN close_reason TEXT")

    if "transcript_url" not in columns:
        print("Migrating DB: adding transcript_url column")
        await client.db.execute("ALTER TABLE tickets ADD COLUMN transcript_url TEXT")

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

    # Table for developer-prefixed commands (dev!*)
    await client.db.execute("""
        CREATE TABLE IF NOT EXISTS developer_users(
            user_id INTEGER PRIMARY KEY
        )
    """)

    # Table for owner-defined maintenance password.
    await client.db.execute("""
        CREATE TABLE IF NOT EXISTS dev_maintenance_passwords(
            guild_id INTEGER PRIMARY KEY,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            updated_by INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)

    # Table for maintenance enabled/disabled state.
    await client.db.execute("""
        CREATE TABLE IF NOT EXISTS dev_maintenance_state(
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER NOT NULL CHECK(enabled IN (0, 1)),
            updated_by INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)

    # Table for dev-managed permission role overrides
    await client.db.execute("""
        CREATE TABLE IF NOT EXISTS dev_permission_role_overrides(
            category TEXT NOT NULL,
            role_name TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('add', 'remove')),
            PRIMARY KEY(category, role_name)
        )
    """)

    # Cleanup invalid legacy entries
    await client.db.execute("DELETE FROM privileged_users WHERE user_id <= 0")
    await client.db.execute("DELETE FROM developer_users WHERE user_id <= 0")

    # Load privileged users list and clears the in-memory set first to avoid duplicates on reconnects
    PRIVILEGED_USERS.clear()
    cursor = await client.db.execute("SELECT user_id FROM privileged_users")
    rows = await cursor.fetchall()
    for row in rows:
    
        # Adds privileged user IDs to the in-memory set
        PRIVILEGED_USERS.add(row[0])

    # Load DB-backed developer cache (guild owners are implicitly handled at runtime)
    await refresh_dev_users(client.db)

    # Load per-guild maintenance state into runtime cache.
    await load_maintenance_state_cache(client.db)

    # Load DB-backed permission role overrides into runtime permission sets
    cursor = await client.db.execute(
        "SELECT category, role_name, action FROM dev_permission_role_overrides"
    )
    permission_override_rows = await cursor.fetchall()
    apply_permission_role_overrides(permission_override_rows)

    # Table for persisting the ticket log channel
    await client.db.execute("""
        CREATE TABLE IF NOT EXISTS log_channel(
            id INTEGER PRIMARY KEY CHECK(id = 1),
            channel_id INTEGER NOT NULL
        )
    """)

    # Load log channel into memory
    cursor = await client.db.execute("SELECT channel_id FROM log_channel WHERE id = 1")
    row = await cursor.fetchone()
    if row:
        LOG_CHANNEL_ID[0] = row[0]

    # Initialize automated management summary feature state
    await initialize_summary_reporting()

    # discord.py 2.4 in this environment does not expose add_check on CommandTree
    # Assigning interaction_check keeps a global gate for all app commands
    tree.interaction_check = _maintenance_interaction_check

    await client.db.commit()
    await tree.sync()

    login_banner = r"""
========================================================================================================================
  
  ___________.__          __             __          _____                   .__           __                    __    
  \__    ___/|__|  ____  |  | __  ____ _/  |_       /  _  \    ______  ______|__|  _______/  |_ _____     ____ _/  |_  
    |    |   |  |_/ ___\ |  |/ /_/ __ \\   __\     /  /_\  \  /  ___/ /  ___/|  | /  ___/\   __\\__  \   /    \\   __\ 
    |    |   |  |\  \___ |    < \  ___/ |  |      /    |    \ \___ \  \___ \ |  | \___ \  |  |   / __ \_|   |  \|  |   
    |____|   |__| \___  >|__|_ \ \___  >|__|      \____|__  //____  >/____  >|__|/____  > |__|  (____  /|___|  /|__|   
                      \/      \/     \/                   \/      \/      \/          \/             \/      \/        
  
========================================================================================================================
"""
    display_info = r"""
                                                                                                         Version: 1.4.0
                                                                                                         Status: Online
___________________________________________________
"""

    # 💻 CONSOLE OUTPUT: Cool ass banner
    print(login_banner)

    # 💻 CONSOLE OUTPUT: Info about bot
    print(display_info)

    # 💻 CONSOLE OUTPUT: Successful bot startup
    print(f"Bot logged in successfully as {client.user}")
    print()
    print("========================================================================================================================")
    print()



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
# Edit with caution: Rather unstable and can *potentially* cause data loss

# Creates the definition for DB handling
async def run_ticket_stats(interaction: discord.Interaction, days: int, category_key: str | None):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("❌ Server only.", ephemeral=True)
        return

    # Permission check
    if not has_stats_permission(interaction.user):
        await interaction.response.send_message("❌ No permission.", ephemeral=True)
        return

    # Calculates timestamp 'days' ago from current time
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

    # Fetch ticket rows from the database using the query.
    cursor = await client.db.execute(query, params)
    rows = await cursor.fetchall()

    # If no tickets are found, send a message and return early
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

    # Important section for calculation argument names
    first_response_times = []
    handling_times = []
    rep_response_times = []

    # Collects response and handling times for ticket statistics
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

        # Computes staff response times
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

    # Ensures multiple handled tickets on the same day increase one bar
    handled_by_day = Counter()
    for _, _, closed_at, _ in rows:
        if closed_at:
            # Use local date boundaries so same-day handled tickets are grouped as expected
            close_day = datetime.fromtimestamp(closed_at).date()
            handled_by_day[close_day] += 1

    # Always show every day in the requested range, even when count is zero
    start_day = datetime.fromtimestamp(since).date()
    end_day = datetime.now().date()

    # Graph data
    graph_days = []
    graph_counts = []
    cursor_day = start_day
    while cursor_day <= end_day:
        graph_days.append(cursor_day.strftime("%b %d"))
        graph_counts.append(handled_by_day.get(cursor_day, 0))
        cursor_day += timedelta(days=1)


    # Defines the units of measurement
    def fmt(seconds):
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h}h {m}m {s}s"

    # Header for the `/ticketstatistics <category>` command
    description_content = (
        f"# 📊 Ticket Statistics\n"
        f"-# Showing stats for {label} over the past {days} day(s)\n\n"
        f"**- Total Tickets**: `{len(tickets)}`\n"
    )

    # Only adds the breakdown if not filtering by a specific category
    if category_key is None:
        counts = {"General Tickets": 0, "Player-Reports": 0, "Appeals": 0, "Unknown": 0}
        for _, _, _, cat in rows:
            cat = cat or "Unknown"
            counts[cat] = counts.get(cat, 0) + 1

        # Displays the first set of information for tickets
        description_content += (
            f"**- General**: `{counts.get('General Tickets', 0)}`\n"
            f"**- Reports**: `{counts.get('Player-Reports', 0)}`\n"
            f"**- Appeals**: `{counts.get('Appeals', 0)}`\n"
        )

    # Displays the second set of information for tickets
    description_content += (
        f"**- Peak Concurrent**: `{peak_open}`\n"
        f"**- Average Initial Response**: `{fmt(avg_first)}`\n"
        f"**- Average Response Time**: `{fmt(avg_rep_response)}`\n"
        f"**- Average Duration**: `{fmt(avg_handle)}`\n"
        f"**- Handled Tickets**: `{sum(graph_counts)}`"
    )

    embed = discord.Embed(description=description_content,color=discord.Color.from_rgb(182, 182, 182))

    # Following code is executed if matplotlib is available in the current environment
    if MATPLOTLIB_AVAILABLE:
        # Creates a graph image in-memory and attach it to the embed
        fig, ax = plt.subplots(figsize=(9, 3.5))
        fig.patch.set_facecolor("#dcdcdc")
        ax.set_facecolor("#dcdcdc")
        x_positions = list(range(len(graph_days)))
        ax.bar(x_positions, graph_counts, color="#5f7ea5")
        ax.set_title("Handled Tickets Per Day")
        ax.set_ylabel("Handled")
        ax.title.set_color("#1a1a1a")
        ax.yaxis.label.set_color("#1a1a1a")

        # Adjust x-axis ticks based on the number of days to avoid clutter
        if len(graph_days) <= 14:
            tick_step = 1
        elif len(graph_days) <= 45:
            tick_step = 3
        else:
            tick_step = 7

        # Adjust x-axis ticks and labels based on the number of days
        tick_positions = x_positions[::tick_step] if x_positions else []
        tick_labels = graph_days[::tick_step] if graph_days else []
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=35, ha="right")
        ax.tick_params(axis="x", colors="#1f1f1f")
        ax.tick_params(axis="y", colors="#1f1f1f")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(axis="y", linestyle="--", color="#5c5c5c", alpha=0.35)
        fig.tight_layout()

        # Saves the graph to an in-memory buffer and prepares it for Discord upload
        image_buffer = io.BytesIO()
        fig.savefig(image_buffer, format="png", dpi=130)
        plt.close(fig)
        image_buffer.seek(0)

        # Prepares the image file for Discord and sets it in the embed
        chart_file = discord.File(fp=image_buffer, filename="ticketstats_handled.png")
        embed.set_image(url="attachment://ticketstats_handled.png")

        # Sends message
        await interaction.response.send_message(embed=embed, file=chart_file)
        return

    # Fallback in case matplotlib is unavailable in the current environment
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
# Very fucking important command (for obvious reasons)
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



# Import event handlers so their @client.event decorators register (ChatGPT told me to do this, idk man, it's 2AM)
import cogs.events.message_detection
import cogs.events.channel_deletion
import cogs.events.guild_join
import development.dev_commands



async def on_disconnect():
    try:
        print("Attempting to reconnect...")
        await client.connect(reconnect=True)
    except Exception as e:
        print(f"Reconnection failed: {e}")
        await asyncio.sleep(5)



# Runs the bot with the selected token
client.run(TOKEN)