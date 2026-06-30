"""Guinevere Gamification System — XP, levels, and skill progression.

Level formula: cumulative_xp_required = 100 * level²
  - Level 1 requires 100 XP
  - Level 10 requires 10,000 XP
  - Level 50 requires 250,000 XP

Inverse: level = floor(sqrt(total_xp / 100))

This module provides:
  - Database models for XP tracking (skill_xp, agent_xp, xp_events, level_ups, xp_multipliers)
  - Level calculation utilities
  - Async XP service for PostgreSQL operations
  - Integration with existing RewardEngine and StreakTracker
"""

from guinvere.gamification.models import (
    AgentXP,
    LevelThreshold,
    LevelUp,
    SkillXP,
    XPEvent,
    XPMultiplier,
)
from guinvere.gamification.levels import (
    calculate_level,
    xp_for_level,
    xp_for_next_level,
    xp_progress_to_next_level,
    MAX_LEVEL,
    LEVEL_FORMULA_BASE,
    LEVEL_FORMULA_EXPONENT,
)
from guinvere.gamification.service import GamificationService

__all__ = [
    # Models
    "AgentXP",
    "LevelThreshold",
    "LevelUp",
    "SkillXP",
    "XPEvent",
    "XPMultiplier",
    # Level utils
    "calculate_level",
    "xp_for_level",
    "xp_for_next_level",
    "xp_progress_to_next_level",
    "MAX_LEVEL",
    "LEVEL_FORMULA_BASE",
    "LEVEL_FORMULA_EXPONENT",
    # Service
    "GamificationService",
]
