# Necessary imports
import discord

from development.dev.state import ACTIVE_DEV_PANELS, ACTIVE_PERMS_PANELS



# Resolves a target guild member from mention or user ID input
async def resolve_target_member(message: discord.Message, raw_value: str | None) -> discord.Member | None:
    if not message.guild:
        return None

    if message.mentions:
        mentioned = message.mentions[0]
        if isinstance(mentioned, discord.Member):
            return mentioned

        guild_member = message.guild.get_member(mentioned.id)
        if guild_member:
            return guild_member

        try:
            return await message.guild.fetch_member(mentioned.id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    if not raw_value:
        return None

    candidate = raw_value.strip().strip("<@!").strip(">")
    if not candidate.isdigit():
        return None

    user_id = int(candidate)
    member = message.guild.get_member(user_id)
    if member:
        return member

    try:
        return await message.guild.fetch_member(user_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None


# Sends a temporary command-style response in message channels
async def send_ephemeral_like(
    message: discord.Message,
    *,
    content: str | None = None,
    embed: discord.Embed | None = None,
    view: discord.ui.View | None = None,
    file: discord.File | None = None,
    timeout_seconds: float | None = 20.0,
    delete_invoker: bool = True,
) -> discord.Message:
    sent = await message.channel.send(
        content=content,
        embed=embed,
        view=view,
        file=file,
        delete_after=timeout_seconds,
    )

    if delete_invoker:
        try:
            await message.delete()
        except (discord.Forbidden, discord.HTTPException, discord.NotFound):
            pass

    if view is not None:
        try:
            await sent.edit(view=view)
        except (discord.Forbidden, discord.HTTPException, discord.NotFound):
            pass

    return sent


# Checks whether the tracked developer panel message is still reachable
async def get_active_panel(guild: discord.Guild) -> tuple[bool, dict[str, int] | None]:
    panel = ACTIVE_DEV_PANELS.get(guild.id)
    if not panel:
        return False, None

    channel_id = panel.get("channel_id")
    message_id = panel.get("message_id")
    if not isinstance(channel_id, int) or not isinstance(message_id, int):
        ACTIVE_DEV_PANELS.pop(guild.id, None)
        return False, None

    channel = guild.get_channel(channel_id)
    if channel is None:
        try:
            channel = await guild.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            ACTIVE_DEV_PANELS.pop(guild.id, None)
            return False, None

    fetch_message = getattr(channel, "fetch_message", None)
    if fetch_message is None:
        ACTIVE_DEV_PANELS.pop(guild.id, None)
        return False, None

    try:
        await fetch_message(message_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        ACTIVE_DEV_PANELS.pop(guild.id, None)
        return False, None

    return True, panel


# Checks whether the tracked permissions panel message is still reachable
async def get_active_perms_panel(guild: discord.Guild) -> tuple[bool, dict[str, int] | None]:
    panel = ACTIVE_PERMS_PANELS.get(guild.id)
    if not panel:
        return False, None

    channel_id = panel.get("channel_id")
    message_id = panel.get("message_id")
    if not isinstance(channel_id, int) or not isinstance(message_id, int):
        ACTIVE_PERMS_PANELS.pop(guild.id, None)
        return False, None

    channel = guild.get_channel(channel_id)
    if channel is None:
        try:
            channel = await guild.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            ACTIVE_PERMS_PANELS.pop(guild.id, None)
            return False, None

    fetch_message = getattr(channel, "fetch_message", None)
    if fetch_message is None:
        ACTIVE_PERMS_PANELS.pop(guild.id, None)
        return False, None

    try:
        await fetch_message(message_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        ACTIVE_PERMS_PANELS.pop(guild.id, None)
        return False, None

    return True, panel