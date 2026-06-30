"""P13 X Auto Poster — 3-state circuit breaker with PostgreSQL persistence."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum

import structlog

from .db import DatabaseManager
from .exceptions import XPosterError
from .metrics import set_circuit_breaker_state

_logger = structlog.get_logger(__name__)


def _state_to_metric(state: CircuitState) -> int:
    if state == CircuitState.CLOSED:
        return 0
    if state == CircuitState.OPEN:
        return 1
    return 2


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """3-state circuit breaker (CLOSED/OPEN/HALF_OPEN) with PostgreSQL persistence.

    Tracks failures per component and opens the circuit when failure threshold
    is reached. Transitions to HALF_OPEN after recovery timeout, then to CLOSED
    on success or back to OPEN on failure.
    """

    _db: DatabaseManager
    _component: str
    _failure_threshold: int
    _recovery_timeout_seconds: int
    _half_open_max_calls: int
    _state: CircuitState
    _failure_count: int
    _last_failure_at: datetime | None
    _last_success_at: datetime | None
    _opened_at: datetime | None
    _half_open_at: datetime | None
    _half_open_calls: int
    _lock: asyncio.Lock

    def __init__(
        self,
        db: DatabaseManager,
        component: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 300,
        half_open_max_calls: int = 1,
    ) -> None:
        self._db = db
        self._component = component
        self._failure_threshold = failure_threshold
        self._recovery_timeout_seconds = recovery_timeout_seconds
        self._half_open_max_calls = half_open_max_calls
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_at = None
        self._last_success_at = None
        self._opened_at = None
        self._half_open_at = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Load state from DB, default to CLOSED if not exists."""
        row = await self._db.fetchrow(
            """
            SELECT state, failure_count, last_failure_at, last_success_at,
                   opened_at
            FROM p13_circuit_breaker
            WHERE component = $1
            """,
            self._component,
        )
        if row:
            self._state = CircuitState(row["state"])
            self._failure_count = int(row["failure_count"])
            self._last_failure_at = row.get("last_failure_at")
            self._last_success_at = row.get("last_success_at")
            self._opened_at = row.get("opened_at")
            self._half_open_at = None
            _logger.info(
                "circuit_breaker.loaded",
                component=self._component,
                state=self._state.value,
                failure_count=self._failure_count,
            )
        else:
            await self._persist_state(CircuitState.CLOSED, 0)
            _logger.info(
                "circuit_breaker.initialized_default",
                component=self._component,
                state=CircuitState.CLOSED.value,
            )
        set_circuit_breaker_state(_state_to_metric(self._state))

    async def allow_request(self) -> bool:
        """Check if a request is allowed through the circuit breaker.

        Returns:
            True if request is allowed (CLOSED or HALF_OPEN), False if circuit is OPEN.
        """
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self._half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

            # OPEN state — check if recovery timeout has elapsed
            if self._opened_at:
                now = datetime.now(timezone.utc)
                elapsed = (now - self._opened_at).total_seconds()
                if elapsed >= self._recovery_timeout_seconds:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._half_open_at = now
                    await self._persist_state(
                        CircuitState.HALF_OPEN, self._failure_count
                    )
                    set_circuit_breaker_state(_state_to_metric(CircuitState.HALF_OPEN))
                    _logger.info(
                        "circuit_breaker.open_to_half_open",
                        component=self._component,
                        elapsed_seconds=elapsed,
                    )
                    return True

            return False

    async def record_success(self) -> None:
        """Record a successful operation.

        Resets failure count and transitions to CLOSED if in HALF_OPEN.
        """
        async with self._lock:
            now = datetime.now(timezone.utc)
            self._last_success_at = now
            self._failure_count = 0

            if self._state != CircuitState.CLOSED:
                _logger.info(
                    "circuit_breaker.success_closing",
                    component=self._component,
                    previous_state=self._state.value,
                )
                self._state = CircuitState.CLOSED
                self._half_open_calls = 0

            await self._persist_state(CircuitState.CLOSED, 0)
            set_circuit_breaker_state(_state_to_metric(CircuitState.CLOSED))

    async def record_failure(self) -> None:
        """Record a failed operation.

        Increments failure count. If threshold reached, transitions to OPEN.
        """
        async with self._lock:
            now = datetime.now(timezone.utc)
            self._last_failure_at = now
            self._failure_count += 1

            if self._state == CircuitState.HALF_OPEN:
                _logger.warning(
                    "circuit_breaker.half_open_failure_opening",
                    component=self._component,
                    failure_count=self._failure_count,
                )
                self._state = CircuitState.OPEN
                self._opened_at = now
                await self._persist_state(CircuitState.OPEN, self._failure_count)
                set_circuit_breaker_state(_state_to_metric(CircuitState.OPEN))
                return

            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = now
                await self._persist_state(CircuitState.OPEN, self._failure_count)
                set_circuit_breaker_state(_state_to_metric(CircuitState.OPEN))
                _logger.warning(
                    "circuit_breaker.threshold_reached_opening",
                    component=self._component,
                    failure_count=self._failure_count,
                    threshold=self._failure_threshold,
                )
                return

            # Still CLOSED, just persist updated failure count
            await self._persist_state(CircuitState.CLOSED, self._failure_count)
            _logger.debug(
                "circuit_breaker.failure_recorded",
                component=self._component,
                failure_count=self._failure_count,
                threshold=self._failure_threshold,
            )

    async def get_state(self) -> CircuitState:
        """Return current state, checking for OPEN→HALF_OPEN transition."""
        async with self._lock:
            if self._state == CircuitState.OPEN and self._opened_at:
                now = datetime.now(timezone.utc)
                elapsed = (now - self._opened_at).total_seconds()
                if elapsed >= self._recovery_timeout_seconds:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._half_open_at = now
                    await self._persist_state(
                        CircuitState.HALF_OPEN, self._failure_count
                    )
                    set_circuit_breaker_state(_state_to_metric(CircuitState.HALF_OPEN))
            return self._state

    async def reset(self) -> None:
        """Force reset to CLOSED state."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_calls = 0
            self._opened_at = None
            self._half_open_at = None
            await self._persist_state(CircuitState.CLOSED, 0)
            set_circuit_breaker_state(_state_to_metric(CircuitState.CLOSED))
            _logger.info(
                "circuit_breaker.reset",
                component=self._component,
            )

    async def _persist_state(self, state: CircuitState, failure_count: int) -> None:
        """UPSERT circuit breaker state to PostgreSQL."""
        now = datetime.now(timezone.utc)
        try:
            await self._db.execute(
                """
                INSERT INTO p13_circuit_breaker
                    (
                        component,
                        state,
                        failure_count,
                        last_failure_at,
                        last_success_at,
                        opened_at,
                        reset_timeout_seconds,
                        updated_at
                    )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (component) DO UPDATE SET
                    state = EXCLUDED.state,
                    failure_count = EXCLUDED.failure_count,
                    last_failure_at = COALESCE(
                        EXCLUDED.last_failure_at,
                        p13_circuit_breaker.last_failure_at
                    ),
                    last_success_at = COALESCE(
                        EXCLUDED.last_success_at,
                        p13_circuit_breaker.last_success_at
                    ),
                    opened_at = COALESCE(
                        EXCLUDED.opened_at,
                        p13_circuit_breaker.opened_at
                    ),
                    reset_timeout_seconds = EXCLUDED.reset_timeout_seconds,
                    updated_at = EXCLUDED.updated_at
                """,
                self._component,
                state.value,
                failure_count,
                self._last_failure_at,
                self._last_success_at,
                self._opened_at,
                self._recovery_timeout_seconds,
                now,
            )
        except Exception as e:
            _logger.error(
                "circuit_breaker.persist_error",
                component=self._component,
                state=state.value,
                error=str(e),
            )
            raise XPosterError(
                f"Failed to persist circuit breaker state: {e}"
            ) from e
