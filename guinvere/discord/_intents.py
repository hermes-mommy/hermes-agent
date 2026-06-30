"""Discord gateway intent configuration for Guinevere (non-deprecated home).

This module is the active replacement for ``src/discord/intents.py``.
All production code should import from ``._intents``, not ``.intents``.

P2-003 requires the three privileged Developer Portal intents to be mirrored
in code: Message Content, Server Members, and Presence. The extra standard
intents below are non-privileged interaction surfaces needed by later P2
steps for reactions, messages, and voice channel orchestration.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Protocol, cast


class DiscordIntents(Protocol):
    """Subset of discord.Intents used by Guinevere."""

    guilds: bool
    members: bool
    presences: bool
    message_content: bool
    messages: bool
    reactions: bool
    voice_states: bool


class DiscordIntentsFactory(Protocol):
    """Factory interface exposed by discord.Intents."""

    def default(self) -> DiscordIntents:
        """Return discord.py default intents."""
        ...


class DiscordModule(Protocol):
    """Subset of the external discord.py module used by this file."""

    Intents: DiscordIntentsFactory


@dataclass(frozen=True)
class IntentValidationResult:
    """Structured result for Discord intent validation."""

    valid: bool
    enabled: tuple[str, ...]
    missing: tuple[str, ...]


REQUIRED_PRIVILEGED_INTENTS: tuple[str, ...] = (
    "message_content",
    "members",
    "presences",
)

STANDARD_OPERATIONAL_INTENTS: tuple[str, ...] = (
    "guilds",
    "messages",
    "reactions",
    "voice_states",
)


REQUIRED_INTENTS: tuple[str, ...] = REQUIRED_PRIVILEGED_INTENTS + STANDARD_OPERATIONAL_INTENTS


def get_intents() -> DiscordIntents:
    """Build Guinevere's Discord gateway intents.

    Developer Portal state already enables Message Content, Server Members,
    and Presence. This function mirrors that state in code so discord.py can
    subscribe to the same gateway events at runtime.
    """

    discord_module = cast(DiscordModule, cast(object, importlib.import_module("discord")))
    intents = discord_module.Intents.default()

    intents.message_content = True
    intents.members = True
    intents.presences = True

    intents.guilds = True
    intents.messages = True
    intents.reactions = True
    intents.voice_states = True

    result = validate_intents(intents)
    if not result.valid:
        missing = ", ".join(result.missing)
        raise RuntimeError(f"Discord intents missing required flags: {missing}")

    return intents


def validate_intents(intents: DiscordIntents) -> IntentValidationResult:
    """Validate that the required P2-003 Discord intents are enabled."""

    states: tuple[tuple[str, bool], ...] = (
        ("message_content", intents.message_content),
        ("members", intents.members),
        ("presences", intents.presences),
        ("guilds", intents.guilds),
        ("messages", intents.messages),
        ("reactions", intents.reactions),
        ("voice_states", intents.voice_states),
    )

    enabled = tuple(name for name, active in states if active)
    missing = tuple(name for name, active in states if not active)

    return IntentValidationResult(valid=not missing, enabled=enabled, missing=missing)
