"""Safe-Mode Surveillance Blocking — Confrontation Gate (P7-011).

Pauses confrontation/blackmail/punishment features when the system enters
SAFE state (HARD STOP) while preserving the ingestion pipeline.

Architecture:
- Injects a ``SafetyState`` getter callable (returns NORMAL or SAFE).
- When SAFE: blocks 8 confrontation action types, allows 6 pipeline action types.
- When NORMAL: all actions pass through.
- Includes ``check_message_safety()`` for pattern-based detection of prohibited
  surveillance references in generated text (pre-LLM output guard).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

import structlog

from src.core.services.hard_stop_handler import SafetyState

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_BLOCKED_ACTIONS: Final[frozenset[str]] = frozenset({
    "confrontation",
    "blackmail",
    "punishment",
    "jealousy_escalation",
    "dependency_manipulation",
    "intimate_data_reference",
    "humiliation",
    "public_disclosure",
})

_ALLOWED_PIPELINE_ACTIONS: Final[frozenset[str]] = frozenset({
    "ingestion",
    "classification",
    "consent_check",
    "secret_scan",
    "buffer",
    "status_query",
})

# Regex patterns that detect prohibited surveillance use in generated messages.
# These are checked by ``check_message_safety()`` and should catch phrases
# like "you were at X", "I saw you at Y", "surveillance shows Z".
PROHIBITED_USE_PATTERNS: Final[list[str]] = [
    r"\byou\s+(were|are)\s+at\b",
    r"\bI\s+saw\s+you\b",
    r"\bI\s+know\s+you\b",
    r"\bsurveillance\s+shows?\b",
    r"\bmonitoring\s+detected\b",
]


# ---------------------------------------------------------------------------
# ConfrontationDecision
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfrontationDecision:
    """Immutable decision about whether a confrontation action is permitted.

    Attributes:
        allowed: ``True`` if the action is permitted in the current safety state.
        reason: Human-readable explanation of the decision.
        blocked_action: The blocked action type string, or ``None`` if allowed.
    """

    allowed: bool
    reason: str
    blocked_action: str | None


# ---------------------------------------------------------------------------
# SurveillanceSafeModeGuard
# ---------------------------------------------------------------------------


class SurveillanceSafeModeGuard:
    """Confrontation-blocking gate that ties HARD STOP state to surveillance actions.

    Injects a callable that returns the current ``SafetyState`` so the guard
    can make decisions without owning mutable state.
    """

    def __init__(self, safety_state_getter: Callable[[], SafetyState]) -> None:
        """Initialise the guard with a callable that returns current ``SafetyState``.

        Args:
            safety_state_getter: Zero-argument callable → ``SafetyState``.
                Typically a lambda that reads ``HardStopHandler.state``.
        """
        self._safety_state_getter = safety_state_getter

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_confrontation(
        self,
        action: str,
        surveillance_data_available: bool = False,
    ) -> ConfrontationDecision:
        """Determine whether *action* is permitted in the current safety state.

        Args:
            action: Action type string (e.g. ``"confrontation"``, ``"ingestion"``).
            surveillance_data_available: Whether relevant surveillance data exists.
                Not used in SAFE mode (always blocked), but wired for future use.

        Returns:
            ``ConfrontationDecision`` with ``allowed``, ``reason``, and optional
            ``blocked_action``.
        """
        state = self._safety_state_getter()

        if state == SafetyState.NORMAL:
            return ConfrontationDecision(
                allowed=True,
                reason="Normal mode — all actions allowed",
                blocked_action=None,
            )

        # SAFE mode — distinction between blocked and pipeline actions.
        if action in _BLOCKED_ACTIONS:
            logger.info(
                "confrontation_blocked_safe_mode",
                action=action,
                safety_state=state.value,
            )
            return ConfrontationDecision(
                allowed=False,
                reason=f"Safe mode active — {action!r} is blocked",
                blocked_action=action,
            )

        if action in _ALLOWED_PIPELINE_ACTIONS:
            return ConfrontationDecision(
                allowed=True,
                reason="Safe mode active — pipeline action preserved",
                blocked_action=None,
            )

        # Unknown action type -- fail-closed: BLOCK in safe mode.
        logger.warning(
            "confrontation_unknown_action_blocked",
            action=action,
            safety_state=state.value,
        )
        return ConfrontationDecision(
            allowed=False,
            reason=f"Unknown action type -- blocked in safe mode (fail-closed)",
            blocked_action=action,
        )

    def is_confrontation_blocked(self, action: str) -> bool:
        """Quick boolean check — is *action* currently blocked?

        Returns ``True`` only when safety state is SAFE **and** the action
        is in ``_BLOCKED_ACTIONS``.
        """
        return (
            self._safety_state_getter() == SafetyState.SAFE
            and action in _BLOCKED_ACTIONS
        )

    def get_blocked_actions(self) -> list[str]:
        """Return currently blocked action types.

        In NORMAL mode this returns an empty list.
        In SAFE mode this returns all 8 blocked action types.
        """
        if self._safety_state_getter() == SafetyState.NORMAL:
            return []
        return sorted(_BLOCKED_ACTIONS)

    def check_message_safety(self, message: str) -> ConfrontationDecision:
        """Scan *message* for prohibited surveillance-use patterns.

        This is a pre-LLM-output guard that checks whether generated text
        contains phrases that indicate surveillance-data misuse (e.g.
        "you were at …", "I saw you …").

        Args:
            message: The text to scan for prohibited patterns.

        Returns:
            ``ConfrontationDecision`` — ``allowed=False`` with the matched
            pattern as ``blocked_action`` if any pattern matches, otherwise
            ``allowed=True``.
        """
        for pattern in PROHIBITED_USE_PATTERNS:
            if match := re.search(pattern, message, re.IGNORECASE):
                logger.info(
                    "message_safety_blocked",
                    pattern=pattern,
                    match_span=match.span(),
                )
                return ConfrontationDecision(
                    allowed=False,
                    reason=f"Message matches prohibited surveillance pattern: {pattern!r}",
                    blocked_action=pattern,
                )

        return ConfrontationDecision(
            allowed=True,
            reason="Message passes prohibited-use pattern check",
            blocked_action=None,
        )