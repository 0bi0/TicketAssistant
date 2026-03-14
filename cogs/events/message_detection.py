# Necessary imports
import time
import discord

from main.bot import(
    client,
    TICKETS_BOT_ID
)

from cogs.permissions import(
    get_ticket_category,
    is_staff
)

from cogs.lists.opening_messages import(
    OPEN_MARKERS
)



# Helper function to get a human-readable (AKA not ID) channel name
async def get_readable_channel_name(message: discord.Message) -> str:
    channel = message.channel

    name = getattr(channel, "name", None)
    if isinstance(name, str) and name.strip():
        return name

    # If the event channel object is partial/uncached, try guild cache by id.
    if message.guild:
        cached_channel = message.guild.get_channel(message.channel.id)
        cached_name = getattr(cached_channel, "name", None)
        if isinstance(cached_name, str) and cached_name.strip():
            return cached_name

        cached_thread = message.guild.get_thread(message.channel.id)
        thread_name = getattr(cached_thread, "name", None)
        if isinstance(thread_name, str) and thread_name.strip():
            return thread_name

    # Last-resort API fetch for channels not present in local cache.
    try:
        fetched_channel = await client.fetch_channel(message.channel.id)
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        fetched_channel = None

    fetched_name = getattr(fetched_channel, "name", None)
    if isinstance(fetched_name, str) and fetched_name.strip():
        return fetched_name

    recipient = getattr(channel, "recipient", None)
    if recipient:
        recipient_name = getattr(recipient, "display_name", None) or getattr(recipient, "name", None)
        if isinstance(recipient_name, str) and recipient_name.strip():
            return recipient_name

    return "Unknown Channel"



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
        channel_name = await get_readable_channel_name(message)
        print(
            "[BOT MSG] |",
            # "author_id=", message.author.id,     # Uncomment if you want to log bot message authors (even though it's always just the tickets bot)
            "channel=", channel_name, "|",
            "embeds=", len(message.embeds), "|",
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
                open_log = f"🎫 Ticket OPEN: {message.channel.id} | category: {category_name}"
                print(open_log)
                print("-" * len(open_log))