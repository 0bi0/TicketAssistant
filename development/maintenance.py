# Necessary imports
import hashlib
import hmac
import secrets
import time
import aiosqlite



# Maintenance mode management
MAINTENANCE_NOTICE = "Bot is in maintenance mode. Please contact the server owner for more information."

# In-memory cache keyed by guild_id
MAINTENANCE_STATE: dict[int, bool] = {}


def _hash_password(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return digest.hex()


async def set_maintenance_password(db: aiosqlite.Connection, guild_id: int, password: str, updated_by: int) -> None:
    salt_hex = secrets.token_hex(16)
    password_hash = _hash_password(password, salt_hex)
    now = int(time.time())
    await db.execute(
        """
        INSERT INTO dev_maintenance_passwords(guild_id, password_salt, password_hash, updated_by, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET
            password_salt=excluded.password_salt,
            password_hash=excluded.password_hash,
            updated_by=excluded.updated_by,
            updated_at=excluded.updated_at
        """,
        (guild_id, salt_hex, password_hash, updated_by, now),
    )
    await db.commit()


# Verifies a provided password against the stored hash for the guild
async def verify_maintenance_password(db: aiosqlite.Connection, guild_id: int, password: str) -> bool:
    cursor = await db.execute(
        "SELECT password_salt, password_hash FROM dev_maintenance_passwords WHERE guild_id = ?",
        (guild_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return False

    salt_hex, stored_hash = row
    computed_hash = _hash_password(password, salt_hex)
    return hmac.compare_digest(computed_hash, stored_hash)


# Checks if a maintenance password is set for the guild (used to determine if maintenance mode can be enabled)
async def has_maintenance_password(db: aiosqlite.Connection, guild_id: int) -> bool:
    cursor = await db.execute(
        "SELECT 1 FROM dev_maintenance_passwords WHERE guild_id = ?",
        (guild_id,),
    )
    return (await cursor.fetchone()) is not None


# Checks if maintenance mode is currently enabled for the given server ID
async def set_maintenance_mode(db: aiosqlite.Connection, guild_id: int, enabled: bool, updated_by: int) -> None:
    now = int(time.time())
    await db.execute(
        """
        INSERT INTO dev_maintenance_state(guild_id, enabled, updated_by, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET
            enabled=excluded.enabled,
            updated_by=excluded.updated_by,
            updated_at=excluded.updated_at
        """,
        (guild_id, 1 if enabled else 0, updated_by, now),
    )
    await db.commit()
    MAINTENANCE_STATE[guild_id] = enabled


# Loads maintenance state for all guilds into the in-memory cache at startup
async def load_maintenance_state_cache(db: aiosqlite.Connection) -> None:
    cursor = await db.execute("SELECT guild_id, enabled FROM dev_maintenance_state")
    rows = await cursor.fetchall()
    MAINTENANCE_STATE.clear()
    for guild_id, enabled in rows:
        if isinstance(guild_id, int):
            MAINTENANCE_STATE[guild_id] = bool(enabled)


# Checks if maintenance mode is currently enabled for the given server ID
def is_maintenance_enabled(guild_id: int) -> bool:
    return MAINTENANCE_STATE.get(guild_id, False)