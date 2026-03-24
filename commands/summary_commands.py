# Necessary imports
import time
from collections import Counter
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import tasks

from cogs.permissions import has_manage_perms_permission
from main.bot import client



# Global variable to track if the summary loop has been started, ensuring only one instance runs
_SUMMARY_LOOP_STARTED = False


# Helper function to format seconds into a human-readable string
def _format_seconds(seconds: float) -> str:
    minutes, seconds_value = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {seconds_value}s"


# Parses a period string like "12h" or "1d" into minutes, returns None for invalid formats
def _parse_period_to_minutes(period: str) -> int | None:
    normalized = (period or "").strip().lower()
    if len(normalized) < 2:
        return None

    number_part = normalized[:-1]
    unit = normalized[-1]

    if not number_part.isdigit():
        return None

    amount = int(number_part)
    if amount <= 0:
        return None

    if unit == "h":
        return amount * 60
    if unit == "d":
        return amount * 24 * 60
    return None


# Formats the frequency in minutes back into a human-readable string for messages
def _format_frequency_minutes(minutes: int) -> str:
    if minutes % (24 * 60) == 0:
        return f"{minutes // (24 * 60)}d"
    if minutes % 60 == 0:
        return f"{minutes // 60}h"
    return f"{minutes}m"


# Initializes the database table for summary settings and starts the background loop if not already running
async def initialize_summary_reporting() -> None:
    global _SUMMARY_LOOP_STARTED

    await client.db.execute(
        """
        CREATE TABLE IF NOT EXISTS summary_settings(
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER NOT NULL,
            frequency_minutes INTEGER NOT NULL CHECK(frequency_minutes > 0),
            last_sent_at INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    if not _SUMMARY_LOOP_STARTED:
        summary_report_loop.start()
        _SUMMARY_LOOP_STARTED = True


async def _fetch_scoped_rows(since: int, guild: discord.Guild) -> list[tuple[int, int, int | None, str | None]]:
    cursor = await client.db.execute(
        """
        SELECT channel_id, opened_at, closed_at, category
        FROM tickets
        WHERE opened_at >= ?
        """,
        (since,),
    )
    rows = await cursor.fetchall()

    # Keep summary stats tied to the guild where the report is posted.
    scoped_rows = [
        (row[0], row[1], row[2], row[3])
        for row in rows
        if guild.get_channel(row[0]) is not None
    ]
    return scoped_rows


# Builds the summary payload data based on the scoped ticket rows
async def _build_summary_payload(
    rows: list[tuple[int, int, int | None, str | None]],
    since: int,
) -> dict[str, object]:
    tickets = [(opened_at, closed_at) for _, opened_at, closed_at, _ in rows]

    events: list[tuple[int, int]] = []
    for opened_at, closed_at in tickets:
        events.append((opened_at, 1))
        if closed_at is not None:
            events.append((closed_at, -1))

    events.sort(key=lambda event: (event[0], -event[1]))

    current_open = 0
    peak_open = 0
    for _, delta in events:
        current_open += delta
        if current_open > peak_open:
            peak_open = current_open

    first_response_times: list[int] = []
    handling_times: list[int] = []
    rep_response_times: list[int] = []

    for channel_id, opened_at, closed_at, _ in rows:
        cursor = await client.db.execute(
            """
            SELECT timestamp
            FROM messages
            WHERE channel_id = ? AND is_staff = 1 AND timestamp >= ?
            ORDER BY timestamp ASC
            LIMIT 1
            """,
            (channel_id, opened_at),
        )
        first_staff_row = await cursor.fetchone()
        if first_staff_row:
            first_response_times.append(first_staff_row[0] - opened_at)

        if closed_at:
            handling_times.append(closed_at - opened_at)

        cursor = await client.db.execute(
            """
            SELECT timestamp
            FROM messages
            WHERE channel_id = ? AND is_staff = 1
            ORDER BY timestamp ASC
            """,
            (channel_id,),
        )
        staff_rows = await cursor.fetchall()

        if len(staff_rows) >= 2:
            staff_timestamps = [staff_row[0] for staff_row in staff_rows]
            for index in range(1, len(staff_timestamps)):
                delta = staff_timestamps[index] - staff_timestamps[index - 1]
                if delta > 0:
                    rep_response_times.append(delta)

    avg_first = sum(first_response_times) / len(first_response_times) if first_response_times else 0.0
    avg_handle = sum(handling_times) / len(handling_times) if handling_times else 0.0
    avg_rep_response = sum(rep_response_times) / len(rep_response_times) if rep_response_times else 0.0

    handled_by_day = Counter()
    for _, _, closed_at, _ in rows:
        if closed_at:
            handled_day = datetime.fromtimestamp(closed_at).date()
            handled_by_day[handled_day] += 1

    start_day = datetime.fromtimestamp(since).date()
    end_day = datetime.now().date()
    graph_counts: list[int] = []
    cursor_day = start_day
    while cursor_day <= end_day:
        graph_counts.append(handled_by_day.get(cursor_day, 0))
        cursor_day += timedelta(days=1)

    counts = {
        "General Tickets": 0,
        "Player-Reports": 0,
        "Appeals": 0,
        "Unknown": 0,
    }
    for _, _, _, category_name in rows:
        normalized = category_name or "Unknown"
        counts[normalized] = counts.get(normalized, 0) + 1

    return {
        "total_tickets": len(tickets),
        "peak_open": peak_open,
        "avg_first": avg_first,
        "avg_handle": avg_handle,
        "avg_rep_response": avg_rep_response,
        "handled_total": sum(graph_counts),
        "category_counts": counts,
    }


# Builds the summary message text based on the payload data
def _build_summary_message(
    guild: discord.Guild,
    frequency_minutes: int,
    payload: dict[str, object] | None,
) -> str:
    timestamp_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"Management ticket summary for {guild.name}",
        f"Generated at: {timestamp_text}",
        f"Window: last {_format_frequency_minutes(frequency_minutes)}",
    ]

    if payload is None:
        lines.append("No ticket updates were recorded in this window.")
        return "\n".join(lines)

    counts = payload["category_counts"]
    lines.extend(
        [
            f"Total tickets opened: {int(payload['total_tickets'])}",
            (
                "By category: "
                f"General {counts.get('General Tickets', 0)} | "
                f"Reports {counts.get('Player-Reports', 0)} | "
                f"Appeals {counts.get('Appeals', 0)}"
            ),
            f"Handled tickets: {int(payload['handled_total'])}",
            f"Peak concurrent open: {int(payload['peak_open'])}",
            f"Average initial response: {_format_seconds(float(payload['avg_first']))}",
            f"Average staff response: {_format_seconds(float(payload['avg_rep_response']))}",
            f"Average handling duration: {_format_seconds(float(payload['avg_handle']))}",
        ]
    )
    return "\n".join(lines)


# Background loop to post summary reports
@tasks.loop(minutes=1)
async def summary_report_loop() -> None:
    if not hasattr(client, "db"):
        return

    now_ts = int(time.time())
    cursor = await client.db.execute(
        "SELECT guild_id, channel_id, frequency_minutes, last_sent_at FROM summary_settings"
    )
    settings_rows = await cursor.fetchall()

    if not settings_rows:
        return

    should_commit = False

    for guild_id, channel_id, frequency_minutes, last_sent_at in settings_rows:
        frequency_minutes = int(frequency_minutes)
        last_sent_at = int(last_sent_at)

        if now_ts - last_sent_at < frequency_minutes * 60:
            continue

        guild = client.get_guild(int(guild_id))
        if guild is None:
            await client.db.execute(
                "UPDATE summary_settings SET last_sent_at = ? WHERE guild_id = ?",
                (now_ts, guild_id),
            )
            should_commit = True
            continue

        channel = guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            await client.db.execute(
                "UPDATE summary_settings SET last_sent_at = ? WHERE guild_id = ?",
                (now_ts, guild_id),
            )
            should_commit = True
            continue

        since = now_ts - (frequency_minutes * 60)
        scoped_rows = await _fetch_scoped_rows(since, guild)
        payload = await _build_summary_payload(scoped_rows, since) if scoped_rows else None
        message_text = _build_summary_message(guild, frequency_minutes, payload)

        try:
            await channel.send(message_text)
        except (discord.Forbidden, discord.HTTPException):
            pass

        await client.db.execute(
            "UPDATE summary_settings SET last_sent_at = ? WHERE guild_id = ?",
            (now_ts, guild_id),
        )
        should_commit = True

    if should_commit:
        await client.db.commit()


@summary_report_loop.before_loop
async def _before_summary_loop() -> None:
    await client.wait_until_ready()



# Summary channel command
@app_commands.command(name="summarychannel", description="Set the channel for automated management summaries")
@app_commands.describe(channel="Channel where plain-text ticket summaries should be posted")
async def summarychannel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("❌ Server only.", ephemeral=True)
        return

    if not has_manage_perms_permission(interaction.user):
        await interaction.response.send_message("❌ No permission to configure summary reports.", ephemeral=True)
        return

    cursor = await interaction.client.db.execute(
        "SELECT frequency_minutes FROM summary_settings WHERE guild_id = ?",
        (interaction.guild.id,),
    )
    existing = await cursor.fetchone()
    frequency_minutes = int(existing[0]) if existing else 24 * 60

    await interaction.client.db.execute(
        """
        INSERT OR REPLACE INTO summary_settings(guild_id, channel_id, frequency_minutes, last_sent_at)
        VALUES (?, ?, ?, ?)
        """,
        (interaction.guild.id, channel.id, frequency_minutes, int(time.time())),
    )
    await interaction.client.db.commit()

    await interaction.response.send_message(
        f"✅ Summary channel set to {channel.mention}. Frequency: `{_format_frequency_minutes(frequency_minutes)}`.",
        ephemeral=True,
    )



# Summary frequency command
@app_commands.command(name="summaryfrequency", description="Set how often automated management summaries are posted")
@app_commands.describe(period="Frequency like 12h or 1d")
async def summaryfrequency(interaction: discord.Interaction, period: str):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("❌ Server only.", ephemeral=True)
        return

    if not has_manage_perms_permission(interaction.user):
        await interaction.response.send_message("❌ No permission to configure summary reports.", ephemeral=True)
        return

    frequency_minutes = _parse_period_to_minutes(period)
    if frequency_minutes is None:
        await interaction.response.send_message("❌ Invalid period format, use values like 12h or 1d.", ephemeral=True)
        return

    cursor = await interaction.client.db.execute(
        "SELECT channel_id FROM summary_settings WHERE guild_id = ?",
        (interaction.guild.id,),
    )
    existing = await cursor.fetchone()
    if not existing:
        await interaction.response.send_message("❌ Set a summary channel first with `/summarychannel`.", ephemeral=True)
        return

    await interaction.client.db.execute(
        """
        UPDATE summary_settings
        SET frequency_minutes = ?, last_sent_at = ?
        WHERE guild_id = ?
        """,
        (frequency_minutes, int(time.time()), interaction.guild.id),
    )
    await interaction.client.db.commit()

    channel = interaction.guild.get_channel(int(existing[0]))
    channel_mention = channel.mention if isinstance(channel, discord.TextChannel) else f"<#{existing[0]}>"

    await interaction.response.send_message(
        f"✅ Summary frequency set to `{_format_frequency_minutes(frequency_minutes)}` for {channel_mention}.",
        ephemeral=True,
    )