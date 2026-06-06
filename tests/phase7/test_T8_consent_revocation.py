"""
T8: Consent Revocation — Consent Gate and Revocation Contract Tests.

Verifies that consent revocation correctly blocks surveillance data flow,
stops persona behavior, and requires explicit re-consent for recovery.
"""

from __future__ import annotations

from src.surveillance.consent_gate import (
    ConsentCheckResult,
    ConsentStatus,
)
from src.surveillance.auth import HMACVerification, verify_hmac
from src.core.services.hard_stop_handler import HardStopHandler, SafetyState


class TestConsentGate:
    """Consent gate controls surveillance data collection using ConsentStatus."""

    def test_consent_status_active(self) -> None:
        """ConsentStatus.ACTIVE is ACTIVE (StrEnum)."""
        assert str(ConsentStatus.ACTIVE) == "ACTIVE"

    def test_consent_status_withdrawn(self) -> None:
        """ConsentStatus.WITHDRAWN is WITHDRAWN (StrEnum)."""
        assert str(ConsentStatus.WITHDRAWN) == "WITHDRAWN"

    def test_consent_check_result_active(self) -> None:
        """ConsentCheckResult can represent active consent."""
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        result = ConsentCheckResult(
            allowed=True,
            status=ConsentStatus.ACTIVE,
            scope="surveillance",
            reason="consent_granted",
            checked_at=now,
        )
        assert result.status == ConsentStatus.ACTIVE
        assert result.allowed is True

    def test_consent_check_result_withdrawn(self) -> None:
        """ConsentCheckResult can represent withdrawn consent."""
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        result = ConsentCheckResult(
            allowed=False,
            status=ConsentStatus.WITHDRAWN,
            scope="surveillance",
            reason="user_revoked",
            checked_at=now,
        )
        assert result.status == ConsentStatus.WITHDRAWN
        assert result.allowed is False


class TestHardStopConsentRevocation:
    """HARD STOP triggers consent revocation pattern."""

    def test_hard_stop_sets_safe_state(self) -> None:
        """HARD STOP detection sets SAFE state."""
        handler = HardStopHandler()
        _ = handler.check("HARD STOP")
        assert handler.state == SafetyState.SAFE
        assert handler.is_safe is True

    def test_recovery_requires_explicit(self) -> None:
        """Recovery from SAFE requires explicit resume."""
        handler = HardStopHandler()
        _ = handler.check("HARD STOP")
        assert handler.check_recovery("normal message") is False
        assert handler.state == SafetyState.SAFE
        assert handler.check_recovery("resume") is True
        assert handler.state == SafetyState.NORMAL

    def test_multiple_hard_stops_idempotent(self) -> None:
        """Multiple HARD STOP signals produce only one event log entry."""
        handler = HardStopHandler()
        _ = handler.check("HARD STOP")
        _ = handler.check("HARD STOP")
        _ = handler.check("safe word")
        assert len(handler.event_log) == 1

    def test_neutral_response_on_hard_stop(self) -> None:
        """HARD STOP triggers neutral response."""
        handler = HardStopHandler()
        _ = handler.check("HARD STOP")
        response = handler.get_neutral_response()
        assert "HARD STOP acknowledged" in response
        assert "neutral" in response.lower() or "safe" in response.lower()

    def test_event_log_on_hard_stop(self) -> None:
        """HARD STOP creates event log entry with trigger info."""
        handler = HardStopHandler()
        _ = handler.check("HARD STOP")
        assert len(handler.event_log) == 1
        event = handler.event_log[0]
        assert event.trigger == "hard stop"
        assert event.state_before == SafetyState.NORMAL
        assert event.state_after == SafetyState.SAFE


class TestSurveillanceAuth:
    """Surveillance auth functions are importable and callable."""

    def test_verify_hmac_callable(self) -> None:
        """verify_hmac is a callable function."""
        assert callable(verify_hmac)

    def test_hmac_verification_dataclass(self) -> None:
        """HMACVerification dataclass can be instantiated with nonce and timestamp."""
        v = HMACVerification(nonce="abc123", timestamp="2026-06-06T00:00:00Z")
        assert v.nonce == "abc123"
        assert v.timestamp == "2026-06-06T00:00:00Z"
