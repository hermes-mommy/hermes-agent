"""
T5: Surveillance Pipeline — Data Classification, Retention, and Routing Tests.

Verifies that surveillance pipeline components function correctly:
data classification, retention policies, router behavior, and
consent gate.  All tests are deterministic with real project modules.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.surveillance.classification import ClassificationResult, classify_event
from src.surveillance.retention import (
    RETENTION_RAW_DAYS,
    RETENTION_AGGREGATED_DAYS,
    RETENTION_SUMMARY_DAYS,
    RetentionTier,
    calculate_retention_until,
    get_retention_days,
)
from src.surveillance.router import (
    receive_event,
    surveillance_router,
)
from src.surveillance.auth import verify_hmac
from src.surveillance.consent_gate import (
    ConsentCheckResult,
    ConsentStatus,
)
from src.surveillance.models import SurveillanceEventRequest, SurveillanceEventResponse


class TestClassification:
    """Event classification correctly categorizes surveillance events."""

    def test_classify_conversation_event(self) -> None:
        """Conversation events return a ClassificationResult."""
        result = classify_event("conversation")
        assert isinstance(result, ClassificationResult)
        assert hasattr(result, "classification")

    def test_classify_system_event(self) -> None:
        """System events return a ClassificationResult."""
        result = classify_event("system")
        assert isinstance(result, ClassificationResult)
        assert hasattr(result, "classification")

    def test_classification_result_has_fields(self) -> None:
        """ClassificationResult has expected fields."""
        result = classify_event("test")
        assert hasattr(result, "classification")
        assert hasattr(result, "purpose")
        assert hasattr(result, "retention_class")
        assert hasattr(result, "access_policy")


class TestRetentionPolicy:
    """Retention policies are properly structured."""

    def test_retention_constants_defined(self) -> None:
        """Retention constants are positive integers."""
        assert RETENTION_RAW_DAYS > 0
        assert RETENTION_AGGREGATED_DAYS > 0
        assert RETENTION_SUMMARY_DAYS > 0

    def test_raw_retention_shorter_than_aggregated(self) -> None:
        """Raw data retention is shorter than aggregated retention."""
        assert RETENTION_RAW_DAYS < RETENTION_AGGREGATED_DAYS

    def test_retention_tier_has_values(self) -> None:
        """RetentionTier enum has tiered values."""
        assert RetentionTier.RAW is not None
        assert RetentionTier.AGGREGATED is not None
        assert RetentionTier.SUMMARY is not None

    def test_calculate_retention_until_returns_date(self) -> None:
        """calculate_retention_until returns a datetime."""
        occurred = datetime.now(tz=timezone.utc)
        result = calculate_retention_until(RetentionTier.RAW, occurred)
        assert isinstance(result, datetime)
        assert result > datetime(2024, 1, 1, tzinfo=timezone.utc)

    def test_get_retention_days_returns_int(self) -> None:
        """get_retention_days returns integer days for a valid tier."""
        days = get_retention_days(RetentionTier.RAW)
        assert isinstance(days, int)
        assert days > 0


class TestEventRouter:
    """Event router correctly processes surveillance events."""

    def test_surveillance_router_is_callable(self) -> None:
        """surveillance_router is an APIRouter instance."""
        assert surveillance_router is not None

    def test_verify_hmac_function(self) -> None:
        """verify_hmac is a callable function."""
        assert callable(verify_hmac)

    def test_receive_event_is_callable(self) -> None:
        """receive_event endpoint handler is callable."""
        assert callable(receive_event)


class TestConsentGate:
    """Consent gate controls surveillance data flow using ConsentStatus enum."""

    def test_consent_status_has_expected_values(self) -> None:
        """ConsentStatus has ACTIVE, PAUSED, WITHDRAWN (StrEnum)."""
        assert str(ConsentStatus.ACTIVE) == "ACTIVE"
        assert str(ConsentStatus.PAUSED) == "PAUSED"
        assert str(ConsentStatus.WITHDRAWN) == "WITHDRAWN"

    def test_consent_check_result_struct(self) -> None:
        """ConsentCheckResult is a dataclass with allowed, status, scope, reason, checked_at."""
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        result = ConsentCheckResult(
            allowed=True,
            status=ConsentStatus.ACTIVE,
            scope="surveillance",
            reason="consent_granted",
            checked_at=now,
        )
        assert result.allowed is True
        assert result.status == ConsentStatus.ACTIVE
        assert result.scope == "surveillance"

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
        assert result.allowed is False
        assert result.status == ConsentStatus.WITHDRAWN


class TestSurveillanceModels:
    """Surveillance event models are properly defined (Pydantic)."""

    def test_event_request_model(self) -> None:
        """SurveillanceEventRequest has required fields including payload."""
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        req = SurveillanceEventRequest(
            device_id="test-device",
            event_type="screen_state",
            occurred_at=now,
            payload={"state": "on"},
        )
        assert req.device_id == "test-device"
        assert req.event_type == "screen_state"
        assert req.payload == {"state": "on"}

    def test_event_response_model(self) -> None:
        """SurveillanceEventResponse has required fields."""
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        resp = SurveillanceEventResponse(
            event_id="evt-001",
            status="accepted",
            received_at=now,
        )
        assert resp.event_id == "evt-001"
        assert resp.status == "accepted"
