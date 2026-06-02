"""Comprehensive tests for persona drift detection module."""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from persona.drift_detector import (
    DriftBaseline,
    DriftBaselineError,
    DriftComputationError,
    DriftDetector,
    DriftResult,
)

# ---------------------------------------------------------------------------
# Constants for deterministic test hashes (64 hex chars each, SHA-256 format)
# ---------------------------------------------------------------------------

_BASELINE_HASH: str = "a" * 64  # 64 × 'a'
_EXACT_MATCH_HASH: str = _BASELINE_HASH

# 10 positions differ → score = 10/64 = 0.15625 → "alert" (0.10 < 0.15625 <= 0.20)
_ALERT_HASH: str = "b" * 10 + "a" * 54

# 20 positions differ → score = 20/64 = 0.3125 → "rollback" (> 0.20)
_ROLLBACK_HASH: str = "b" * 20 + "a" * 44

# 3 positions differ → score = 3/64 ≈ 0.046875 → "none" (<= 0.10)
_MINOR_DRIFT_HASH: str = "b" * 3 + "a" * 61

# Different length → score = 1.0 → "rollback"
_SHORT_HASH: str = "c" * 32

_FIXED_NOW: datetime = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def baseline() -> DriftBaseline:
    """Return a standard test baseline."""
    return DriftBaseline(
        prompt_hash=_BASELINE_HASH,
        version="v1.1",
        created_at=_FIXED_NOW,
        description="Test baseline",
    )


@pytest.fixture()
def detector(baseline: DriftBaseline) -> DriftDetector:
    """Return a DriftDetector with the default threshold."""
    return DriftDetector(baseline=baseline)


@pytest.fixture()
def low_threshold_detector(baseline: DriftBaseline) -> DriftDetector:
    """Return a DriftDetector with a low threshold (0.05)."""
    return DriftDetector(baseline=baseline, threshold=0.05)


# ---------------------------------------------------------------------------
# compute_prompt_hash
# ---------------------------------------------------------------------------


class TestComputePromptHash:
    """Tests for DriftDetector.compute_prompt_hash static method."""

    def test_produces_valid_sha256_hex(self) -> None:
        """Hash must be 64 lowercase hex characters."""
        result = DriftDetector.compute_prompt_hash("hello world")
        assert len(result) == 64
        assert re.fullmatch(r"[0-9a-f]{64}", result) is not None

    def test_deterministic(self) -> None:
        """Same input must always produce the same hash."""
        text = "Guinevere SystemPromptMaster v1.1 — full persona definition"
        assert (
            DriftDetector.compute_prompt_hash(text)
            == DriftDetector.compute_prompt_hash(text)
        )

    def test_known_value(self) -> None:
        """Verify against a known SHA-256 digest."""
        expected = (
            "2cf24dba5fb0a30e26e83b2ac5b9e29e"
            "1b161e5c1fa7425e73043362938b9824"
        )
        assert DriftDetector.compute_prompt_hash("hello") == expected

    def test_empty_text_raises(self) -> None:
        with pytest.raises(DriftComputationError, match="must not be empty"):
            DriftDetector.compute_prompt_hash("")


# ---------------------------------------------------------------------------
# compute_drift_score
# ---------------------------------------------------------------------------


class TestComputeDriftScore:
    """Tests for DriftDetector.compute_drift_score."""

    def test_exact_match_returns_zero(self, detector: DriftDetector) -> None:
        assert detector.compute_drift_score(_EXACT_MATCH_HASH) == 0.0

    def test_different_hash_returns_positive(self, detector: DriftDetector) -> None:
        score = detector.compute_drift_score(_ALERT_HASH)
        assert score > 0.0

    def test_different_length_returns_one(self, detector: DriftDetector) -> None:
        assert detector.compute_drift_score(_SHORT_HASH) == 1.0

    @pytest.mark.parametrize(
        ("current_hash", "expected_score"),
        [
            (_BASELINE_HASH, 0.0),
            (_ALERT_HASH, 10 / 64),
            (_ROLLBACK_HASH, 20 / 64),
            (_MINOR_DRIFT_HASH, 3 / 64),
        ],
        ids=["exact", "alert-range", "rollback-range", "minor-drift"],
    )
    def test_known_scores(
        self,
        detector: DriftDetector,
        current_hash: str,
        expected_score: float,
    ) -> None:
        assert detector.compute_drift_score(current_hash) == pytest.approx(
            expected_score
        )

    def test_empty_current_hash_raises(self, detector: DriftDetector) -> None:
        with pytest.raises(DriftComputationError, match="must not be empty"):
            detector.compute_drift_score("")


# ---------------------------------------------------------------------------
# detect — action mapping
# ---------------------------------------------------------------------------


class TestDetect:
    """Tests for DriftDetector.detect action tiers."""

    def test_none_when_exact_match(self, detector: DriftDetector) -> None:
        result = detector.detect(_EXACT_MATCH_HASH, now=_FIXED_NOW)
        assert result.action == "none"
        assert result.drift_detected is False
        assert result.drift_score == 0.0

    def test_none_when_minor_drift(self, detector: DriftDetector) -> None:
        """Score 3/64 ≈ 0.047 is within default threshold 0.10."""
        result = detector.detect(_MINOR_DRIFT_HASH, now=_FIXED_NOW)
        assert result.action == "none"
        assert result.drift_detected is False

    def test_alert_for_moderate_drift(self, detector: DriftDetector) -> None:
        """Score 10/64 = 0.15625 is in alert range (0.10, 0.20]."""
        result = detector.detect(_ALERT_HASH, now=_FIXED_NOW)
        assert result.action == "alert"
        assert result.drift_detected is True

    def test_rollback_for_severe_drift(self, detector: DriftDetector) -> None:
        """Score 20/64 = 0.3125 is in rollback range (> 0.20)."""
        result = detector.detect(_ROLLBACK_HASH, now=_FIXED_NOW)
        assert result.action == "rollback"
        assert result.drift_detected is True

    def test_detect_populates_result_fields(
        self, detector: DriftDetector
    ) -> None:
        result = detector.detect(_ALERT_HASH, now=_FIXED_NOW)
        assert result.baseline_hash == _BASELINE_HASH
        assert result.current_hash == _ALERT_HASH
        assert result.threshold == pytest.approx(0.10)
        assert result.checked_at == _FIXED_NOW

    def test_detect_uses_utc_now_when_no_timestamp(
        self, detector: DriftDetector
    ) -> None:
        before = datetime.now(timezone.utc)
        result = detector.detect(_EXACT_MATCH_HASH)
        after = datetime.now(timezone.utc)
        assert before <= result.checked_at <= after


# ---------------------------------------------------------------------------
# Threshold configuration
# ---------------------------------------------------------------------------


class TestThresholdConfiguration:
    """Tests for configurable threshold behaviour."""

    def test_default_threshold(self, detector: DriftDetector) -> None:
        assert detector.threshold == pytest.approx(0.10)

    def test_custom_threshold(self, baseline: DriftBaseline) -> None:
        det = DriftDetector(baseline=baseline, threshold=0.25)
        assert det.threshold == pytest.approx(0.25)

    def test_low_threshold_changes_action(
        self, low_threshold_detector: DriftDetector
    ) -> None:
        """With threshold=0.05, a score of 3/64 ≈ 0.047 is still 'none'."""
        result = low_threshold_detector.detect(_MINOR_DRIFT_HASH, now=_FIXED_NOW)
        assert result.action == "none"

    def test_low_threshold_alert_boundary(
        self, low_threshold_detector: DriftDetector
    ) -> None:
        """With threshold=0.05, score 10/64 ≈ 0.156 is in rollback (> 0.10)."""
        result = low_threshold_detector.detect(_ALERT_HASH, now=_FIXED_NOW)
        assert result.action == "rollback"

    def test_invalid_threshold_zero_raises(self, baseline: DriftBaseline) -> None:
        with pytest.raises(DriftBaselineError, match="Threshold"):
            DriftDetector(baseline=baseline, threshold=0.0)

    def test_invalid_threshold_negative_raises(
        self, baseline: DriftBaseline
    ) -> None:
        with pytest.raises(DriftBaselineError, match="Threshold"):
            DriftDetector(baseline=baseline, threshold=-0.1)

    def test_invalid_threshold_above_one_raises(
        self, baseline: DriftBaseline
    ) -> None:
        with pytest.raises(DriftBaselineError, match="Threshold"):
            DriftDetector(baseline=baseline, threshold=1.5)

    def test_threshold_one_is_valid(self, baseline: DriftBaseline) -> None:
        det = DriftDetector(baseline=baseline, threshold=1.0)
        assert det.threshold == 1.0


# ---------------------------------------------------------------------------
# update_baseline
# ---------------------------------------------------------------------------


class TestUpdateBaseline:
    """Tests for DriftDetector.update_baseline."""

    def test_update_changes_reference(self, detector: DriftDetector) -> None:
        new_hash = "f" * 64
        new_baseline = DriftBaseline(
            prompt_hash=new_hash,
            version="v2.0",
            created_at=_FIXED_NOW,
            description="Updated prompt",
        )
        detector.update_baseline(new_baseline)
        assert detector.baseline.prompt_hash == new_hash
        assert detector.baseline.version == "v2.0"

    def test_update_affects_subsequent_detection(
        self, detector: DriftDetector
    ) -> None:
        """After updating baseline, old hash should show drift."""
        new_hash = "f" * 64
        new_baseline = DriftBaseline(
            prompt_hash=new_hash,
            version="v2.0",
            created_at=_FIXED_NOW,
        )
        detector.update_baseline(new_baseline)
        # Old baseline hash now differs from new baseline
        result = detector.detect(_BASELINE_HASH, now=_FIXED_NOW)
        assert result.drift_detected is True
        assert result.drift_score > 0.0

    def test_update_empty_hash_raises(self, detector: DriftDetector) -> None:
        bad_baseline = DriftBaseline(
            prompt_hash="",
            version="v2.0",
            created_at=_FIXED_NOW,
        )
        with pytest.raises(DriftBaselineError, match="must not be empty"):
            detector.update_baseline(bad_baseline)


# ---------------------------------------------------------------------------
# check_count & last_result
# ---------------------------------------------------------------------------


class TestCheckCountAndLastResult:
    """Tests for check_count and last_result properties."""

    def test_initial_check_count_zero(self, detector: DriftDetector) -> None:
        assert detector.check_count == 0

    def test_initial_last_result_none(self, detector: DriftDetector) -> None:
        assert detector.last_result is None

    def test_check_count_increments(self, detector: DriftDetector) -> None:
        detector.detect(_EXACT_MATCH_HASH, now=_FIXED_NOW)
        assert detector.check_count == 1
        detector.detect(_ALERT_HASH, now=_FIXED_NOW)
        assert detector.check_count == 2
        detector.detect(_ROLLBACK_HASH, now=_FIXED_NOW)
        assert detector.check_count == 3

    def test_last_result_updates(self, detector: DriftDetector) -> None:
        detector.detect(_EXACT_MATCH_HASH, now=_FIXED_NOW)
        first = detector.last_result
        assert first is not None
        assert first.action == "none"

        detector.detect(_ALERT_HASH, now=_FIXED_NOW)
        second = detector.last_result
        assert second is not None
        assert second.action == "alert"
        # Previous result is replaced, not accumulated
        assert second is not first


# ---------------------------------------------------------------------------
# Frozen dataclass enforcement
# ---------------------------------------------------------------------------


class TestFrozenDataclasses:
    """DriftBaseline and DriftResult must be frozen (immutable)."""

    def test_drift_baseline_is_frozen(self) -> None:
        bl = DriftBaseline(
            prompt_hash="a" * 64,
            version="v1.0",
            created_at=_FIXED_NOW,
        )
        with pytest.raises(FrozenInstanceError):
            bl.prompt_hash = "b" * 64  # type: ignore[misc]

    def test_drift_result_is_frozen(self) -> None:
        result = DriftResult(
            drift_detected=False,
            drift_score=0.0,
            threshold=0.10,
            action="none",
            baseline_hash="a" * 64,
            current_hash="a" * 64,
            checked_at=_FIXED_NOW,
        )
        with pytest.raises(FrozenInstanceError):
            result.drift_score = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------


class TestConstructorValidation:
    """DriftDetector constructor must validate inputs."""

    def test_empty_baseline_hash_raises(self) -> None:
        bad = DriftBaseline(
            prompt_hash="",
            version="v1.0",
            created_at=_FIXED_NOW,
        )
        with pytest.raises(DriftBaselineError, match="must not be empty"):
            DriftDetector(baseline=bad)


# ---------------------------------------------------------------------------
# Parametrized end-to-end scenarios
# ---------------------------------------------------------------------------


class TestEndToEndScenarios:
    """Parametrized end-to-end scenarios covering the full action spectrum."""

    @pytest.mark.parametrize(
        ("current_hash", "expected_action", "expected_drift"),
        [
            (_EXACT_MATCH_HASH, "none", False),
            (_MINOR_DRIFT_HASH, "none", False),
            (_ALERT_HASH, "alert", True),
            (_ROLLBACK_HASH, "rollback", True),
            (_SHORT_HASH, "rollback", True),
        ],
        ids=[
            "exact-match",
            "minor-within-threshold",
            "moderate-alert",
            "severe-rollback",
            "length-mismatch-rollback",
        ],
    )
    def test_action_spectrum(
        self,
        detector: DriftDetector,
        current_hash: str,
        expected_action: str,
        expected_drift: bool,
    ) -> None:
        result = detector.detect(current_hash, now=_FIXED_NOW)
        assert result.action == expected_action
        assert result.drift_detected is expected_drift
