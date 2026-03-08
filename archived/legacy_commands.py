# Legacy commands - Not in use anymore as of v1.0.1

'''# ===| Slash command group |===
#
# Main command plus subcommands for `/ticketstats <category>`
# everything related to them is handled here
#
ticketstats = app_commands.Group(
    name="ticketstats",
    description="Show ticket statistics"
)
tree.add_command(ticketstats)


# `/ticketstats <appeals>`
#
# Displays information for the selected time period
# for the appeal category of tickets
#
@ticketstats.command(name="appeals", description="Stats for Appeal tickets")
@app_commands.describe(days="How many days back to include")
async def ticketstats_appeals(interaction: discord.Interaction, days: int):
    await run_ticket_stats(interaction, days, "appeals")


# `/ticketstats <general>`
#
# Displays information for the selected time period
# for the general category of tickets
#
@ticketstats.command(name="general", description="Stats for General tickets")
@app_commands.describe(days="How many days back to include")
async def ticketstats_general(interaction: discord.Interaction, days: int):
    await run_ticket_stats(interaction, days, "general")


# `/ticketstats <reports>`
#
# Displays information for the selected time period
# for the report category of tickets
#
@ticketstats.command(name="reports", description="Stats for Report tickets")
@app_commands.describe(days="How many days back to include")
async def ticketstats_reports(interaction: discord.Interaction, days: int):
    await run_ticket_stats(interaction, days, "reports")


# `/ticketstats <all>`
#
# Displays information for the selected time period
# for all of the ticket categories
#
@ticketstats.command(name="all", description="Stats for all ticket categories")
@app_commands.describe(days="How many days back to include")
async def ticketstats_all(interaction: discord.Interaction, days: int):
    await run_ticket_stats(interaction, days, None)'''