"""P4-015: Drift Correction Auto-Rollback — deterministic unit tests.

Tests cover:
- DriftCorrectionResult and RollbackResult dataclass construction
- DriftCorrector.evaluate: no-drift, drift-detected, auto-rollback, safe_mode defer
- DriftCorrector.rollback: success, safe_mode defer, error handling
- DriftCorrector.create_drift_log: persistence, error handling
- Error hierarchy: DriftCorrectionError, RollbackError

All tests use FakeAsyncSession — no real DB connection.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from persona.drift_corrector import (
    DRIFT_THRESHOLD,
    DriftCorrectionError,
    DriftCorrectionResult,
    DriftCorrector,
    RollbackError,
    RollbackResult,
)
from persona.drift_detector import DriftBaseline, DriftDetector
from persona.safe_mode import SafeModeController


# ---------------------------------------------------------------------------
# Fake DB infrastructure (same pattern as test_mood_persistence.py)
# ---------------------------------------------------------------------------

UTC = timezone.utc
NOW = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)


class FakeResult:
    """Mimics SQLAlchemy ``Result`` object."""

    def scalars(self) -> FakeResult:
        return self

    def all(self) -> list[Any]:
        return []

    def scalar_one_or_none(self) -> Any | None:
        return None


class FakeAsyncSession:
    """Deterministic fake of ``AsyncSession`` for unit tests.

    Added objects and commit/rollback calls are tracked for assertion.
    """

    def __init__(self, fail_on_commit: bool = False) -> None:
        self.added: list[Any] = []
        self.committed: int = 0
        self.rolled_back: int = 0
        self._fail_on_commit = fail_on_commit

    async def execute(self, stmt: Any) -> FakeResult:
        return FakeResult()

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        if self._fail_on_commit:
            raise RuntimeError("simulated DB failure on commit")
        self.committed += 1

    async def rollback(self) -> None:
        self.rolled_back += 1


class FailingAsyncSession:
    """Session that raises on commit AND on rollback (double failure)."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.committed: int = 0
        self.rolled_back: int = 0

    async def execute(self, stmt: Any) -> FakeResult:
        return FakeResult()

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        raise RuntimeError("simulated DB failure on commit")

    async def rollback(self) -> None:
        raise RuntimeError("simulated DB failure on rollback")


# ---------------------------------------------------------------------------
# Constants — deterministic test hashes (64 hex chars each, SHA-256 format)
# ---------------------------------------------------------------------------

_BASELINE_HASH: str = "a" * 64

# Exact match → score 0.0, drift_detected=False, action="none"
_EXACT_HASH: str = _BASELINE_HASH

# 3 positions differ → score = 3/64 ≈ 0.047, drift_detected=False, action="none"
_MINOR_DRIFT_HASH: str = "b" * 3 + "a" * 61

# 10 positions differ → score = 10/64 = 0.15625, drift_detected=True, action="alert"
# Auto-rollback triggers since score > DRIFT_THRESHOLD (0.10)
_ALERT_HASH: str = "b" * 10 + "a" * 54

# 20 positions differ → score = 20/64 = 0.3125, drift_detected=True, action="rollback"
_SEVERE_HASH: str = "b" * 20 + "a" * 44

# Different length → score 1.0, drift_detected=True, action="rollback"
_SHORT_HASH: str = "c" * 32


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def baseline() -> DriftBaseline:
    """Return a standard test baseline."""
    return DriftBaseline(
        prompt_hash=_BASELINE_HASH,
        version="v1.1",
        created_at=NOW,
        description="Test baseline for drift corrector",
    )


@pytest.fixture()
def detector(baseline: DriftBaseline) -> DriftDetector:
    """Return a DriftDetector with the default threshold (0.10)."""
    return DriftDetector(baseline=baseline)


@pytest.fixture()
def corrector(detector: DriftDetector) -> DriftCorrector:
    """Return a DriftCorrector without safe_mode controller."""
    return DriftCorrector(detector=detector)


@pytest.fixture()
def safe_controller() -> SafeModeController:
    """Return a SafeModeController in non-active state."""
    return SafeModeController()


@pytest.fixture()
def corrector_with_safe_mode(
    detector: DriftDetector,
    safe_controller: SafeModeController,
) -> DriftCorrector:
    """Return a DriftCorrector with a safe_mode controller (initially inactive)."""
    return DriftCorrector(detector=detector, safe_mode_controller=safe_controller)


@pytest.fixture()
def active_safe_mode_controller(safe_controller: SafeModeController) -> SafeModeController:
    """Return a SafeModeController with safe_mode already active."""
    from persona.safe_mode import DistressLevel, DistressSignal

    signal = DistressSignal(
        text="I feel anxious and helpless",
        detected_level=DistressLevel.D2_MODERATE,
        confidence=0.8,
        matched_patterns=[r"\b(anxious|panic|depressed|anxiety|depresi|cemas|panik|takut)\b"],
        timestamp=NOW,
    )
    safe_controller.evaluate(signal)
    assert safe_controller.is_active
    return safe_controller


@pytest.fixture()
def corrector_active_safe_mode(
    detector: DriftDetector,
    active_safe_mode_controller: SafeModeController,
) -> DriftCorrector:
    """Return a DriftCorrector with safe_mode already active."""
    return DriftCorrector(
        detector=detector,
        safe_mode_controller=active_safe_mode_controller,
    )


# ---------------------------------------------------------------------------
# DriftCorrectionResult dataclass
# ---------------------------------------------------------------------------


class TestDriftCorrectionResult:
    """Tests for DriftCorrectionResult frozen dataclass."""

    def test_construction(self) -> None:
        """All fields populated correctly."""
        result = DriftCorrectionResult(
            drift_detected=True,
            drift_score=0.15,
            action="rollback",
            rollback_performed=True,
            reason="Auto-rollback triggered",
        )
        assert result.drift_detected is True
        assert result.drift_score == 0.15
        assert result.action == "rollback"
        assert result.rollback_performed is True
        assert result.reason == "Auto-rollback triggered"

    def test_frozen_enforcement(self) -> None:
        """Cannot modify fields after construction."""
        result = DriftCorrectionResult(
            drift_detected=False,
            drift_score=0.0,
            action="none",
            rollback_performed=False,
            reason="No drift",
        )
        with pytest.raises(AttributeError):
            result.action = "rollback"

    def test_action_none(self) -> None:
        result = DriftCorrectionResult(
            drift_detected=False,
            drift_score=0.0,
            action="none",
            rollback_performed=False,
            reason="clean",
        )
        assert result.action == "none"

    def test_action_alert(self) -> None:
        result = DriftCorrectionResult(
            drift_detected=True,
            drift_score=0.12,
            action="alert",
            rollback_performed=False,
            reason="safe_mode",
        )
        assert result.action == "alert"


# ---------------------------------------------------------------------------
# RollbackResult dataclass
# ---------------------------------------------------------------------------


class TestRollbackResult:
    """Tests for RollbackResult frozen dataclass."""

    def test_construction(self) -> None:
        result = RollbackResult(
            success=True,
            previous_hash="abc123",
            restored_hash="def456",
            timestamp=NOW,
        )
        assert result.success is True
        assert result.previous_hash == "abc123"
        assert result.restored_hash == "def456"
        assert result.timestamp == NOW

    def test_frozen_enforcement(self) -> None:
        result = RollbackResult(
            success=False,
            previous_hash="",
            restored_hash="",
            timestamp=NOW,
        )
        with pytest.raises(AttributeError):
            result.success = True


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class TestErrorHierarchy:
    """DriftCorrectionError and RollbackError relationship."""

    def test_drift_correction_error_is_exception(self) -> None:
        assert issubclass(DriftCorrectionError, Exception)

    def test_rollback_error_is_drift_correction_error(self) -> None:
        assert issubclass(RollbackError, DriftCorrectionError)

    def test_rollback_error_catchable_as_base(self) -> None:
        with pytest.raises(DriftCorrectionError):
            raise RollbackError("test rollback failure")


# ---------------------------------------------------------------------------
# evaluate — no drift scenarios
# ---------------------------------------------------------------------------


class TestEvaluateNoDrift:
    """evaluate returns action='none' when drift_score is within threshold."""

    @pytest.mark.asyncio
    async def test_exact_match(self, corrector: DriftCorrector) -> None:
        """Exact hash match → score 0.0, no drift."""
        db = FakeAsyncSession()
        result = await corrector.evaluate(db, _EXACT_HASH)
        assert result.drift_detected is False
        assert result.drift_score == 0.0
        assert result.action == "none"
        assert result.rollback_performed is False

    @pytest.mark.asyncio
    async def test_minor_drift_within_threshold(
        self, corrector: DriftCorrector
    ) -> None:
        """Score 3/64 ≈ 0.047 < 0.10 → no drift."""
        db = FakeAsyncSession()
        result = await corrector.evaluate(db, _MINOR_DRIFT_HASH)
        assert result.drift_detected is False
        assert result.drift_score == pytest.approx(3 / 64)
        assert result.action == "none"
        assert result.rollback_performed is False

    @pytest.mark.asyncio
    async def test_no_drift_reason_message(
        self, corrector: DriftCorrector
    ) -> None:
        """Reason string indicates no drift when score is within threshold."""
        db = FakeAsyncSession()
        result = await corrector.evaluate(db, _EXACT_HASH)
        assert "No drift" in result.reason

    @pytest.mark.asyncio
    async def test_no_drift_creates_drift_log(
        self, corrector: DriftCorrector
    ) -> None:
        """DriftLog entry is persisted even for no-drift evaluations."""
        db = FakeAsyncSession()
        await corrector.evaluate(db, _EXACT_HASH)
        assert len(db.added) == 1
        assert db.committed == 1

    @pytest.mark.asyncio
    async def test_no_drift_increments_detector_count(
        self, corrector: DriftCorrector
    ) -> None:
        """Detector's check_count increments after evaluate."""
        db = FakeAsyncSession()
        assert corrector.detector.check_count == 0
        await corrector.evaluate(db, _EXACT_HASH)
        assert corrector.detector.check_count == 1


# ---------------------------------------------------------------------------
# evaluate — drift detected with auto-rollback
# ---------------------------------------------------------------------------


class TestEvaluateDriftDetected:
    """evaluate triggers auto-rollback when drift_score > DRIFT_THRESHOLD."""

    @pytest.mark.asyncio
    async def test_alert_range_triggers_auto_rollback(
        self, corrector: DriftCorrector
    ) -> None:
        """Score 10/64 = 0.15625 > 0.10 → auto-rollback."""
        db = FakeAsyncSession()
        result = await corrector.evaluate(db, _ALERT_HASH)
        assert result.drift_detected is True
        assert result.drift_score == pytest.approx(10 / 64)
        assert result.action == "rollback"
        assert result.rollback_performed is True

    @pytest.mark.asyncio
    async def test_severe_drift_triggers_auto_rollback(
        self, corrector: DriftCorrector
    ) -> None:
        """Score 20/64 = 0.3125 > 0.10 → auto-rollback."""
        db = FakeAsyncSession()
        result = await corrector.evaluate(db, _SEVERE_HASH)
        assert result.drift_detected is True
        assert result.action == "rollback"
        assert result.rollback_performed is True

    @pytest.mark.asyncio
    async def test_length_mismatch_triggers_auto_rollback(
        self, corrector: DriftCorrector
    ) -> None:
        """Score 1.0 > 0.10 → auto-rollback."""
        db = FakeAsyncSession()
        result = await corrector.evaluate(db, _SHORT_HASH)
        assert result.drift_detected is True
        assert result.drift_score == 1.0
        assert result.action == "rollback"
        assert result.rollback_performed is True

    @pytest.mark.asyncio
    async def test_drift_reason_contains_score(
        self, corrector: DriftCorrector
    ) -> None:
        """Reason string includes drift_score and threshold."""
        db = FakeAsyncSession()
        result = await corrector.evaluate(db, _SEVERE_HASH)
        assert "drift_score=" in result.reason
        assert "threshold=" in result.reason

    @pytest.mark.asyncio
    async def test_drift_creates_rollback_and_evaluation_logs(
        self, corrector: DriftCorrector
    ) -> None:
        """Auto-rollback creates 2 DriftLog entries: rollback + evaluation."""
        db = FakeAsyncSession()
        await corrector.evaluate(db, _SEVERE_HASH)
        # rollback() creates 1 log entry + evaluate() creates 1 log entry
        assert len(db.added) == 2
        assert db.committed == 2


# ---------------------------------------------------------------------------
# evaluate — safe_mode defer
# ---------------------------------------------------------------------------


class TestEvaluateSafeModeDefer:
    """evaluate defers rollback when safe_mode is active."""

    @pytest.mark.asyncio
    async def test_safe_mode_active_defers_rollback(
        self,
        detector: DriftDetector,
        active_safe_mode_controller: SafeModeController,
    ) -> None:
        """Drift detected + safe_mode active → action='alert', no rollback."""
        corrector = DriftCorrector(
            detector=detector,
            safe_mode_controller=active_safe_mode_controller,
        )
        db = FakeAsyncSession()
        result = await corrector.evaluate(db, _SEVERE_HASH)
        assert result.drift_detected is True
        assert result.action == "alert"
        assert result.rollback_performed is False

    @pytest.mark.asyncio
    async def test_safe_mode_defer_reason_mentions_safe_mode(
        self,
        detector: DriftDetector,
        active_safe_mode_controller: SafeModeController,
    ) -> None:
        """Deferred rollback reason mentions safe_mode."""
        corrector = DriftCorrector(
            detector=detector,
            safe_mode_controller=active_safe_mode_controller,
        )
        db = FakeAsyncSession()
        result = await corrector.evaluate(db, _SEVERE_HASH)
        assert "safe_mode" in result.reason

    @pytest.mark.asyncio
    async def test_safe_mode_inactive_allows_rollback(
        self, corrector_with_safe_mode: DriftCorrector
    ) -> None:
        """safe_mode controller present but inactive → auto-rollback proceeds."""
        db = FakeAsyncSession()
        result = await corrector_with_safe_mode.evaluate(db, _SEVERE_HASH)
        assert result.drift_detected is True
        assert result.action == "rollback"
        assert result.rollback_performed is True

    @pytest.mark.asyncio
    async def test_safe_mode_no_drift_still_returns_none(
        self, corrector_with_safe_mode: DriftCorrector
    ) -> None:
        """No drift + safe_mode inactive → action='none'."""
        db = FakeAsyncSession()
        result = await corrector_with_safe_mode.evaluate(db, _EXACT_HASH)
        assert result.action == "none"
        assert result.rollback_performed is False

    @pytest.mark.asyncio
    async def test_safe_mode_defer_creates_evaluation_log_only(
        self,
        detector: DriftDetector,
        active_safe_mode_controller: SafeModeController,
    ) -> None:
        """Deferred rollback creates only the evaluation DriftLog (no rollback log)."""
        corrector = DriftCorrector(
            detector=detector,
            safe_mode_controller=active_safe_mode_controller,
        )
        db = FakeAsyncSession()
        await corrector.evaluate(db, _SEVERE_HASH)
        # Only the evaluation log entry (no rollback log)
        assert len(db.added) == 1
        assert db.committed == 1


# ---------------------------------------------------------------------------
# rollback
# ---------------------------------------------------------------------------


class TestRollback:
    """Tests for DriftCorrector.rollback."""

    @pytest.mark.asyncio
    async def test_rollback_success(self, corrector: DriftCorrector) -> None:
        """Rollback returns success=True and correct hashes."""
        # First run a detection so last_result is populated
        corrector.detector.detect(_SEVERE_HASH, now=NOW)

        db = FakeAsyncSession()
        result = await corrector.rollback(db, reason="test rollback")
        assert result.success is True
        assert result.restored_hash == _BASELINE_HASH
        assert result.previous_hash == _SEVERE_HASH
        assert isinstance(result.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_rollback_restored_hash_is_baseline(
        self, corrector: DriftCorrector
    ) -> None:
        """Restored hash always matches the detector baseline."""
        corrector.detector.detect(_ALERT_HASH, now=NOW)
        db = FakeAsyncSession()
        result = await corrector.rollback(db, reason="baseline restore")
        assert result.restored_hash == corrector.detector.baseline.prompt_hash

    @pytest.mark.asyncio
    async def test_rollback_previous_hash_from_last_result(
        self, corrector: DriftCorrector
    ) -> None:
        """Previous hash comes from the last detection's current_hash."""
        corrector.detector.detect(_ALERT_HASH, now=NOW)
        db = FakeAsyncSession()
        result = await corrector.rollback(db, reason="check previous")
        assert result.previous_hash == _ALERT_HASH

    @pytest.mark.asyncio
    async def test_rollback_no_previous_detection(
        self, corrector: DriftCorrector
    ) -> None:
        """When no prior detection, previous_hash is empty string."""
        db = FakeAsyncSession()
        result = await corrector.rollback(db, reason="no prior check")
        assert result.success is True
        assert result.previous_hash == ""

    @pytest.mark.asyncio
    async def test_rollback_creates_drift_log(
        self, corrector: DriftCorrector
    ) -> None:
        """Rollback persists a DriftLog entry."""
        corrector.detector.detect(_SEVERE_HASH, now=NOW)
        db = FakeAsyncSession()
        await corrector.rollback(db, reason="log test")
        assert len(db.added) == 1
        assert db.committed == 1

    @pytest.mark.asyncio
    async def test_rollback_with_safe_mode_defers(
        self,
        detector: DriftDetector,
        active_safe_mode_controller: SafeModeController,
    ) -> None:
        """Safe_mode active → rollback deferred, success=False."""
        corrector = DriftCorrector(
            detector=detector,
            safe_mode_controller=active_safe_mode_controller,
        )
        db = FakeAsyncSession()
        result = await corrector.rollback(db, reason="should defer")
        assert result.success is False
        assert result.previous_hash == ""
        assert result.restored_hash == ""

    @pytest.mark.asyncio
    async def test_rollback_commit_failure_raises_rollback_error(
        self, corrector: DriftCorrector
    ) -> None:
        """DB commit failure during rollback raises RollbackError."""
        corrector.detector.detect(_SEVERE_HASH, now=NOW)
        db = FakeAsyncSession(fail_on_commit=True)
        with pytest.raises(RollbackError, match="Failed to persist"):
            await corrector.rollback(db, reason="commit fail")
        # Session rollback should have been called
        assert db.rolled_back >= 1

    @pytest.mark.asyncio
    async def test_rollback_timestamp_is_utc(
        self, corrector: DriftCorrector
    ) -> None:
        """Rollback timestamp is timezone-aware UTC."""
        corrector.detector.detect(_SEVERE_HASH, now=NOW)
        db = FakeAsyncSession()
        result = await corrector.rollback(db, reason="utc test")
        assert result.timestamp.tzinfo is not None

    @pytest.mark.asyncio
    async def test_rollback_double_failure_raises(
        self, corrector: DriftCorrector
    ) -> None:
        """Both commit and rollback fail → RollbackError still raised."""
        corrector.detector.detect(_SEVERE_HASH, now=NOW)
        db = FailingAsyncSession()
        with pytest.raises(RollbackError):
            await corrector.rollback(db, reason="double fail")


# ---------------------------------------------------------------------------
# create_drift_log
# ---------------------------------------------------------------------------


class TestCreateDriftLog:
    """Tests for DriftCorrector.create_drift_log."""

    @pytest.mark.asyncio
    async def test_creates_drift_log_entry(
        self, corrector: DriftCorrector
    ) -> None:
        """DriftLog is added to session and committed."""
        from persona.drift_detector import DriftResult

        drift_result = DriftResult(
            drift_detected=False,
            drift_score=0.0,
            threshold=0.10,
            action="none",
            baseline_hash=_BASELINE_HASH,
            current_hash=_EXACT_HASH,
            checked_at=NOW,
        )
        db = FakeAsyncSession()
        log_entry = await corrector.create_drift_log(db, drift_result, "none")
        assert len(db.added) == 1
        assert db.committed == 1
        assert log_entry is db.added[0]

    @pytest.mark.asyncio
    async def test_drift_log_fields_populated(
        self, corrector: DriftCorrector
    ) -> None:
        """DriftLog fields are correctly mapped from DriftResult."""
        from persona.drift_detector import DriftResult

        drift_result = DriftResult(
            drift_detected=True,
            drift_score=0.25,
            threshold=0.10,
            action="rollback",
            baseline_hash=_BASELINE_HASH,
            current_hash=_SEVERE_HASH,
            checked_at=NOW,
        )
        db = FakeAsyncSession()
        log_entry = await corrector.create_drift_log(db, drift_result, "rollback")
        assert log_entry.drift_type == "rollback"
        assert log_entry.before_state["prompt_hash"] == _BASELINE_HASH
        assert log_entry.after_state["prompt_hash"] == _SEVERE_HASH
        assert log_entry.delta["drift_score"] == 0.25
        assert log_entry.delta["drift_detected"] is True
        assert log_entry.trigger_context == "drift_corrector:rollback"
        assert log_entry.safety_score == 25
        assert log_entry.rollback_available is True
        assert log_entry.occurred_at == NOW

    @pytest.mark.asyncio
    async def test_drift_log_rollback_available_false_for_none(
        self, corrector: DriftCorrector
    ) -> None:
        """rollback_available is False when action is 'none'."""
        from persona.drift_detector import DriftResult

        drift_result = DriftResult(
            drift_detected=False,
            drift_score=0.0,
            threshold=0.10,
            action="none",
            baseline_hash=_BASELINE_HASH,
            current_hash=_EXACT_HASH,
            checked_at=NOW,
        )
        db = FakeAsyncSession()
        log_entry = await corrector.create_drift_log(db, drift_result, "none")
        assert log_entry.rollback_available is False

    @pytest.mark.asyncio
    async def test_drift_log_commit_failure_raises(
        self, corrector: DriftCorrector
    ) -> None:
        """DB commit failure during log creation raises DriftCorrectionError."""
        from persona.drift_detector import DriftResult

        drift_result = DriftResult(
            drift_detected=False,
            drift_score=0.0,
            threshold=0.10,
            action="none",
            baseline_hash=_BASELINE_HASH,
            current_hash=_EXACT_HASH,
            checked_at=NOW,
        )
        db = FakeAsyncSession(fail_on_commit=True)
        with pytest.raises(DriftCorrectionError, match="Failed to persist"):
            await corrector.create_drift_log(db, drift_result, "none")
        # Session rollback should have been called
        assert db.rolled_back >= 1

    @pytest.mark.asyncio
    async def test_drift_log_double_failure_still_raises(
        self, corrector: DriftCorrector
    ) -> None:
        """Both commit and rollback fail → DriftCorrectionError still raised."""
        from persona.drift_detector import DriftResult

        drift_result = DriftResult(
            drift_detected=False,
            drift_score=0.0,
            threshold=0.10,
            action="none",
            baseline_hash=_BASELINE_HASH,
            current_hash=_EXACT_HASH,
            checked_at=NOW,
        )
        db = FailingAsyncSession()
        with pytest.raises(DriftCorrectionError, match="Failed to persist"):
            await corrector.create_drift_log(db, drift_result, "none")


# ---------------------------------------------------------------------------
# Constructor and properties
# ---------------------------------------------------------------------------


class TestDriftCorrectorConstruction:
    """Tests for DriftCorrector constructor and properties."""

    def test_constructor_without_safe_mode(self, detector: DriftDetector) -> None:
        corrector = DriftCorrector(detector=detector)
        assert corrector.detector is detector
        assert corrector.safe_mode_controller is None

    def test_constructor_with_safe_mode(
        self,
        detector: DriftDetector,
        safe_controller: SafeModeController,
    ) -> None:
        corrector = DriftCorrector(
            detector=detector,
            safe_mode_controller=safe_controller,
        )
        assert corrector.detector is detector
        assert corrector.safe_mode_controller is safe_controller


# ---------------------------------------------------------------------------
# DRIFT_THRESHOLD constant
# ---------------------------------------------------------------------------


class TestDriftThresholdConstant:
    """Verify the DRIFT_THRESHOLD constant."""

    def test_threshold_value(self) -> None:
        assert DRIFT_THRESHOLD == 0.10

    def test_threshold_matches_detector_default(self, detector: DriftDetector) -> None:
        """DRIFT_THRESHOLD matches DriftDetector.DEFAULT_THRESHOLD."""
        assert DRIFT_THRESHOLD == pytest.approx(detector.threshold)


# ---------------------------------------------------------------------------
# Parametrized end-to-end scenarios
# ---------------------------------------------------------------------------


class TestEndToEndScenarios:
    """Parametrized scenarios covering the full action spectrum."""

    @pytest.mark.parametrize(
        ("current_hash", "expected_action", "expected_drift", "expected_rollback"),
        [
            (_EXACT_HASH, "none", False, False),
            (_MINOR_DRIFT_HASH, "none", False, False),
            (_ALERT_HASH, "rollback", True, True),
            (_SEVERE_HASH, "rollback", True, True),
            (_SHORT_HASH, "rollback", True, True),
        ],
        ids=[
            "exact-match",
            "minor-within-threshold",
            "alert-range-rollback",
            "severe-rollback",
            "length-mismatch-rollback",
        ],
    )
    @pytest.mark.asyncio
    async def test_action_spectrum(
        self,
        corrector: DriftCorrector,
        current_hash: str,
        expected_action: str,
        expected_drift: bool,
        expected_rollback: bool,
    ) -> None:
        db = FakeAsyncSession()
        result = await corrector.evaluate(db, current_hash)
        assert result.action == expected_action
        assert result.drift_detected is expected_drift
        assert result.rollback_performed is expected_rollback
