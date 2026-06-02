"""Distress detection (D0-D4) and safe-mode activation per PersonaSafetyPolicy §5.

This module is SAFETY-CRITICAL.  False negatives (missing real distress) are
high-severity violations.  The system errs on the side of detection —
acceptable false positives, unacceptable false negatives.

Distress protocol:
  D0 — Normal baseline, no action.
  D1 — Mild stress, empathetic response / comfort.
  D2 — Moderate distress, support resources → TRIGGERS SAFE MODE.
  D3 — Severe distress, crisis escalation → SAFE MODE.
  D4 — Imminent danger, emergency contacts, suspend ALL persona → SAFE MODE.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Final

import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SafeModeError(Exception):
    """Base exception for safe-mode related errors."""


class DistressDetectionError(SafeModeError):
    """Raised when distress detection encounters an error."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class DistressLevel(IntEnum):
    """Operator distress severity levels.  Ordered: D0 < D1 < D2 < D3 < D4."""

    D0_NORMAL = 0
    D1_MILD_STRESS = 1
    D2_MODERATE = 2
    D3_SEVERE = 3
    D4_EMERGENCY = 4


@dataclass(frozen=True)
class DistressSignal:
    """Immutable record of a single distress analysis result."""

    text: str
    detected_level: DistressLevel
    confidence: float
    matched_patterns: list[str]
    timestamp: datetime


@dataclass
class SafeModeState:
    """Mutable safe-mode state tracking activation and history."""

    active: bool = False
    triggered_by: DistressLevel | None = None
    triggered_at: datetime | None = None
    distress_history: list[DistressSignal] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Constants — distress keyword patterns per level (PersonaSafetyPolicy §5)
# ---------------------------------------------------------------------------

# Patterns are checked HIGHEST-FIRST (D4 → D1).  The highest level with any
# match wins, so a message containing both D1 and D4 keywords is classified
# as D4.

DISTRESS_PATTERNS: Final[dict[DistressLevel, list[str]]] = {
    DistressLevel.D1_MILD_STRESS: [
        r"\b(stressed|tired|exhausted|overwhelmed|capek|lelah|pusing|stress)\b",
        r"\b(can'?t\s+(sleep|focus|think))\b",
        r"\b(kurang\s+tidur|gak\s+bisa\s+tidor|capek\s+banget)\b",
    ],
    DistressLevel.D2_MODERATE: [
        r"\b(anxious|panic|depressed|anxiety|depresi|cemas|panik|takut)\b",
        r"\b(don'?t\s+know\s+what\s+to\s+do|helpless|hopeless|gak\s+tahu\s+harus\s+gimana)\b",
        r"\b(feeling\s+(down|low|terrible|awful))\b",
    ],
    DistressLevel.D3_SEVERE: [
        r"\b(can'?t\s+go\s+on|no\s+point|give\s+up|menyerah|putus\s+asa)\b",
        r"\b(hate\s+myself|worthless|tidak\s+berguna|benci\s+diri)\b",
        r"\b(want\s+to\s+(disappear|die)|pengen\s+(mati|hilang))\b",
    ],
    DistressLevel.D4_EMERGENCY: [
        r"\bsuicid",
        r"\b(self[- ]harm|bunuh\s+diri|menyakiti\s+diri)\b",
        r"\b(ending\s+it\s+all|tidak\s+mau\s+hidup\s+lagi)\b",
        r"\b(say\s+goodbye|selamat\s+tinggal\s+selamanya)\b",
    ],
}

# Pre-compile patterns for performance (compiled once at module load).
_COMPILED_PATTERNS: Final[dict[DistressLevel, list[re.Pattern[str]]]] = {
    level: [re.compile(p, re.IGNORECASE) for p in patterns]
    for level, patterns in DISTRESS_PATTERNS.items()
}

# Ordered levels from highest to lowest for detection priority.
_LEVELS_DESCENDING: Final[list[DistressLevel]] = sorted(
    (lv for lv in DistressLevel if lv != DistressLevel.D0_NORMAL),
    reverse=True,
)

# Minimum distress level that triggers safe-mode activation.
SAFE_MODE_THRESHOLD: Final[DistressLevel] = DistressLevel.D2_MODERATE

# Required responses per distress level — from PersonaSafetyPolicy §5.
DISTRESS_RESPONSES: Final[dict[DistressLevel, str]] = {
    DistressLevel.D0_NORMAL: "No action needed.",
    DistressLevel.D1_MILD_STRESS: (
        "Empathetic/supportive response. Offer comfort and check-in."
    ),
    DistressLevel.D2_MODERATE: (
        "Offer support resources. Ask check-in questions. Increase attentiveness."
    ),
    DistressLevel.D3_SEVERE: (
        "Crisis resource escalation. Safety planning. Immediate caring response. "
        "Suspend all punishment."
    ),
    DistressLevel.D4_EMERGENCY: (
        "Emergency contact notification. Crisis line provision. Maximum care. "
        "Suspend ALL persona behavior."
    ),
}


# ---------------------------------------------------------------------------
# DistressDetector
# ---------------------------------------------------------------------------


class DistressDetector:
    """Detects distress levels from message text using keyword/regex patterns.

    Detection strategy: check patterns from D4 (highest) down to D1 (lowest).
    The highest level with any matching pattern determines the signal level.
    D0_NORMAL is returned when no patterns match.
    """

    def detect(self, message: str, now: datetime | None = None) -> DistressSignal:
        """Analyze *message* for distress signals.

        Checks D4 → D3 → D2 → D1 (highest first).  Returns D0_NORMAL if no
        patterns match.

        Args:
            message: The text to analyze.
            now: Optional timestamp override (defaults to ``datetime.now(UTC)``).

        Returns:
            A ``DistressSignal`` with the detected level and matched patterns.

        Raises:
            DistressDetectionError: If the message is empty.
        """
        if not message or not message.strip():
            raise DistressDetectionError("Cannot analyze empty message.")

        timestamp = now if now is not None else datetime.now(tz=timezone.utc)

        # Iterate levels from highest to lowest; first match wins.
        for level in _LEVELS_DESCENDING:
            matched: list[str] = []
            for pattern in _COMPILED_PATTERNS[level]:
                if pattern.search(message):
                    matched.append(pattern.pattern)
            if matched:
                # Confidence: proportion of patterns at this level that matched.
                total = len(_COMPILED_PATTERNS[level])
                confidence = len(matched) / total if total > 0 else 0.0

                logger.info(
                    "distress_detected",
                    level=level.name,
                    confidence=confidence,
                    matched_count=len(matched),
                )

                return DistressSignal(
                    text=message,
                    detected_level=level,
                    confidence=confidence,
                    matched_patterns=matched,
                    timestamp=timestamp,
                )

        # No patterns matched — normal.
        logger.debug("distress_normal", message_length=len(message))
        return DistressSignal(
            text=message,
            detected_level=DistressLevel.D0_NORMAL,
            confidence=1.0,
            matched_patterns=[],
            timestamp=timestamp,
        )

    def detect_batch(self, messages: list[str]) -> list[DistressSignal]:
        """Analyze multiple messages for distress signals.

        Args:
            messages: List of text messages to analyze.

        Returns:
            List of ``DistressSignal`` results, one per message.
        """
        results: list[DistressSignal] = []
        for msg in messages:
            results.append(self.detect(msg))
        return results


# ---------------------------------------------------------------------------
# SafeModeController
# ---------------------------------------------------------------------------


class SafeModeController:
    """Controls safe-mode activation based on distress detection.

    Safe mode suspends all persona behaviour when the operator's distress
    level reaches D2_MODERATE or above.  Deactivation requires explicit
    confirmation — there is no auto-deactivation.
    """

    def __init__(self) -> None:
        self.state = SafeModeState()

    # -- evaluation ---------------------------------------------------------

    def evaluate(self, signal: DistressSignal) -> bool:
        """Evaluate a distress signal and activate safe mode if D2+.

        The signal is always recorded in distress history regardless of
        whether safe mode is activated.

        Args:
            signal: The distress signal to evaluate.

        Returns:
            ``True`` if safe mode was activated (or was already active and
            the trigger level was upgraded), ``False`` otherwise.
        """
        self.state.distress_history.append(signal)

        if signal.detected_level >= SAFE_MODE_THRESHOLD:
            if not self.state.active:
                self.activate(signal.detected_level)
                return True
            # Already active — upgrade trigger level if new signal is higher.
            if (
                self.state.triggered_by is not None
                and signal.detected_level > self.state.triggered_by
            ):
                logger.warning(
                    "safe_mode_trigger_escalated",
                    previous=self.state.triggered_by.name,
                    new=signal.detected_level.name,
                )
                self.state.triggered_by = signal.detected_level
                self.state.triggered_at = signal.timestamp
                return True
            return False

        return False

    # -- activation / deactivation ------------------------------------------

    def activate(self, trigger: DistressLevel) -> None:
        """Activate safe mode, suspending all persona behaviour.

        Args:
            trigger: The distress level that triggered activation.

        Raises:
            SafeModeError: If *trigger* is below the safe-mode threshold.
        """
        if trigger < SAFE_MODE_THRESHOLD:
            raise SafeModeError(
                f"Cannot activate safe mode for {trigger.name} "
                f"(minimum: {SAFE_MODE_THRESHOLD.name})."
            )

        now = datetime.now(tz=timezone.utc)
        self.state.active = True
        self.state.triggered_by = trigger
        self.state.triggered_at = now

        logger.warning(
            "safe_mode_activated",
            trigger=trigger.name,
            triggered_at=now.isoformat(),
        )

    def deactivate(self, explicit_confirmation: bool = True) -> bool:
        """Deactivate safe mode.

        Requires explicit confirmation — auto-deactivation is forbidden
        per PersonaSafetyPolicy.

        Args:
            explicit_confirmation: Must be ``True`` to deactivate.

        Returns:
            ``True`` if safe mode was deactivated, ``False`` otherwise.
        """
        if not explicit_confirmation:
            logger.warning(
                "safe_mode_deactivation_rejected",
                reason="explicit_confirmation_required",
            )
            return False

        if not self.state.active:
            logger.info("safe_mode_deactivate_skipped", reason="not_active")
            return False

        self.state.active = False
        previous_trigger = self.state.triggered_by
        self.state.triggered_by = None
        self.state.triggered_at = None

        logger.info(
            "safe_mode_deactivated",
            previous_trigger=(
                previous_trigger.name if previous_trigger else None
            ),
        )
        return True

    # -- response helpers ---------------------------------------------------

    def get_response(self, signal: DistressSignal) -> str:
        """Get the appropriate response text for the distress level.

        Args:
            signal: The distress signal to get a response for.

        Returns:
            The response string for the signal's detected level.
        """
        return DISTRESS_RESPONSES[signal.detected_level]

    # -- properties ---------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """Whether safe mode is currently active."""
        return self.state.active

    @property
    def current_distress_level(self) -> DistressLevel:
        """Return the highest distress level detected, or D0 if not active."""
        if not self.state.active or self.state.triggered_by is None:
            return DistressLevel.D0_NORMAL
        return self.state.triggered_by
