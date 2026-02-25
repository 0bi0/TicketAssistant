# Necessary imports
import time
import discord
from discord import client

from main.main import(
    TICKETS_BOT_ID
)

from cogs.permissions import(
    get_ticket_category,
    is_staff
)



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