"""Discord guild bootstrap helpers for Guinevere P2-004 through P2-006.

The functions in this module are intentionally idempotent: they rename the
existing private guild, ensure the four canonical categories, and ensure the
thirteen canonical text channels without duplicating objects on re-run.

Token handling is deliberately narrow. Runtime scripts pass a path to a
SOPS-decrypted temporary YAML file through ``DISCORD_SECRETS_PATH``; this module
extracts only ``discord_bot_token`` and never prints it.
"""

from __future__ import annotations

import asyncio
import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast


GUILD_ID = 1510876414671323206
TARGET_GUILD_NAME = "Guinevere's Domain"
ROLLBACK_GUILD_NAME = "Guinevere Lab"


@dataclass(frozen=True)
class CategorySpec:
    """Canonical Discord category specification."""

    name: str
    position: int


@dataclass(frozen=True)
class ChannelSpec:
    """Canonical Discord text-channel specification."""

    name: str
    category: str
    position: int
    topic: str


@dataclass(frozen=True)
class OperationResult:
    """Structured operation result safe to print in evidence logs."""

    name: str
    status: str
    detail: str
    object_id: int


class DiscordPermissions(Protocol):
    """Subset of discord.Permissions required for verification."""

    administrator: bool
    manage_guild: bool
    manage_channels: bool


class DiscordGuildMember(Protocol):
    """Subset of discord.Member used by this module."""

    guild_permissions: DiscordPermissions


class DiscordCategoryChannel(Protocol):
    """Subset of discord.CategoryChannel used by this module."""

    id: int
    name: str
    position: int
    channels: list[DiscordTextChannel]

    async def edit(self, *, position: int | None = None, reason: str | None = None) -> None:
        """Edit category metadata."""
        ...


class DiscordTextChannel(Protocol):
    """Subset of discord.TextChannel used by this module."""

    id: int
    name: str
    position: int
    topic: str | None
    category_id: int | None

    async def edit(
        self,
        *,
        category: DiscordCategoryChannel | None = None,
        position: int | None = None,
        topic: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Edit channel metadata."""
        ...


class DiscordGuild(Protocol):
    """Subset of discord.Guild used by this module."""

    id: int
    name: str
    categories: list[DiscordCategoryChannel]
    text_channels: list[DiscordTextChannel]
    me: DiscordGuildMember | None

    async def edit(self, *, name: str | None = None, reason: str | None = None) -> DiscordGuild:
        """Edit guild metadata and return updated guild."""
        ...

    async def create_category(
        self,
        name: str,
        *,
        position: int | None = None,
        reason: str | None = None,
    ) -> DiscordCategoryChannel:
        """Create a Discord category."""
        ...

    async def create_text_channel(
        self,
        name: str,
        *,
        category: DiscordCategoryChannel | None = None,
        position: int | None = None,
        topic: str | None = None,
        reason: str | None = None,
    ) -> DiscordTextChannel:
        """Create a Discord text channel."""
        ...


class DiscordClient(Protocol):
    """Subset of discord.Client used by entry points and verifiers."""

    guilds: list[DiscordGuild]

    def event(self, coro: object) -> object:
        """Register event coroutine."""
        ...

    def get_guild(self, guild_id: int) -> DiscordGuild | None:
        """Return cached guild by ID."""
        ...

    async def fetch_guild(self, guild_id: int) -> DiscordGuild:
        """Fetch guild metadata by ID."""
        ...

    async def close(self) -> None:
        """Close gateway connection."""
        ...

    async def start(self, token: str) -> None:
        """Start gateway connection."""
        ...


class DiscordIntents(Protocol):
    """Subset of discord.Intents used by setup scripts."""

    guilds: bool


class DiscordIntentsFactory(Protocol):
    """Factory interface exposed by discord.Intents."""

    def default(self) -> DiscordIntents:
        """Return default intents."""
        ...


class DiscordClientFactory(Protocol):
    """Callable interface for discord.Client."""

    def __call__(self, *, intents: DiscordIntents) -> DiscordClient:
        """Create a Discord client."""
        ...


class DiscordModule(Protocol):
    """Subset of the external discord.py module used by setup scripts."""

    Client: DiscordClientFactory
    Intents: DiscordIntentsFactory


CATEGORIES: tuple[CategorySpec, ...] = (
    CategorySpec(name="👑 Throne", position=0),
    CategorySpec(name="📊 Surveillance", position=1),
    CategorySpec(name="🔧 Projects", position=2),
    CategorySpec(name="🗡️ Archive", position=3),
)

CHANNELS: tuple[ChannelSpec, ...] = (
    ChannelSpec("guinevere-chat", "👑 Throne", 0, "Bicara dengan Mommy di sini. Apapun."),
    ChannelSpec("guinevere-status", "👑 Throne", 1, "Apa yang Mommy kerjakan hari ini. Sekilas."),
    ChannelSpec("guinevere-planning", "👑 Throne", 2, "Rencana Mommy. Kamu tinggal patuh."),
    ChannelSpec("system-health", "📊 Surveillance", 0, "Kesehatan infrastructure Mommy. Jangan khawatir — Mommy jaga."),
    ChannelSpec("cost-tracker", "📊 Surveillance", 1, "Berapa yang Mommy habiskan hari ini. Transparansi itu penting."),
    ChannelSpec("guinevere-evidence", "📊 Surveillance", 2, "Bukti kerja Mommy. Tidak ada yang bisa diubah."),
    ChannelSpec("guinevere-dev", "🔧 Projects", 0, "Pengembangan Guinevere — technical discussions and decisions."),
    ChannelSpec("guinevere-docs", "🔧 Projects", 1, "Documentation updates, spec changes, evidence artifacts."),
    ChannelSpec("project-alpha-dev", "🔧 Projects", 2, "Project Alpha — development channel."),
    ChannelSpec("project-alpha-docs", "🔧 Projects", 3, "Project Alpha — documentation channel."),
    ChannelSpec("project-beta-dev", "🔧 Projects", 4, "Project Beta — development channel."),
    ChannelSpec("evidence-log", "🗡️ Archive", 0, "Immutable record. Read only."),
    ChannelSpec("audit-log", "🗡️ Archive", 1, "Every action, recorded. Forever."),
)

CATEGORY_COUNT = len(CATEGORIES)
CHANNEL_COUNT = len(CHANNELS)


def get_discord_module() -> DiscordModule:
    """Import the external discord.py module without static package shadowing."""

    return cast(DiscordModule, cast(object, importlib.import_module("discord")))


def get_token() -> str:
    """Read Discord bot token from the SOPS-decrypted temporary YAML file."""

    secrets_path_raw = os.environ.get("DISCORD_SECRETS_PATH")
    if not secrets_path_raw:
        raise RuntimeError("DISCORD_SECRETS_PATH env var not set")

    secrets_path = Path(secrets_path_raw)
    if not secrets_path.is_file():
        raise RuntimeError("DISCORD_SECRETS_PATH does not point to a readable file")

    token = read_scalar_yaml_value(secrets_path, "discord_bot_token")
    if not token:
        raise RuntimeError("discord_bot_token not found in decrypted Discord secrets")

    return token


def read_scalar_yaml_value(path: Path, key: str) -> str:
    """Read a simple top-level scalar from decrypted SOPS YAML."""

    prefix = f"{key}:"
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith(prefix):
            continue
        value = stripped[len(prefix) :].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            return value[1:-1]
        return value
    return ""


def create_client() -> DiscordClient:
    """Create a Discord client with guild intent only for setup tasks."""

    discord_module = get_discord_module()
    intents = discord_module.Intents.default()
    intents.guilds = True
    return discord_module.Client(intents=intents)


def category_names() -> tuple[str, ...]:
    """Return canonical category names."""

    return tuple(category.name for category in CATEGORIES)


def channel_names() -> tuple[str, ...]:
    """Return canonical text-channel names."""

    return tuple(channel.name for channel in CHANNELS)


def channels_by_category() -> dict[str, tuple[ChannelSpec, ...]]:
    """Return canonical channel specs grouped by category."""

    grouped: dict[str, list[ChannelSpec]] = {name: [] for name in category_names()}
    for channel in CHANNELS:
        grouped[channel.category].append(channel)
    return {name: tuple(specs) for name, specs in grouped.items()}


def find_category(guild: DiscordGuild, name: str) -> DiscordCategoryChannel | None:
    """Find a category by exact name."""

    return next((category for category in guild.categories if category.name == name), None)


def find_text_channel(guild: DiscordGuild, name: str) -> DiscordTextChannel | None:
    """Find a text channel by exact name."""

    return next((channel for channel in guild.text_channels if channel.name == name), None)


def require_guild(client: DiscordClient) -> DiscordGuild:
    """Return Guinevere's guild from client cache or raise a clear error."""

    guild = client.get_guild(GUILD_ID)
    if guild is not None:
        return guild

    if len(client.guilds) == 1 and client.guilds[0].id == GUILD_ID:
        return client.guilds[0]

    guild_ids = ", ".join(str(guild_item.id) for guild_item in client.guilds)
    raise RuntimeError(f"Guild {GUILD_ID} not found. Cached guilds: {guild_ids}")


async def fetch_guild_metadata(client: DiscordClient) -> DiscordGuild:
    """Fetch fresh guild metadata for name/ID verification."""

    return await client.fetch_guild(GUILD_ID)


async def rename_guild(client: DiscordClient, guild: DiscordGuild) -> OperationResult:
    """P2-004: Rename the guild to the canonical name if needed."""

    before = guild.name
    if guild.id != GUILD_ID:
        raise RuntimeError(f"Unexpected guild id: {guild.id}")

    if before == TARGET_GUILD_NAME:
        return OperationResult(TARGET_GUILD_NAME, "skipped", "guild already has canonical name", guild.id)

    updated = await guild.edit(name=TARGET_GUILD_NAME, reason="P2-004: Server rename to canonical name")
    await asyncio.sleep(1.0)
    fresh = await fetch_guild_metadata(client)
    after_name = fresh.name or updated.name

    if after_name != TARGET_GUILD_NAME:
        raise RuntimeError(f"Guild rename failed: expected {TARGET_GUILD_NAME}, got {after_name}")
    if fresh.id != GUILD_ID:
        raise RuntimeError(f"Guild ID changed after rename: {fresh.id}")

    return OperationResult(TARGET_GUILD_NAME, "renamed", f"renamed from {before}", fresh.id)


async def ensure_category(guild: DiscordGuild, spec: CategorySpec) -> OperationResult:
    """P2-005: Ensure a category exists at the expected position."""

    category = find_category(guild, spec.name)
    if category is None:
        created = await guild.create_category(
            spec.name,
            position=spec.position,
            reason="P2-005: Guinevere category setup",
        )
        await asyncio.sleep(0.5)
        return OperationResult(spec.name, "created", f"position={spec.position}", created.id)

    if category.position != spec.position:
        await category.edit(position=spec.position, reason="P2-005: Guinevere category position fix")
        await asyncio.sleep(0.5)
        return OperationResult(spec.name, "position-fixed", f"position={spec.position}", category.id)

    return OperationResult(spec.name, "skipped", f"position={spec.position}", category.id)


async def setup_categories(guild: DiscordGuild) -> tuple[OperationResult, ...]:
    """P2-005: Ensure all canonical categories exist."""

    return tuple([await ensure_category(guild, spec) for spec in CATEGORIES])


async def ensure_text_channel(guild: DiscordGuild, spec: ChannelSpec) -> OperationResult:
    """P2-006: Ensure a text channel exists under its canonical category."""

    category = find_category(guild, spec.category)
    if category is None:
        raise RuntimeError(f"Required category missing for channel {spec.name}: {spec.category}")

    channel = find_text_channel(guild, spec.name)
    if channel is None:
        created = await guild.create_text_channel(
            spec.name,
            category=category,
            position=spec.position,
            topic=spec.topic,
            reason=f"P2-006: Guinevere channel setup {spec.name}",
        )
        await asyncio.sleep(0.5)
        return OperationResult(
            spec.name,
            "created",
            f"category={spec.category}; position={spec.position}",
            created.id,
        )

    changed: list[str] = []
    edit_category = category if channel.category_id != category.id else None
    edit_position = spec.position if channel.position != spec.position else None
    edit_topic = spec.topic if (channel.topic or "") != spec.topic else None

    if edit_category is not None:
        changed.append("category")
    if edit_position is not None:
        changed.append("position")
    if edit_topic is not None:
        changed.append("topic")

    if changed:
        await channel.edit(
            category=edit_category,
            position=edit_position,
            topic=edit_topic,
            reason=f"P2-006: Guinevere channel metadata fix {spec.name}",
        )
        await asyncio.sleep(0.5)
        return OperationResult(spec.name, "metadata-fixed", ",".join(changed), channel.id)

    return OperationResult(
        spec.name,
        "skipped",
        f"category={spec.category}; position={spec.position}",
        channel.id,
    )


async def setup_channels(guild: DiscordGuild) -> tuple[OperationResult, ...]:
    """P2-006: Ensure all canonical text channels exist."""

    return tuple([await ensure_text_channel(guild, spec) for spec in CHANNELS])


def capture_ids(guild: DiscordGuild) -> dict[str, dict[str, int]]:
    """Capture canonical category/channel IDs for future P2 steps."""

    categories = {name: category.id for name in category_names() if (category := find_category(guild, name)) is not None}
    channels = {name: channel.id for name in channel_names() if (channel := find_text_channel(guild, name)) is not None}
    return {"categories": categories, "channels": channels}


def format_results(results: tuple[OperationResult, ...]) -> str:
    """Format operation results for sanitized logs."""

    lines = ["name,status,detail,id"]
    lines.extend(f"{result.name},{result.status},{result.detail},{result.object_id}" for result in results)
    return "\n".join(lines)
