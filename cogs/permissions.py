# Necessary imports
import discord



# User roles that are registered as Support Representatives
SUPPORT_ROLES = {
    "Admin Permissions",
    "Owner",
    "System-Admin",
    "Administrator",
    "Sr. Mod",
    "Mod",
    "Support"
}

# Roles allowed to execute the command `/ticketstats <category>`
STATS_ALLOWED_ROLES = [
    "Admin Permissions",
    "Owner",
    "System-Admin",
    "Administrator",
    "General Tickets Manager",
    "Reports Manager",
    "Appeals Manager"
]

# Users allowed to wipe the databse and view its audit log
DATABASE_PERMS = [
    "Admin Permissions",
    "Owner",
    "System-Admin"
]

# Users allowed to add/remove users to/from the max perms list
MANAGE_USER_PERMS = [
    "Owner"
]

# Users with max perms (bypasses role requirements)
PRIVILEGED_USERS = {
    000000000000000000   # Example user
}

# Ticket categories (pretty self-explanatory)
TICKET_CATEGORIES = {
    "appeals": "Appeals",
    "general": "General Tickets",
    "reports": "Player-Reports"
}



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