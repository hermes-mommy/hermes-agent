"""P7-011: Safe-Mode Surveillance Blocking — comprehensive unit tests.

Tests cover:
- Normal mode: all 8 blocked + 6 pipeline actions allowed
- Safe mode: 8 confrontation types blocked, 6 pipeline types allowed
- ``check_confrontation`` returns correct ``ConfrontationDecision`` per action
- ``is_confrontation_blocked`` quick boolean check
- ``get_blocked_actions`` returns correct lists in both modes
- ``check_message_safety`` pattern matching for all 5 prohibited patterns
- ``check_message_safety`` allows benign messages
- ``ConfrontationDecision`` frozen dataclass immutability
- SafetyState injection via callable (both NORMAL and SAFE)
- Edge cases: empty action string, unknown action type (fail-closed BLOCKED)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import pytest

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.core.services.hard_stop_handler import SafetyState
from src.surveillance.safe_mode import (
    ConfrontationDecision,
    SurveillanceSafeModeGuard,
)

# =============================================================================
# Action type lists matching module constants
# =============================================================================

BLOCKED_ACTIONS = [
    "confrontation",
    "blackmail",
    "punishment",
    "jealousy_escalation",
    "dependency_manipulation",
    "intimate_data_reference",
    "humiliation",
    "public_disclosure",
]

PIPELINE_ACTIONS = [
    "ingestion",
    "classification",
    "consent_check",
    "secret_scan",
    "buffer",
    "status_query",
]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def normal_state_getter() -> Callable[[], SafetyState]:
    """Zero-argument callable that returns SafetyState.NORMAL."""

    def _getter() -> SafetyState:
        return SafetyState.NORMAL

    return _getter


@pytest.fixture
def safe_state_getter() -> Callable[[], SafetyState]:
    """Zero-argument callable that returns SafetyState.SAFE."""

    def _getter() -> SafetyState:
        return SafetyState.SAFE

    return _getter


@pytest.fixture
def normal_guard(normal_state_getter: Callable[[], SafetyState]) -> SurveillanceSafeModeGuard:
    """Guard wired to always return NORMAL."""
    return SurveillanceSafeModeGuard(safety_state_getter=normal_state_getter)


@pytest.fixture
def safe_guard(safe_state_getter: Callable[[], SafetyState]) -> SurveillanceSafeModeGuard:
    """Guard wired to always return SAFE."""
    return SurveillanceSafeModeGuard(safety_state_getter=safe_state_getter)


# =============================================================================
# Normal mode — all actions allowed
# =============================================================================


class TestNormalModeAllActionsAllowed:
    """In NORMAL mode every action type must be allowed."""

    @pytest.mark.parametrize("action", BLOCKED_ACTIONS)
    def test_blocked_action_allowed_in_normal_mode(
        self, normal_guard: SurveillanceSafeModeGuard, action: str
    ) -> None:
        decision = normal_guard.check_confrontation(action)
        assert decision.allowed is True
        assert decision.blocked_action is None
        assert "Normal mode" in decision.reason

    @pytest.mark.parametrize("action", PIPELINE_ACTIONS)
    def test_pipeline_action_allowed_in_normal_mode(
        self, normal_guard: SurveillanceSafeModeGuard, action: str
    ) -> None:
        decision = normal_guard.check_confrontation(action)
        assert decision.allowed is True
        assert decision.blocked_action is None
        assert "Normal mode" in decision.reason


# =============================================================================
# Safe mode — confrontation blocked, pipeline allowed
# =============================================================================


class TestSafeModeConfrontationBlocked:
    """In SAFE mode every confrontation action type must be blocked."""

    @pytest.mark.parametrize("action", BLOCKED_ACTIONS)
    def test_confrontation_action_blocked_in_safe_mode(
        self, safe_guard: SurveillanceSafeModeGuard, action: str
    ) -> None:
        decision = safe_guard.check_confrontation(action)
        assert decision.allowed is False
        assert decision.blocked_action == action
        assert "blocked" in decision.reason.lower()
        assert action in decision.reason


class TestSafeModePipelineAllowed:
    """In SAFE mode every pipeline action type must be allowed (ingestion preserved)."""

    @pytest.mark.parametrize("action", PIPELINE_ACTIONS)
    def test_pipeline_action_allowed_in_safe_mode(
        self, safe_guard: SurveillanceSafeModeGuard, action: str
    ) -> None:
        decision = safe_guard.check_confrontation(action)
        assert decision.allowed is True
        assert decision.blocked_action is None
        assert "preserved" in decision.reason.lower()


# =============================================================================
# ``is_confrontation_blocked`` quick boolean check
# =============================================================================


class TestIsConfrontationBlocked:
    """``is_confrontation_blocked`` must return the right boolean per action + state."""

    @pytest.mark.parametrize("action", BLOCKED_ACTIONS)
    def test_blocked_action_true_in_safe(
        self, safe_guard: SurveillanceSafeModeGuard, action: str
    ) -> None:
        assert safe_guard.is_confrontation_blocked(action) is True

    @pytest.mark.parametrize("action", PIPELINE_ACTIONS)
    def test_pipeline_action_false_in_safe(
        self, safe_guard: SurveillanceSafeModeGuard, action: str
    ) -> None:
        assert safe_guard.is_confrontation_blocked(action) is False

    @pytest.mark.parametrize("action", BLOCKED_ACTIONS)
    def test_blocked_action_false_in_normal(
        self, normal_guard: SurveillanceSafeModeGuard, action: str
    ) -> None:
        assert normal_guard.is_confrontation_blocked(action) is False

    def test_unknown_action_false_in_safe(
        self, safe_guard: SurveillanceSafeModeGuard
    ) -> None:
        assert safe_guard.is_confrontation_blocked("garbage_action") is False


# =============================================================================
# ``get_blocked_actions``
# =============================================================================


class TestGetBlockedActions:
    """``get_blocked_actions`` must return correct lists per safety state."""

    def test_empty_in_normal_mode(
        self, normal_guard: SurveillanceSafeModeGuard
    ) -> None:
        assert normal_guard.get_blocked_actions() == []

    def test_all_eight_in_safe_mode(
        self, safe_guard: SurveillanceSafeModeGuard
    ) -> None:
        result = safe_guard.get_blocked_actions()
        assert len(result) == 8
        assert sorted(BLOCKED_ACTIONS) == result


# =============================================================================
# ``check_message_safety`` — prohibited pattern matching
# =============================================================================


class TestMessageSafetyProhibitedPatterns:
    """``check_message_safety`` must block messages containing prohibited patterns."""

    def test_blocks_you_were_at_pattern(
        self, safe_guard: SurveillanceSafeModeGuard
    ) -> None:
        decision = safe_guard.check_message_safety("I noticed you were at the mall earlier.")
        assert decision.allowed is False
        assert decision.blocked_action is not None

    def test_blocks_i_saw_you_pattern(
        self, safe_guard: SurveillanceSafeModeGuard
    ) -> None:
        decision = safe_guard.check_message_safety("I saw you with that friend yesterday.")
        assert decision.allowed is False
        assert decision.blocked_action is not None

    def test_blocks_i_know_you_pattern(
        self, safe_guard: SurveillanceSafeModeGuard
    ) -> None:
        decision = safe_guard.check_message_safety("I know you were not at work today.")
        assert decision.allowed is False
        assert decision.blocked_action is not None

    def test_blocks_surveillance_shows_pattern(
        self, safe_guard: SurveillanceSafeModeGuard
    ) -> None:
        decision = safe_guard.check_message_safety(
            "My surveillance shows you left the house at 3 AM."
        )
        assert decision.allowed is False
        assert decision.blocked_action is not None

    def test_blocks_monitoring_detected_pattern(
        self, safe_guard: SurveillanceSafeModeGuard
    ) -> None:
        decision = safe_guard.check_message_safety(
            "Our monitoring detected unusual activity on your phone."
        )
        assert decision.allowed is False
        assert decision.blocked_action is not None

    def test_case_insensitive_matching(
        self, safe_guard: SurveillanceSafeModeGuard
    ) -> None:
        decision = safe_guard.check_message_safety("I SAW YOU at the store.")
        assert decision.allowed is False


class TestMessageSafetyAllowsBenign:
    """``check_message_safety`` must allow harmless messages through."""

    def test_allows_normal_greeting(
        self, safe_guard: SurveillanceSafeModeGuard
    ) -> None:
        decision = safe_guard.check_message_safety("Hello! How was your day?")
        assert decision.allowed is True
        assert decision.blocked_action is None

    def test_allows_technical_message(
        self, safe_guard: SurveillanceSafeModeGuard
    ) -> None:
        decision = safe_guard.check_message_safety("The database migration completed at 3:00 PM.")
        assert decision.allowed is True

    def test_allows_empty_string(
        self, safe_guard: SurveillanceSafeModeGuard
    ) -> None:
        decision = safe_guard.check_message_safety("")
        assert decision.allowed is True
        assert decision.blocked_action is None


# =============================================================================
# ``ConfrontationDecision`` — frozen dataclass
# =============================================================================


class TestConfrontationDecisionFrozen:
    """``ConfrontationDecision`` must be truly immutable."""

    def test_cannot_set_allowed_field(self) -> None:
        decision = ConfrontationDecision(allowed=True, reason="test", blocked_action=None)
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError or AttributeError
            decision.allowed = False  # type: ignore[misc]

    def test_cannot_set_reason_field(self) -> None:
        decision = ConfrontationDecision(allowed=True, reason="test", blocked_action=None)
        with pytest.raises(Exception):
            decision.reason = "changed"  # type: ignore[misc]

    def test_cannot_set_blocked_action_field(self) -> None:
        decision = ConfrontationDecision(allowed=True, reason="test", blocked_action=None)
        with pytest.raises(Exception):
            decision.blocked_action = "confrontation"  # type: ignore[misc]

    def test_not_hashable_eq_works(self) -> None:
        """Equality should work even if frozen class isn't hashed."""
        d1 = ConfrontationDecision(allowed=False, reason="safe mode", blocked_action="blackmail")
        d2 = ConfrontationDecision(allowed=False, reason="safe mode", blocked_action="blackmail")
        assert d1 == d2
        assert d1 is not d2


# =============================================================================
# SafetyState injection via callable
# =============================================================================


class TestSafetyStateInjection:
    """The guard must respect the callable's returned state."""

    def test_guard_reads_state_on_every_call(self) -> None:
        """State changes between calls must be reflected immediately."""
        state = SafetyState.NORMAL

        def _dynamic_getter() -> SafetyState:
            return state

        guard = SurveillanceSafeModeGuard(safety_state_getter=_dynamic_getter)

        # Normal mode — everything allowed
        assert guard.is_confrontation_blocked("blackmail") is False
        decision = guard.check_confrontation("confrontation")
        assert decision.allowed is True

        # Switch to SAFE
        state = SafetyState.SAFE
        assert guard.is_confrontation_blocked("blackmail") is True
        decision = guard.check_confrontation("confrontation")
        assert decision.allowed is False

        # Switch back to NORMAL
        state = SafetyState.NORMAL
        assert guard.is_confrontation_blocked("blackmail") is False


# =============================================================================
# Edge cases
# =============================================================================


class TestEdgeCases:
    """Boundary and edge-case behaviour."""

    def test_empty_action_string_blocked_in_safe(
        self, safe_guard: SurveillanceSafeModeGuard
    ) -> None:
        """Empty string is unknown -- fail-closed BLOCKED in safe mode."""
        decision = safe_guard.check_confrontation("")
        assert decision.allowed is False
        assert "Unknown" in decision.reason

    def test_unknown_action_blocked_in_safe(
        self, safe_guard: SurveillanceSafeModeGuard
    ) -> None:
        """Unknown action -- fail-closed: BLOCKED in safe mode."""
        decision = safe_guard.check_confrontation("some_future_feature")
        assert decision.allowed is False
        assert "Unknown" in decision.reason

    def test_unknown_action_allowed_in_normal(
        self, normal_guard: SurveillanceSafeModeGuard
    ) -> None:
        """Unknown action in NORMAL mode is allowed (everything is)."""
        decision = normal_guard.check_confrontation("some_future_feature")
        assert decision.allowed is True

    def test_decision_has_expected_attributes(self) -> None:
        """``ConfrontationDecision`` must have all three fields."""
        decision = ConfrontationDecision(allowed=False, reason="test", blocked_action="confrontation")
        assert hasattr(decision, "allowed")
        assert hasattr(decision, "reason")
        assert hasattr(decision, "blocked_action")

    def test_blocked_action_none_for_allowed_decision(self) -> None:
        """When allowed=True, ``blocked_action`` must be ``None``."""
        decision = ConfrontationDecision(allowed=True, reason="ok", blocked_action=None)
        assert decision.allowed is True
        assert decision.blocked_action is None

    def test_surveillance_data_available_does_not_change_safe_behavior(
        self, safe_guard: SurveillanceSafeModeGuard
    ) -> None:
        """Even with data available, SAFE mode still blocks confrontation."""
        decision = safe_guard.check_confrontation(
            "blackmail", surveillance_data_available=True
        )
        assert decision.allowed is False
        assert decision.blocked_action == "blackmail"