# Necessary imports
import discord

from cogs.lists.allowed_roles import STATS_ALLOWED_ROLES
from cogs.lists.database_perms import DATABASE_PERMS
from cogs.lists.manage_user_perms import MANAGE_USER_PERMS
from cogs.lists.support_roles import SUPPORT_ROLES
from cogs.lists.ticket_categories import TICKET_CATEGORIES



# Users with max perms (bypasses role requirements)
PRIVILEGED_USERS = set()

# Log channel for ticket events (persisted in DB, loaded on startup)
LOG_CHANNEL_ID: list[int | None] = [None]



# Permission checks

# Determines if someone is “staff” for message logging purposes
def is_staff(member: discord.Member) -> bool:
    if member.id in PRIVILEGED_USERS:
        return True
    return any(role.name in SUPPORT_ROLES for role in member.roles)

# Users who are able to view ticket stats
def has_stats_permission(member: discord.Member) -> bool:
    if member.id in PRIVILEGED_USERS:
        return True
    return any(role.name in STATS_ALLOWED_ROLES for role in member.roles)

# Users who can wipe the databse and view the wipe log
def has_database_permission(member: discord.Member) -> bool:
    if member.id in PRIVILEGED_USERS:
        return True
    return any(role.name in DATABASE_PERMS for role in member.roles)

# Users who are allowed to add/remove max perms to/from other users
def has_manage_perms_permission(member: discord.Member) -> bool:
    if member.id in PRIVILEGED_USERS:
        return True
    return any (role.name in MANAGE_USER_PERMS for role in member.roles)

# Defines what is considered to be a ticket category
def get_ticket_category(channel: discord.TextChannel) -> str | None:
    category = getattr(channel, "category", None)
    return category.name if category else None