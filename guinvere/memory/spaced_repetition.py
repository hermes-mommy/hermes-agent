"""P18-002: FSRS-6 Spaced Repetition Scheduler.

Wraps the ``fsrs`` library (pip install fsrs) to provide:

- Schedule reviews with 4 grades: Again(1), Hard(2), Good(3), Easy(4).
- Predict retrievability R(t) = (1 + t / (9 * S)) ** (-D).
- Update FSRS state (stability, difficulty, elapsed_days, scheduled_days,
  reps, lapses, state, last_review).
- Get next review time.

This module is **lazy-imported** by ``guinvere.memory.consolidation`` so that the
memory pipeline can still import when the optional ``fsrs`` dependency is not
installed. When ``fsrs`` is missing, every public method returns a no-op
result and the caller must treat the call as best-effort.

Design decisions (locked, see ``research-reports/p18-fsrs-vs-sm2-benchmark.md``
and ``research-reports/p18-consolidation-forgetting-benchmark.md``):

- **Algorithm:** FSRS-6 (open-spaced-repetition reference implementation). Cuts
  log-loss vs Anki SM-2 by ~34% on the 350M-review benchmark; 99.6% pairwise
  win rate; ~20–30% fewer reviews at matched retention.
- **Request retention:** 0.9 (90% target). Standard for memory pipelines.
- **No raw content logging.** Only metadata (counts, grades, errors) is logged
  in the ``extra=`` payload.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Final

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public grade constants — match fsrs.ReviewLog rating values.
# ---------------------------------------------------------------------------

GRADE_AGAIN: Final[int] = 1
GRADE_HARD: Final[int] = 2
GRADE_GOOD: Final[int] = 3
GRADE_EASY: Final[int] = 4
"""FSRS rating enum — keep numeric values aligned with ``fsrs.ReviewLog``."""

DEFAULT_REQUEST_RETENTION: Final[float] = 0.9
"""Target retrievability for the scheduler (90% retention is the memory default)."""

VALID_GRADES: Final[frozenset[int]] = frozenset({GRADE_AGAIN, GRADE_HARD, GRADE_GOOD, GRADE_EASY})
"""Allowed grade set; rejected in :meth:`FSRSScheduler.schedule_review`."""

# Map from FSRS State enum (or int) to canonical int:
#   0=New, 1=Learning, 2=Review, 3=Relearning
FSRS_STATE_NEW: Final[int] = 0
FSRS_STATE_LEARNING: Final[int] = 1
FSRS_STATE_REVIEW: Final[int] = 2
FSRS_STATE_RELEARNING: Final[int] = 3

# ---------------------------------------------------------------------------
# Result dataclass — return type for every public scheduler method.
# ---------------------------------------------------------------------------


@dataclass
class FSRSReviewResult:
    """Result of a single FSRS review.

    Mirrors the FSRS-6 ``Card`` schema plus a computed ``next_review`` datetime.

    Attributes
    ----------
    stability:
        FSRS stability parameter (days).  ``0.0`` for a brand-new card.
    difficulty:
        FSRS difficulty parameter (1–10).  ``0.0`` for a brand-new card.
    elapsed_days:
        Number of days between the previous review and ``last_review``.
    scheduled_days:
        Number of days until the next review is due.
    reps:
        Total successful (Good/Easy) review count.
    lapses:
        Total lapse count (consecutive Again failures).
    state:
        Canonical state int: 0=New, 1=Learning, 2=Review, 3=Relearning.
    last_review:
        When this review was logged.  ``None`` only for brand-new cards.
    next_review:
        Computed ``last_review + scheduled_days`` (UTC).
    """

    stability: float
    difficulty: float
    elapsed_days: int
    scheduled_days: int
    reps: int
    lapses: int
    state: int
    last_review: datetime | None
    next_review: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSONB-safe dict matching ``episodes.fsrs_state``.

        ``last_review`` is rendered as ISO-8601 string so the dict is
        immediately storable in a ``JSONB`` column without further conversion.
        """
        return {
            "stability": float(self.stability),
            "difficulty": float(self.difficulty),
            "elapsed_days": int(self.elapsed_days),
            "scheduled_days": int(self.scheduled_days),
            "reps": int(self.reps),
            "lapses": int(self.lapses),
            "state": int(self.state),
            "last_review": (
                self.last_review.isoformat()
                if isinstance(self.last_review, datetime)
                else None
            ),
        }

    @classmethod
    def no_op(cls, now: datetime | None = None) -> FSRSReviewResult:
        """Build a safe no-op result used when the ``fsrs`` library is unavailable.

        The next review is placed 24h in the future so callers that rely on
        ``next_review_at`` never see ``None``.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return cls(
            stability=0.0,
            difficulty=0.0,
            elapsed_days=0,
            scheduled_days=1,
            reps=0,
            lapses=0,
            state=FSRS_STATE_NEW,
            last_review=now,
            next_review=now + timedelta(days=1),
        )


# ---------------------------------------------------------------------------
# Main scheduler wrapper
# ---------------------------------------------------------------------------


class FSRSScheduler:
    """Thin defensive wrapper around ``fsrs.Scheduler``.

    The wrapper makes three guarantees beyond the raw library:

    1. **Lazy init.** The optional ``fsrs`` import happens only when
       :class:`FSRSScheduler` is constructed.  When the library is missing,
       every method returns the no-op :class:`FSRSReviewResult` so that
       downstream code (the daily consolidation, the decay sweep) never
       fails because FSRS is unavailable.
    2. **Dict-friendly state.** Internally the FSRS ``Card`` is converted to
       and from a JSONB-safe ``dict`` so callers can persist it directly
       into ``episodes.fsrs_state`` without bespoke serialization.
    3. **Episode adapter.** :meth:`update_episode_state` writes back to the
       domain ``Episodes`` row (FSRS columns plus the side-effect fields
       ``last_reviewed_at``, ``next_review_at``, ``retrievability``).
    """

    def __init__(
        self,
        w: list[float] | None = None,
        request_retention: float = DEFAULT_REQUEST_RETENTION,
    ) -> None:
        self._w: list[float] | None = list(w) if w is not None else None
        self._request_retention: float = float(request_retention)
        self._scheduler: Any = None
        self._fsrs_module: Any = None
        self._available: bool = False
        self._init_backend()

    # ------------------------------------------------------------------ init

    def _init_backend(self) -> None:
        """Lazy-import ``fsrs`` and instantiate the scheduler.

        Mirrors the ``kg_ingestion_enabled`` pattern in
        ``guinvere.memory.consolidation``: any import error or constructor error
        logs a warning and degrades gracefully to a no-op scheduler.
        """
        try:
            import fsrs as _fsrs_module  # noqa: PLC0415
        except ImportError as _fsrs_imp:
            logger.warning(
                "fsrs_unavailable_no_op_scheduler",
                extra={"detail": "pip install 'fsrs>=5.0.0' to enable spaced repetition"},
            )
            self._available = False
            return
        except Exception as _fsrs_exc:  # pragma: no cover - defensive
            logger.warning(
                "fsrs_import_failed",
                extra={"error": str(_fsrs_exc)},
            )
            self._available = False
            return

        try:
            if self._w is not None:
                scheduler = _fsrs_module.Scheduler(
                    w=self._w,
                    request_retention=self._request_retention,
                )
            else:
                scheduler = _fsrs_module.Scheduler(
                    request_retention=self._request_retention,
                )
        except Exception as _sched_exc:
            logger.warning(
                "fsrs_scheduler_init_failed",
                extra={"error": str(_sched_exc)},
            )
            self._available = False
            return

        self._fsrs_module = _fsrs_module
        self._scheduler = scheduler
        self._available = True
        logger.debug(
            "fsrs_scheduler_initialized",
            extra={
                "request_retention": self._request_retention,
                "weight_count": len(self._w) if self._w is not None else None,
            },
        )

    @property
    def available(self) -> bool:
        """Return ``True`` when the ``fsrs`` library was successfully loaded."""
        return self._available

    # --------------------------------------------------------- dict <-> Card

    def _to_card(self, card_state: dict[str, Any] | None) -> Any:
        """Materialize a JSONB-shaped ``dict`` into an ``fsrs.Card``."""
        card_cls = getattr(self._fsrs_module, "Card", None)
        if card_cls is None:
            raise AttributeError("fsrs.Card missing")
        card = card_cls()
        if not card_state:
            return card

        if card_state.get("stability") is not None:
            try:
                card.stability = float(card_state["stability"])
            except (TypeError, ValueError):
                card.stability = 0.0
        if card_state.get("difficulty") is not None:
            try:
                card.difficulty = float(card_state["difficulty"])
            except (TypeError, ValueError):
                card.difficulty = 0.0
        if card_state.get("elapsed_days") is not None:
            try:
                card.elapsed_days = int(card_state["elapsed_days"])
            except (TypeError, ValueError):
                card.elapsed_days = 0
        if card_state.get("scheduled_days") is not None:
            try:
                card.scheduled_days = int(card_state["scheduled_days"])
            except (TypeError, ValueError):
                card.scheduled_days = 0
        if card_state.get("reps") is not None:
            try:
                card.reps = int(card_state["reps"])
            except (TypeError, ValueError):
                card.reps = 0
        if card_state.get("lapses") is not None:
            try:
                card.lapses = int(card_state["lapses"])
            except (TypeError, ValueError):
                card.lapses = 0
        if card_state.get("state") is not None:
            state_raw = card_state["state"]
            if isinstance(state_raw, int):
                card.state = state_raw
            else:
                try:
                    card.state = int(state_raw)
                except (TypeError, ValueError):
                    # Best-effort mapping from library enum.
                    state_enum_cls = getattr(self._fsrs_module, "State", None)
                    if state_enum_cls is not None:
                        try:
                            card.state = state_enum_cls(state_raw)
                        except (ValueError, TypeError):
                            card.state = FSRS_STATE_NEW
                    else:
                        card.state = FSRS_STATE_NEW
        if card_state.get("last_review") is not None:
            lr_raw = card_state["last_review"]
            lr_dt: datetime | None = None
            if isinstance(lr_raw, datetime):
                lr_dt = lr_raw
            elif isinstance(lr_raw, str):
                try:
                    lr_dt = datetime.fromisoformat(lr_raw)
                except ValueError:
                    lr_dt = None
            if lr_dt is not None:
                if lr_dt.tzinfo is None:
                    lr_dt = lr_dt.replace(tzinfo=timezone.utc)
                card.last_review = lr_dt
        return card

    @staticmethod
    def _coerce_state(state_value: Any) -> int:
        """Convert library ``State`` (or int) into canonical int 0–3."""
        if state_value is None:
            return FSRS_STATE_NEW
        if isinstance(state_value, int):
            return state_value
        # Enum case (e.g., fsrs.State)
        value_attr = getattr(state_value, "value", None)
        if isinstance(value_attr, int):
            return value_attr
        name_attr = getattr(state_value, "name", "")
        if isinstance(name_attr, str):
            mapping = {
                "New": FSRS_STATE_NEW,
                "Learning": FSRS_STATE_LEARNING,
                "Review": FSRS_STATE_REVIEW,
                "Relearning": FSRS_STATE_RELEARNING,
            }
            return mapping.get(name_attr, FSRS_STATE_NEW)
        return FSRS_STATE_NEW

    @staticmethod
    def _retrievability_formula(stability: float, difficulty: float, elapsed_days: float) -> float:
        """Pure-Python FSRS-6 retrievability formula.

        R(t) = (1 + t / (9 * S)) ** (-D)

        Used as a fallback when the library is unavailable or
        ``get_card_retrievability`` is not implemented.
        """
        s = stability if stability and stability > 0 else 1.0
        d = difficulty if difficulty and difficulty > 0 else 5.0
        t = max(0.0, float(elapsed_days))
        try:
            value = (1.0 + t / (9.0 * s)) ** (-d)
        except (OverflowError, ZeroDivisionError, ValueError):
            return 0.0
        if value != value:  # NaN guard
            return 0.0
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return value

    # ------------------------------------------------------------ public API

    def schedule_review(
        self,
        card_state: dict[str, Any] | None,
        grade: int,
        now: datetime | None = None,
    ) -> FSRSReviewResult:
        """Schedule a review at *now* with the supplied *grade*.

        Parameters
        ----------
        card_state:
            JSONB-shaped FSRS state (``None`` for a brand-new card).
        grade:
            One of :data:`GRADE_AGAIN`, :data:`GRADE_HARD`,
            :data:`GRADE_GOOD`, :data:`GRADE_EASY`.
        now:
            Wall-clock ``datetime``.  Defaults to ``datetime.now(UTC)``.

        Returns
        -------
        FSRSReviewResult
            New state plus the scheduled next-review datetime.
            If the ``fsrs`` library is unavailable or the call fails, a
            :meth:`FSRSReviewResult.no_op` result is returned.
        """
        if grade not in VALID_GRADES:
            raise ValueError(
                f"Invalid FSRS grade: {grade!r}. "
                f"Must be one of 1 (Again), 2 (Hard), 3 (Good), 4 (Easy)."
            )

        if now is None:
            now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        if not self._available or self._scheduler is None:
            logger.debug("fsrs_scheduler_unavailable_returning_no_op", extra={"grade": grade})
            return FSRSReviewResult.no_op(now=now)

        try:
            card = self._to_card(card_state)
            review_log_cls = getattr(self._fsrs_module, "ReviewLog", None)
            if review_log_cls is None:
                raise AttributeError("fsrs.ReviewLog missing")
            review_log = review_log_cls(grade, now)
            new_card = self._scheduler.review_card(card, review_log)
        except Exception as _sched_exc:
            logger.warning(
                "fsrs_schedule_review_failed",
                extra={
                    "error": str(_sched_exc),
                    "error_type": type(_sched_exc).__name__,
                    "grade": grade,
                },
            )
            return FSRSReviewResult.no_op(now=now)

        # Compute next_review deterministically from scheduled_days.
        scheduled_days_raw = getattr(new_card, "scheduled_days", 0) or 0
        try:
            scheduled_days = int(scheduled_days_raw)
        except (TypeError, ValueError):
            scheduled_days = 0
        if scheduled_days < 0:
            scheduled_days = 0
        next_review = now + timedelta(days=scheduled_days)

        last_review_attr = getattr(new_card, "last_review", None)
        last_review_dt: datetime | None = now
        if isinstance(last_review_attr, datetime):
            last_review_dt = last_review_attr
            if last_review_dt.tzinfo is None:
                last_review_dt = last_review_dt.replace(tzinfo=timezone.utc)

        elapsed_days_raw = getattr(new_card, "elapsed_days", 0) or 0
        try:
            elapsed_days = int(elapsed_days_raw)
        except (TypeError, ValueError):
            elapsed_days = 0

        return FSRSReviewResult(
            stability=float(getattr(new_card, "stability", 0.0) or 0.0),
            difficulty=float(getattr(new_card, "difficulty", 0.0) or 0.0),
            elapsed_days=elapsed_days,
            scheduled_days=scheduled_days,
            reps=int(getattr(new_card, "reps", 0) or 0),
            lapses=int(getattr(new_card, "lapses", 0) or 0),
            state=self._coerce_state(getattr(new_card, "state", FSRS_STATE_NEW)),
            last_review=last_review_dt,
            next_review=next_review,
        )

    def predict_retrievability(
        self,
        card_state: dict[str, Any],
        elapsed_days: float,
    ) -> float:
        """Predict retrievability ``R(t) = (1 + t / (9 * S)) ** (-D)``.

        Tries the library's :meth:`get_card_retrievability` first; falls back
        to the closed-form formula when unavailable.

        Returns a float in ``[0.0, 1.0]``.
        """
        try:
            t = max(0.0, float(elapsed_days))
        except (TypeError, ValueError):
            t = 0.0

        stability_raw = card_state.get("stability") if card_state else None
        difficulty_raw = card_state.get("difficulty") if card_state else None
        try:
            stability = float(stability_raw) if stability_raw is not None else 0.0
        except (TypeError, ValueError):
            stability = 0.0
        try:
            difficulty = float(difficulty_raw) if difficulty_raw is not None else 0.0
        except (TypeError, ValueError):
            difficulty = 0.0

        if self._available and self._scheduler is not None:
            try:
                card = self._to_card(card_state)
                # Prefer scheduler method when present (some FSRS versions
                # expose ``get_card_retrievability``; older versions expose
                # ``predict_retention``).  Both should accept (card, t).
                # Use ``getattr`` to keep the call type-safe without
                # resorting to inline type-suppression comments.
                _pred_retrievability = getattr(
                    self._scheduler, "get_card_retrievability", None
                )
                if _pred_retrievability is None:
                    _pred_retrievability = getattr(
                        self._scheduler, "predict_retention", None
                    )
                if _pred_retrievability is None:
                    raise AttributeError("no scheduler retrievability method")
                r_value = _pred_retrievability(card, t)
                r_float = float(r_value)
                if r_float != r_float:  # NaN
                    raise ValueError("library returned NaN")
                return r_float
            except Exception as _predict_exc:
                logger.debug(
                    "fsrs_predict_retrievability_fallback",
                    extra={"error": str(_predict_exc), "error_type": type(_predict_exc).__name__},
                )
        return self._retrievability_formula(stability, difficulty, t)

    def get_next_review(
        self,
        card_state: dict[str, Any] | None,
        grade: int,
        now: datetime | None = None,
    ) -> datetime:
        """Return the scheduled next-review ``datetime`` for a given grade."""
        result = self.schedule_review(card_state, grade, now=now)
        return result.next_review

    # --------------------------------------------------------- episode adapter

    def update_episode_state(
        self,
        episode: object,
        grade: int,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Apply a review result to a domain ``Episodes`` row.

        Reads ``episode.fsrs_state`` (defensive ``getattr``), runs the review,
        then writes back the canonical FSRS fields:

        - ``fsrs_state`` (JSONB dict)
        - ``last_reviewed_at`` (datetime)
        - ``next_review_at`` (datetime)
        - ``retrievability`` (float, predicted at t=0)
        - ``stability`` (float)
        - ``difficulty`` (float)

        Returns the new JSONB-shaped state dict.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        fsrs_state_raw = getattr(episode, "fsrs_state", None)
        card_state: dict[str, Any] | None = None
        if isinstance(fsrs_state_raw, dict):
            card_state = fsrs_state_raw

        result = self.schedule_review(card_state, grade, now=now)
        state_dict = result.to_dict()

        # Predict retrievability at the moment of review (elapsed_days=0).
        retrievability = self.predict_retrievability(state_dict, 0.0)

        # Defensive writes — never raise from the adapter.
        try:
            episode.fsrs_state = state_dict
        except Exception:
            logger.debug("update_episode_state: defensive write failed for fsrs_state", exc_info=True)
        try:
            episode.last_reviewed_at = result.last_review
        except Exception:
            logger.debug("update_episode_state: defensive write failed for last_reviewed_at", exc_info=True)
        try:
            episode.next_review_at = result.next_review
        except Exception:
            logger.debug("update_episode_state: defensive write failed for next_review_at", exc_info=True)
        try:
            episode.retrievability = retrievability
        except Exception:
            logger.debug("update_episode_state: defensive write failed for retrievability", exc_info=True)
        try:
            episode.stability = result.stability
        except Exception:
            logger.debug("update_episode_state: defensive write failed for stability", exc_info=True)
        try:
            episode.difficulty = result.difficulty
        except Exception:
            logger.debug("update_episode_state: defensive write failed for difficulty", exc_info=True)

        return state_dict


__all__ = [
    "FSRSScheduler",
    "FSRSReviewResult",
    "GRADE_AGAIN",
    "GRADE_HARD",
    "GRADE_GOOD",
    "GRADE_EASY",
    "DEFAULT_REQUEST_RETENTION",
    "VALID_GRADES",
    "FSRS_STATE_NEW",
    "FSRS_STATE_LEARNING",
    "FSRS_STATE_REVIEW",
    "FSRS_STATE_RELEARNING",
]
