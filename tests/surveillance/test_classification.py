"""P7-008: Data classification module — comprehensive unit tests.

Tests cover:
- DataClassification enum values and string representations
- classify_event() for all 12 known event types
- classify_event() fail-closed behavior for unknown event types
- ClassificationResult dataclass immutability
- get_retention_days() for all 7 retention classes + unknown
- EVENT_TYPE_CLASSIFICATION mapping completeness and encryption profiles

All tests use synthetic parameter values — no real surveillance data.
"""

from __future__ import annotations

import sys
from enum import StrEnum
from pathlib import Path
from unittest.mock import patch

import pytest

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
sys.path.insert(0, _PROJECT_ROOT)

from src.surveillance.classification import (  # noqa: E402
    EVENT_TYPE_CLASSIFICATION,
    ClassificationResult,
    DataClassification,
    classify_event,
    get_retention_days,
)


# ---------------------------------------------------------------------------
# TestDataClassificationEnum
# ---------------------------------------------------------------------------


class TestDataClassificationEnum:
    """Tests for the DataClassification StrEnum."""

    def test_enum_is_str_enum(self) -> None:
        """DataClassification must inherit from StrEnum."""
        assert issubclass(DataClassification, str)
        assert issubclass(DataClassification, StrEnum)

    def test_three_values_exist(self) -> None:
        """Exactly three classification levels must be defined."""
        members = list(DataClassification)
        assert len(members) == 3
        member_names = {m.name for m in members}
        assert member_names == {"INTERNAL", "CONFIDENTIAL", "RESTRICTED"}

    def test_internal_value(self) -> None:
        """INTERNAL must have string value 'Internal'."""
        assert DataClassification.INTERNAL == "Internal"
        assert DataClassification.INTERNAL.value == "Internal"
        assert str(DataClassification.INTERNAL) == "Internal"

    def test_confidential_value(self) -> None:
        """CONFIDENTIAL must have string value 'Confidential'."""
        assert DataClassification.CONFIDENTIAL == "Confidential"
        assert DataClassification.CONFIDENTIAL.value == "Confidential"

    def test_restricted_value(self) -> None:
        """RESTRICTED must have string value 'Restricted'."""
        assert DataClassification.RESTRICTED == "Restricted"
        assert DataClassification.RESTRICTED.value == "Restricted"


# ---------------------------------------------------------------------------
# TestClassifyEvent — known event types
# ---------------------------------------------------------------------------


KNOWN_EVENT_TYPES = [
    # (event_type, expected_classification, purpose, retention_class, access_policy, enc_profile)
    ("app_usage", DataClassification.INTERNAL, "productivity_monitoring", "short_raw", "guinevere_core", "standard"),
    ("screen_state", DataClassification.INTERNAL, "activity_tracking", "short_raw", "guinevere_core", "standard"),
    ("active_window", DataClassification.INTERNAL, "productivity_monitoring", "short_raw", "guinevere_core", "standard"),
    ("idle_time", DataClassification.INTERNAL, "activity_tracking", "short_raw", "guinevere_core", "standard"),
    ("notification", DataClassification.CONFIDENTIAL, "context_awareness", "short_raw", "guinevere_core+faiz", "standard"),
    ("browser", DataClassification.CONFIDENTIAL, "productivity_monitoring", "short_raw", "guinevere_core+faiz", "standard"),
    ("location", DataClassification.CONFIDENTIAL, "safety_geofencing", "short_raw", "guinevere_core+faiz", "enhanced"),
    ("call_log", DataClassification.CONFIDENTIAL, "context_awareness", "short_raw", "guinevere_core+faiz", "enhanced"),
    ("health", DataClassification.CONFIDENTIAL, "health_monitoring", "medium_operational", "guinevere_core+faiz", "enhanced"),
    ("clipboard", DataClassification.RESTRICTED, "secret_protection", "transient", "guinevere_core_only", "high"),
    ("screenshot", DataClassification.RESTRICTED, "visual_context", "critical_media", "guinevere_core_only", "high"),
    ("camera", DataClassification.RESTRICTED, "visual_context", "critical_media", "guinevere_core_only", "high"),
]


class TestClassifyEvent:
    """Tests for the classify_event() function."""

    @pytest.mark.parametrize(
        "event_type,expected_class,purpose,retention_class,access_policy,enc_profile",
        KNOWN_EVENT_TYPES,
    )
    def test_known_event_type_returns_correct_classification(
        self,
        event_type: str,
        expected_class: DataClassification,
        purpose: str,
        retention_class: str,
        access_policy: str,
        enc_profile: str,
    ) -> None:
        """Each known event type must return the exact ClassificationResult."""
        result = classify_event(event_type)
        assert isinstance(result, ClassificationResult)
        assert result.classification == expected_class
        assert result.purpose == purpose
        assert result.retention_class == retention_class
        assert result.access_policy == access_policy
        assert result.encryption_profile == enc_profile

    def test_unknown_event_type_fail_closed(self) -> None:
        """Unknown event types must default to Restricted with transient retention."""
        result = classify_event("unknown_sensor")
        assert result.classification == DataClassification.RESTRICTED
        assert result.purpose == "unknown"
        assert result.retention_class == "transient"
        assert result.access_policy == "guinevere_core_only"
        assert result.encryption_profile == "high"

    def test_unknown_event_type_with_empty_string(self) -> None:
        """Empty string event type must also fail-closed to Restricted."""
        result = classify_event("")
        assert result.classification == DataClassification.RESTRICTED

    def test_classification_result_is_frozen(self) -> None:
        """ClassificationResult must be immutable (frozen=True)."""
        result = classify_event("app_usage")
        with pytest.raises(AttributeError):
            setattr(result, "classification", DataClassification.CONFIDENTIAL)

    @patch("src.surveillance.classification.logger")
    def test_classify_event_logs_debug(self, mock_logger) -> None:
        """classify_event must log classification at debug level."""
        classify_event("app_usage")
        mock_logger.debug.assert_called()
        call_args = mock_logger.debug.call_args
        assert call_args[0][0] == "event_classified"
        assert call_args[1]["event_type"] == "app_usage"


# ---------------------------------------------------------------------------
# TestGetRetentionDays
# ---------------------------------------------------------------------------


class TestGetRetentionDays:
    """Tests for the get_retention_days() function."""

    def test_transient_returns_1(self) -> None:
        assert get_retention_days("transient") == 1

    def test_short_raw_returns_7(self) -> None:
        assert get_retention_days("short_raw") == 7

    def test_critical_media_returns_1(self) -> None:
        assert get_retention_days("critical_media") == 1

    def test_medium_operational_returns_90(self) -> None:
        assert get_retention_days("medium_operational") == 90

    def test_long_term_curated_returns_365(self) -> None:
        assert get_retention_days("long_term_curated") == 365

    def test_regulated_audit_returns_365(self) -> None:
        assert get_retention_days("regulated_audit") == 365

    def test_formal_hold_returns_730(self) -> None:
        assert get_retention_days("formal_hold") == 730

    def test_unknown_retention_class_fail_closed(self) -> None:
        """Unknown retention classes must default to 1 day (fail-closed)."""
        assert get_retention_days("nonexistent_class") == 1

    def test_empty_string_fail_closed(self) -> None:
        """Empty string retention class must default to 1 day."""
        assert get_retention_days("") == 1

    def test_return_type_is_int(self) -> None:
        """get_retention_days must always return an int."""
        result = get_retention_days("short_raw")
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# TestClassificationMapping
# ---------------------------------------------------------------------------


class TestClassificationMapping:
    """Tests for the EVENT_TYPE_CLASSIFICATION mapping."""

    def test_all_12_event_types_in_mapping(self) -> None:
        """The mapping must contain exactly 12 known event types."""
        assert len(EVENT_TYPE_CLASSIFICATION) == 12
        expected_types = {
            "app_usage", "screen_state", "active_window", "idle_time",
            "notification", "browser", "location", "call_log",
            "health", "clipboard", "screenshot", "camera",
        }
        assert set(EVENT_TYPE_CLASSIFICATION.keys()) == expected_types

    def test_restricted_types_use_high_encryption(self) -> None:
        """All Restricted event types must use 'high' encryption profile."""
        restricted_types = ["clipboard", "screenshot", "camera"]
        for event_type in restricted_types:
            result = classify_event(event_type)
            assert result.encryption_profile == "high", (
                f"{event_type} expected 'high' encryption, got '{result.encryption_profile}'"
            )

    def test_internal_types_use_standard_encryption(self) -> None:
        """All Internal event types must use 'standard' encryption profile."""
        internal_types = ["app_usage", "screen_state", "active_window", "idle_time"]
        for event_type in internal_types:
            result = classify_event(event_type)
            assert result.encryption_profile == "standard", (
                f"{event_type} expected 'standard' encryption, got '{result.encryption_profile}'"
            )

    def test_confidential_health_uses_enhanced_encryption(self) -> None:
        """Confidential health data must use 'enhanced' encryption."""
        result = classify_event("health")
        assert result.classification == DataClassification.CONFIDENTIAL
        assert result.encryption_profile == "enhanced"

    def test_confidential_location_uses_enhanced_encryption(self) -> None:
        """Confidential location data must use 'enhanced' encryption."""
        result = classify_event("location")
        assert result.encryption_profile == "enhanced"

    def test_classification_result_all_fields_populated(self) -> None:
        """Every ClassificationResult must have all five fields non-empty."""
        for event_type, result in EVENT_TYPE_CLASSIFICATION.items():
            assert isinstance(result.classification, DataClassification), (
                f"{event_type} classification is not a DataClassification"
            )
            assert isinstance(result.purpose, str) and result.purpose, (
                f"{event_type} purpose is empty"
            )
            assert isinstance(result.retention_class, str) and result.retention_class, (
                f"{event_type} retention_class is empty"
            )
            assert isinstance(result.access_policy, str) and result.access_policy, (
                f"{event_type} access_policy is empty"
            )
            assert isinstance(result.encryption_profile, str) and result.encryption_profile, (
                f"{event_type} encryption_profile is empty"
            )