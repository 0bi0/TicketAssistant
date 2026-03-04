# Necessary imports
import time
from discord import client

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