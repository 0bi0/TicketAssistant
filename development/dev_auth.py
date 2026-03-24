# Necessary imports
import discord
import aiosqlite



# In-memory cache for DB-backed developer IDs
DEV_USERS: set[int] = set()



# Load developer IDs from database into memory on startup
async def refresh_dev_users(db: aiosqlite.Connection) -> None:
    # Reload developer IDs from database into memory
    cursor = await db.execute("SELECT user_id FROM developer_users WHERE user_id > 0")
    rows = await cursor.fetchall()

    DEV_USERS.clear()
    for row in rows:
        DEV_USERS.add(row[0])


# Add a developer user ID and refresh cache
async def add_developer(db: aiosqlite.Connection, user_id: int) -> None:
    # Persist a developer user ID and refresh cache
    await db.execute(
        "INSERT OR IGNORE INTO developer_users(user_id) VALUES (?)",
        (user_id,),
    )
    await db.commit()
    await refresh_dev_users(db)


# Remove a developer user ID and refresh cache
async def remove_developer(db: aiosqlite.Connection, user_id: int) -> None:
    # Remove a developer user ID and refresh cache
    await db.execute(
        "DELETE FROM developer_users WHERE user_id = ?",
        (user_id,),
    )
    await db.commit()
    await refresh_dev_users(db)


# Miscallenous helper to check if a member is a developer
def is_developer(member: discord.Member) -> bool:
    # Server owner is always a developer; others must be in the dev cache
    return member.id == member.guild.owner_id or member.id in DEV_USERS