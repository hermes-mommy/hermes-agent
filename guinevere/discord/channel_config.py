"""Channel configuration and per-channel command permission gating.

This module defines:
- ``ChannelConfig`` — maps logical channel keys to Discord snowflake IDs.
- ``ChannelPermissions`` — maps channel keys to sets of allowed command names.
- ``CHANNEL_COMMAND_ALLOW`` — the default permission mapping used at runtime.
- ``is_command_allowed()`` — the gate function called before dispatching a slash
  command to determine whether it is permitted in the originating channel.

Channel IDs are **never** hardcoded here.  They arrive via environment variables
(``DISCORD_CHANNEL_*``) or a YAML/dict config object, both resolved at startup.

The module is pure data — no Discord API calls, no ``discord.utils.get`` lookups,
no gateway connections.  It depends only on the standard library and the
``_command_registry`` module for the canonical command-name set.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Final

from guinevere.discord._command_registry import EXPECTED_COMMAND_NAME_SET

logger: Final[logging.Logger] = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Channel config keys — canonical order used across the project
# ---------------------------------------------------------------------------

CHANNEL_KEYS: Final[tuple[str, ...]] = (
    "general",
    "commands_hq",
    "media_gallery",
    "notifications",
    "admin_internal",
)

# Mapping from ChannelConfig attribute name → environment variable name.
_ENV_MAP: Final[dict[str, str]] = {
    "general": "DISCORD_CHANNEL_GENERAL",
    "commands_hq": "DISCORD_CHANNEL_COMMANDS_HQ",
    "media_gallery": "DISCORD_CHANNEL_MEDIA_GALLERY",
    "notifications": "DISCORD_CHANNEL_NOTIFICATIONS",
    "admin_internal": "DISCORD_CHANNEL_ADMIN_INTERNAL",
}

# Mapping from env-var name → ChannelConfig attribute name (inverse of above).
_ENV_TO_KEY: Final[dict[str, str]] = {v: k for k, v in _ENV_MAP.items()}


# ---------------------------------------------------------------------------
# ChannelConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChannelConfig:
    """Discord channel snowflake IDs for the five operational channels.

    Instances are frozen — once created they cannot be mutated.  Use
    ``from_env()`` or ``from_dict()`` to construct.
    """

    general: int
    commands_hq: int
    media_gallery: int
    notifications: int
    admin_internal: int

    # -- Construction helpers ------------------------------------------------

    @classmethod
    def from_env(cls) -> ChannelConfig:
        """Build a ``ChannelConfig`` from environment variables.

        Required environment variables (all must be set):

        - ``DISCORD_CHANNEL_GENERAL``
        - ``DISCORD_CHANNEL_COMMANDS_HQ``
        - ``DISCORD_CHANNEL_MEDIA_GALLERY``
        - ``DISCORD_CHANNEL_NOTIFICATIONS``
        - ``DISCORD_CHANNEL_ADMIN_INTERNAL``

        Raises
        ------
        EnvironmentError
            If any required variable is missing or not a valid integer.
        """

        values: dict[str, int] = {}
        missing: list[str] = []
        for key, env_var in _ENV_MAP.items():
            raw = os.environ.get(env_var)
            if raw is None:
                missing.append(env_var)
                continue
            try:
                values[key] = int(raw)
            except ValueError:
                raise EnvironmentError(
                    f"Environment variable {env_var} must be a valid integer, "
                    f"got {raw!r}."
                ) from None

        if missing:
            raise EnvironmentError(
                "Missing required environment variables for ChannelConfig: "
                + ", ".join(sorted(missing))
            )

        return cls(**values)

    @classmethod
    def from_dict(cls, d: dict[str, int]) -> ChannelConfig:
        """Build a ``ChannelConfig`` from a dictionary (e.g. YAML config).

        The dictionary must contain all five channel keys with integer values.

        Raises
        ------
        KeyError
            If any required key is missing.
        TypeError
            If a value is not an integer.
        """

        missing = [k for k in CHANNEL_KEYS if k not in d]
        if missing:
            raise KeyError(
                "Missing required channel config keys: "
                + ", ".join(sorted(missing))
            )

        values: dict[str, int] = {}
        for key in CHANNEL_KEYS:
            val = d[key]
            if not isinstance(val, int):
                raise TypeError(
                    f"Channel config key {key!r} must be an int, "
                    f"got {type(val).__name__}: {val!r}"
                )
            values[key] = val

        return cls(**values)

    # -- Lookup --------------------------------------------------------------

    def channel_id_to_key(self, channel_id: int) -> str | None:
        """Return the config key whose snowflake matches *channel_id*.

        Returns ``None`` if no configured channel matches.
        """
        for key in CHANNEL_KEYS:
            if getattr(self, key) == channel_id:
                return key
        return None


# ---------------------------------------------------------------------------
# ChannelPermissions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChannelPermissions:
    """Mapping of channel config keys to sets of allowed command names.

    Special values within a set:

    * ``{"__all__"}`` — all commands are permitted in that channel.
    * ``set()`` (empty) — **no** commands are permitted (read-only / bot-only
      posting channel).

    If a channel key is absent from the mapping, the default is to **deny all**
    (equivalent to an empty set).
    """

    permissions: dict[str, frozenset[str]] = field(
        default_factory=lambda: {
            key: frozenset() for key in CHANNEL_KEYS
        }
    )

    def allowed_commands(self, channel_key: str) -> frozenset[str]:
        """Return the allowed command set for *channel_key*.

        Returns an empty frozenset if the key is not present.
        """
        return self.permissions.get(channel_key, frozenset())


# ---------------------------------------------------------------------------
# Default permission mapping
# ---------------------------------------------------------------------------

_WILDCARD: Final[str] = "__all__"

CHANNEL_COMMAND_ALLOW: Final[dict[str, frozenset[str]]] = {
    "general": frozenset({"status", "mood", "help", "casual", "safeword"}),
    "commands_hq": frozenset({_WILDCARD}),
    "media_gallery": frozenset({"mood", "help", "memory-search"}),
    "notifications": frozenset(),  # no commands — bot-only posting
    "admin_internal": frozenset({_WILDCARD}),
}


def build_default_permissions() -> ChannelPermissions:
    """Return a ``ChannelPermissions`` instance from the default allow mapping."""
    return ChannelPermissions(permissions=CHANNEL_COMMAND_ALLOW)


# ---------------------------------------------------------------------------
# Gate function
# ---------------------------------------------------------------------------


def is_command_allowed(
    channel_id: int,
    command_name: str,
    channel_config: ChannelConfig,
    permissions: ChannelPermissions,
) -> bool:
    """Determine whether *command_name* may be invoked in the given channel.

    Parameters
    ----------
    channel_id:
        The Discord snowflake of the channel where the command was issued.
    command_name:
        The slash-command name (e.g. ``"status"``, ``"loop-start"``).
    channel_config:
        The resolved ``ChannelConfig`` mapping keys to snowflake IDs.
    permissions:
        The ``ChannelPermissions`` instance governing per-channel allowlists.

    Returns
    -------
    bool
        ``True`` if the command is allowed, ``False`` otherwise.

    Notes
    -----
    * If *channel_id* does not match any configured channel, the command is
      **allowed** by default and a warning is logged.
    * If the channel's allowed set contains ``"__all__"``, the command is
      allowed regardless of its name.
    * If the channel's allowed set is empty, no commands pass.
    """

    # Resolve channel_id → config key
    key = channel_config.channel_id_to_key(channel_id)

    if key is None:
        # Unknown channel — default-allow with warning
        logger.warning(
            "Command %r invoked in unconfigured channel %s — defaulting to "
            "ALLOW.  Register the channel in ChannelConfig to remove this "
            "warning.",
            command_name,
            channel_id,
        )
        return True

    allowed = permissions.allowed_commands(key)

    # Wildcard: all commands pass
    if _WILDCARD in allowed:
        return True

    # Exact set membership check
    return command_name in allowed
