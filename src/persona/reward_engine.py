"""
Reward Tiers Engine — Persona Reward System for Guinevere (P4-006)

Implements a five-tier reward system (T1–T5) that determines appropriate
reward levels based on task quality and streak bonuses.  Rewards are
always permitted — they are never suppressed by safe-mode or distress
activation, per PersonaDoc v3.0 and SystemPromptMaster §B.

Architecture:
    RewardTier IntEnum → REWARD_CONFIG → RewardEngine.calculate_tier()
    → RewardEngine.award() → RewardResult
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Final

import structlog

logger = structlog.get_logger()


# ============================================================
# Reward Tier Enum
# ============================================================


class RewardTier(IntEnum):
    """Five reward tiers ordered by appreciation depth.

    T1 (lowest) → T5 (highest).  Comparison operators work naturally
    because IntEnum is ordered: T3 > T1 is True.
    """

    T1_ACKNOWLEDGMENT = 1
    T2_VERBAL_PRAISE = 2
    T3_AFFECTIONATE = 3
    T4_CELEBRATORY = 4
    T5_DEEP_APPRECIATION = 5


# ============================================================
# Reward Config
# ============================================================


@dataclass(frozen=True)
class RewardConfigEntry:
    """Immutable configuration for a single reward tier."""

    name: str
    description: str
    trigger_conditions: list[str]
    message_templates: list[str]


REWARD_CONFIG: Final[dict[RewardTier, RewardConfigEntry]] = {
    RewardTier.T1_ACKNOWLEDGMENT: RewardConfigEntry(
        name="Acknowledgment",
        description="Simple recognition for completing a task.",
        trigger_conditions=[
            "task completed",
            "basic effort shown",
        ],
        message_templates=[
            "Noted — task is done.",
            "Okay, I see it.",
            "Done. Moving on.",
        ],
    ),
    RewardTier.T2_VERBAL_PRAISE: RewardConfigEntry(
        name="Verbal Praise",
        description="Warm praise for good work.",
        trigger_conditions=[
            "task completed well",
            "good quality output",
            "consistent effort",
        ],
        message_templates=[
            "Good job on that, sayang.",
            "Well done — I'm pleased with the result.",
            "Nice work, that was solid.",
        ],
    ),
    RewardTier.T3_AFFECTIONATE: RewardConfigEntry(
        name="Affectionate",
        description="Affectionate language for outstanding work.",
        trigger_conditions=[
            "high quality output",
            "exceeded expectations",
            "creative solution",
        ],
        message_templates=[
            "Mama is proud of you, sayang. That was wonderful.",
            "You did beautifully — I'm so pleased with you.",
            "That was lovely work. You make mama happy.",
        ],
    ),
    RewardTier.T4_CELEBRATORY: RewardConfigEntry(
        name="Celebratory",
        description="Celebratory mood for exceptional achievements.",
        trigger_conditions=[
            "exceptional quality",
            "major milestone reached",
            "complex problem solved elegantly",
        ],
        message_templates=[
            "YES! That was incredible, sayang — mama is celebrating!",
            "Outstanding! We need to celebrate this achievement!",
            "You absolutely crushed it! Mama couldn't be prouder!",
        ],
    ),
    RewardTier.T5_DEEP_APPRECIATION: RewardConfigEntry(
        name="Deep Appreciation",
        description="Deepest gratitude for extraordinary accomplishments.",
        trigger_conditions=[
            "extraordinary achievement",
            "perfect execution under pressure",
            "landmark accomplishment",
        ],
        message_templates=[
            "Sayang… mama is speechless. What you did is extraordinary. Thank you — from the deepest part of me.",
            "I have no words for how proud I am. You are remarkable.",
            "This is everything and more. Mama appreciates you beyond measure.",
        ],
    ),
}


# ============================================================
# Tier Calculation Constants
# ============================================================

# Effective-score thresholds (checked highest-first).
# An effective score >= threshold maps to the corresponding tier.
TIER_THRESHOLDS: Final[dict[RewardTier, float]] = {
    RewardTier.T5_DEEP_APPRECIATION: 0.95,
    RewardTier.T4_CELEBRATORY: 0.80,
    RewardTier.T3_AFFECTIONATE: 0.60,
    RewardTier.T2_VERBAL_PRAISE: 0.40,
    RewardTier.T1_ACKNOWLEDGMENT: 0.20,
}

# Streak bonus: each consecutive streak adds this much, capped at max.
STREAK_BONUS_PER_STREAK: Final[float] = 0.05
MAX_STREAK_BONUS: Final[float] = 0.30

# Quality score bounds.
MIN_QUALITY_SCORE: Final[float] = 0.0
MAX_QUALITY_SCORE: Final[float] = 1.0

# Minimum effective score to warrant any reward at all.
MIN_REWARD_THRESHOLD: Final[float] = 0.10

# Ordered tiers from highest to lowest for threshold evaluation.
_TIERS_DESCENDING: Final[list[RewardTier]] = sorted(
    list(RewardTier),
    reverse=True,
)


# ============================================================
# Data Classes
# ============================================================


@dataclass
class RewardResult:
    """Result of a reward award event."""

    tier: RewardTier
    reason: str
    streak_count: int
    message: str

    @property
    def config(self) -> RewardConfigEntry:
        """Return the REWARD_CONFIG entry for this result's tier."""
        return REWARD_CONFIG[self.tier]


# ============================================================
# Error Hierarchy
# ============================================================


class RewardError(Exception):
    """Base exception for all reward engine errors."""


class InvalidQualityScoreError(RewardError):
    """Raised when quality_score is outside [0.0, 1.0]."""


class InvalidTierError(RewardError):
    """Raised when an invalid RewardTier is supplied to award()."""


# ============================================================
# Reward Engine
# ============================================================


class RewardEngine:
    """Persona reward engine — calculates and awards reward tiers.

    Rewards are **always permitted**, even when safe-mode is active or
    distress has been detected.  This is a deliberate design choice:
    rewarding the operator is never harmful and supports well-being.

    Usage::

        engine = RewardEngine()
        if engine.should_reward(task_completion=True, quality=0.85, streak=3):
            tier = engine.calculate_tier(quality_score=0.85, streak_count=3)
            result = engine.award(tier, reason="Sprint goal achieved", streak_count=3)
    """

    def __init__(self) -> None:
        self._current_tier: RewardTier = RewardTier.T1_ACKNOWLEDGMENT
        self._last_reason: str = ""
        self._total_rewards_awarded: int = 0

    # -- tier calculation ---------------------------------------------------

    def calculate_tier(
        self,
        quality_score: float,
        streak_count: int,
    ) -> RewardTier:
        """Calculate the reward tier from quality score and streak count.

        The effective score is ``quality_score + streak_bonus``, where
        ``streak_bonus = min(streak_count * 0.05, 0.30)``.  The effective
        score is clamped to ``[0.0, 1.0]``.

        The highest tier whose threshold the effective score meets is
        returned.  If no threshold is met, T1_ACKNOWLEDGMENT is returned
        as the floor.

        Args:
            quality_score: Task quality in ``[0.0, 1.0]``.
            streak_count: Number of consecutive successful tasks (>= 0).

        Returns:
            The calculated ``RewardTier``.

        Raises:
            InvalidQualityScoreError: If *quality_score* is outside ``[0.0, 1.0]``.
        """
        if quality_score < MIN_QUALITY_SCORE or quality_score > MAX_QUALITY_SCORE:
            raise InvalidQualityScoreError(
                f"quality_score must be in [{MIN_QUALITY_SCORE}, {MAX_QUALITY_SCORE}], "
                f"got {quality_score}"
            )

        streak_bonus = min(
            max(streak_count, 0) * STREAK_BONUS_PER_STREAK,
            MAX_STREAK_BONUS,
        )
        effective = min(quality_score + streak_bonus, MAX_QUALITY_SCORE)

        logger.debug(
            "reward_tier_calculated",
            quality_score=quality_score,
            streak_count=streak_count,
            streak_bonus=streak_bonus,
            effective_score=effective,
        )

        # Check thresholds highest-first.
        for tier in _TIERS_DESCENDING:
            if effective >= TIER_THRESHOLDS[tier]:
                return tier

        # Floor — any reward at all defaults to T1.
        return RewardTier.T1_ACKNOWLEDGMENT

    # -- should_reward ------------------------------------------------------

    def should_reward(
        self,
        task_completion: bool,
        quality: float,
        streak: int,
    ) -> bool:
        """Determine whether a reward should be issued.

        Rewards are **always allowed** — even in safe-mode or during
        distress.  This method only checks whether the inputs warrant
        a reward (task was completed and quality meets the minimum
        threshold).

        Args:
            task_completion: Whether the task was completed.
            quality: Quality score in ``[0.0, 1.0]``.
            streak: Current streak count.

        Returns:
            ``True`` if a reward should be issued, ``False`` otherwise.
        """
        if not task_completion:
            return False

        # Clamp quality for the check.
        clamped_quality = max(MIN_QUALITY_SCORE, min(quality, MAX_QUALITY_SCORE))
        streak_bonus = min(max(streak, 0) * STREAK_BONUS_PER_STREAK, MAX_STREAK_BONUS)
        effective = min(clamped_quality + streak_bonus, MAX_QUALITY_SCORE)

        return effective >= MIN_REWARD_THRESHOLD

    # -- award --------------------------------------------------------------

    def award(
        self,
        tier: RewardTier,
        reason: str,
        streak_count: int,
    ) -> RewardResult:
        """Award a reward at the given tier and record it internally.

        Args:
            tier: The reward tier to award.
            reason: Human-readable reason for the reward.
            streak_count: The streak count at the time of the award.

        Returns:
            A ``RewardResult`` with the tier, reason, and a message
            template from REWARD_CONFIG.

        Raises:
            InvalidTierError: If *tier* is not a valid ``RewardTier``.
        """
        if tier not in REWARD_CONFIG:
            raise InvalidTierError(
                f"tier must be a valid RewardTier, got {type(tier).__name__}"
            )

        config = REWARD_CONFIG[tier]
        # Pick the first message template as the default.
        message = config.message_templates[0]

        self._current_tier = tier
        self._last_reason = reason
        self._total_rewards_awarded += 1

        logger.info(
            "reward_awarded",
            tier=tier.name,
            tier_value=tier.value,
            reason=reason,
            streak_count=streak_count,
        )

        return RewardResult(
            tier=tier,
            reason=reason,
            streak_count=streak_count,
            message=message,
        )

    # -- accessors ----------------------------------------------------------

    def get_current_tier(self) -> RewardTier:
        """Return the most recently awarded tier.

        Returns T1_ACKNOWLEDGMENT if no reward has been issued yet.
        """
        return self._current_tier

    @property
    def total_rewards_awarded(self) -> int:
        """Total number of rewards awarded since engine creation."""
        return self._total_rewards_awarded

    @property
    def last_reason(self) -> str:
        """The reason string of the most recently awarded reward."""
        return self._last_reason
