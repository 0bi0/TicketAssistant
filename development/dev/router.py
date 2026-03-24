# Necessary imports
import asyncio
import os

import discord

from development.dev.helpers import (
    get_active_panel,
    get_active_perms_panel,
    resolve_target_member,
    send_ephemeral_like,
)

from development.dev.panel_ui import DevPanelView, build_panel_embed
from development.dev.perms_ui import PermissionsPanelView, build_perms_embed
from development.dev.command_catalog import format_dev_command_lines
from development.dev.state import ACTIVE_DEV_PANELS, ACTIVE_PERMS_PANELS, BANNER_PATH
from development.dev_auth import DEV_USERS, add_developer, is_developer, remove_developer
from development.maintenance import MAINTENANCE_NOTICE, is_maintenance_enabled
from main.bot import client



# Main router for handling incoming dev command messages
async def handle_dev_command_message(message: discord.Message) -> bool:
    if message.author.bot or not message.guild:
        return False

    content = message.content.strip()
    if not content.lower().startswith("dev!"):
        return False

    if not isinstance(message.author, discord.Member):
        return False

    if not hasattr(client, "db"):
        await send_ephemeral_like(message, content="Database is not ready yet.")
        return True

    without_prefix = content[4:].strip()
    if not without_prefix:
        await send_ephemeral_like(message, content="Usage: dev!help")
        return True

    parts = without_prefix.split(maxsplit=1)
    command = parts[0].lower()
    raw_arg = parts[1] if len(parts) > 1 else None


    # Dev access check
    if not is_developer(message.author):
        await send_ephemeral_like(
            message,
            content="You are not registered as a developer.",
            timeout_seconds=3.0,
        )
        return True


    # Maintenance mode check
    if is_maintenance_enabled(message.guild.id) and message.author.id != message.guild.owner_id:
        await send_ephemeral_like(
            message,
            content=MAINTENANCE_NOTICE,
            timeout_seconds=8.0,
            delete_invoker=False,
        )
        return True



    # Help command
    if command == "help":
        dev_commands = "\n".join(format_dev_command_lines(include_owner_only=True))

        embed = discord.Embed(
            title="Ticket Management Bot",
            color=0xB6B6B6,
        )

        embed.add_field(
            name="📰  Information",
            value=(
                "The `Developer Panel` is a private command interface for maintenance and\n"
                "runtime control tasks. Access is restricted to the server owner and users\n"
                "whitelisted with `dev!whitelist`.\n"
                "––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––"
            ),
            inline=False,
        )

        embed.add_field(
            name="🧩  Developer Commands",
            value=(
                f"{dev_commands}\n"
                "––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––"
            ),
            inline=False,
        )

        embed.set_footer(text="Ticket Assistant | Made by 0bi0")
        await send_ephemeral_like(message, embed=embed, timeout_seconds=15.0)
        return True



    # Permissions panel command
    if command == "perms":
        is_active, existing_session = await get_active_perms_panel(message.guild)
        if is_active and existing_session is not None:
            existing_owner_id = existing_session.get("creator_id", 0)
            existing_channel_id = existing_session.get("channel_id", 0)
            existing_message_id = existing_session.get("message_id", 0)
            panel_link = (
                f"https://discord.com/channels/{message.guild.id}/{existing_channel_id}/{existing_message_id}"
                if existing_channel_id and existing_message_id
                else "(link unavailable)"
            )
            await send_ephemeral_like(
                message,
                content=(
                    "A permissions session is already active in this server. "
                    f"Opened by <@{existing_owner_id}>.\n{panel_link}"
                ),
                timeout_seconds=8.0,
            )
            return True

        await message.channel.send(f"{message.author.mention} Started new session.")

        default_category = "stats"
        perms_embed = build_perms_embed(message.guild, default_category)
        perms_view = PermissionsPanelView(
            guild_id=message.guild.id,
            creator_id=message.author.id,
            selected_category=default_category,
        )

        perms_message = await send_ephemeral_like(
            message,
            embed=perms_embed,
            view=perms_view,
            timeout_seconds=300.0,
            delete_invoker=False,
        )

        ACTIVE_PERMS_PANELS[message.guild.id] = {
            "creator_id": message.author.id,
            "channel_id": perms_message.channel.id,
            "message_id": perms_message.id,
        }

        log_line_panel = f"[🧰 DEV PERMS OPEN] {message.author} opened permissions panel in guild {message.guild.id}"
        print(log_line_panel)
        print("-" * len(log_line_panel))
        return True



    # Whitelist command
    if command == "whitelist":
        if message.author.id != message.guild.owner_id:
            await send_ephemeral_like(message, content="Only the server owner can whitelist new developers.")
            return True

        target_member = await resolve_target_member(message, raw_arg)
        if not target_member:
            await send_ephemeral_like(message, content="Usage: dev!whitelist <@user|user_id>")
            return True

        if target_member.id == message.guild.owner_id:
            await send_ephemeral_like(message, content="The server owner is already a developer.")
            return True

        if target_member.id in DEV_USERS:
            await send_ephemeral_like(message, content=f"{target_member.mention} is already whitelisted as a developer.")
            return True

        await add_developer(client.db, target_member.id)

        log_line_dev_add = f"[🟢 DEV ADD] {message.author} added developer {target_member} ({target_member.id})"
        print(log_line_dev_add)
        print("-" * len(log_line_dev_add))

        await send_ephemeral_like(message, content=f"{target_member.mention} is now a registered developer.")
        return True



    # Unwhitelist command
    if command == "unwhitelist":
        if message.author.id != message.guild.owner_id:
            await send_ephemeral_like(message, content="Only the server owner can remove developers.")
            return True

        target_member = await resolve_target_member(message, raw_arg)
        if not target_member:
            await send_ephemeral_like(message, content="Usage: dev!unwhitelist <@user|user_id>")
            return True

        if target_member.id == message.guild.owner_id:
            await send_ephemeral_like(message, content="The server owner cannot be unwhitelisted.")
            return True

        if target_member.id not in DEV_USERS:
            await send_ephemeral_like(message, content=f"{target_member.mention} is not a whitelisted developer.")
            return True

        await remove_developer(client.db, target_member.id)

        log_line_dev_remove = f"[🔴 DEV REMOVE] {message.author} removed developer {target_member} ({target_member.id})"
        print(log_line_dev_remove)
        print("-" * len(log_line_dev_remove))

        await send_ephemeral_like(message, content=f"{target_member.mention} has been removed from developers.")
        return True



    # Dev list command
    if command == "list":
        developer_ids = sorted(set(DEV_USERS) | {message.guild.owner_id})
        lines = []

        for user_id in developer_ids:
            member = message.guild.get_member(user_id)
            suffix = " (Server Owner)" if user_id == message.guild.owner_id else ""
            if member:
                lines.append(f"- {member.mention} - `{user_id}`{suffix}")
            else:
                lines.append(f"- <@{user_id}> - `{user_id}` (Not in Server){suffix}")

        embed = discord.Embed(
            title="Registered Developers",
            description="\n".join(lines) if lines else "No developers registered.",
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Total: {len(developer_ids)}")

        log_line_dev = f"[🛠️ DEV LIST VIEW] {message.author} viewed developer users list"
        print(log_line_dev)
        print("-" * len(log_line_dev))

        await send_ephemeral_like(message, embed=embed)
        return True



    # DM user command
    if command == "dm":
        if not raw_arg:
            await send_ephemeral_like(
                message,
                content="Usage: `dev!dm <@user|user_id> <message>`",
                timeout_seconds=None,
                delete_invoker=False,
            )
            return True

        dm_parts = raw_arg.split(maxsplit=1)
        target_raw = dm_parts[0]
        dm_text = dm_parts[1].strip() if len(dm_parts) > 1 else ""
        if not dm_text:
            await send_ephemeral_like(
                message,
                content="Usage: `dev!dm <@user|user_id> <message>`",
                timeout_seconds=None,
                delete_invoker=False,
            )
            return True

        target_member = await resolve_target_member(message, target_raw)
        if not target_member:
            await send_ephemeral_like(
                message,
                content="Could not resolve target user.",
                timeout_seconds=None,
                delete_invoker=False,
            )
            return True

        try:
            await target_member.send(dm_text)
        except (discord.Forbidden, discord.HTTPException):
            await send_ephemeral_like(
                message,
                content="Failed to send DM. User may have DMs disabled.",
                timeout_seconds=None,
                delete_invoker=False,
            )
            return True

        sent_embed = discord.Embed(
            title="✅ DM Sent Successfully",
            color=discord.Color.green(),
        )
        sent_embed.add_field(
            name="Recipient",
            value=f"{target_member.mention} ({target_member})",
            inline=False,
        )
        sent_embed.add_field(
            name="Sent by",
            value=message.author.mention,
            inline=False,
        )
        sent_embed.add_field(
            name="Message",
            value=dm_text,
            inline=False,
        )
        sent_embed.timestamp = discord.utils.utcnow()
        if client.user:
            sent_embed.set_thumbnail(url=client.user.display_avatar.url)

        await send_ephemeral_like(message, embed=sent_embed, timeout_seconds=None, delete_invoker=False)
        return True



    # DM all command
    if command == "dmall":
        dm_text = (raw_arg or "").strip()
        if not dm_text:
            await send_ephemeral_like(
                message,
                content="Usage: dev!dmall <message>",
                timeout_seconds=None,
                delete_invoker=False,
            )
            return True

        delivered = 0
        failed = 0
        bots_skipped = 0

        for member in message.guild.members:
            if member.bot:
                bots_skipped += 1
                continue

            try:
                await member.send(dm_text)
                delivered += 1
            except (discord.Forbidden, discord.HTTPException):
                failed += 1

            # Gentle pacing helps reduce burst pressure on DM endpoints.
            await asyncio.sleep(0.05)

        summary_embed = discord.Embed(
            title="Mass DM Sent",
            color=discord.Color.from_rgb(182, 182, 182),
        )
        summary_embed.add_field(
            name="Sent by",
            value=f"{message.author.mention} (`{message.author.id}`)",
            inline=False,
        )
        summary_embed.add_field(
            name="Server",
            value=message.guild.name,
            inline=False,
        )
        summary_embed.add_field(
            name="Results",
            value=(
                f"- <:open:1483106542428360846> Delivered: `{delivered}`\n"
                f"- <:close:1483107264838766602> Failed: `{failed}`\n"
                f"- <:bot:1483907904758354103> Bots Skipped: `{bots_skipped}`"
            ),
            inline=False,
        )
        summary_embed.add_field(
            name="Message",
            value=dm_text[:1024],
            inline=False,
        )
        summary_embed.add_field(
            name="Timestamp",
            value=f"<t:{int(discord.utils.utcnow().timestamp())}:F>",
            inline=False,
        )

        log_line_dmall = (
            f"[📣 DEV DMALL] {message.author} sent mass DM in guild {message.guild.id} "
            f"(delivered={delivered}, failed={failed}, bots_skipped={bots_skipped})"
        )
        print(log_line_dmall)
        print("-" * len(log_line_dmall))

        await send_ephemeral_like(message, embed=summary_embed, timeout_seconds=None, delete_invoker=False)
        return True



    # Panel command
    if command == "panel":
        is_active, existing_panel = await get_active_panel(message.guild)
        if is_active and existing_panel is not None:
            existing_owner_id = existing_panel.get("creator_id", 0)
            existing_channel_id = existing_panel.get("channel_id", 0)
            existing_message_id = existing_panel.get("message_id", 0)
            panel_link = (
                f"https://discord.com/channels/{message.guild.id}/{existing_channel_id}/{existing_message_id}"
                if existing_channel_id and existing_message_id
                else "(link unavailable)"
            )
            await send_ephemeral_like(
                message,
                content=(
                    "A panel instance is already active in this server. "
                    f"Opened by <@{existing_owner_id}>.\n{panel_link}"
                ),
                timeout_seconds=8.0,
            )
            return True

        await message.channel.send(f"Started new dashboard session for {message.author.mention}.")

        panel_mode = "OWNER MODE" if message.author.id == message.guild.owner_id else "DEVELOPER MODE"
        panel_embed = build_panel_embed(message.guild, panel_mode=panel_mode)

        panel_file = None
        if os.path.isfile(BANNER_PATH):
            panel_embed.set_image(url="attachment://banner.png")
            panel_file = discord.File(BANNER_PATH, filename="banner.png")
        elif client.user:
            panel_embed.set_image(url=client.user.display_avatar.url)

        view = DevPanelView(
            guild_id=message.guild.id,
            creator_id=message.author.id,
            owner_mode=(message.author.id == message.guild.owner_id),
        )
        panel_message = await send_ephemeral_like(
            message,
            embed=panel_embed,
            view=view,
            file=panel_file,
            timeout_seconds=None,
            delete_invoker=False,
        )

        ACTIVE_DEV_PANELS[message.guild.id] = {
            "creator_id": message.author.id,
            "channel_id": panel_message.channel.id,
            "message_id": panel_message.id,
        }

        log_line_panel = (
            f"[🧩 DEV PANEL OPEN] {message.author} opened panel in guild {message.guild.id} "
            f"(mode: {panel_mode})"
        )
        print(log_line_panel)
        print("-" * len(log_line_panel))
        return True

    await send_ephemeral_like(message, content="Unknown dev command. Run `dev!help` for more info.")
    return True