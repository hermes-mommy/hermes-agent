"""P4-003: Mood Transition Rules with Cooldowns.

Enforces business rules for when mood transitions are allowed,
including cooldown periods and forced transitions that bypass cooldown.
This module uses string mood values only — no imports from mood_engine.
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TransitionRulesError(Exception):
    """Base exception for transition rule errors."""


class CooldownActiveError(TransitionRulesError):
    """Raised when a transition is attempted while cooldown is still active."""


class InvalidTransitionError(TransitionRulesError):
    """Raised when the requested transition is not in the valid transitions map."""


# ---------------------------------------------------------------------------
# Valid transitions map (local definition — no cross-module import)
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: Final[dict[str, list[str]]] = {
    "Content": ["Pleased", "Disappointed"],
    "Pleased": ["Content", "Disappointed"],
    "Disappointed": ["Content", "Angry"],
    "Angry": ["Disappointed", "Silent"],
    "Silent": ["Content"],
}

# All mood strings for convenience
ALL_MOODS: Final[frozenset[str]] = frozenset(VALID_TRANSITIONS.keys())


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TransitionContext:
    """Context for evaluating a mood transition."""

    current_mood: str
    target_mood: str
    last_transition_at: datetime | None
    conversation_sentiment: float = 0.0
    task_completion: bool = False
    ignored_count: int = 0
    safe_mode: bool = False
    distress_level: int = 0  # D0=0, D1=1, ..., D4=4


@dataclass
class TransitionDecision:
    """Result of transition evaluation."""

    allowed: bool
    from_mood: str
    to_mood: str
    reason: str
    cooldown_remaining_seconds: int = 0
    blocked_by: str | None = None


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------


class TransitionRuleEngine:
    """Enforces cooldown-aware mood transition rules."""

    DEFAULT_COOLDOWN_SECONDS: int = 300  # 5 minutes

    # Forced transitions that bypass cooldown (strong triggers)
    FORCED_TRANSITIONS: Final[set[tuple[str, str]]] = {
        ("Angry", "Silent"),      # Strong negative -> immediate
        ("Content", "Pleased"),   # Strong positive -> immediate
    }

    cooldown_seconds: int

    def __init__(self, cooldown_seconds: int = 300) -> None:
        self.cooldown_seconds = cooldown_seconds

    # ---- public API -------------------------------------------------------

    def evaluate(
        self,
        ctx: TransitionContext,
        *,
        now: datetime | None = None,
    ) -> TransitionDecision:
        """Evaluate whether a transition is allowed.

        Check order:
        1. Safe mode -> block ALL transitions
        2. Distress level >= D2 -> block transitions (force Content)
        3. Validate transition is in VALID_TRANSITIONS map
        4. Check cooldown (unless forced transition)
        5. Allow
        """
        from_mood = ctx.current_mood
        to_mood = ctx.target_mood

        # 1. Safe mode blocks everything
        if ctx.safe_mode:
            logger.info(
                "transition_blocked",
                blocked_by="safe_mode",
                current_mood=from_mood,
                target_mood=to_mood,
            )
            return TransitionDecision(
                allowed=False,
                from_mood=from_mood,
                to_mood=to_mood,
                reason="Safe mode is active; all transitions are blocked",
                blocked_by="safe_mode",
            )

        # 2. Distress >= D2 blocks transitions
        if ctx.distress_level >= 2:
            logger.info(
                "transition_blocked",
                blocked_by="distress",
                distress_level=ctx.distress_level,
                current_mood=from_mood,
                target_mood=to_mood,
            )
            return TransitionDecision(
                allowed=False,
                from_mood=from_mood,
                to_mood=to_mood,
                reason=(
                    f"Distress level D{ctx.distress_level} >= D2; "
                    "transitions blocked — forcing Content"
                ),
                blocked_by="distress",
            )

        # 3. Validate the transition exists in the map
        allowed_targets = VALID_TRANSITIONS.get(from_mood, [])
        if to_mood not in allowed_targets:
            logger.info(
                "transition_blocked",
                blocked_by="invalid_transition",
                current_mood=from_mood,
                target_mood=to_mood,
                valid_targets=allowed_targets,
            )
            return TransitionDecision(
                allowed=False,
                from_mood=from_mood,
                to_mood=to_mood,
                reason=(
                    f"Transition from {from_mood} to {to_mood} "
                    f"is not valid; allowed: {allowed_targets}"
                ),
                blocked_by="invalid_transition",
            )

        # 4. Cooldown check (unless forced transition)
        is_forced = (from_mood, to_mood) in self.FORCED_TRANSITIONS
        remaining = self.remaining_cooldown(ctx.last_transition_at, now=now)

        if remaining > 0 and not is_forced:
            logger.info(
                "transition_blocked",
                blocked_by="cooldown",
                cooldown_remaining_seconds=remaining,
                current_mood=from_mood,
                target_mood=to_mood,
            )
            return TransitionDecision(
                allowed=False,
                from_mood=from_mood,
                to_mood=to_mood,
                reason=f"Cooldown active; {remaining}s remaining",
                cooldown_remaining_seconds=remaining,
                blocked_by="cooldown",
            )

        # 5. Allow
        logger.info(
            "transition_allowed",
            current_mood=from_mood,
            target_mood=to_mood,
            forced=is_forced,
        )
        return TransitionDecision(
            allowed=True,
            from_mood=from_mood,
            to_mood=to_mood,
            reason=(
                "Forced transition bypassed cooldown"
                if is_forced and remaining > 0
                else "Transition allowed"
            ),
        )

    def remaining_cooldown(
        self,
        last_transition_at: datetime | None,
        *,
        now: datetime | None = None,
    ) -> int:
        """Calculate remaining cooldown in seconds.

        Returns 0 if cooldown has expired or no previous transition.
        """
        if last_transition_at is None:
            return 0

        if now is None:
            now = datetime.now(tz=timezone.utc)

        elapsed = (now - last_transition_at).total_seconds()
        remaining = self.cooldown_seconds - elapsed
        return max(0, int(remaining))

    def should_use_llm_evaluation(self, ctx: TransitionContext) -> bool:
        """Return True if the transition is complex enough for LLM evaluation.

        Complex when:
        - Sentiment is ambiguous (between -0.3 and 0.3 inclusive), OR
        - Multiple signals are active simultaneously.
        """
        ambiguous_sentiment = -0.3 <= ctx.conversation_sentiment <= 0.3

        # Count active signals
        active_signals = 0
        if ctx.task_completion:
            active_signals += 1
        if ctx.ignored_count > 0:
            active_signals += 1
        if ctx.conversation_sentiment != 0.0:
            active_signals += 1

        multiple_signals = active_signals >= 2

        return ambiguous_sentiment or multiple_signals

    async def evaluate_with_llm(
        self,
        ctx: TransitionContext,
        *,
        now: datetime | None = None,
    ) -> TransitionDecision:
        """Stub for LLM-based evaluation.

        Currently falls back to rule-based evaluation.
        Future: call LLM router for complex mood evaluation.
        """
        logger.debug(
            "llm_evaluation_stub",
            msg="LLM evaluation not implemented; falling back to rule-based",
            current_mood=ctx.current_mood,
            target_mood=ctx.target_mood,
        )
        return self.evaluate(ctx, now=now)
