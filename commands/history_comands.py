# Necessary imports
import math
import re
import time

import discord
from discord import app_commands

from cogs.permissions import SUPPORT_ROLES, TICKET_CATEGORIES



TICKETS_PER_PAGE = 20
TRANSCRIPT_BASE_URL = "https://dashboard.tickets.bot/manage/{guild_id}/transcripts/view/{transcript_id}"



# Custom view that handles pagination for the ticket history command
class TicketHistoryPaginationView(discord.ui.View):
    def __init__(
        self,
        *,
        interaction_user_id: int,
        pages: list[discord.Embed],
        timeout: float = 180,
    ):
        # Initialize the view with the user ID of the command invoker
        super().__init__(timeout=timeout)
        self.interaction_user_id = interaction_user_id
        self.pages = pages
        self.page_index = 0
        self._sync_buttons()

    # Helper function to enable/disable buttons based on the current page index and total pages
    def _sync_buttons(self) -> None:
        self.previous_button.disabled = self.page_index <= 0
        self.next_button.disabled = self.page_index >= len(self.pages) - 1

    # Helper function to switch to a new page index, update the buttons, and edit the message with the new embed for that page
    async def _switch_page(self, interaction: discord.Interaction, new_index: int) -> None:
        self.page_index = new_index
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page_index], view=self)

    # Override the interaction check to ensure that only the command invoker can use the pagination buttons, and send an ephemeral message if another user tries to interact with them
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.interaction_user_id:
            await interaction.response.send_message(
                "❌ Only the command author can use these buttons.",
                ephemeral=True,
            )
            return False
        return True

    # Button definitions
    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous_button(
        self,
        interaction: discord.Interaction,
        _button: discord.ui.Button,
    ) -> None:
        await self._switch_page(interaction, self.page_index - 1)

    # The next button is disabled on the last page, so this won't be called if we're already on the last page
    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_button(
        self,
        interaction: discord.Interaction,
        _button: discord.ui.Button,
    ) -> None:
        await self._switch_page(interaction, self.page_index + 1)

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True



# Helper functions for the ticket history command
def _format_ticket_line(
    transcript_url: str,
    opened_at: int,
    closed_at: int | None,
    category_name: str,
) -> str:
    status = "Closed" if closed_at else "Open"
    opened_relative = f"<t:{opened_at}:R>"
    return (
        f"・[Ticket Log]({transcript_url}) | **{category_name}** | "
        f"Opened {opened_relative} | {status}"
    )


def _build_transcript_url(guild_id: int, transcript_id: int) -> str:
    return TRANSCRIPT_BASE_URL.format(guild_id=guild_id, transcript_id=transcript_id)


def _extract_transcript_id_from_channel_name(channel_name: str) -> int | None:
    channel_suffix_match = re.search(r"(\d+)$", channel_name)
    if not channel_suffix_match:
        return None
    return int(channel_suffix_match.group(1))


async def _resolve_transcript_url(
    *,
    guild: discord.Guild,
    guild_id: int,
    channel_id: int,
    stored_transcript_url: str | None,
) -> str:
    if stored_transcript_url:
        return stored_transcript_url

    channel = guild.get_channel(channel_id)
    if isinstance(channel, discord.TextChannel):
        transcript_id = _extract_transcript_id_from_channel_name(channel.name)
        if transcript_id is not None:
            return _build_transcript_url(guild_id, transcript_id)

    return _build_transcript_url(guild_id, channel_id)



# Builds the list of embeds for the ticket history command based on the query results
async def _build_history_embeds(
    *,
    guild: discord.Guild,
    guild_id: int,
    rows: list[tuple[int, int, int | None, str | None, str | None]],
    category_label: str,
    period_label: str,
) -> list[discord.Embed]:
    total_pages = math.ceil(len(rows) / TICKETS_PER_PAGE)
    embeds: list[discord.Embed] = []

    # Build each page's embed based on the slice of rows for that page
    for page in range(total_pages):
        start = page * TICKETS_PER_PAGE
        end = start + TICKETS_PER_PAGE
        page_rows = rows[start:end]

        # The description of the embed contains the list of tickets for that page, formatted with the helper function
        description_lines = [
            "# Ticket History",
            f"-# Showing **{category_label}** tickets from the last **{period_label}**",
            "",
        ]

        # Each row corresponds to a ticket, and we format it into a line in the embed's description
        for channel_id, opened_at, closed_at, category, transcript_url in page_rows:
            safe_category = category or "Unknown"
            resolved_transcript_url = await _resolve_transcript_url(
                guild=guild,
                guild_id=guild_id,
                channel_id=channel_id,
                stored_transcript_url=transcript_url,
            )
            description_lines.append(
                _format_ticket_line(resolved_transcript_url, opened_at, closed_at, safe_category)
            )

        # Creates the embed for this page
        embed = discord.Embed(
            description="\n".join(description_lines),
            color=discord.Color.from_rgb(182, 182, 182),
        )
        embed.set_footer(
            text=(
                f"Ticket Assistant | {len(rows)} tickets total | "
                f"Page {page + 1}/{total_pages}"
            )
        )
        embeds.append(embed)

    return embeds



# The slash command that users will invoke to see the ticket history, which uses the above helper functions and pagination view
@app_commands.command(name="tickethistory", description="Show ticket history for a category and time period")
@app_commands.describe(
    category="Category: all, appeals, general, or reports",
    period="Period like 12h (hours) or 14d (days)",
)

# Choices for the category argument, which will be shown in the UI as a dropdown menu with the specified options
@app_commands.choices(
    category=[
        app_commands.Choice(name="All", value="all"),
        app_commands.Choice(name="Appeals", value="appeals"),
        app_commands.Choice(name="General", value="general"),
        app_commands.Choice(name="Reports", value="reports"),
    ]
)



# The command function, which takes in the interaction and the command arguments, performs validation and queries the database
async def tickethistory(
    interaction: discord.Interaction,
    category: app_commands.Choice[str],
    period: str,
) -> None:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("❌ You can only use this command in a server.", ephemeral=True)
        return

    # Only users with a support role can use this command.
    if not any(role.name in SUPPORT_ROLES for role in interaction.user.roles):
        await interaction.response.send_message("❌ You do not have permission to view ticket history.", ephemeral=True)
        return

    try:
        number = int(period[:-1])
        unit = period[-1].lower()
    except ValueError:
        await interaction.response.send_message(
            "❌ Invalid period format, e.g., 12h or 14d.",
            ephemeral=True,
        )
        return

    if number <= 0:
        await interaction.response.send_message(
            "❌ Time value must be greater than 0.",
            ephemeral=True,
        )
        return

    if unit == "h":
        seconds = number * 3600
    elif unit == "d":
        seconds = number * 86400
    else:
        await interaction.response.send_message(
            "❌ Invalid period unit, use 'h' or 'd'.",
            ephemeral=True,
        )
        return

    # Calculate the timestamp for the start of the period to query tickets created since then
    since = int(time.time()) - seconds
    category_value = category.value.lower()

    # Build the appropriate query based on whether the user wants all categories or a specific category, and execute it
    if category_value == "all":
        query = """
            SELECT channel_id, opened_at, closed_at, category, transcript_url
            FROM tickets
            WHERE opened_at >= ?
            ORDER BY opened_at DESC
        """
        params: tuple[int] | tuple[int, str] = (since,)
        category_label = "all"
    else:
        category_name = TICKET_CATEGORIES[category_value]
        query = """
                        SELECT channel_id, opened_at, closed_at, category, transcript_url
            FROM tickets
            WHERE opened_at >= ?
              AND category = ?
            ORDER BY opened_at DESC
        """
        params = (since, category_name)
        category_label = category_name

    # Execute the query and fetch all matching tickets
    cursor = await interaction.client.db.execute(query, params)
    rows = await cursor.fetchall()

    # If there are no tickets, we send a message instead of an embed with pagination, since there would be no pages to paginate through
    if not rows:
        await interaction.response.send_message(
            f"No **{category_label}** tickets were created in the last **{period}**.",
            ephemeral=True,
        )
        return

    # Build the list of embeds for the pagination view based on the query results
    pages = await _build_history_embeds(
        guild=interaction.guild,
        guild_id=interaction.guild.id,
        rows=rows,
        category_label=category_label,
        period_label=period,
    )

    view = TicketHistoryPaginationView(
        interaction_user_id=interaction.user.id,
        pages=pages,
    )

    await interaction.response.send_message(
        embed=pages[0],
        view=view,
        ephemeral=True,
    )