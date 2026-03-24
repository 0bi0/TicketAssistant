# Necessary imports
import asyncio
import hmac
import importlib
import io
import os
import sys
import time

import discord

from cogs.permissions import LOG_CHANNEL_ID
from development.dev.log_aliasing import alias_console_line
from development.maintenance import (
    has_maintenance_password,
    is_maintenance_enabled,
    set_maintenance_mode,
    verify_maintenance_password,
)

from development.dev.state import ACTIVE_DEV_PANELS, BANNER_PATH
from development.runtime_logs import get_recent_logs
from development.dev_auth import DEV_USERS
from main.bot import client, tree
from main.command_registry import register_commands



# Custom emoji objects
EMOJI_STOP = discord.PartialEmoji(id=1483818555131560137, name="close")
EMOJI_RESTART = discord.PartialEmoji(id=1483823194266927286, name="restart")
EMOJI_RELOAD = discord.PartialEmoji(id=1483845196591534121, name="reload")
EMOJI_MAINTENANCE_ON = discord.PartialEmoji(id=1483940167680004296, name="maintenance_on")
EMOJI_MAINTENANCE_OFF = discord.PartialEmoji(id=1483958035042009130, name="maintenance_off")
EMOJI_DEBUG = discord.PartialEmoji(id=1483512504473878538, name="debug")
EMOJI_LOGS = discord.PartialEmoji(id=1483850265336742111, name="logs")
EMOJI_EXIT = discord.PartialEmoji(id=1483513071325675703, name="exit")


# Bot restart helper
async def restart_process() -> None:
    await asyncio.sleep(1.0)
    python_exec = sys.executable
    os.execv(python_exec, [python_exec, "-m", "main.main"])

# Reload command helper
async def run_hot_reload() -> tuple[list[str], list[str]]:
    importlib.invalidate_caches()

    reload_targets = [
        "commands.database_commands",
        "commands.history_commands",
        "commands.miscellaneous_commands",
        "commands.privileged_user_commands",
        "commands.log_channel_commands",
        "cogs.events.message_detection",
        "cogs.events.channel_deletion",
        "cogs.events.guild_join",
        "development.dev.router",
        "development.dev.helpers",
        "development.dev.perms_ui",
        "development.dev.log_aliasing",
        "development.dev_auth",
        "main.command_registry",
    ]

    reloaded: list[str] = []
    failed: list[str] = []

    for module_name in reload_targets:
        module = sys.modules.get(module_name)
        if module is None:
            continue
        try:
            importlib.reload(module)
            reloaded.append(module_name)
        except Exception as exc:
            failed.append(f"{module_name}: {exc}")

    try:
        tree.clear_commands(guild=None)
        register_commands(tree)
        await tree.sync()
        reloaded.append("slash_commands.sync")
    except Exception as exc:
        failed.append(f"slash_commands.sync: {exc}")

    return reloaded, failed


# Developer panel UI
def build_panel_embed(guild: discord.Guild, panel_mode: str) -> discord.Embed:
    started_at = int(getattr(client, "_started_at", int(time.time())))
    dev_count = len(set(DEV_USERS) | {guild.owner_id})
    session_started_relative = f"<t:{started_at}:R>"
    maintenance_status = "ENABLED" if is_maintenance_enabled(guild.id) else "DISABLED"
    is_owner_mode = panel_mode == "OWNER MODE"

    embed = discord.Embed(
        title="Developer Control Panel",
        description=(
            "Bot operations dashboard for runtime controls and system visibility. Only one active panel instance is allowed per server.\n"
            "––––––––––––––––––––––––––––––––––––––––––––––––––––––––"
            "‎"
        ),
        color=discord.Color.from_rgb(182, 182, 182),
    )
    # status_badge = "ONLINE" if not client.is_closed() else "OFFLINE"

    embed.add_field(
        name="System",
        value=(
            # f"- Bot Status: `{status_badge}`\n"
            f"- Active Panel Mode: `{panel_mode}`\n"
            + (f"- Maintenance Mode: `{maintenance_status}`\n" if is_owner_mode else "")
            + f"- Session Started: {session_started_relative}\n"
        ),
        inline=False,
    )
    '''embed.add_field(
        name="Runtime",
        value=(
            
            # f"- Guild ID: `{guild.id}`"
        ),
        inline=False,
    )'''
    embed.add_field(
        name="Access",
        value=(
            f"- Registered Developers: `{dev_count}`\n"
            f"- Server Owner: <@{guild.owner_id}>\n"
            f"––––––––––––––––––––––––––––––––––––––––––––––––––––––––"
        ),
        inline=False,
    )
    embed.add_field(
        name="System Controls",
        value=(
            "- <:stop:1483818555131560137> `Stop` - Gracefully shuts down the bot process\n"
            "- <:restart:1483823194266927286> `Restart` - Restarts the running bot process\n"
            "- <:reload:1483845196591534121> `Reload` - Reloads system modules without restart\n"
        ),
        inline=False,
    )
    embed.add_field(
        name="Developer Tools",
        value=(
            "- <:debug:1483512504473878538> `Debug` - Runs consistency checks and report results\n"
            "- <:logs:1483850265336742111> `Logs` - Displays recent console output\n"
            "- <:exit:1483513071325675703> `Exit` - Closes the developer dashboard"
        ),
        inline=False,
    )
    embed.set_footer(text="Developer actions are restricted to the server owner + whitelisted developers")
    return embed


# Developer debug checks to identify common issues and attempt auto-repair
async def run_debug_checks(guild: discord.Guild) -> discord.Embed:
    now = int(time.time())

    cursor = await client.db.execute(
        "SELECT channel_id, closed_at FROM tickets WHERE opened_at IS NULL OR opened_at <= 0"
    )
    broken_opened_rows = await cursor.fetchall()

    repaired_opened = 0
    for channel_id, closed_at in broken_opened_rows:
        replacement_opened_at = closed_at if isinstance(closed_at, int) and closed_at > 0 else now
        await client.db.execute(
            "UPDATE tickets SET opened_at = ? WHERE channel_id = ?",
            (replacement_opened_at, channel_id),
        )
        repaired_opened += 1

    cursor = await client.db.execute(
        """
        SELECT channel_id
        FROM tickets
        WHERE closed_at IS NOT NULL
          AND opened_at IS NOT NULL
          AND closed_at <= opened_at
        """
    )
    broken_order_rows = await cursor.fetchall()
    repaired_closed_order = 0
    for (channel_id,) in broken_order_rows:
        await client.db.execute(
            "UPDATE tickets SET closed_at = NULL WHERE channel_id = ?",
            (channel_id,),
        )
        repaired_closed_order += 1

    cursor = await client.db.execute(
        """
        SELECT COUNT(*)
        FROM messages m
        LEFT JOIN tickets t ON t.channel_id = m.channel_id
        WHERE t.channel_id IS NULL
        """
    )
    orphan_messages = (await cursor.fetchone())[0]

    if orphan_messages > 0:
        await client.db.execute(
            """
            DELETE FROM messages
            WHERE channel_id IN (
                SELECT m.channel_id
                FROM messages m
                LEFT JOIN tickets t ON t.channel_id = m.channel_id
                WHERE t.channel_id IS NULL
            )
            """
        )

    cleared_log_channel = False
    if LOG_CHANNEL_ID[0] is not None and guild.get_channel(LOG_CHANNEL_ID[0]) is None:
        await client.db.execute("DELETE FROM log_channel WHERE id = 1")
        LOG_CHANNEL_ID[0] = None
        cleared_log_channel = True

    await client.db.commit()

    checks_ran = 4
    fixed_total = repaired_opened + repaired_closed_order + orphan_messages + (1 if cleared_log_channel else 0)

    embed = discord.Embed(
        title="Developer Debug Report",
        color=discord.Color.green() if fixed_total else discord.Color.orange(),
    )

    embed.add_field(name="Checks run", value=str(checks_ran), inline=True)
    embed.add_field(name="Total fixes", value=str(fixed_total), inline=True)
    embed.add_field(
        name="Details",
        value=(
            f"- Repaired ticket open times: `{repaired_opened}`\n"
            f"- Repaired invalid close order: `{repaired_closed_order}`\n"
            f"- Removed orphan message logs: `{orphan_messages}`\n"
            f"- Cleared invalid ticket log channel: `{1 if cleared_log_channel else 0}`"
        ),
        inline=False,
    )

    return embed



# Password confirmation modal for maintenance actions
class MaintenancePasswordModal(discord.ui.Modal, title="Confirm Maintenance Action"):
    password = discord.ui.TextInput(
        label="Maintenance password",
        placeholder="Enter password set via /passwordset",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=128,
        required=True,
    )

    # Initializes the modal with context for the maintenance action being confirmed
    def __init__(self, guild_id: int, requester_id: int, enable_mode: bool):
        super().__init__()
        self.guild_id = guild_id
        self.requester_id = requester_id
        self.enable_mode = enable_mode

    # Password handling for maintenance actions
    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or interaction.guild.id != self.guild_id:
            await interaction.response.send_message("This maintenance action is no longer valid in this server.", ephemeral=True)
            return

        if interaction.user.id != self.requester_id:
            await interaction.response.send_message("Only the developer who opened this panel can use this action.", ephemeral=True)
            return

        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("Only the server owner can change maintenance mode.", ephemeral=True)
            return

        if not await has_maintenance_password(client.db, self.guild_id):
            await interaction.response.send_message("Maintenance password is not configured. Run `/passwordset` first.", ephemeral=True)
            return

        password_ok = await verify_maintenance_password(client.db, self.guild_id, self.password.value)
        if not password_ok:
            await interaction.response.send_message("Invalid maintenance password.", ephemeral=True)
            return

        await set_maintenance_mode(
            client.db,
            guild_id=self.guild_id,
            enabled=self.enable_mode,
            updated_by=interaction.user.id,
        )

        # If the panel is open in the guild, live-refresh the embed to reflect the updated maintenance status immediately
        panel_state = ACTIVE_DEV_PANELS.get(self.guild_id)
        if panel_state and interaction.guild:
            channel_id = panel_state.get("channel_id")
            message_id = panel_state.get("message_id")
            if isinstance(channel_id, int) and isinstance(message_id, int):
                panel_channel = interaction.guild.get_channel(channel_id)
                if panel_channel is None:
                    try:
                        panel_channel = await interaction.guild.fetch_channel(channel_id)
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        panel_channel = None

                # Fetches panel message and updates embed with new maintenance status
                fetch_message = getattr(panel_channel, "fetch_message", None)
                if callable(fetch_message):
                    try:
                        panel_message = await fetch_message(message_id)
                        panel_mode = "OWNER MODE" if self.requester_id == interaction.guild.owner_id else "DEVELOPER MODE"
                        updated_embed = build_panel_embed(interaction.guild, panel_mode=panel_mode)

                        if os.path.isfile(BANNER_PATH):
                            updated_embed.set_image(url="attachment://banner.png")
                            banner_file = discord.File(BANNER_PATH, filename="banner.png")
                            # Replaces existing attachments so stale previews from prior edits are removed
                            await panel_message.edit(embed=updated_embed, attachments=[banner_file])
                        else:
                            # If banner is missing, clears image and attachments rather than falling back to avatar
                            updated_embed.set_image(url=None)
                            await panel_message.edit(embed=updated_embed, attachments=[])
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        pass

        state_label = "enabled" if self.enable_mode else "disabled"
        await interaction.response.send_message(f"Maintenance mode has been {state_label}.", ephemeral=True)



# Selection menu for maintenance actions
class MaintenanceActionSelect(discord.ui.Select):
    def __init__(self, guild_id: int, requester_id: int):
        self.guild_id = guild_id
        self.requester_id = requester_id
        options = [
            discord.SelectOption(
                label="Enable Maintenance Mode",
                value="enable",
                description="Blocks all users from interacting with the bot",
                emoji=EMOJI_MAINTENANCE_ON,
            ),
            discord.SelectOption(
                label="Disable Maintenance Mode",
                value="disable",
                description="Restores normal bot interaction perms for all users",
                emoji=EMOJI_MAINTENANCE_OFF,
            ),
        ]

        super().__init__(
            placeholder="Maintenance Actions",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    # Handles maintenance action selection and prompts for password confirmation
    async def callback(self, interaction: discord.Interaction):
        # Owner-only trigger that opens password confirmation modal
        if not interaction.guild or interaction.guild.id != self.guild_id:
            await interaction.response.send_message("This maintenance menu is no longer valid in this server.", ephemeral=True)
            return

        if interaction.user.id != self.requester_id:
            await interaction.response.send_message("Only the developer who opened this panel can use this menu.", ephemeral=True)
            return

        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("Only the server owner can use maintenance actions.", ephemeral=True)
            return

        enable_mode = self.values[0] == "enable"
        await interaction.response.send_modal(
            MaintenancePasswordModal(
                guild_id=self.guild_id,
                requester_id=self.requester_id,
                enable_mode=enable_mode,
            )
        )



# Checks whether the tracked developer panel message is still reachable and valid
class DevPanelView(discord.ui.View):
    def __init__(self, guild_id: int, creator_id: int, owner_mode: bool = False):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.creator_id = creator_id
        self.owner_mode = owner_mode
        if owner_mode:
            self.add_item(MaintenanceActionSelect(guild_id=guild_id, requester_id=creator_id))


    # Checks whether the interaction is from the original panel creator
    def _is_allowed(self, interaction: discord.Interaction) -> bool:
        # Panel controls are restricted to the original creator in the originating guild
        if not interaction.guild or interaction.guild.id != self.guild_id:
            return False
        if not isinstance(interaction.user, discord.Member):
            return False
        if is_maintenance_enabled(interaction.guild.id) and interaction.user.id != interaction.guild.owner_id:
            return False
        return interaction.user.id == self.creator_id



    # Stop button
    @discord.ui.button(emoji=EMOJI_STOP, label="Stop", style=discord.ButtonStyle.secondary, row=1)
    async def stop_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not self._is_allowed(interaction):
            await interaction.response.send_message("Only the developer who opened this panel can use these controls.", ephemeral=True)
            return

        await interaction.response.send_message("Stopping bot process...", ephemeral=True)
        await client.close()



    # Restart button
    @discord.ui.button(emoji=EMOJI_RESTART, label="Restart", style=discord.ButtonStyle.secondary, row=1)
    async def restart_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not self._is_allowed(interaction):
            await interaction.response.send_message("Only the developer who opened this panel can use these controls.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        ACTIVE_DEV_PANELS.pop(self.guild_id, None)

        try:
            await interaction.message.delete()
        except (discord.Forbidden, discord.HTTPException, AttributeError):
            await interaction.followup.send("Could not delete panel message, but restart is continuing.", ephemeral=True)

        await interaction.followup.send("Restarting bot process...", ephemeral=True)
        asyncio.create_task(restart_process())



    # Reload button
    @discord.ui.button(emoji=EMOJI_RELOAD, label="Reload", style=discord.ButtonStyle.secondary, row=1)
    async def reload_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not self._is_allowed(interaction):
            await interaction.response.send_message("Only the developer who opened this panel can use these controls.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        # Hot-reload project modules and report a concise result summary
        reloaded, failed = await run_hot_reload()

        color = discord.Color.green() if not failed else discord.Color.orange()
        embed = discord.Embed(title="Reload Report", color=color)
        embed.add_field(name="Reloaded", value=str(len(reloaded)), inline=True)
        embed.add_field(name="Failures", value=str(len(failed)), inline=True)
        if reloaded:
            embed.add_field(
                name="Updated Modules",
                value="\n".join(f"- `{name}`" for name in reloaded[:15]),
                inline=False,
            )
        if failed:
            embed.add_field(
                name="Errors",
                value="\n".join(f"- {line}" for line in failed[:8]),
                inline=False,
            )
            embed.set_footer(text="Some modules failed to reload; a full restart may still be required.")
        else:
            embed.set_footer(text="Bot reload completed successfully.")

        await interaction.followup.send(embed=embed, ephemeral=True)



    # Debug button
    @discord.ui.button(emoji=EMOJI_DEBUG, label="Debug", style=discord.ButtonStyle.secondary, row=2)
    async def debug_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not self._is_allowed(interaction):
            await interaction.response.send_message("Only the developer who opened this panel can use these controls.", ephemeral=True)
            return

        if not interaction.guild:
            await interaction.response.send_message("This control can only run inside a server.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        debug_embed = await run_debug_checks(interaction.guild)
        await interaction.followup.send(embed=debug_embed, ephemeral=True)



    # Logs button
    @discord.ui.button(emoji=EMOJI_LOGS, label="Logs", style=discord.ButtonStyle.secondary, row=2)
    async def logs_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not self._is_allowed(interaction):
            await interaction.response.send_message("Only the developer who opened this panel can use these controls.", ephemeral=True)
            return

        raw_logs = get_recent_logs(limit=800)
        aliased_logs = [entry for entry in (alias_console_line(line) for line in raw_logs) if entry]
        if not aliased_logs:
            await interaction.response.send_message("No aliased console events are available yet.", ephemeral=True)
            return

        payload = "\n".join(aliased_logs[-250:])
        if len(payload) <= 3500:
            embed = discord.Embed(
                title="Console Event Feed",
                description=f"```text\n{payload}\n```",
                color=discord.Color.from_rgb(182, 182, 182),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        data = io.BytesIO(payload.encode("utf-8"))
        log_file = discord.File(fp=data, filename="console_events.log")
        await interaction.followup.send(
            content="Event feed is too long for an embed. Attached as file.",
            file=log_file,
            ephemeral=True,
        )



    # Exit button
    @discord.ui.button(emoji=EMOJI_EXIT, label="Exit", style=discord.ButtonStyle.secondary, row=2)
    async def close_panel_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not self._is_allowed(interaction):
            await interaction.response.send_message("Only the developer who opened this panel can use these controls.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        ACTIVE_DEV_PANELS.pop(self.guild_id, None)

        try:
            await interaction.message.delete()
        except (discord.Forbidden, discord.HTTPException, AttributeError):
            await interaction.followup.send("Panel lock released, but I could not delete the panel message.", ephemeral=True)
            return

        await interaction.followup.send("Dashboard session terminated successfully.", ephemeral=False)