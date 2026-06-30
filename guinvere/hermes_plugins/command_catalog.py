"""Hermes-native command catalog — command metadata without Discord dependencies.

Provides the canonical command listing for help generation and introspection
within the Hermes plugin system. Mirrors the data from ``guinvere.discord.commands``
without importing any Discord-specific types.
"""

from __future__ import annotations

from typing import Final

_COMMAND_CATEGORIES: Final[dict[str, tuple[str, ...]]] = {
    "core": ("status", "mood", "help", "safeword", "new", "history"),
    "loop": (
        "loop-start",
        "loop-stop",
        "loop-pause",
        "loop-resume",
        "loops",
        "evidence",
        "loop-priority",
    ),
    "memory": ("memory-search", "memory-add", "memory-forget", "memory-export"),
    "surveillance": (
        "surveillance-status",
        "surveillance-pause",
        "surveillance-resume",
    ),
    "finance": ("cost", "budget", "cost-alert"),
    "system": (
        "approve",
        "deny",
        "approve-all",
        "focus",
        "casual",
        "consent",
        "punishment",
        "reward",
    ),
    "admin": ("restart-service", "backup-now", "health-check", "clear-cache"),
}


def command_categories() -> dict[str, tuple[str, ...]]:
    """Return command names grouped by canonical category."""
    return dict(_COMMAND_CATEGORIES)


def command_count() -> int:
    """Return the total number of canonical commands."""
    return sum(len(cmds) for cmds in _COMMAND_CATEGORIES.values())
