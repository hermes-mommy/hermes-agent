"""Hermes command plugins — HIGH feasibility group (S3.1).

Registers all 8 migrated Discord slash commands as Hermes plugin handlers:
/status, /mood, /help, /safeword, /new, /history, /casual, /focus.
"""

from __future__ import annotations

from typing import Any

from . import casual, focus, help, history, mood, new_session, safeword, status

__all__ = [
    "register",
    "status",
    "mood",
    "help",
    "safeword",
    "new_session",
    "history",
    "casual",
    "focus",
]


def register(ctx: Any) -> None:
    """Register all 8 HIGH feasibility commands with the Hermes plugin context.

    Args:
        ctx: The Hermes PluginContext instance.
    """
    for module in (
        status,
        mood,
        help,
        safeword,
        new_session,
        history,
        casual,
        focus,
    ):
        module.register(ctx)