"""Persona drift detection — compare current prompt hash vs baseline."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final

import structlog

logger = structlog.get_logger()


class DriftDetectionError(Exception):
    """Base exception for drift detection errors."""


class DriftBaselineError(DriftDetectionError):
    """Raised when baseline is invalid or missing."""


class DriftComputationError(DriftDetectionError):
    """Raised when drift score computation fails."""


@dataclass(frozen=True)
class DriftResult:
    """Result of a single drift detection check."""

    drift_detected: bool
    drift_score: float
    threshold: float
    action: str
    baseline_hash: str
    current_hash: str
    checked_at: datetime


@dataclass(frozen=True)
class DriftBaseline:
    """Baseline snapshot of a known-good system prompt."""

    prompt_hash: str
    version: str
    created_at: datetime
    description: str = ""


class DriftDetector:
    """Detects persona drift by comparing prompt hashes.

    The SystemPromptMaster is the canonical persona definition.  If the
    loaded prompt drifts from the recorded baseline — whether through
    configuration bugs, unauthorised edits, or injection — persona
    behaviour changes unpredictably.  This detector catches that by
    computing a normalised Hamming distance between two SHA-256 hex
    digests and mapping the score to an action tier.
    """

    DEFAULT_THRESHOLD: Final[float] = 0.10
    SOUL_BASELINE_HASH: Final[str] = "b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740"

    def __init__(
        self,
        baseline: DriftBaseline,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        if not baseline.prompt_hash:
            raise DriftBaselineError("Baseline prompt_hash must not be empty.")
        if not (0.0 < threshold <= 1.0):
            raise DriftBaselineError(
                f"Threshold must be in (0.0, 1.0]; got {threshold!r}."
            )
        self._baseline: DriftBaseline = baseline
        self._threshold: float = threshold
        self._check_count: int = 0
        self._last_result: DriftResult | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_drift_score(self, current_prompt_hash: str) -> float:
        """Compute drift score between baseline and current hash.

        Comparison strategy:
        * Exact match → 0.0
        * Different length → 1.0 (complete drift)
        * Same length → Hamming distance ratio (differing positions / length)

        For SHA-256 hex digests (64 characters) the Hamming distance
        gives a granular score between 0.0 and 1.0.

        Raises:
            DriftComputationError: If *current_prompt_hash* is empty.
        """
        if not current_prompt_hash:
            raise DriftComputationError(
                "current_prompt_hash must not be empty."
            )

        baseline_hash = self._baseline.prompt_hash

        if current_prompt_hash == baseline_hash:
            return 0.0

        if len(current_prompt_hash) != len(baseline_hash):
            logger.warning(
                "drift_hash_length_mismatch",
                baseline_len=len(baseline_hash),
                current_len=len(current_prompt_hash),
            )
            return 1.0

        # Hamming distance ratio
        length = len(baseline_hash)
        differing = sum(
            1 for a, b in zip(baseline_hash, current_prompt_hash) if a != b
        )
        return differing / length

    def detect(
        self,
        current_prompt_hash: str,
        now: datetime | None = None,
    ) -> DriftResult:
        """Run a drift detection check.

        Returns a :class:`DriftResult` with *action* set to:

        * ``"none"`` — drift_score <= threshold
        * ``"alert"`` — threshold < drift_score <= 2 * threshold
        * ``"rollback"`` — drift_score > 2 * threshold

        Raises:
            DriftComputationError: If *current_prompt_hash* is empty.
        """
        score = self.compute_drift_score(current_prompt_hash)
        checked_at = now if now is not None else datetime.now(timezone.utc)

        if score <= self._threshold:
            action = "none"
        elif score <= 2.0 * self._threshold:
            action = "alert"
        else:
            action = "rollback"

        drift_detected = score > self._threshold

        result = DriftResult(
            drift_detected=drift_detected,
            drift_score=score,
            threshold=self._threshold,
            action=action,
            baseline_hash=self._baseline.prompt_hash,
            current_hash=current_prompt_hash,
            checked_at=checked_at,
        )

        self._check_count += 1
        self._last_result = result

        logger.info(
            "drift_check_complete",
            drift_detected=drift_detected,
            drift_score=score,
            action=action,
            check_number=self._check_count,
        )

        return result

    def update_baseline(self, new_baseline: DriftBaseline) -> None:
        """Update baseline after an intentional prompt change.

        Raises:
            DriftBaselineError: If *new_baseline.prompt_hash* is empty.
        """
        if not new_baseline.prompt_hash:
            raise DriftBaselineError(
                "New baseline prompt_hash must not be empty."
            )
        logger.info(
            "drift_baseline_updated",
            old_version=self._baseline.version,
            new_version=new_baseline.version,
        )
        self._baseline = new_baseline

    @staticmethod
    def compute_prompt_hash(prompt_text: str) -> str:
        """Compute SHA-256 hash of prompt text.

        Returns:
            Lower-case hex digest (64 characters).

        Raises:
            DriftComputationError: If *prompt_text* is empty.
        """
        if not prompt_text:
            raise DriftComputationError("prompt_text must not be empty.")
        return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def baseline(self) -> DriftBaseline:
        """Current baseline."""
        return self._baseline

    @property
    def threshold(self) -> float:
        """Configured drift threshold."""
        return self._threshold

    @property
    def check_count(self) -> int:
        """Number of ``detect()`` calls since construction."""
        return self._check_count

    @property
    def last_result(self) -> DriftResult | None:
        """Most recent :class:`DriftResult`, or ``None`` if no check has run."""
        return self._last_result
