# Necessary imports
import re


_TIMESTAMPED_LOG_RE = re.compile(r"^\[(\d{2}:\d{2}:\d{2})\]\s*(.*)$")
_BRACKET_TAG_RE = re.compile(r"^\[[^\]]+\]\s*")
_IN_GUILD_RE = re.compile(r"\s+in\s+guild\s+\d+", re.IGNORECASE)
_GUILD_ID_RE = re.compile(r"\bguild\s*id\s*[:=]?\s*\d+\b", re.IGNORECASE)


# Filters decorative/boot-time lines that should not appear in the dev logs panel
def is_visual_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if all(ch in "=-_ \\|/<>.`'" for ch in stripped):
        return True

    startup_prefixes = (
        "Version:",
        "Status:",
        "Bot logged in successfully",
        "Bot reconnected as",
    )
    if stripped.startswith(startup_prefixes):
        return True
    return False


# Converts raw runtime log lines into concise, aliased dev panel events
def alias_console_line(raw_line: str) -> str | None:
    match = _TIMESTAMPED_LOG_RE.match(raw_line)
    if not match:
        return None

    timestamp, content = match.groups()
    content = content.strip()
    if is_visual_noise_line(content):
        return None

    alias = "📝 EVENT"
    details = content

    if content.startswith("[🧩 DEV PANEL OPEN]"):
        alias = "🧩 DEV_PANEL_OPEN"
        details = _BRACKET_TAG_RE.sub("", content)
    elif content.startswith("[🧰 DEV PERMS OPEN]"):
        alias = "🧰 DEV_PERMS_OPEN"
        details = _BRACKET_TAG_RE.sub("", content)
    elif content.startswith("[🧰 PERMS ADD]"):
        alias = "🧰 PERMS_ADD"
        details = _BRACKET_TAG_RE.sub("", content)
    elif content.startswith("[🧰 PERMS REMOVE]"):
        alias = "🧰 PERMS_REMOVE"
        details = _BRACKET_TAG_RE.sub("", content)
    elif content.startswith("[🟢 DEV ADD]"):
        alias = "🟢 DEV_ADD"
        details = _BRACKET_TAG_RE.sub("", content)
    elif content.startswith("[🔴 DEV REMOVE]"):
        alias = "🔴 DEV_REMOVE"
        details = _BRACKET_TAG_RE.sub("", content)
    elif content.startswith("[👑 PRIV USERS VIEW]"):
        alias = "👑 PRIV_USERS_VIEW"
        details = _BRACKET_TAG_RE.sub("", content)
    elif content.startswith("[🟢 MAX PERMS ADD]"):
        alias = "🟢 MAX_PERMS_ADD"
        details = _BRACKET_TAG_RE.sub("", content)
    elif content.startswith("[🔴 MAX PERMS REMOVE]"):
        alias = "🔴 MAX_PERMS_REMOVE"
        details = _BRACKET_TAG_RE.sub("", content)
    elif content.startswith("🎫 Ticket OPEN:"):
        alias = "🎫 TICKET_OPEN"
        details = content
    elif content.startswith("🗑️"):
        alias = "🗑️ TICKET_CLOSE"
        details = content
    elif content.startswith("[BOT MSG]"):
        alias = "🤖 BOT_MESSAGE"
        details = content
    elif content.startswith("Migrating DB:"):
        alias = "🛠️ DB_MIGRATION"
        details = content

    details = _IN_GUILD_RE.sub("", details)
    details = _GUILD_ID_RE.sub("", details).strip()
    details = " ".join(details.split())

    if alias == "📝 EVENT" or not details:
        return None

    return f"[{timestamp}] {alias} | {details}"