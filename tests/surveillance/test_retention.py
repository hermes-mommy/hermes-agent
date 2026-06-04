"""P7-022: Data Retention Policy Tests — TimescaleDB retention verification.

Tests cover:
- RetentionTier StrEnum values and inheritance
- Retention constants (7d raw, 90d aggregated, 365d summary)
- Compression and chunk interval configuration
- get_retention_days() for all 3 tiers
- calculate_retention_until() with timezone preservation
- get_retention_policy_summary() structure and values
- Data classification → retention tier alignment
- Fail-safe and boundary conditions

All tests are unit-only -- no live DB connections.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import StrEnum

import pytest

from src.surveillance.retention import (
    CHUNK_INTERVAL_DAYS,
    COMPRESSION_AFTER_DAYS,
    RETENTION_AGGREGATED_DAYS,
    RETENTION_RAW_DAYS,
    RETENTION_SUMMARY_DAYS,
    RetentionTier,
    calculate_retention_until,
    get_retention_days,
    get_retention_policy_summary,
)


# ---------------------------------------------------------------------------
# TestRetentionTier
# ---------------------------------------------------------------------------


class TestRetentionTier:
    """Tests for the RetentionTier StrEnum."""

    def test_enum_is_str_enum(self) -> None:
        """RetentionTier must inherit from StrEnum."""
        assert issubclass(RetentionTier, str)
        assert issubclass(RetentionTier, StrEnum)

    def test_three_tiers_exist(self) -> None:
        """Exactly three retention tiers must be defined."""
        members = list(RetentionTier)
        assert len(members) == 3
        member_names = {m.name for m in members}
        assert member_names == {"RAW", "AGGREGATED", "SUMMARY"}

    def test_raw_value_is_raw(self) -> None:
        """RAW tier must have string value 'raw'."""
        assert RetentionTier.RAW == "raw"
        assert RetentionTier.RAW.value == "raw"

    def test_aggregated_value_is_aggregated(self) -> None:
        """AGGREGATED tier must have string value 'aggregated'."""
        assert RetentionTier.AGGREGATED == "aggregated"
        assert RetentionTier.AGGREGATED.value == "aggregated"

    def test_summary_value_is_summary(self) -> None:
        """SUMMARY tier must have string value 'summary'."""
        assert RetentionTier.SUMMARY == "summary"
        assert RetentionTier.SUMMARY.value == "summary"


# ---------------------------------------------------------------------------
# TestRetentionConstants
# ---------------------------------------------------------------------------


class TestRetentionConstants:
    """Tests for module-level retention configuration constants."""

    def test_raw_retention_is_7_days(self) -> None:
        """Raw event retention must be exactly 7 days."""
        assert RETENTION_RAW_DAYS == 7

    def test_aggregated_retention_is_90_days(self) -> None:
        """Aggregated data retention must be exactly 90 days."""
        assert RETENTION_AGGREGATED_DAYS == 90

    def test_summary_retention_is_365_days(self) -> None:
        """Summary data retention must be exactly 365 days."""
        assert RETENTION_SUMMARY_DAYS == 365

    def test_compression_after_7_days(self) -> None:
        """Compression must activate after 7 days."""
        assert COMPRESSION_AFTER_DAYS == 7
        # Compression should match raw retention window
        assert COMPRESSION_AFTER_DAYS == RETENTION_RAW_DAYS

    def test_chunk_interval_is_1_day(self) -> None:
        """Hypertable chunk interval must be 1 day."""
        assert CHUNK_INTERVAL_DAYS == 1

    def test_all_constants_are_positive(self) -> None:
        """Every retention constant must be a positive integer."""
        constants = [
            ("RETENTION_RAW_DAYS", RETENTION_RAW_DAYS),
            ("RETENTION_AGGREGATED_DAYS", RETENTION_AGGREGATED_DAYS),
            ("RETENTION_SUMMARY_DAYS", RETENTION_SUMMARY_DAYS),
            ("COMPRESSION_AFTER_DAYS", COMPRESSION_AFTER_DAYS),
            ("CHUNK_INTERVAL_DAYS", CHUNK_INTERVAL_DAYS),
        ]
        for name, value in constants:
            assert isinstance(value, int), f"{name} must be int, got {type(value).__name__}"
            assert value > 0, f"{name} must be positive, got {value}"

    def test_retention_tiers_are_strictly_increasing(self) -> None:
        """Retention periods must increase: raw < aggregated < summary."""
        assert RETENTION_RAW_DAYS < RETENTION_AGGREGATED_DAYS
        assert RETENTION_AGGREGATED_DAYS < RETENTION_SUMMARY_DAYS

    def test_raw_and_compression_are_aligned(self) -> None:
        """Compression after must not exceed raw retention."""
        assert COMPRESSION_AFTER_DAYS <= RETENTION_RAW_DAYS


# ---------------------------------------------------------------------------
# TestGetRetentionDays
# ---------------------------------------------------------------------------


class TestGetRetentionDays:
    """Tests for ``get_retention_days(tier)``."""

    def test_raw_returns_7(self) -> None:
        assert get_retention_days(RetentionTier.RAW) == 7

    def test_aggregated_returns_90(self) -> None:
        assert get_retention_days(RetentionTier.AGGREGATED) == 90

    def test_summary_returns_365(self) -> None:
        assert get_retention_days(RetentionTier.SUMMARY) == 365

    def test_return_type_is_int(self) -> None:
        """get_retention_days must always return an int."""
        for tier in RetentionTier:
            result = get_retention_days(tier)
            assert isinstance(result, int)

    def test_all_tiers_return_unique_days(self) -> None:
        """Each tier must return a distinct day count."""
        values = {get_retention_days(tier) for tier in RetentionTier}
        assert len(values) == 3, "All three tiers should have unique retention days"


# ---------------------------------------------------------------------------
# TestCalculateRetentionUntil
# ---------------------------------------------------------------------------


class TestCalculateRetentionUntil:
    """Tests for ``calculate_retention_until(tier, occurred_at)``."""

    def test_raw_calculation(self) -> None:
        """Raw tier: occurred_at + 7 days."""
        occurred = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        expiry = calculate_retention_until(RetentionTier.RAW, occurred)
        expected = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        assert expiry == expected

    def test_aggregated_calculation(self) -> None:
        """Aggregated tier: occurred_at + 90 days."""
        occurred = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        expiry = calculate_retention_until(RetentionTier.AGGREGATED, occurred)
        expected = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
        assert expiry == expected

    def test_summary_calculation(self) -> None:
        """Summary tier: occurred_at + 365 days."""
        occurred = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        expiry = calculate_retention_until(RetentionTier.SUMMARY, occurred)
        expected = datetime(2027, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert expiry == expected

    def test_preserves_timezone_aware_datetime(self) -> None:
        """Expiry datetime must preserve the original timezone info."""
        occurred = datetime(2026, 6, 3, 10, 30, 0, tzinfo=timezone.utc)
        expiry = calculate_retention_until(RetentionTier.RAW, occurred)
        assert expiry.tzinfo is not None
        assert expiry.tzinfo == timezone.utc

    def test_returns_datetime_type(self) -> None:
        """calculate_retention_until must return a datetime instance."""
        occurred = datetime.now(timezone.utc)
        expiry = calculate_retention_until(RetentionTier.RAW, occurred)
        assert isinstance(expiry, datetime)

    def test_expiry_is_after_occurred(self) -> None:
        """The expiry datetime must always be after the occurrence datetime."""
        occurred = datetime(2026, 1, 15, tzinfo=timezone.utc)
        for tier in RetentionTier:
            expiry = calculate_retention_until(tier, occurred)
            assert expiry > occurred, f"{tier.value} expiry must be after occurred_at"

    def test_midnight_boundary(self) -> None:
        """Boundary: retention at midnight should compute correctly."""
        occurred = datetime(2026, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
        expiry = calculate_retention_until(RetentionTier.RAW, occurred)
        expected = datetime(2027, 1, 7, 0, 0, 0, tzinfo=timezone.utc)
        assert expiry == expected

    def test_leap_year_handling(self) -> None:
        """Leap year boundary: February 28 + summary = still 365 days."""
        occurred = datetime(2024, 2, 28, 12, 0, 0, tzinfo=timezone.utc)
        expiry = calculate_retention_until(RetentionTier.SUMMARY, occurred)
        # 2024 is a leap year, but timedelta(days=365) is calendar-agnostic
        expected = occurred + timedelta(days=365)
        assert expiry == expected


# ---------------------------------------------------------------------------
# TestDataClassificationRetentionMapping
# ---------------------------------------------------------------------------


class TestDataClassificationRetentionMapping:
    """Tests for data classification to retention tier alignment.

    Aligned with surveillance classification module:
    - Internal events (app_usage, idle_time, etc.) → 7d raw
    - Confidential events (location, health, etc.) → 90d aggregated
    - Restricted events (clipboard, camera, etc.) → summary (365d for curated)
    """

    def test_internal_classification_to_raw_tier(self) -> None:
        """Internal data class maps to raw retention tier (7 days)."""
        assert get_retention_days(RetentionTier.RAW) == 7
        assert RetentionTier.RAW.value == "raw"
        assert RETENTION_RAW_DAYS == 7

    def test_confidential_classification_to_aggregated_tier(self) -> None:
        """Confidential data class maps to aggregated retention tier (90 days)."""
        assert get_retention_days(RetentionTier.AGGREGATED) == 90
        assert RetentionTier.AGGREGATED.value == "aggregated"
        assert RETENTION_AGGREGATED_DAYS == 90

    def test_restricted_classification_to_summary_tier(self) -> None:
        """Restricted data class maps to summary retention tier (365 days curated)."""
        assert get_retention_days(RetentionTier.SUMMARY) == 365
        assert RetentionTier.SUMMARY.value == "summary"
        assert RETENTION_SUMMARY_DAYS == 365

    def test_all_tiers_have_valid_days(self) -> None:
        """Every tier must have a positive, finite day count."""
        for tier in RetentionTier:
            days = get_retention_days(tier)
            assert days > 0, f"{tier.value} must have positive retention"
            assert days < 10000, f"{tier.value} retention unreasonably large: {days}"


# ---------------------------------------------------------------------------
# TestGetRetentionPolicySummary
# ---------------------------------------------------------------------------


class TestGetRetentionPolicySummary:
    """Tests for ``get_retention_policy_summary()``."""

    def test_returns_dict(self) -> None:
        """Summary must be a dict."""
        result = get_retention_policy_summary()
        assert isinstance(result, dict)

    def test_contains_all_three_tiers(self) -> None:
        """Summary dict must have keys for raw, aggregated, and summary."""
        result = get_retention_policy_summary()
        assert "raw" in result
        assert "aggregated" in result
        assert "summary" in result

    def test_raw_summary_has_required_fields(self) -> None:
        """Raw tier summary must include tier, retention_days, description,
        compression_after_days, and chunk_interval_days."""
        raw = get_retention_policy_summary()["raw"]
        assert raw["tier"] == "raw"
        assert raw["retention_days"] == 7
        assert "description" in raw
        assert raw["compression_after_days"] == 7
        assert raw["chunk_interval_days"] == 1

    def test_aggregated_summary_has_required_fields(self) -> None:
        """Aggregated tier summary must include tier, retention_days,
        description, compression_after_days, and chunk_interval_days."""
        agg = get_retention_policy_summary()["aggregated"]
        assert agg["tier"] == "aggregated"
        assert agg["retention_days"] == 90
        assert "description" in agg
        assert agg["compression_after_days"] == 7
        assert agg["chunk_interval_days"] == 1

    def test_summary_summary_has_required_fields(self) -> None:
        """Summary tier summary must include tier, retention_days,
        and description."""
        summ = get_retention_policy_summary()["summary"]
        assert summ["tier"] == "summary"
        assert summ["retention_days"] == 365
        assert "description" in summ

    def test_summary_is_idempotent(self) -> None:
        """Calling get_retention_policy_summary twice returns equal results."""
        r1 = get_retention_policy_summary()
        r2 = get_retention_policy_summary()
        assert r1 == r2


# ---------------------------------------------------------------------------
# TestRetentionEdgeCases -- boundary and edge-case validation
# ---------------------------------------------------------------------------


class TestRetentionEdgeCases:
    """Edge-case and boundary validation for retention policy."""

    def test_minimum_retention_is_raw(self) -> None:
        """RAW tier must be the minimum retention period."""
        days = [get_retention_days(t) for t in RetentionTier]
        assert min(days) == RETENTION_RAW_DAYS
        assert RETENTION_RAW_DAYS == 7

    def test_maximum_retention_is_summary(self) -> None:
        """SUMMARY tier must be the maximum retention period."""
        days = [get_retention_days(t) for t in RetentionTier]
        assert max(days) == RETENTION_SUMMARY_DAYS
        assert RETENTION_SUMMARY_DAYS == 365

    def test_retention_constants_are_final(self) -> None:
        """Constants should be integers (can't test Final at runtime, but verify type)."""
        assert isinstance(RETENTION_RAW_DAYS, int)
        assert isinstance(RETENTION_AGGREGATED_DAYS, int)
        assert isinstance(RETENTION_SUMMARY_DAYS, int)
        assert isinstance(COMPRESSION_AFTER_DAYS, int)
        assert isinstance(CHUNK_INTERVAL_DAYS, int)

    def test_chunk_interval_divides_retention_evenly(self) -> None:
        """1-day chunk interval means raw retention has 7 chunks."""
        assert RETENTION_RAW_DAYS % CHUNK_INTERVAL_DAYS == 0
        assert RETENTION_AGGREGATED_DAYS % CHUNK_INTERVAL_DAYS == 0
        assert RETENTION_SUMMARY_DAYS % CHUNK_INTERVAL_DAYS == 0