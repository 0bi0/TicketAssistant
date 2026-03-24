# Necessary imports
import discord

from main.bot import client



@client.event
async def on_guild_join(guild: discord.Guild):
    owner = guild.owner
    if owner is None:
        try:
            owner = await guild.fetch_member(guild.owner_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            owner = None

    if owner is None:
        return

    embed = discord.Embed(
        title="Thanks for adding Ticket Assistant",
        description=(
            f"Hey there {owner.mention}, thanks for picking me as your ticket assistant! I am now connected to your server. Use the quick-start steps below to finish setup."
        ),
        color=discord.Color.from_rgb(182, 182, 182),
    )
    embed.add_field(
        name="Quick Start",
        value=(
            "1. Run `/logchannelset <channel>` to configure ticket event logs.\n"
            "2. Run `/help` to review commands and required roles.\n"
            "3. Use `/ticketstats` after activity starts to verify tracking."
        ),
        inline=False,
    )
    embed.add_field(
        name="Developer Tools",
        value=(
            "If you are the server owner, you can use `dev!` commands such as `dev!help` and `dev!panel` in order to manage the bot."
        ),
        inline=False,
    )
    embed.set_footer(text=f"Server: {guild.name} | ID: {guild.id}")

    try:
        await owner.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        return
