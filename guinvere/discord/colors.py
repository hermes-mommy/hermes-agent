"""
Discord embed color constants and helpers for Guinevere.

This module defines the canonical color palette for all Discord embeds
used in Guinevere. Colors are sourced from DiscordUXSpec v1.0 §4.1
with user-verified overrides documented below.

Usage:
    from guinvere.discord.colors import PRIMARY, color_for_mood, as_hex
"""

from __future__ import annotations

from typing import Final


# ── Canonical Constants (DiscordUXSpec §4.1 + User Override) ────────────────

PRIMARY: Final[int] = 0x6B21A8
"""Default brand colour — status embeds, info embeds.
   Hex: #6B21A8. Source: User override ✅ DiscordUXSpec ✅."""

ALERT: Final[int] = 0xDC2626
"""Errors, SEV0/SEV1, denials, red embeds.
   Hex: #DC2626. Source: User override ✅ DiscordUXSpec ✅."""

WARNING: Final[int] = 0xCA8A04
"""Warnings, cautionary notices.
   Hex: #CA8A04. User override accepted — maps to gold/yellow.
   Note: DiscordUXSpec §4.1 defines warnings as Orange (#EA580C).
   The ORANGE constant is provided below for future differentiation."""

ACHIEVEMENT: Final[int] = 0xCA8A04
"""Rewards, streaks, achievements, gold embeds.
   Hex: #CA8A04. Source: User override ✅ DiscordUXSpec ✅."""

SUCCESS: Final[int] = 0x16A34A
"""Completions, approvals, safe mode, green embeds.
   Hex: #16A34A. Source: DiscordUXSpec §4.1."""

INFO: Final[int] = 0xCA8A04
"""Info notices, SEV3.
   Hex: #CA8A04. P2 batch maps INFO and WARNING to gold (#CA8A04)
   per user direction. Provides a distinct name for semantic use."""

ORANGE: Final[int] = 0xEA580C
"""Future orange constant per DiscordUXSpec §4.1.
   Hex: #EA580C. Defined here as a documented caveat for adoption
   when the user elects to differentiate warnings from achievements.
   Not currently used as a primary P2 colour."""

NEUTRAL: Final[int] = 0x6B7280
"""Neutral/gray embeds.
Hex: #6B7280. Non-canonical extension beyond DiscordUXSpec §4.1."""


# ── Extra Colors (Non-Canonical Extensions) ─────────────────────────────────

INFO_BLUE: Final[int] = 0x2563EB
"""Info embeds. Non-canonical extension (beyond DiscordUXSpec §4.1)."""

PERSONA: Final[int] = 0x9333EA
"""Persona-related embeds. Non-canonical extension (beyond DiscordUXSpec §4.1)."""

SURVEILLANCE: Final[int] = 0x0891B2
"""Surveillance embeds. Non-canonical extension (beyond DiscordUXSpec §4.1)."""

FINANCE: Final[int] = 0x059669
"""Finance embeds. Non-canonical extension (beyond DiscordUXSpec §4.1)."""


# ── Mood-to-Colour Mapping ──────────────────────────────────────────────────

MOOD_COLORS: Final[dict[str, int]] = {
    "content": SUCCESS,
    "pleased": ACHIEVEMENT,
    "disappointed": WARNING,
    "angry": ALERT,
    "silent": NEUTRAL,
}
"""Maps Guinevere mood names to embed colours.

Keys are lowercase mood names. Values reference the canonical constants
defined above. This mapping is used by P2-012 (/status) and subsequent
mood-aware commands.
"""


# ── Helpers ─────────────────────────────────────────────────────────────────

def color_for_mood(mood: str) -> int:
    """Return the embed colour integer for a given mood name.

    Args:
        mood: A lowercase mood name (e.g. "content", "angry", "silent").

    Returns:
        The integer colour value for the mood, or PRIMARY if the mood
        is not recognised.

    Example:
        >>> color_for_mood("angry")
        0xDC2626
        >>> color_for_mood("unknown")
        0x6B21A8
    """
    return MOOD_COLORS.get(mood, PRIMARY)


def as_hex(color: int) -> str:
    """Format an integer colour as a CSS-style hex string.

    Args:
        color: An integer colour value (e.g. 0x6B21A8).

    Returns:
        A six-digit hex string with leading hash, e.g. "#6B21A8".

    Example:
        >>> as_hex(0x6B21A8)
        '#6B21A8'
        >>> as_hex(0xDC2626)
        '#DC2626'
    """
    return f"#{color:06X}"