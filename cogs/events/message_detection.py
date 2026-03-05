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

from lists.opening_messages import(
    OPEN_MARKERS
)



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
            # Adds to DB
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

        # Check if any of the markers are present in the embed text to identify ticket openings
        if any(marker in text_blob.lower() for marker in OPEN_MARKERS):
            cursor = await client.db.execute(
                "SELECT 1 FROM tickets WHERE channel_id=?",
                (message.channel.id,)
            )
            exists = await cursor.fetchone()

            if not exists:
                category_name = get_ticket_category(message.channel)

                # Insert new ticket record into the database
                await client.db.execute(
                    "INSERT INTO tickets(channel_id, category, opened_at, closed_at) VALUES (?, ?, ?, NULL)",
                    (message.channel.id, category_name, now)
                )
                await client.db.commit()

                # 💻 CONSOLE OUTPUT: Ticket opened
                print("🎫 Ticket OPEN:", message.channel.id, "| category:", category_name)