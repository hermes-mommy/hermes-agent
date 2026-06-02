"""Discord permission, topic, and bot-scope helpers for P2-007 through P2-009.

This module intentionally reads Discord object identifiers from the P2-006
``channel-ids.yaml`` artifact and discovers guild/member/role identifiers at
runtime. Token handling is delegated to the existing SOPS temp-file wrapper via
``DISCORD_SECRETS_PATH`` and ``src.discord.guild_setup.get_token``.
"""

from __future__ import annotations

import http.client
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import quote

from src.discord.guild_setup import CHANNELS, get_token

CHANNEL_IDS_PATH = Path("docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml")
DISCORD_API_HOST = "discord.com"
API_PREFIX = "/api/v10"
TARGET_GUILD_NAME = "Guinevere's Domain"
LEAST_PRIVILEGE_PERMISSIONS = 2_147_599_472
LEAST_PRIVILEGE_PERMISSIONS_HEX = "0x8000F870"

VIEW_CHANNEL = 1 << 10
SEND_MESSAGES = 1 << 11
MANAGE_MESSAGES = 1 << 13
EMBED_LINKS = 1 << 14
ATTACH_FILES = 1 << 15
READ_MESSAGE_HISTORY = 1 << 16
ADD_REACTIONS = 1 << 6
MANAGE_CHANNELS = 1 << 4
MANAGE_WEBHOOKS = 1 << 29
ADMINISTRATOR = 1 << 3

NORMAL_USER_ALLOW = VIEW_CHANNEL | READ_MESSAGE_HISTORY | SEND_MESSAGES | ADD_REACTIONS
EVIDENCE_USER_ALLOW = VIEW_CHANNEL | READ_MESSAGE_HISTORY
EVIDENCE_USER_DENY = SEND_MESSAGES | MANAGE_MESSAGES
BOT_ALLOW = VIEW_CHANNEL | READ_MESSAGE_HISTORY | SEND_MESSAGES | EMBED_LINKS | ATTACH_FILES | ADD_REACTIONS
BOT_EVIDENCE_DENY = MANAGE_MESSAGES | MANAGE_CHANNELS | MANAGE_WEBHOOKS
EVERYONE_DENY = VIEW_CHANNEL

APPEND_ONLY_CHANNELS = frozenset({"guinevere-evidence", "evidence-log", "audit-log"})
TOPICS = {spec.name: spec.topic for spec in CHANNELS}


@dataclass(frozen=True)
class ChannelIdMap:
    """Category and channel IDs captured by P2-006."""

    categories: dict[str, str]
    channels: dict[str, str]


@dataclass(frozen=True)
class GuildContext:
    """Runtime-discovered Discord guild and actor identifiers."""

    guild_id: str
    guild_name: str
    owner_id: str
    bot_id: str
    bot_role_ids: tuple[str, ...]


@dataclass(frozen=True)
class ChannelRecord:
    """Normalized Discord channel object."""

    id: str
    name: str
    type: int
    parent_id: str
    topic: str
    overwrites: tuple[PermissionOverwrite, ...]


@dataclass(frozen=True)
class PermissionOverwrite:
    """Normalized Discord permission overwrite."""

    id: str
    type: int
    allow: int
    deny: int


@dataclass(frozen=True)
class PermissionResult:
    """Permission operation result safe for evidence logs."""

    channel: str
    everyone_private: bool
    owner_read: bool
    owner_send_expected: bool
    owner_send_actual: bool
    bot_send: bool
    append_only: bool


@dataclass(frozen=True)
class TopicResult:
    """Topic reconciliation result safe for evidence logs."""

    channel: str
    topic_ok: bool
    changed: bool


@dataclass(frozen=True)
class AdminReview:
    """Bot permission-scope review result."""

    guild_id: str
    guild_name: str
    bot_id: str
    administrator: bool
    permissions_bitfield: int
    least_privilege_permissions: int
    invite_url: str
    decision: str


def read_channel_ids(path: Path = CHANNEL_IDS_PATH) -> ChannelIdMap:
    """Read the simple P2-006 channel ID YAML artifact."""

    if not path.is_file():
        raise RuntimeError(f"channel IDs file not found: {path}")

    current_section = ""
    categories: dict[str, str] = {}
    channels: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        if not raw_line.startswith(" ") and raw_line.endswith(":"):
            current_section = raw_line[:-1]
            continue
        if current_section not in {"categories", "channels"}:
            continue
        if ":" not in raw_line:
            continue
        key_raw, value_raw = raw_line.split(":", 1)
        key = key_raw.strip().strip("'").strip('"')
        value = value_raw.strip().strip("'").strip('"')
        if current_section == "categories":
            categories[key] = value
        else:
            channels[key] = value

    expected_channels = set(TOPICS)
    missing = expected_channels - set(channels)
    if missing:
        raise RuntimeError("channel IDs missing: " + ",".join(sorted(missing)))
    return ChannelIdMap(categories=categories, channels=channels)


def discord_request(
    token: str,
    method: str,
    path: str,
    body: dict[str, object] | list[dict[str, object]] | None = None,
    reason: str = "",
) -> object:
    """Call Discord REST API and return decoded JSON or an empty object."""

    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "Guinevere-P2-007-009",
    }
    payload = b""
    if body is not None:
        payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if reason:
        headers["X-Audit-Log-Reason"] = quote(reason, safe="")

    connection = http.client.HTTPSConnection(DISCORD_API_HOST, timeout=30)
    try:
        connection.request(method, API_PREFIX + path, body=payload, headers=headers)
        response = connection.getresponse()
        response_body = response.read().decode("utf-8")
    finally:
        connection.close()

    if response.status < 200 or response.status >= 300:
        raise RuntimeError(f"Discord API {method} {path} returned HTTP {response.status}: {response_body[:200]}")
    if not response_body:
        return {}
    return cast(object, json.loads(response_body))


def require_mapping(value: object, label: str) -> dict[str, object]:
    """Require a decoded JSON mapping."""

    if not isinstance(value, dict):
        raise RuntimeError(f"{label} was not an object")
    return cast(dict[str, object], value)


def require_list(value: object, label: str) -> list[object]:
    """Require a decoded JSON list."""

    if not isinstance(value, list):
        raise RuntimeError(f"{label} was not a list")
    return cast(list[object], value)


def text_value(mapping: dict[str, object], key: str) -> str:
    """Return a string field or an empty string."""

    value = mapping.get(key)
    return value if isinstance(value, str) else ""


def int_value(mapping: dict[str, object], key: str) -> int:
    """Return an integer field or zero."""

    value = mapping.get(key)
    return value if isinstance(value, int) else 0


def discover_context(token: str) -> GuildContext:
    """Discover target guild, owner, and bot identifiers at runtime."""

    user = require_mapping(discord_request(token, "GET", "/users/@me"), "bot user")
    bot_id = text_value(user, "id")
    if not bot_id:
        raise RuntimeError("bot id missing from /users/@me")

    guilds = require_list(discord_request(token, "GET", "/users/@me/guilds"), "guild list")
    guild_candidates: list[dict[str, object]] = []
    for item in guilds:
        if isinstance(item, dict):
            guild_candidates.append(cast(dict[str, object], item))
    matching = [guild for guild in guild_candidates if text_value(guild, "name") == TARGET_GUILD_NAME]
    if not matching and len(guild_candidates) == 1:
        matching = guild_candidates
    if not matching:
        names = ",".join(text_value(guild, "name") for guild in guild_candidates)
        raise RuntimeError(f"target guild not found; guilds={names}")

    guild_id = text_value(matching[0], "id")
    guild = require_mapping(discord_request(token, "GET", f"/guilds/{guild_id}"), "guild")
    owner_id = text_value(guild, "owner_id")
    guild_name = text_value(guild, "name")
    if not owner_id:
        raise RuntimeError("guild owner_id missing")

    member = require_mapping(discord_request(token, "GET", f"/guilds/{guild_id}/members/{bot_id}"), "bot member")
    roles_raw = member.get("roles")
    role_items = cast(list[object], roles_raw) if isinstance(roles_raw, list) else []
    role_ids = tuple(role_item for role_item in role_items if isinstance(role_item, str))
    return GuildContext(guild_id=guild_id, guild_name=guild_name, owner_id=owner_id, bot_id=bot_id, bot_role_ids=role_ids)


def fetch_channels(token: str, guild_id: str) -> list[ChannelRecord]:
    """Fetch normalized guild channels via REST."""

    decoded = require_list(discord_request(token, "GET", f"/guilds/{guild_id}/channels"), "guild channels")
    records: list[ChannelRecord] = []
    for item in decoded:
        if not isinstance(item, dict):
            continue
        mapping = cast(dict[str, object], item)
        overwrites = parse_overwrites(mapping.get("permission_overwrites"))
        records.append(
            ChannelRecord(
                id=text_value(mapping, "id"),
                name=text_value(mapping, "name"),
                type=int_value(mapping, "type"),
                parent_id=text_value(mapping, "parent_id"),
                topic=text_value(mapping, "topic"),
                overwrites=overwrites,
            )
        )
    return records


def parse_overwrites(value: object) -> tuple[PermissionOverwrite, ...]:
    """Normalize Discord permission overwrites."""

    if not isinstance(value, list):
        return ()
    overwrite_items = cast(list[object], value)
    overwrites: list[PermissionOverwrite] = []
    for item in overwrite_items:
        if not isinstance(item, dict):
            continue
        mapping = cast(dict[str, object], item)
        overwrite_id = text_value(mapping, "id")
        overwrite_type = int_value(mapping, "type")
        allow = int(text_value(mapping, "allow") or "0")
        deny = int(text_value(mapping, "deny") or "0")
        if overwrite_id:
            overwrites.append(PermissionOverwrite(overwrite_id, overwrite_type, allow, deny))
    return tuple(overwrites)


def find_overwrite(channel: ChannelRecord, target_id: str, target_type: int) -> PermissionOverwrite | None:
    """Find a channel overwrite by target id and type."""

    return next((item for item in channel.overwrites if item.id == target_id and item.type == target_type), None)


def has_bits(value: int, bits: int) -> bool:
    """Return whether all requested permission bits are present."""

    return (value & bits) == bits


def set_overwrite(token: str, channel_id: str, target_id: str, target_type: int, allow: int, deny: int, reason: str) -> None:
    """Set a channel permission overwrite."""

    _ = discord_request(
        token,
        "PUT",
        f"/channels/{channel_id}/permissions/{target_id}",
        {"type": target_type, "allow": str(allow), "deny": str(deny)},
        reason=reason,
    )


def apply_permissions(token: str) -> list[PermissionResult]:
    """Apply P2-007 canonical channel permission overwrites."""

    ids = read_channel_ids()
    context = discover_context(token)
    for channel_name, channel_id in sorted(ids.channels.items()):
        append_only = channel_name in APPEND_ONLY_CHANNELS
        owner_allow = EVIDENCE_USER_ALLOW if append_only else NORMAL_USER_ALLOW
        owner_deny = EVIDENCE_USER_DENY if append_only else 0
        bot_deny = BOT_EVIDENCE_DENY if append_only else 0
        set_overwrite(token, channel_id, context.guild_id, 0, 0, EVERYONE_DENY, "P2-007: deny @everyone canonical channel visibility")
        set_overwrite(token, channel_id, context.owner_id, 1, owner_allow, owner_deny, "P2-007: allow Faiz canonical channel access")
        set_overwrite(token, channel_id, context.bot_id, 1, BOT_ALLOW, bot_deny, "P2-007: allow Guinevere bot canonical channel access")
    return verify_permissions(token)


def verify_permissions(token: str) -> list[PermissionResult]:
    """Verify P2-007 canonical permission overwrites."""

    ids = read_channel_ids()
    context = discover_context(token)
    channels = {channel.id: channel for channel in fetch_channels(token, context.guild_id)}
    results: list[PermissionResult] = []
    for channel_name, channel_id in sorted(ids.channels.items()):
        channel = channels.get(channel_id)
        if channel is None:
            raise RuntimeError(f"channel missing during permission verify: {channel_name}")
        append_only = channel_name in APPEND_ONLY_CHANNELS
        everyone = find_overwrite(channel, context.guild_id, 0)
        owner = find_overwrite(channel, context.owner_id, 1)
        bot = find_overwrite(channel, context.bot_id, 1)
        everyone_private = everyone is not None and has_bits(everyone.deny, VIEW_CHANNEL)
        owner_read = owner is not None and has_bits(owner.allow, VIEW_CHANNEL | READ_MESSAGE_HISTORY)
        owner_send_expected = not append_only
        owner_send_actual = owner is not None and has_bits(owner.allow, SEND_MESSAGES) and not has_bits(owner.deny, SEND_MESSAGES)
        bot_send = bot is not None and has_bits(bot.allow, VIEW_CHANNEL | SEND_MESSAGES | READ_MESSAGE_HISTORY)
        results.append(
            PermissionResult(
                channel=channel_name,
                everyone_private=everyone_private,
                owner_read=owner_read,
                owner_send_expected=owner_send_expected,
                owner_send_actual=owner_send_actual,
                bot_send=bot_send,
                append_only=append_only,
            )
        )
    return results


def reconcile_topics(token: str) -> list[TopicResult]:
    """Update only drifted channel topics and return verification results."""

    ids = read_channel_ids()
    context = discover_context(token)
    before = {channel.id: channel for channel in fetch_channels(token, context.guild_id)}
    changed_channels: set[str] = set()
    for channel_name, expected_topic in sorted(TOPICS.items()):
        channel_id = ids.channels[channel_name]
        current = before.get(channel_id)
        if current is None:
            raise RuntimeError(f"channel missing during topic reconcile: {channel_name}")
        if current.topic == expected_topic:
            continue
        _ = discord_request(
            token,
            "PATCH",
            f"/channels/{channel_id}",
            {"topic": expected_topic},
            reason=f"P2-008: canonical topic update {channel_name}",
        )
        changed_channels.add(channel_name)
    return verify_topics(token, changed_channels)


def verify_topics(token: str, changed_channels: set[str] | None = None) -> list[TopicResult]:
    """Verify all P2-008 channel topics."""

    changed = changed_channels or set()
    ids = read_channel_ids()
    context = discover_context(token)
    channels = {channel.id: channel for channel in fetch_channels(token, context.guild_id)}
    results: list[TopicResult] = []
    for channel_name, expected_topic in sorted(TOPICS.items()):
        channel = channels.get(ids.channels[channel_name])
        if channel is None:
            raise RuntimeError(f"channel missing during topic verify: {channel_name}")
        results.append(TopicResult(channel_name, channel.topic == expected_topic, channel_name in changed))
    return results


def fetch_roles(token: str, guild_id: str) -> list[dict[str, object]]:
    """Fetch guild roles."""

    decoded = require_list(discord_request(token, "GET", f"/guilds/{guild_id}/roles"), "guild roles")
    return [cast(dict[str, object], item) for item in decoded if isinstance(item, dict)]


def review_admin_scope(token: str) -> AdminReview:
    """Review current bot permission scope and produce least-privilege invite URL."""

    context = discover_context(token)
    roles = fetch_roles(token, context.guild_id)
    permissions = 0
    for role in roles:
        role_id = text_value(role, "id")
        if role_id not in context.bot_role_ids:
            continue
        permissions_raw = text_value(role, "permissions")
        if permissions_raw:
            permissions |= int(permissions_raw)
    administrator = has_bits(permissions, ADMINISTRATOR)
    invite_url = (
        "https://discord.com/oauth2/authorize?"
        f"client_id={context.bot_id}&permissions={LEAST_PRIVILEGE_PERMISSIONS}&scope=bot%20applications.commands"
    )
    decision = (
        "Administrator is not justified long-term; managed role/OAuth reauthorization required for safe reduction"
        if administrator
        else "Administrator already absent; current scope is reduced"
    )
    return AdminReview(
        guild_id=context.guild_id,
        guild_name=context.guild_name,
        bot_id=context.bot_id,
        administrator=administrator,
        permissions_bitfield=permissions,
        least_privilege_permissions=LEAST_PRIVILEGE_PERMISSIONS,
        invite_url=invite_url,
        decision=decision,
    )


def format_permission_results(results: list[PermissionResult]) -> str:
    """Format permission verification results as sanitized lines."""

    lines = ["channel,everyone_private,owner_read,owner_send_expected,owner_send_actual,bot_send,append_only,ok"]
    for result in results:
        owner_send_ok = result.owner_send_actual == result.owner_send_expected
        ok = result.everyone_private and result.owner_read and owner_send_ok and result.bot_send
        row = (
            f"{result.channel},{str(result.everyone_private).lower()},{str(result.owner_read).lower()},"
            f"{str(result.owner_send_expected).lower()},{str(result.owner_send_actual).lower()},"
            f"{str(result.bot_send).lower()},{str(result.append_only).lower()},{str(ok).lower()}"
        )
        lines.append(row)
    return "\n".join(lines)


def format_topic_results(results: list[TopicResult]) -> str:
    """Format topic verification results as sanitized lines."""

    lines = ["channel,topic_ok,changed,ok"]
    for result in results:
        lines.append(f"{result.channel},{str(result.topic_ok).lower()},{str(result.changed).lower()},{str(result.topic_ok).lower()}")
    return "\n".join(lines)


def format_admin_review(review: AdminReview) -> str:
    """Format admin review without secrets."""

    return "\n".join(
        [
            f"guild_id={review.guild_id}",
            f"guild_name={review.guild_name}",
            f"bot_id={review.bot_id}",
            f"administrator={str(review.administrator).lower()}",
            f"permissions_bitfield={review.permissions_bitfield}",
            f"least_privilege_permissions={review.least_privilege_permissions}",
            f"least_privilege_permissions_hex={LEAST_PRIVILEGE_PERMISSIONS_HEX}",
            f"least_privilege_invite_url={review.invite_url}",
            f"decision={review.decision}",
        ]
    )


def all_permissions_ok(results: list[PermissionResult]) -> bool:
    """Return whether all permission verification rows pass."""

    for result in results:
        if not result.everyone_private:
            return False
        if not result.owner_read:
            return False
        if result.owner_send_actual != result.owner_send_expected:
            return False
        if not result.bot_send:
            return False
    return True


def all_topics_ok(results: list[TopicResult]) -> bool:
    """Return whether all topic rows pass."""

    return all(result.topic_ok for result in results)


def token_from_environment() -> str:
    """Return token through shared helper for CLI scripts."""

    return get_token()
