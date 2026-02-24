#  TrackingBot/
#  │
#  ├── README.md                                         − □ ✕
#  │
#  │   "Ticket Assistant" is a simple Python bot that tracks 
#  │   ticket activity to ensure that the Management Team is
#  │   up-to-date with all of the latest updates regarding
#  │   tickets' situation. Licensed under the MIT License.
#  │
#  │   Not the best code I've written, but it gets the
#  │   job done, so I'm not going to complain!
#  │
#  │   Project status:
#  │          v.1.0.0: 24/01/2026 | Initial release
#  │          v.1.0.1: 27/01/2026 | Added priv. users
#  │
#  │
#  ├── permissions.txt                                  − □ ✕
#  │
#  │   Permission to alter the following code for usage
#  │   on PvPHub is granted to 0bi0 (project owner), MattMX
#  │   (Owner of PvPHub), DevBram (System-Admin), and
#  │   OutDev (System-Admin).
#  │
#  │
#  ├── main/
#  │   ├── main.py
#  │   └── tickets.db
#  │
#  └── LICENSE.txt                                                               − □ ✕
#
#      MIT License
#      Copyright (c) 2026 0bi0
#
#      Permission is hereby granted, free of charge, to any person obtaining a copy
#      of this software and associated documentation files (the "Software"), to deal
#      in the Software without restriction, including without limitation the rights
#      to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#      copies of the Software, and to permit persons to whom the Software is
#      furnished to do so, subject to the following conditions:
#
#      The above copyright notice and this permission notice shall be included in all
#      copies or substantial portions of the Software.
#
#      THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#      IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#      FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#      AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#      LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#      OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#      SOFTWARE.



# Necessary imports
from contextlib import nullcontext
from operator import call
import discord
from discord import app_commands
import aiosqlite
import time
import os



# Bot token
TOKEN = ("MTQ2NTA2NzE3MzQyMzg3NDA0OA.GbkYam.6E3fiJZF2hdTOccqO4kHKMgmzmpVkAbDPGNu4w")

# TicketsV2 UserID
TICKETS_BOT_ID = 1325579039888511056

# User roles that are registered as Support Representatives
SUPPORT_ROLES = {
    "Admin Permissions",
    "Owner",
    "System-Admin",
    "Administrator",
    "Sr. Mod",
    "Mod",
    "Support"
}

# Roles allowed to execute the command `/ticketstats <category>`
STATS_ALLOWED_ROLES = [
    "Admin Permissions",
    "Owner",
    "System-Admin",
    "Administrator",
    "General Tickets Manager",
    "Reports Manager",
    "Appeals Manager"
]

# Users allowed to wipe the databse and view its audit log
DATABASE_PERMS = [
    "Admin Permissions",
    "Owner",
    "System-Admin"
]

# Users allowed to add/remove users to/from the max perms list
MANAGE_USER_PERMS = [
    "Owner"
]

# Users with max perms (bypasses role requirements)
PRIVILEGED_USERS = {
    312693889582759938,   # Matt
    574958028651233281,   # Bram
    849335062444769290,   # OutDev
    1037375706600062996,  # 0bi0     # Please don't remove my perms, thanks <3
}

# Ticket categories (pretty self-explanatory)
TICKET_CATEGORIES = {
    "appeals": "Appeals",
    "general": "General Tickets",
    "reports": "Player-Reports"
}



# Enables necessary Discord intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# I do not need to explain what this does
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)



# Sequence for when bot starts
@client.event
async def on_ready():
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

    # 💻 CONSOLE OUTPUT: Successfull bot startup
    print(f"Bot logged in successfully as {client.user}")


# Detection for when a ticket is closed (*see attached note)
@client.event
async def on_guild_channel_delete(channel):
    now = int(time.time())
    await client.db.execute(
        "UPDATE tickets SET closed_at=? WHERE channel_id=? AND closed_at IS NULL",
        (now, channel.id)
    )
    await client.db.commit()

    # 💻 CONSOLE OUTPUT: Closed ticket
    print(f"🗑️  Channel Deleted - Ticket Marked Closed: {channel.id}")

    # NOTE: The only flaw in this bot is the fact that, in order to account for tickets closing,
    #       it simply detects wehther a channel has been deleted or not, thus resulting in its
    #       stats becoming bloated if too many channels, which are not tickets, get deleted.
    #       While this is an unrealistic outcome, it should still be noted that this bot is
    #       flawed and subject to be improved in the future.



# Permission checks

# Determines if someone is “staff” for message logging purposes
def is_staff(member: discord.Member) -> bool:
    if member.id in PRIVILEGED_USERS:
        return True
    return any(role.name in SUPPORT_ROLES for role in member.roles)

# Users who are able to view ticket stats
def has_stats_permission(member: discord.Member) -> bool:
    if member.id in PRIVILEGED_USERS:
        return True
    return any(role.name in STATS_ALLOWED_ROLES for role in member.roles)

# Users who can wipe the databse and view the wipe log
def has_database_permission(member: discord.Member) -> bool:
    if member.id in PRIVILEGED_USERS:
        return True
    return any(role.name in DATABASE_PERMS for role in member.roles)

# Users who are allowed to add/remove max perms to/from other users
def has_manage_perms_permission(member: discord.Member) -> bool:
    if member.id in PRIVILEGED_USERS:
        return True
    return any (role.name in MANAGE_USER_PERMS for role in member.roles)

# Defines what is considered to be a ticket category
def get_ticket_category(channel: discord.TextChannel) -> str | None:
    category = getattr(channel, "category", None)
    return category.name if category else None



# Creates the definition related to ticket-opening
@client.event
async def on_message(message: discord.Message):
    now = int(time.time())

    # Log messages that happen inside ticket channels
    if message.guild and isinstance(message.channel, discord.TextChannel):

        # Only logs messages for channels that are known tickets
        cursor = await client.db.execute(
            "SELECT 1 FROM tickets WHERE channel_id=?",
            (message.channel.id,)
        )
        is_ticket = await cursor.fetchone()

        if is_ticket:
            staff_flag = 1 if (not message.author.bot and is_staff(message.author)) else 0

            await client.db.execute(
                """
                INSERT INTO messages(channel_id, author_id, is_staff, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (
                    message.channel.id,
                    message.author.id,
                    staff_flag,
                    now
                )
            )
            await client.db.commit()

    # Safe DM category logging
    category_name = getattr(message.channel, "category", None)
    category_name = category_name.name if category_name else None

    if message.author.bot:
        print(
            "[BOT MSG]",
            "author_id=", message.author.id,
            "channel=", message.channel.id,
            "embeds=", len(message.embeds),
            "category=", category_name
        )

    # Ticket opening detection
    if message.author.bot and message.author.id == TICKETS_BOT_ID and message.embeds:
        embed = message.embeds[0]
        text_blob = (embed.title or "") + " " + (embed.description or "")

        OPEN_MARKERS = [
            "what is your username",
            "please describe your issue",
            "what server is this happening on"
        ]

        if any(marker in text_blob.lower() for marker in OPEN_MARKERS):
            cursor = await client.db.execute(
                "SELECT 1 FROM tickets WHERE channel_id=?",
                (message.channel.id,)
            )
            exists = await cursor.fetchone()

            if not exists:
                category_name = get_ticket_category(message.channel)

                await client.db.execute(
                    "INSERT INTO tickets(channel_id, category, opened_at, closed_at) VALUES (?, ?, ?, NULL)",
                    (message.channel.id, category_name, now)
                )
                await client.db.commit()

                # 💻 CONSOLE OUTPUT: Ticket opened
                print("🎫 Ticket OPEN:", message.channel.id, "| category:", category_name)



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
        label = "All Categories"
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
    embed = discord.Embed(
        title="Ticket Statistics",
        description=f"{label} | Past {days} day(s)",
        color=discord.Color.blue()
    )

    breakdown_text = ""
    if category_key is None:
        counts = {"General Tickets": 0, "Player-Reports": 0, "Appeals": 0, "Unknown": 0}
        for _, _, _, cat in rows:
            cat = cat or "Unknown"
            counts[cat] = counts.get(cat, 0) + 1

        # Displays the first set of information for tickets
        breakdown_text = (
            f"・General: {counts.get('General Tickets', 0)}\n"
            f"・Reports: {counts.get('Player-Reports', 0)}\n"
            f"・Appeals: {counts.get('Appeals', 0)}\n"
            "–––––––––––––––––––––––––––––––––––\n"
        )

    # Displays the second set of information for tickets
    general_stats_value = (
        "–––––––––––––––––––––––––––––––––––\n"
        f"・Total Tickets: {len(tickets)}\n"
        + breakdown_text +
        f"・Peak Concurrent: {peak_open}\n"
        f"・Avg. First Response: {fmt(avg_first)}\n"
        f"・Avg. Staff Response Time: {fmt(avg_rep_response)}\n"
        f"・Avg. Handling Time: {fmt(avg_handle)}\n"
        "––––––––––––––––––––––––––––––––––"
    )

    # Footer + Send message argument
    embed.add_field(name="📊 Statistics Breakdown", value=general_stats_value, inline=False)
    await interaction.response.send_message(embed=embed)



# ===| Slash command group |===
#
# Main command plus subcommands for `/ticketstats <category>`
# everything related to them is handled here
#
ticketstats = app_commands.Group(
    name="ticketstats",
    description="Show ticket statistics"
)
tree.add_command(ticketstats)


# `/ticketstats <appeals>`
#
# Displays information for the selected time period
# for the appeal category of tickets
#
@ticketstats.command(name="appeals", description="Stats for Appeal tickets")
@app_commands.describe(days="How many days back to include")
async def ticketstats_appeals(interaction: discord.Interaction, days: int):
    await run_ticket_stats(interaction, days, "appeals")


# `/ticketstats <general>`
#
# Displays information for the selected time period
# for the general category of tickets
#
@ticketstats.command(name="general", description="Stats for General tickets")
@app_commands.describe(days="How many days back to include")
async def ticketstats_general(interaction: discord.Interaction, days: int):
    await run_ticket_stats(interaction, days, "general")


# `/ticketstats <reports>`
#
# Displays information for the selected time period
# for the report category of tickets
#
@ticketstats.command(name="reports", description="Stats for Report tickets")
@app_commands.describe(days="How many days back to include")
async def ticketstats_reports(interaction: discord.Interaction, days: int):
    await run_ticket_stats(interaction, days, "reports")


# `/ticketstats <all>`
#
# Displays information for the selected time period
# for all of the ticket categories
#
@ticketstats.command(name="all", description="Stats for all ticket categories")
@app_commands.describe(days="How many days back to include")
async def ticketstats_all(interaction: discord.Interaction, days: int):
    await run_ticket_stats(interaction, days, None)



# ===| Max perms add command |===
#
# Adds max permissions to a user

# Creates the command and sets its permissions
@tree.command(name="maxpermsadd", description="Give a user max permissions")
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
    await client.db.execute("INSERT OR IGNORE INTO privileged_users(user_id) VALUES (?)", (user.id,))
    await client.db.commit()

    # Confirms that that the permissions have been added to the stated user
    await interaction.response.send_message(f"✅ {user.mention} now has max permissions.", ephemeral=True)

    # 💻 CONSOLE OUTPUT: Added max perms to a user
    print(f"🟢 [MAX PERMS ADD] {interaction.user} granted max perms to {user}")



# ===| Max perms remove command |===
#
# Removes max permissions from a user

# Creates the command and sets its permissions
@tree.command(name="maxpermsremove", description="Remove max permissions from a user")
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
        await client.db.execute("DELETE FROM privileged_users WHERE user_id=?", (user.id,))
        await client.db.commit()

    # Confirms that that the permissions have been removed from the stated user
    await interaction.response.send_message(f"✅ {user.mention} max permissions removed.", ephemeral=True)

    # 💻 CONSOLE OUTPUT: Removed max perms from a user
    print(f"🔴 [MAX PERMS REMOVE] {interaction.user} removed max perms from {user}")



# ===| Privileged users list command |===
#
# Displays all users with max permissions

@tree.command(name="privilegedusers", description="List all users with max permissions")
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



# ===| Stat wipe command (USE WITH CAUTION) |===
#
# The wipe command can be useful for databse resets
# and for other miscellaneous reasons

# Creates the command and sets its permissions
@tree.command(name="wipestats", description="Permanently delete ticket data from a specific period")
@app_commands.describe(days="Wipe data older than this many days (e.g. 30d)")
async def wipestats(interaction: discord.Interaction, days: int):
    # DataBase Permission check
    if not has_database_permission(interaction.user):
        await interaction.response.send_message("❌ You do not have permission to wipe data.", ephemeral=True)
        return

    # Calculates the cutoff timestamp
    cutoff_time = int(time.time()) - (days * 86400)

    try:
        await client.db.execute("""
            DELETE FROM messages 
            WHERE timestamp >= ?
        """, (cutoff_time,))

        cursor = await client.db.execute("""
            DELETE FROM tickets 
            WHERE opened_at >= ?
        """, (cutoff_time,))
        
        deleted_count = cursor.rowcount

        # Logs the wipe action in the DB
        await client.db.execute("""
            INSERT INTO wipe_log(wiped_by, cutoff_days, deleted_tickets, timestamp)
            VALUES (?, ?, ?, ?)
        """, (
            interaction.user.id,
            days,
            deleted_count,
            int(time.time())
        ))

        await client.db.commit()

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
@tree.command(name="wipehistory", description="Show recent database wipe history")
async def wipehistory(interaction: discord.Interaction):
    # Permission check
    if not has_database_permission(interaction.user):
        await interaction.response.send_message("❌ You do not have permission to view wipe history.", ephemeral=True)
        return

    cursor = await client.db.execute("""
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



# ===| Help command |===
#
# A generic help command that displays information
# about the bot and its features

# Creates the command
@tree.command(name="help", description="General assistance regarding this bot")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Ticket Management Bot",
        color=0x00ffcc
    )

    # First section of the Bot's output
    embed.add_field(name="📰  Information", value=(
        "The 'Ticket Assistant' is a simple Python bot that tracks ticket activity in order to\n"
        "ensure that the Management Team is up-to-date with all of the latest updates\n" 
        "regarding the tickets' situation.\n"
        "––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––"
    ), inline=False)

    # Second section of the Bot's output
    embed.add_field(name="🛡️  Required Roles", value=(
        "In order to interact with the bot, you need to either hold one of the following\n"
        "positions, or be a user with max permissions (see note in `/viewpermissions`).\n"
        "・`Owner`\n"
        "・`System-Admin`\n"
        "・`Administrator`\n"
        "・`Appeals Manager`\n"
        "・`Reports Manager`\n"
        "・`General Tickets Manager`\n"
        "––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––"
    ), inline=False)

    # Third section of the Bot's output
    embed.add_field(name="📋  Commands", value=(
        "All executable commands can be found in the list below.\n"
        "\n"
        "Ticket Stat commands:\n"
        "・`/ticketstats all <days>` - Shows stats for all ticket categories in last X days\n"
        "・`/ticketstats <category> <days>` - Shows stats for the specified category\n"
        "Ticket DataBase commands:\n"
        "・`/wipestats` - Wipes the database of all information (System-Admin+)\n"
        "・`/wipehistory` - Brings up the audit log of the most recent DB wipes\n"
        "User Permission commands:\n"
        "・`/maxpermsadd <user>` - Adds max permissions to the specified user\n"
        "・`/maxpermsremove <user>` - Removes max permissions from specified user\n"
        "・`/privilegedusers` - Displays all users with maximum permissions\n"
        "Miscellaneous commands:\n"
        "・`/viewpermissions` - Lists all of the permissions that each roles has\n"
        "・`/help` - General help about the bot and the features it provides\n"
        "––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––"
    ), inline=False)

    # Footer + Send message argument
    embed.set_footer(text="PvPHub | Made by 0bi0")
    await interaction.response.send_message(embed=embed, ephemeral=True)



# ===| Permissions command |===
#
# Displays the permissions of each role

# Creates the command
@tree.command(name="viewpermissions", description="Information regarding perms of each role")
async def perms_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Information regarding Permissions",
        color=0x00ffcc
    )

    # NOTE: Privileged users will always have max perms regardless
    #       of which roles they have equipped!

    # First section of the Bot's output
    embed.add_field(name="⚙️  Permissions", value=(
        "・Owner - `/ticketstats`, `/maxpermsadd`, `/wipestats`, `/wipehistory`\n"
        "・Sys-Admins - `/ticketstats`, `/wipestats`, `/wipehistory`\n"
        "・Administrators - `/ticketstats`\n"
        "・Ticket Managers - `/ticketstats`\n"
        "––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––\n"
    ), inline=False)

    # Second section of the Bot's output
    embed.add_field(name="📝  Note", value=(
        "Certain users are automatically granted maximum permissions, regardless of their\n"
        "roles. Users can be granted max perms only at the discretion of the server owner.\n"
        "––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––"
    ), inline=False)

    # Footer + Send message argument
    embed.set_footer(text="PvPHub | Made by 0bi0")
    await interaction.response.send_message(embed=embed, ephemeral=True)

        

# Runs the bot with the selected token
client.run("MTQ2NTA2NzE3MzQyMzg3NDA0OA.GbkYam.6E3fiJZF2hdTOccqO4kHKMgmzmpVkAbDPGNu4w")