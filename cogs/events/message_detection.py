# Necessary imports
import re
import time
import discord
from datetime import datetime, timezone

from main.bot import(
    client,
    TICKETS_BOT_ID
)

from cogs.permissions import(
    get_ticket_category,
    is_staff,
    LOG_CHANNEL_ID,
)

from cogs.lists.opening_messages import OPEN_MARKERS
from cogs.lists.closing_messages import CLOSE_MARKERS
from development.dev_commands import handle_dev_command_message



# Pre-compiled regex for Discord user mentions (<@id> or <@!id>)
_MENTION_RE = re.compile(r"<@!?(\d+)>")
_SNOWFLAKE_RE = re.compile(r"(?<!\d)(\d{17,20})(?!\d)")
_TRANSCRIPT_URL_RE = re.compile(r"https://dashboard\.tickets\.bot/manage/\d+/transcripts/view/\d+")
_AT_HANDLE_RE = re.compile(r"@([A-Za-z0-9_.-]{2,32})")
_REASON_LINE_RE = re.compile(r"(?i)^(?:close\s*reason|reason)\s*[:\-]\s*(.+)$")
_REASON_ONLY_LABEL_RE = re.compile(r"(?i)^(?:close\s*reason|reason)\s*[:\-]?$")
_REASON_INLINE_RE = re.compile(r"(?i)\breason\b\s*[:\-]\s*(.+)$")
TRANSCRIPT_BASE_URL = "https://dashboard.tickets.bot/manage/{guild_id}/transcripts/view/{transcript_id}"


# Extracts a user ID from either a Discord mention or raw snowflake text
def _extract_user_id(text: str) -> int | None:
    mention_match = _MENTION_RE.search(text)
    if mention_match:
        return int(mention_match.group(1))

    snowflake_match = _SNOWFLAKE_RE.search(text)
    if snowflake_match:
        return int(snowflake_match.group(1))

    return None


# Attempts to resolve a member ID by matching username/display name fragments inside free-form text
def _resolve_user_id_from_name_text(guild: discord.Guild, text: str) -> int | None:
    cleaned_text = "".join(ch.lower() for ch in text if ch.isalnum())
    if not cleaned_text:
        return None

    candidates: list[int] = []
    for member in guild.members:
        if member.bot:
            continue

        display_clean = "".join(ch.lower() for ch in member.display_name if ch.isalnum())
        name_clean = "".join(ch.lower() for ch in member.name if ch.isalnum())

        # Ignore tiny names to reduce accidental matches.
        if len(display_clean) >= 4 and display_clean in cleaned_text:
            candidates.append(member.id)
            continue
        if len(name_clean) >= 4 and name_clean in cleaned_text:
            candidates.append(member.id)

    unique_ids = list(dict.fromkeys(candidates))
    if len(unique_ids) == 1:
        return unique_ids[0]
    return None


# Fallback for opener detection: inspect channel-specific member overwrites and pick a real user.
async def _find_opener_from_channel_overwrites(channel: discord.TextChannel) -> int | None:
    candidates: list[int] = []

    for target in channel.overwrites.keys():
        member: discord.Member | None = None

        if isinstance(target, discord.Member):
            member = target
        elif isinstance(target, discord.Role):
            continue

        # Some overwrite targets may not be resolved Member objects yet.
        # Try to resolve them by ID via cache/API so we still get opener mentions.
        if member is None:
            target_id = getattr(target, "id", None)
            if not isinstance(target_id, int):
                continue

            member = channel.guild.get_member(target_id)
            if member is None:
                try:
                    member = await channel.guild.fetch_member(target_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    continue

        if member.bot:
            continue

        candidates.append(member.id)

    # Deterministic selection when multiple member overwrites are present
    # Do not exclude staff members here, because staff can also open tickets
    if candidates:
        return min(candidates)
    return None


# Builds transcript URL; falls back to channel_id as transcript_id if no ticket number exists
def _build_transcript_url(guild_id: int, channel_name: str, channel_id: int) -> str:
    channel_suffix_match = re.search(r"(\d+)$", channel_name)
    transcript_id = int(channel_suffix_match.group(1)) if channel_suffix_match else channel_id
    return TRANSCRIPT_BASE_URL.format(guild_id=guild_id, transcript_id=transcript_id)


# Attempts to locate an existing transcript URL inside an embed's text
def _find_transcript_url_in_embed(embed: discord.Embed) -> str | None:
    searchable_texts = [embed.title or "", embed.description or ""]
    searchable_texts.extend(field.name or "" for field in embed.fields)
    searchable_texts.extend(field.value or "" for field in embed.fields)

    for text in searchable_texts:
        match = _TRANSCRIPT_URL_RE.search(text)
        if match:
            return match.group(0)
    return None


# Searches an embed's fields (by name hints) then description for the first Discord user ID
def _find_user_id_in_embed(embed: discord.Embed, guild: discord.Guild, *field_name_hints: str) -> int | None:
    for field in embed.fields:
        if any(hint in field.name.lower() for hint in field_name_hints):
            detected_id = _extract_user_id(field.value or "")
            if detected_id:
                return detected_id
            detected_by_name = _resolve_user_id_from_name_text(guild, field.value or "")
            if detected_by_name:
                return detected_by_name

    detected_in_description = _extract_user_id(embed.description or "")
    if detected_in_description:
        return detected_in_description

    detected_by_name_in_description = _resolve_user_id_from_name_text(guild, embed.description or "")
    if detected_by_name_in_description:
        return detected_by_name_in_description

    # Conservative fallback: only look into likely user-related fields to avoid channel-id false positives
    user_field_tokens = ("user", "member", "created", "opened", "closed", "by", "requester", "author")
    for field in embed.fields:
        if any(token in field.name.lower() for token in user_field_tokens):
            detected_id = _extract_user_id(field.value or "")
            if detected_id:
                return detected_id
            detected_by_name = _resolve_user_id_from_name_text(guild, field.value or "")
            if detected_by_name:
                return detected_by_name

    return None


# Attempts to resolve user ID by querying guild members with @handle-like tokens from text.
async def _resolve_user_id_via_member_query(guild: discord.Guild, text: str) -> int | None:
    handle_candidates = [h.lower() for h in _AT_HANDLE_RE.findall(text or "")]
    if not handle_candidates:
        return None

    for handle in dict.fromkeys(handle_candidates):
        try:
            matches = await guild.query_members(query=handle, limit=12)
        except (discord.Forbidden, discord.HTTPException):
            continue

        exact_matches = []
        handle_clean = "".join(ch for ch in handle if ch.isalnum())
        for member in matches:
            if member.bot:
                continue
            names = [member.name, member.display_name, member.global_name or ""]
            lowered = [n.lower() for n in names if n]
            normalized = ["".join(ch for ch in n if ch.isalnum()) for n in lowered]

            # Support values like "@Admin | 0bi0" by allowing normalized substring matches
            if (
                handle in lowered
                or any(handle in n for n in lowered)
                or any(handle_clean and handle_clean in n for n in normalized)
            ):
                exact_matches.append(member.id)

        unique_ids = list(dict.fromkeys(exact_matches))
        if len(unique_ids) == 1:
            return unique_ids[0]

    return None


# Query-based fallback for embed user detection when no mention/snowflake is present.
async def _find_user_id_in_embed_query_fallback(
    embed: discord.Embed,
    guild: discord.Guild,
    *field_name_hints: str,
) -> int | None:
    hinted_values: list[str] = []
    for field in embed.fields:
        if any(hint in field.name.lower() for hint in field_name_hints):
            hinted_values.append(field.value or "")

    for text in hinted_values:
        found_id = await _resolve_user_id_via_member_query(guild, text)
        if found_id:
            return found_id

    for text in [embed.description or "", *(f.value or "" for f in embed.fields)]:
        found_id = await _resolve_user_id_via_member_query(guild, text)
        if found_id:
            return found_id

    return None


def _strip_embed_markup(text: str) -> str:
    cleaned = text.replace("**", "").replace("__", "").replace("`", "")
    return cleaned.strip()


# Extract close reason from fields first, then fallback to label-style lines in embed text.
def _extract_close_reason_from_embed(embed: discord.Embed) -> str | None:
    for field in embed.fields:
        if any(hint in field.name.lower() for hint in ("reason", "close reason")):
            reason = _strip_embed_markup(field.value or "")
            if reason:
                return reason

    searchable_blocks = [embed.description or ""]
    searchable_blocks.extend(field.value or "" for field in embed.fields)
    searchable_blocks.extend(f"{field.name or ''}\n{field.value or ''}" for field in embed.fields)

    for block in searchable_blocks:
        if not block:
            continue

        lines = [_strip_embed_markup(line) for line in block.splitlines()]
        expect_reason_value_on_next_line = False
        for index, line in enumerate(lines):
            if not line:
                continue

            if expect_reason_value_on_next_line:
                normalized = _normalize_close_reason(line)
                if normalized:
                    return normalized
            expect_reason_value_on_next_line = False

            line_match = _REASON_LINE_RE.match(line)
            if line_match:
                reason = _normalize_close_reason(line_match.group(1))
                if reason:
                    return reason
                expect_reason_value_on_next_line = True
                continue

            inline_match = _REASON_INLINE_RE.search(line)
            if inline_match:
                reason = _normalize_close_reason(inline_match.group(1))
                if reason:
                    return reason
                expect_reason_value_on_next_line = True
                continue

            if _REASON_ONLY_LABEL_RE.match(line):
                for next_line in lines[index + 1:]:
                    normalized = _normalize_close_reason(next_line.strip(" :-"))
                    if normalized:
                        return normalized

    return None


def _normalize_close_reason(reason: str | None) -> str | None:
    if not reason:
        return None

    cleaned = _strip_embed_markup(reason).strip(" \t\r\n:-")
    if not cleaned:
        return None

    placeholders = {
        "not provided",
        "none",
        "n/a",
        "na",
        "no reason",
        "no reason provided",
        "not specified",
    }
    if cleaned.lower() in placeholders:
        return None

    return cleaned


def _extract_close_reason_from_text_blocks(*blocks: str) -> str | None:
    for block in blocks:
        if not block:
            continue

        lines = [_strip_embed_markup(line) for line in block.splitlines()]
        expect_reason_value_on_next_line = False
        for line in lines:
            if not line:
                continue

            if expect_reason_value_on_next_line:
                normalized = _normalize_close_reason(line)
                if normalized:
                    return normalized
            expect_reason_value_on_next_line = False

            line_match = _REASON_LINE_RE.match(line)
            if line_match:
                normalized = _normalize_close_reason(line_match.group(1))
                if normalized:
                    return normalized
                expect_reason_value_on_next_line = True
                continue

            inline_match = _REASON_INLINE_RE.search(line)
            if inline_match:
                normalized = _normalize_close_reason(inline_match.group(1))
                if normalized:
                    return normalized
                expect_reason_value_on_next_line = True
                continue

    return None



# Helper function to get a human-readable (AKA not ID) channel name
async def get_readable_channel_name(message: discord.Message) -> str:
    channel = message.channel

    name = getattr(channel, "name", None)
    if isinstance(name, str) and name.strip():
        return name

    # If the event channel object is partial/uncached, try guild cache by ID
    if message.guild:
        cached_channel = message.guild.get_channel(message.channel.id)
        cached_name = getattr(cached_channel, "name", None)
        if isinstance(cached_name, str) and cached_name.strip():
            return cached_name

        cached_thread = message.guild.get_thread(message.channel.id)
        thread_name = getattr(cached_thread, "name", None)
        if isinstance(thread_name, str) and thread_name.strip():
            return thread_name

    # Last-resort API fetch for channels not present in local cache
    try:
        fetched_channel = await client.fetch_channel(message.channel.id)
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        fetched_channel = None

    fetched_name = getattr(fetched_channel, "name", None)
    if isinstance(fetched_name, str) and fetched_name.strip():
        return fetched_name

    recipient = getattr(channel, "recipient", None)
    if recipient:
        recipient_name = getattr(recipient, "display_name", None) or getattr(recipient, "name", None)
        if isinstance(recipient_name, str) and recipient_name.strip():
            return recipient_name

    return "Unknown Channel"



# Creates the definition related to ticket-opening
@client.event
async def on_message(message: discord.Message):
    now = int(time.time())

    # Run developer-prefixed commands before ticket logging/event parsing.
    if await handle_dev_command_message(message):
        return

    # Log messages that happen inside ticket channels
    if message.guild and isinstance(message.channel, discord.TextChannel):

        # Only logs messages for channels that are known tickets
        cursor = await client.db.execute(
            "SELECT 1 FROM tickets WHERE channel_id=?",
            (message.channel.id,)
        )
        is_ticket = await cursor.fetchone()

        if is_ticket:
            staff_flag = 1 if (not message.author.bot and is_staff(message.author)) else 0

            await client.db.execute(
                """
                INSERT INTO messages(channel_id, author_id, is_staff, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (
                    message.channel.id,
                    message.author.id,
                    staff_flag,
                    now
                )
            )
            # Adds to DB
            await client.db.commit()

    # Safe DM category logging
    category_name = getattr(message.channel, "category", None)
    category_name = category_name.name if category_name else None

    if message.author.bot:
        channel_name = await get_readable_channel_name(message)
        print(
            "[BOT MSG] |",
            # "author_id=", message.author.id     # Uncomment if you want to log bot message authors (even though it's always just the tickets bot)
            "channel=", channel_name, "|",
            "embeds=", len(message.embeds), "|",
            "category=", category_name
        )

    # Ticket opening / closing detection
    if message.author.bot and message.embeds and message.guild and isinstance(message.channel, discord.TextChannel):
        incoming_embed = message.embeds[0]
        embed_author_name = (incoming_embed.author.name or "") if incoming_embed.author else ""
        embed_footer_text = (incoming_embed.footer.text or "") if incoming_embed.footer else ""
        text_blob = " ".join([
            incoming_embed.title or "",
            incoming_embed.description or "",
            embed_author_name,
            embed_footer_text,
            message.content or "",
            *(field.name or "" for field in incoming_embed.fields),
            *(field.value or "" for field in incoming_embed.fields),
        ])

        # Check if any of the markers are present in the embed text to identify ticket openings
        if any(marker in text_blob.lower() for marker in OPEN_MARKERS):
            cursor = await client.db.execute(
                "SELECT 1 FROM tickets WHERE channel_id=?",
                (message.channel.id,)
            )
            exists = await cursor.fetchone()

            if not exists:
                category_name = get_ticket_category(message.channel)
                opened_by_id = _find_user_id_in_embed(
                    incoming_embed,
                    message.guild,
                    "opened by", "created by", "requester", "user", "member", "opener"
                )
                if not opened_by_id:
                    opened_by_id = await _find_user_id_in_embed_query_fallback(
                        incoming_embed,
                        message.guild,
                        "opened by", "created by", "requester", "user", "member", "opener"
                    )
                if not opened_by_id:
                    opened_by_id = _extract_user_id(getattr(message.channel, "topic", "") or "")
                if not opened_by_id:
                    opened_by_id = await _find_opener_from_channel_overwrites(message.channel)

                # Insert new ticket record into the database
                await client.db.execute(
                    "INSERT INTO tickets(channel_id, category, opened_at, closed_at, opened_by) VALUES (?, ?, ?, NULL, ?)",
                    (message.channel.id, category_name, now, opened_by_id)
                )
                await client.db.commit()

                # 💻 CONSOLE OUTPUT: Ticket opened
                open_log = f"🎫 Ticket OPEN: {message.channel.id} | category: {category_name}"
                print(open_log)
                print("-" * len(open_log))

                # Send log embed to the configured log channel
                if LOG_CHANNEL_ID[0]:
                    log_channel = client.get_channel(LOG_CHANNEL_ID[0])
                    if isinstance(log_channel, discord.TextChannel):
                        opened_by_value = f"<@{opened_by_id}>" if opened_by_id else "Not detected"
                        channel_url = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}"
                        log_embed = discord.Embed(
                            title="Ticket Opened",
                            color=0x57f287,
                            timestamp=datetime.fromtimestamp(now, tz=timezone.utc)
                        )
                        log_embed.add_field(
                            name="Details",
                            value=(
                                f"- <:category:1483140351798542466> Category: {category_name or 'Unknown'}\n"
                                f"- <:channel:1483136296447905986> Channel: [#{message.channel.name}]({channel_url})\n"
                                f"- <:ticketid:1483110102260121691> Channel ID: `{message.channel.id}`\n"
                                f"- <:open:1483106542428360846> Opened By: {opened_by_value}\n"
                                f"—------------------------------------------"
                            ),
                            inline=False
                        )
                        
                        try:
                            await log_channel.send(embed=log_embed)
                        except (discord.Forbidden, discord.HTTPException):
                            pass

        # Ticket closing detection — capture closed_by + reason before the channel is deleted
        elif any(marker in text_blob.lower() for marker in CLOSE_MARKERS):
            cursor = await client.db.execute(
                "SELECT 1 FROM tickets WHERE channel_id=? AND closed_at IS NULL",
                (message.channel.id,)
            )
            if await cursor.fetchone():
                opened_by_id = _find_user_id_in_embed(
                    incoming_embed,
                    message.guild,
                    "opened by", "created by", "requester", "user", "member", "opener"
                )
                if not opened_by_id:
                    opened_by_id = await _find_user_id_in_embed_query_fallback(
                        incoming_embed,
                        message.guild,
                        "opened by", "created by", "requester", "user", "member", "opener"
                    )
                closed_by_id = _find_user_id_in_embed(
                    incoming_embed,
                    message.guild,
                    "closed by", "closed", "closer", "moderator", "staff", "user", "member"
                )
                if not closed_by_id:
                    closed_by_id = await _find_user_id_in_embed_query_fallback(
                        incoming_embed,
                        message.guild,
                        "closed by", "closed", "closer", "moderator", "staff", "user", "member"
                    )

                if closed_by_id == message.author.id:
                    closed_by_id = None

                close_reason = _normalize_close_reason(_extract_close_reason_from_embed(incoming_embed))
                if not close_reason:
                    close_reason = _extract_close_reason_from_text_blocks(
                        message.content or "",
                        incoming_embed.title or "",
                        incoming_embed.description or "",
                        embed_author_name,
                        embed_footer_text,
                        *(field.name or "" for field in incoming_embed.fields),
                        *(field.value or "" for field in incoming_embed.fields),
                    )

                transcript_url = _find_transcript_url_in_embed(incoming_embed)
                if not transcript_url:
                    transcript_url = _build_transcript_url(message.guild.id, message.channel.name, message.channel.id)

                await client.db.execute(
                    """
                    UPDATE tickets
                    SET
                        opened_by = COALESCE(opened_by, ?),
                        closed_by = ?,
                        close_reason = COALESCE(?, close_reason),
                        transcript_url = COALESCE(?, transcript_url)
                    WHERE channel_id=? AND closed_at IS NULL
                    """,
                    (opened_by_id, closed_by_id, close_reason, transcript_url, message.channel.id)
                )
                await client.db.commit()

        
    
    # This code is so ass