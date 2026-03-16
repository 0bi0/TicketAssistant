# Necessary imports
import re
import time
import discord
from datetime import datetime, timezone

from main.bot import client
from cogs.permissions import LOG_CHANNEL_ID


TRANSCRIPT_BASE_URL = "https://dashboard.tickets.bot/manage/{guild_id}/transcripts/view/{transcript_id}"


# Formats a duration in seconds into a human-readable string (e.g. "1d 4h 32m")
def _format_elapsed(seconds: int) -> str:
    parts = []
    d, remainder = divmod(seconds, 86400)
    h, remainder = divmod(remainder, 3600)
    m, _ = divmod(remainder, 60)
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    return " ".join(parts) if parts else "<1m"


# Builds transcript URL; falls back to channel_id as transcript_id if no ticket number exists
def _build_transcript_url(guild_id: int, channel_name: str, channel_id: int) -> str:
    channel_suffix_match = re.search(r"(\d+)$", channel_name)
    transcript_id = int(channel_suffix_match.group(1)) if channel_suffix_match else channel_id
    return TRANSCRIPT_BASE_URL.format(guild_id=guild_id, transcript_id=transcript_id)


# Detection for when a ticket is closed (*see attached note)
@client.event
async def on_guild_channel_delete(channel):
    now = int(time.time())
    transcript_url = _build_transcript_url(channel.guild.id, channel.name, channel.id)

    # Fetch ticket details before the update so we can include them in the log embed
    cursor = await client.db.execute(
        "SELECT category, opened_at, opened_by, closed_by, close_reason FROM tickets WHERE channel_id=? AND closed_at IS NULL",
        (channel.id,)
    )
    ticket_row = await cursor.fetchone()

    cursor = await client.db.execute(
        """
        UPDATE tickets
        SET
            closed_at=?,
            transcript_url=COALESCE(transcript_url, ?)
        WHERE channel_id=? AND closed_at IS NULL
        """,
        (now, transcript_url, channel.id)
    )
    await client.db.commit()

    # 💻 CONSOLE OUTPUT: Closed ticket
    close_log = f"🗑️  Channel Deleted - Ticket Marked Closed: {channel.id}"
    print(close_log)
    print("-" * len(close_log))

    # Send log embed to the configured log channel (only when the channel was a tracked ticket)
    if cursor.rowcount > 0 and LOG_CHANNEL_ID[0]:
        log_channel = client.get_channel(LOG_CHANNEL_ID[0])
        if isinstance(log_channel, discord.TextChannel):
            category_name  = ticket_row[0] if ticket_row else None
            opened_at      = ticket_row[1] if ticket_row else None
            opened_by_id   = ticket_row[2] if ticket_row else None
            closed_by_id   = ticket_row[3] if ticket_row else None
            close_reason   = ticket_row[4] if ticket_row else None

            # Fallback: when close embed parsing misses the user ID, try guild audit logs.
            if not closed_by_id:
                try:
                    async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=8):
                        target = getattr(entry, "target", None)
                        user = getattr(entry, "user", None)
                        if getattr(target, "id", None) == channel.id and user and not getattr(user, "bot", False):
                            closed_by_id = user.id
                            break
                except (discord.Forbidden, discord.HTTPException, AttributeError):
                    pass

            elapsed_str = _format_elapsed(now - opened_at) if opened_at else "Unknown"

            msg_cursor = await client.db.execute(
                "SELECT COUNT(*) FROM messages WHERE channel_id=?",
                (channel.id,)
            )
            msg_row = await msg_cursor.fetchone()
            msg_count_str = str(msg_row[0]) if msg_row else "0"
            closed_by_value = f"<@{closed_by_id}>" if closed_by_id else "Not detected"
            reason_value = close_reason if close_reason else "Not provided"
            transcript_url = _build_transcript_url(channel.guild.id, channel.name, channel.id)

            embed = discord.Embed(
                title="Ticket Closed",
                color=0xed4245,
                timestamp=datetime.fromtimestamp(now, tz=timezone.utc)
            )
            embed.add_field(
                name="Details",
                value=(
                    f"- <:category:1483140351798542466> Category: {category_name or 'Unknown'}\n"
                    f"- <:transcript:1483131530825043988> Transcript: [View Transcript]({transcript_url})\n"
                    f"- <:elapsedtime:1483111487097798840> Time Elapsed: {elapsed_str}\n"
                    f"- <:messages:1483134423720395026> Messages Sent: {msg_count_str}\n"
                    # f"- <:closereason:1483131905154093056> Reason: {reason_value}\n"
                    f"- <:close:1483107264838766602> Closed By: {closed_by_value}\n"
                    f"—------------------------------------------"
                ),
                inline=False
            )
            try:
                await log_channel.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException):
                pass

    # NOTE: The only flaw in this bot is the fact that, in order to account for tickets closing,
    #       it simply detects wehther a channel has been deleted or not, thus resulting in its
    #       stats becoming bloated if too many channels, which are not tickets, get deleted.
    #       While this is an unrealistic outcome, it should still be noted that this bot is
    #       flawed and subject to be improved in the future.                                       # NOTE: AFAIK this has been patched as of 1.2.2