"""Guinevere channels package — M14 Channels (W16).

Built-in channel adapters for WhatsApp, Gmail, X/Twitter, and Telegram.
All channels are local-runtime-only with CONFIG_MISSING markers when
credentials are not provisioned (D2 pattern).
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ChannelId(str, Enum):
    """Canonical channel identifiers."""

    WHATSAPP = "whatsapp"
    GMAIL = "gmail"
    X = "x"
    TELEGRAM = "telegram"


class ChannelStatus(str, Enum):
    """Runtime status for a channel adapter."""

    READY = "ready"
    CONFIG_MISSING = "config_missing"
    ERROR = "error"


# ---- Lazy channel registry (populated on first access) ----

_REGISTRY: dict[ChannelId, type] = {}


def register_channel(channel_id: ChannelId, adapter_cls: type) -> None:
    """Register a channel adapter class."""
    _REGISTRY[channel_id] = adapter_cls


def get_channel_class(channel_id: ChannelId) -> type | None:
    """Return the adapter class for *channel_id*, or None."""
    return _REGISTRY.get(channel_id)


def list_channels() -> list[ChannelId]:
    """Return all registered channel IDs."""
    return list(_REGISTRY.keys())


def _populate_registry() -> None:
    """Import and register all built-in channel adapters."""
    from .gmail import GmailAdapter  # noqa: F401
    from .telegram import TelegramAdapter  # noqa: F401
    from .whatsapp import WhatsAppAdapter  # noqa: F401
    from .x import XAdapter  # noqa: F401


# Auto-populate on first registry access.
_populated = False


def _ensure_populated() -> None:
    global _populated  # noqa: PLW0603
    if not _populated:
        _populate_registry()
        _populated = True


def get_all_channel_statuses() -> dict[str, str]:
    """Return status map for all registered channels.

    Returns a dict of {channel_id: status_string} where status is one of
    "ready", "config_missing", or "error".
    """
    _ensure_populated()
    statuses: dict[str, str] = {}
    for cid, cls in _REGISTRY.items():
        try:
            instance = cls()
            if hasattr(instance, "is_config_missing") and instance.is_config_missing:
                statuses[cid.value] = ChannelStatus.CONFIG_MISSING.value
            else:
                statuses[cid.value] = ChannelStatus.READY.value
        except Exception:
            statuses[cid.value] = ChannelStatus.ERROR.value
    return statuses


__all__ = [
    "ChannelId",
    "ChannelStatus",
    "get_all_channel_statuses",
    "get_channel_class",
    "list_channels",
    "register_channel",
]
