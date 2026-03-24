# Necessary imports
import discord
from collections.abc import Iterable

from cogs.lists.allowed_roles import STATS_ALLOWED_ROLES
from cogs.lists.database_perms import DATABASE_PERMS
from cogs.lists.manage_user_perms import MANAGE_USER_PERMS
from cogs.lists.support_roles import SUPPORT_ROLES
from cogs.lists.ticket_categories import TICKET_CATEGORIES



# Users with max perms (bypasses role requirements)
PRIVILEGED_USERS = set()

# Log channel for ticket events (persisted in DB, loaded on startup)
LOG_CHANNEL_ID: list[int | None] = [None]


# Runtime-manageable permission role categories (used by dev!perms)
PERMISSION_ROLE_CATEGORY_LABELS: dict[str, str] = {
    "stats": "Ticket Stats Roles",
    "database": "Database Roles",
    "manage": "Manage Max-Perms Roles",
    "support": "Support Staff Roles",
}

_PERMISSION_ROLE_TARGETS: dict[str, list[str] | set[str] | dict[str, object]] = {
    "stats": STATS_ALLOWED_ROLES,
    "database": DATABASE_PERMS,
    "manage": MANAGE_USER_PERMS,
    "support": SUPPORT_ROLES,
}

_DEFAULT_PERMISSION_ROLE_VALUES: dict[str, set[str]] = {
    "stats": set(STATS_ALLOWED_ROLES),
    "database": set(DATABASE_PERMS),
    "manage": set(MANAGE_USER_PERMS),
    "support": set(SUPPORT_ROLES),
}


# ===| Permission role management |===
#
# The functions below manage the role names stored in the lists/dicts defined above, which are used for permission checks throughout the bot. 
# This allows for dynamic updates to permissions without needing to restart or edit code, and also provides a single source of truth for what 
# roles are considered privileged in each category.

def is_valid_permission_role_category(category: str) -> bool:
    return category in _PERMISSION_ROLE_TARGETS


# Returns the current role names for a category, used for display and validation purposes
def get_permission_roles_for_category(category: str) -> list[str]:
    target = _PERMISSION_ROLE_TARGETS.get(category)
    if target is None:
        return []

    if isinstance(target, list):
        return list(target)
    if isinstance(target, dict):
        return sorted(target.keys())
    return sorted(target)


# Returns the default role names for a category, used for resetting to defaults and for reference in help text
def get_default_permission_roles_for_category(category: str) -> set[str]:
    return set(_DEFAULT_PERMISSION_ROLE_VALUES.get(category, set()))


# Applies a list of role names to the appropriate target based on the category
def _apply_roles_to_target(category: str, roles: Iterable[str]) -> None:
    target = _PERMISSION_ROLE_TARGETS[category]
    cleaned = [r.strip() for r in roles if isinstance(r, str) and r.strip()]

    if isinstance(target, list):
        target.clear()
        for role_name in cleaned:
            if role_name not in target:
                target.append(role_name)
        return

    if isinstance(target, dict):
        target.clear()
        for role_name in cleaned:
            target[role_name] = True
        return

    target.clear()
    target.update(cleaned)


# Adds a role to a permission role category, returns True if successful
def add_permission_role_to_category(category: str, role_name: str) -> bool:
    if category not in _PERMISSION_ROLE_TARGETS:
        return False

    normalized = role_name.strip()
    if not normalized:
        return False

    current = set(get_permission_roles_for_category(category))
    if normalized in current:
        return False

    current.add(normalized)
    _apply_roles_to_target(category, current)
    return True


# Returns False if the category doesn't exist, the role name is invalid, or the role isn't currently in the category
def remove_permission_role_from_category(category: str, role_name: str) -> bool:
    if category not in _PERMISSION_ROLE_TARGETS:
        return False

    normalized = role_name.strip()
    if not normalized:
        return False

    current = set(get_permission_roles_for_category(category))
    if normalized not in current:
        return False

    current.remove(normalized)
    _apply_roles_to_target(category, current)
    return True


# Resets all permission role categories to their default values
def reset_permission_roles_to_defaults() -> None:
    for category, default_values in _DEFAULT_PERMISSION_ROLE_VALUES.items():
        _apply_roles_to_target(category, default_values)


# Loads overrides from database and applies them on top of the defaults
def apply_permission_role_overrides(
    rows: list[tuple[str, str, str]],
) -> None:
    """Apply DB-backed role overrides on top of file-based defaults."""
    reset_permission_roles_to_defaults()

    for category, role_name, action in rows:
        if not is_valid_permission_role_category(category):
            continue

        normalized = role_name.strip()
        if not normalized:
            continue

        if action == "add":
            add_permission_role_to_category(category, normalized)
        elif action == "remove":
            remove_permission_role_from_category(category, normalized)



# ===| Permission checks |===

# v1.3.1+ - Granted server owners automatic privileged access
def has_privileged_access(member: discord.Member) -> bool:
    return member.id in PRIVILEGED_USERS or member.id == member.guild.owner_id


# Determines if someone is “staff” for message logging purposes
def is_staff(member: discord.Member) -> bool:
    if has_privileged_access(member):
        return True
    return any(role.name in SUPPORT_ROLES for role in member.roles)

# Users who are able to view ticket stats
def has_stats_permission(member: discord.Member) -> bool:
    if has_privileged_access(member):
        return True
    return any(role.name in STATS_ALLOWED_ROLES for role in member.roles)

# Users who are allowed to view ticket history (Administrator+ only)
def has_tickethistory_permission(member: discord.Member) -> bool:
    if has_privileged_access(member):
        return True
    admin_plus_roles = {"Admin Permissions", "Owner", "System-Admin", "Administrator"}
    return any(role.name in admin_plus_roles for role in member.roles)

# Users who can wipe the databse and view the wipe log
def has_database_permission(member: discord.Member) -> bool:
    if has_privileged_access(member):
        return True
    return any(role.name in DATABASE_PERMS for role in member.roles)

# Users who are allowed to add/remove max perms to/from other users
def has_manage_perms_permission(member: discord.Member) -> bool:
    if has_privileged_access(member):
        return True
    return any (role.name in MANAGE_USER_PERMS for role in member.roles)

# Defines what is considered to be a ticket category
def get_ticket_category(channel: discord.TextChannel) -> str | None:
    category = getattr(channel, "category", None)
    return category.name if category else None