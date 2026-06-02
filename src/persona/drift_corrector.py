"""Drift correction with auto-rollback — evaluates drift and restores baseline when safe."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog

from src.persona.drift_detector import DriftDetector, DriftResult
from src.persona.safe_mode import SafeModeController
from src.memory.models import DriftLog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DRIFT_THRESHOLD: float = 0.10


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DriftCorrectionError(Exception):
    """Base exception for drift correction errors."""


class RollbackError(DriftCorrectionError):
    """Raised when rollback operation fails."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DriftCorrectionResult:
    """Outcome of a drift evaluation cycle."""

    drift_detected: bool
    drift_score: float
    action: str  # "none" | "alert" | "rollback"
    rollback_performed: bool
    reason: str


@dataclass(frozen=True)
class RollbackResult:
    """Outcome of a rollback attempt."""

    success: bool
    previous_hash: str
    restored_hash: str
    timestamp: datetime


# ---------------------------------------------------------------------------
# DriftCorrector
# ---------------------------------------------------------------------------


class DriftCorrector:
    """Evaluates persona drift and performs auto-rollback when threshold is exceeded.

    Integrates with an existing :class:`DriftDetector` for hash comparison and
    optionally consults a :class:`SafeModeController` to defer rollback during
    operator distress.
    """

    def __init__(
        self,
        detector: DriftDetector,
        safe_mode_controller: SafeModeController | None = None,
    ) -> None:
        self._detector: DriftDetector = detector
        self._safe_mode_controller: SafeModeController | None = safe_mode_controller

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def detector(self) -> DriftDetector:
        """The underlying drift detector."""
        return self._detector

    @property
    def safe_mode_controller(self) -> SafeModeController | None:
        """The safe-mode controller, or ``None`` if not configured."""
        return self._safe_mode_controller

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def evaluate(
        self,
        db: Any,
        current_prompt_hash: str,
    ) -> DriftCorrectionResult:
        """Run drift detection and take corrective action.

        1. Delegates to :meth:`DriftDetector.detect` to obtain a
           :class:`DriftResult`.
        2. If ``drift_score > DRIFT_THRESHOLD`` (i.e. ``drift_detected``),
           determines action:
           - **safe_mode active** → ``action="alert"``, rollback deferred.
           - **safe_mode inactive** → ``action="rollback"``, auto-rollback
             attempted.
        3. Persists a :class:`DriftLog` entry for every evaluation.

        Args:
            db: Database session (duck-typed AsyncSession).
            current_prompt_hash: SHA-256 hash of the currently loaded prompt.

        Returns:
            A :class:`DriftCorrectionResult` summarizing the outcome.

        Raises:
            DriftCorrectionError: If drift detection itself fails or log
                persistence fails.
        """
        try:
            drift_result = self._detector.detect(current_prompt_hash)
        except Exception as exc:
            logger.error("drift_detection_failed", error=str(exc))
            raise DriftCorrectionError(
                f"Drift detection failed: {exc}"
            ) from exc

        rollback_performed = False
        reason: str

        if not drift_result.drift_detected:
            action = "none"
            reason = "No drift detected; score within threshold."
        elif self._safe_mode_controller is not None and self._safe_mode_controller.is_active:
            action = "alert"
            reason = (
                "Drift detected but safe_mode is active; rollback deferred."
            )
            logger.warning(
                "drift_rollback_deferred",
                reason="safe_mode_active",
                drift_score=drift_result.drift_score,
            )
        else:
            action = "rollback"
            reason = (
                f"Auto-rollback triggered: drift_score={drift_result.drift_score:.6f} "
                f"> threshold={DRIFT_THRESHOLD}."
            )
            try:
                await self.rollback(db, reason=reason)
                rollback_performed = True
            except RollbackError:
                raise
            except Exception as exc:
                raise RollbackError(
                    f"Auto-rollback failed: {exc}"
                ) from exc

        # Persist drift log for every evaluation
        await self.create_drift_log(db, drift_result=drift_result, action_taken=action)

        logger.info(
            "drift_evaluation_complete",
            drift_detected=drift_result.drift_detected,
            drift_score=drift_result.drift_score,
            action=action,
            rollback_performed=rollback_performed,
        )

        return DriftCorrectionResult(
            drift_detected=drift_result.drift_detected,
            drift_score=drift_result.drift_score,
            action=action,
            rollback_performed=rollback_performed,
            reason=reason,
        )

    async def rollback(
        self,
        db: Any,
        reason: str,
    ) -> RollbackResult:
        """Rollback persona to the baseline prompt hash.

        Restores the prompt by recording the baseline hash as the restored
        state.  Persists a :class:`DriftLog` entry for the rollback event.

        Does **not** modify persona content when safe_mode is active.

        Args:
            db: Database session (duck-typed AsyncSession).
            reason: Human-readable reason for the rollback.

        Returns:
            A :class:`RollbackResult` indicating success or deferral.

        Raises:
            RollbackError: If the rollback cannot be completed (DB error,
                safe_mode active, or no detector available).
        """
        if self._safe_mode_controller is not None and self._safe_mode_controller.is_active:
            logger.warning(
                "drift_rollback_deferred_safe_mode",
                reason=reason,
            )
            return RollbackResult(
                success=False,
                previous_hash="",
                restored_hash="",
                timestamp=datetime.now(timezone.utc),
            )

        baseline_hash = self._detector.baseline.prompt_hash
        last_result = self._detector.last_result
        previous_hash = last_result.current_hash if last_result is not None else ""

        rollback_ts = datetime.now(timezone.utc)

        # Persist rollback drift log
        try:
            rollback_drift_result = DriftResult(
                drift_detected=True,
                drift_score=last_result.drift_score if last_result is not None else 0.0,
                threshold=last_result.threshold if last_result is not None else DRIFT_THRESHOLD,
                action="rollback",
                baseline_hash=baseline_hash,
                current_hash=previous_hash,
                checked_at=rollback_ts,
            )
            await self.create_drift_log(
                db,
                drift_result=rollback_drift_result,
                action_taken=f"rollback:{reason}",
            )
        except RollbackError:
            raise
        except DriftCorrectionError as exc:
            raise RollbackError(
                f"Failed to persist rollback drift log: {exc}"
            ) from exc
        except Exception as exc:
            raise RollbackError(
                f"Failed to persist rollback drift log: {exc}"
            ) from exc

        logger.info(
            "drift_rollback_complete",
            baseline_hash=baseline_hash,
            previous_hash=previous_hash,
            reason=reason,
        )

        return RollbackResult(
            success=True,
            previous_hash=previous_hash,
            restored_hash=baseline_hash,
            timestamp=rollback_ts,
        )

    async def create_drift_log(
        self,
        db: Any,
        drift_result: DriftResult,
        action_taken: str,
    ) -> DriftLog:
        """Persist a drift event to the database.

        Creates a :class:`DriftLog` entry capturing the before/after state,
        delta, trigger context, and rollback availability.

        Args:
            db: Database session (duck-typed AsyncSession).
            drift_result: The :class:`DriftResult` from detection.
            action_taken: Action taken (e.g. ``"none"``, ``"alert"``,
                ``"rollback"``, ``"rollback:<reason>"``).

        Returns:
            The persisted :class:`DriftLog` instance.

        Raises:
            DriftCorrectionError: If the database write fails.
        """
        try:
            log_entry = DriftLog(
                drift_type=action_taken,
                before_state={
                    "prompt_hash": drift_result.baseline_hash,
                    "version": "baseline",
                },
                after_state={
                    "prompt_hash": drift_result.current_hash,
                    "version": "current",
                },
                delta={
                    "drift_score": drift_result.drift_score,
                    "drift_detected": drift_result.drift_detected,
                    "action": drift_result.action,
                    "threshold": drift_result.threshold,
                },
                trigger_context=f"drift_corrector:{action_taken}",
                safety_score=int(drift_result.drift_score * 100),
                rollback_available=action_taken.startswith("rollback"),
                occurred_at=drift_result.checked_at,
            )
            db.add(log_entry)
            await db.commit()
        except Exception as exc:
            try:
                await db.rollback()
            except Exception:
                logger.error("drift_log_rollback_failed")
            raise DriftCorrectionError(
                f"Failed to persist drift log: {exc}"
            ) from exc

        logger.debug(
            "drift_log_created",
            drift_type=action_taken,
            drift_score=drift_result.drift_score,
        )

        return log_entry
