"""Level threshold calculations for the Guinevere gamification system.

The level curve uses a clean quadratic formula:

    cumulative_xp_required(level) = BASE * level ^ EXPONENT

With BASE=100 and EXPONENT=2 (quadratic), this gives perfect squares:
  - Level 1:  100 XP  (100 × 1²)
  - Level 5:  2,500 XP  (100 × 5²)
  - Level 10: 10,000 XP  (100 × 10²)
  - Level 20: 40,000 XP  (100 × 20²)
  - Level 50: 250,000 XP  (100 × 50²)

The inverse is trivially: level = floor(sqrt(xp / 100))

This makes level calculations O(1) with no lookup table needed,
though a lookup table is still provided for validation and display.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

# ============================================================
# Constants
# ============================================================

LEVEL_FORMULA_BASE: Final[int] = 100
"""Base multiplier in the level formula: base * level^exp."""

LEVEL_FORMULA_EXPONENT: Final[float] = 2.0
"""Exponent in the level formula. 2.0 = quadratic (perfect squares)."""

MAX_LEVEL: Final[int] = 50
"""Maximum level achievable. XP can still accumulate beyond this."""

# ============================================================
# Core Calculation Functions (pure, stateless, O(1))
# ============================================================


def xp_for_level(level: int) -> int:
    """Return the cumulative XP required to *reach* a given level.

    Args:
        level: Target level (1..MAX_LEVEL).

    Returns:
        Cumulative XP needed. Returns 0 for level 0 or negative.

    Examples:
        >>> xp_for_level(1)
        100
        >>> xp_for_level(10)
        10000
        >>> xp_for_level(50)
        250000
    """
    if level <= 0:
        return 0
    return math.floor(LEVEL_FORMULA_BASE * level ** LEVEL_FORMULA_EXPONENT)


def calculate_level(total_xp: int) -> int:
    """Calculate the current level from total accumulated XP.

    This is the inverse of xp_for_level():
        level = floor(sqrt(total_xp / BASE))

    Args:
        total_xp: Total accumulated XP (>= 0).

    Returns:
        Current level (0 if total_xp is negative or zero).

    Examples:
        >>> calculate_level(0)
        0
        >>> calculate_level(99)
        0
        >>> calculate_level(100)
        1
        >>> calculate_level(10000)
        10
    """
    if total_xp <= 0:
        return 0
    level = math.floor(math.sqrt(total_xp / LEVEL_FORMULA_BASE))
    return min(level, MAX_LEVEL)


def xp_for_next_level(total_xp: int) -> int:
    """Return XP needed to reach the next level from current total_xp.

    Args:
        total_xp: Current total XP.

    Returns:
        XP still needed for the next level. Returns 0 if already at MAX_LEVEL.

    Examples:
        >>> xp_for_next_level(0)
        100
        >>> xp_for_next_level(99)
        1
        >>> xp_for_next_level(100)
        300  # next level is 2, which requires 400; 400 - 100 = 300
    """
    current = calculate_level(total_xp)
    if current >= MAX_LEVEL:
        return 0
    next_xp = xp_for_level(current + 1)
    return max(0, next_xp - total_xp)


def xp_progress_to_next_level(total_xp: int) -> tuple[int, int, float]:
    """Return detailed progress toward the next level.

    Args:
        total_xp: Current total XP.

    Returns:
        Tuple of (xp_in_current_level, xp_needed_for_next, progress_ratio).
        progress_ratio is in [0.0, 1.0).

    Examples:
        >>> xp_progress_to_next_level(150)
        (50, 250, 0.2)  # 50 XP into level 1, need 250 more, 20% progress
    """
    current = calculate_level(total_xp)
    if current >= MAX_LEVEL:
        return (0, 0, 1.0)

    current_threshold = xp_for_level(current)
    next_threshold = xp_for_level(current + 1)
    xp_in_level = total_xp - current_threshold
    xp_needed = next_threshold - current_threshold

    progress = xp_in_level / xp_needed if xp_needed > 0 else 0.0
    return (xp_in_level, xp_needed, progress)


# ============================================================
# Level Threshold Table (for validation and display)
# ============================================================


@dataclass(frozen=True)
class LevelInfo:
    """Immutable info for a single level."""

    level: int
    xp_required: int  # cumulative XP to reach this level
    xp_for_this_level: int  # XP delta from previous level

    @property
    def title(self) -> str | None:
        """Optional title for the level (can be customized later)."""
        return _LEVEL_TITLES.get(self.level)


def get_all_levels(max_level: int = MAX_LEVEL) -> list[LevelInfo]:
    """Return a list of all level thresholds from 1 to max_level."""
    result = []
    prev = 0
    for level in range(1, max_level + 1):
        xp_req = xp_for_level(level)
        result.append(LevelInfo(
            level=level,
            xp_required=xp_req,
            xp_for_this_level=xp_req - prev,
        ))
        prev = xp_req
    return result


# Optional level titles (milestone flavor text, can be extended)
_LEVEL_TITLES: dict[int, str] = {
    1: "Newcomer",
    5: "Apprentice",
    10: "Journeyman",
    15: "Adept",
    20: "Expert",
    25: "Master",
    30: "Grandmaster",
    35: "Sage",
    40: "Transcendent",
    45: "Legendary",
    50: "Mythic",
}
