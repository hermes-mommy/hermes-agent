"""Async retry infrastructure with circuit breaker integration and error taxonomy.

This module provides a small, self-contained retry layer for the
autonomous loop system.  It classifies failures along three axes
(transient / deterministic / unknown), applies exponential backoff
with optional jitter, and integrates with the existing circuit breaker
and iteration budget subsystems without adding external dependencies
such as ``tenacity`` or ``pybreaker``.
"""

from __future__ import annotations

import asyncio
import enum
import logging
import random
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypeVar

from guinevere.loops.circuit_breaker import CircuitState

logger = logging.getLogger("guinevere.loops.retry")

T = TypeVar("T")


class ErrorClass(enum.Enum):
    """Three-axis classification for retry decision-making."""

    TRANSIENT = "transient"  # Network timeout, rate limit, 503 — retry safe
    DETERMINISTIC = "deterministic"  # Invalid input, auth failure — retry pointless
    UNKNOWN = "unknown"  # Unclassified — retry with caution


class ErrorTaxonomy:
    """Classify exceptions into retry-actionable categories."""

    _TRANSIENT_STATUSES: frozenset[int] = frozenset({429, 502, 503, 504})
    _DETERMINISTIC_STATUSES: frozenset[int] = frozenset({400, 401, 403, 404})

    def classify(self, exc: Exception) -> ErrorClass:
        """Return the :class:`ErrorClass` for *exc*.

        Known transient patterns:
          - :class:`ConnectionError`, :class:`TimeoutError`
          - Any exception carrying ``status`` in ``{429, 502, 503, 504}``
            (e.g. ``aiohttp.ClientResponseError``).

        Known deterministic patterns:
          - :class:`ValueError`, :class:`PermissionError`
          - Any exception carrying ``status`` in ``{400, 401, 403, 404}``.

        Everything else is classified as :attr:`ErrorClass.UNKNOWN`.
        """
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorClass.TRANSIENT

        if isinstance(exc, (ValueError, PermissionError)):
            return ErrorClass.DETERMINISTIC

        status = getattr(exc, "status", None)
        if isinstance(status, int):
            if status in self._TRANSIENT_STATUSES:
                return ErrorClass.TRANSIENT
            if status in self._DETERMINISTIC_STATUSES:
                return ErrorClass.DETERMINISTIC

        return ErrorClass.UNKNOWN


@dataclass(frozen=True)
class RetryPolicy:
    """Immutable policy controlling retry behaviour."""

    max_attempts: int = 5
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # cap
    jitter: bool = True  # add random jitter
    exponential_base: float = 2.0
    retryable_classes: frozenset[ErrorClass] = frozenset(
        {ErrorClass.TRANSIENT, ErrorClass.UNKNOWN}
    )

    def should_retry(self, error_class: ErrorClass, attempt: int) -> bool:
        """Return ``True`` if *attempt* has not exhausted ``max_attempts`` and
        *error_class* is in the set of retryable classes."""
        if attempt >= self.max_attempts:
            return False
        return error_class in self.retryable_classes

    def compute_delay(self, attempt: int) -> float:
        """Return the backoff delay for *attempt* (1-indexed).

        Delay is ``min(base_delay * exponential_base ** (attempt - 1), max_delay)``.
        When ``jitter`` is enabled, up to 50% of additional random jitter is
        added without exceeding ``max_delay``.
        """
        if attempt < 1:
            return 0.0
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay = delay * (0.5 + random.random())
            delay = min(delay, self.max_delay)
        return delay


@dataclass(frozen=True)
class RetryResult:
    """Immutable outcome of a retry execution."""

    success: bool
    result: Any  # The return value of fn, or None on failure
    attempts: int
    errors: list[str]  # Error messages from each failed attempt
    total_delay: float  # Total seconds spent in backoff
    final_error_class: ErrorClass | None  # Classification of last error


class RetryExecutor:
    """Execute async callables with retry, circuit breaker, and budget awareness."""

    def __init__(
        self,
        policy: RetryPolicy,
        circuit_breaker: Any = None,
        budget: Any = None,
    ) -> None:
        self._policy = policy
        self._circuit_breaker = circuit_breaker
        self._budget = budget
        self._taxonomy = ErrorTaxonomy()

    async def execute(
        self,
        fn: Callable[..., Awaitable[T]],
        *args: Any,
        operation_name: str = "unknown",
        **kwargs: Any,
    ) -> RetryResult:
        """Run *fn* until it succeeds, the policy gives up, or a hard gate stops us.

        The executor honours, in order:
          1. Budget — ``consume_turn`` is debited before each attempt; if the
             budget is exhausted the call returns immediately.
          2. Circuit breaker — state is checked before each attempt; failures
             and successes are recorded so the breaker can trip/close.
          3. Error taxonomy — each failure is classified and ``RetryPolicy``
             decides whether another attempt is worthwhile.

        Args:
            fn: Async callable to execute.
            *args: Positional arguments for *fn*.
            operation_name: Human-readable name for logs and error messages.
            **kwargs: Keyword arguments for *fn*.

        Returns:
            A :class:`RetryResult` describing the final outcome.
        """
        errors: list[str] = []
        total_delay = 0.0
        last_error_class: ErrorClass | None = None

        for attempt in range(1, self._policy.max_attempts + 1):
            budget_ok, budget_msg = await self._check_budget(attempt, operation_name)
            if not budget_ok:
                errors.append(budget_msg)
                logger.warning("%s", budget_msg)
                return RetryResult(
                    success=False,
                    result=None,
                    attempts=attempt - 1,
                    errors=errors,
                    total_delay=total_delay,
                    final_error_class=last_error_class,
                )

            circuit_ok, circuit_msg = await self._check_circuit_breaker(
                attempt, operation_name
            )
            if not circuit_ok:
                errors.append(circuit_msg)
                logger.warning("%s", circuit_msg)
                await self._record_circuit_failure()
                return RetryResult(
                    success=False,
                    result=None,
                    attempts=attempt - 1,
                    errors=errors,
                    total_delay=total_delay,
                    final_error_class=last_error_class,
                )

            try:
                result = await fn(*args, **kwargs)
            except Exception as exc:
                error_class = self._taxonomy.classify(exc)
                last_error_class = error_class
                error_message = str(exc)
                errors.append(error_message)
                logger.warning(
                    "Retry attempt %s for '%s' failed: %s (%s)",
                    attempt,
                    operation_name,
                    error_message,
                    error_class.value,
                )
                await self._record_circuit_failure()

                if not self._policy.should_retry(error_class, attempt):
                    break

                delay = self._policy.compute_delay(attempt)
                if delay > 0.0:
                    total_delay += delay
                    await asyncio.sleep(delay)
                continue

            await self._record_circuit_success()
            return RetryResult(
                success=True,
                result=result,
                attempts=attempt,
                errors=errors,
                total_delay=total_delay,
                final_error_class=None,
            )

        return RetryResult(
            success=False,
            result=None,
            attempts=len(errors),
            errors=errors,
            total_delay=total_delay,
            final_error_class=last_error_class,
        )

    async def _check_budget(
        self, attempt: int, operation_name: str
    ) -> tuple[bool, str]:
        """Return ``(True, "")`` if a turn can be consumed, otherwise ``(False, msg)``."""
        if self._budget is None:
            return True, ""

        if self._budget.exhausted():
            return (
                False,
                f"Budget exhausted before attempt {attempt} of "
                f"operation '{operation_name}'",
            )

        try:
            await self._budget.consume_turn(0, 0.0)
        except Exception as exc:  # noqa: BLE001 — catch any budget rejection
            return (
                False,
                f"Budget consumption failed for attempt {attempt}: {exc}",
            )

        return True, ""

    async def _check_circuit_breaker(
        self, attempt: int, operation_name: str
    ) -> tuple[bool, str]:
        """Return ``(True, "")`` if the circuit breaker allows the attempt."""
        if self._circuit_breaker is None:
            return True, ""

        try:
            allowed = await self._circuit_breaker_check()
        except Exception as exc:  # noqa: BLE001
            return (
                False,
                f"Circuit breaker check failed for attempt {attempt}: {exc}",
            )

        if not allowed:
            return (
                False,
                f"Circuit breaker open for operation '{operation_name}', "
                f"attempt {attempt}",
            )

        return True, ""

    async def _circuit_breaker_check(self) -> bool:
        """Query the wrapped circuit breaker, supporting multiple APIs."""
        breaker = self._circuit_breaker

        check_fn = getattr(breaker, "check", None)
        if callable(check_fn):
            result = check_fn()
            if asyncio.iscoroutine(result):
                result = await result
            return bool(result)

        state = getattr(breaker, "state", None)
        return state != CircuitState.OPEN

    async def _record_circuit_success(self) -> None:
        """Notify the circuit breaker of a successful attempt."""
        if self._circuit_breaker is None:
            return

        record_fn = getattr(self._circuit_breaker, "record_success", None)
        if callable(record_fn):
            result = record_fn()
            if asyncio.iscoroutine(result):
                await result
            return

        private_fn = getattr(self._circuit_breaker, "_record_success", None)
        if callable(private_fn):
            result = private_fn()
            if asyncio.iscoroutine(result):
                await result

    async def _record_circuit_failure(self) -> None:
        """Notify the circuit breaker of a failed attempt."""
        if self._circuit_breaker is None:
            return

        record_fn = getattr(self._circuit_breaker, "record_failure", None)
        if callable(record_fn):
            result = record_fn()
            if asyncio.iscoroutine(result):
                await result
            return

        private_fn = getattr(self._circuit_breaker, "_record_failure", None)
        if callable(private_fn):
            result = private_fn()
            if asyncio.iscoroutine(result):
                await result


async def retry_with_backoff(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    policy: RetryPolicy | None = None,
    **kwargs: Any,
) -> RetryResult:
    """Quick retry without circuit breaker or budget.

    Args:
        fn: Async callable to execute.
        *args: Positional arguments for *fn*.
        policy: Optional :class:`RetryPolicy`; defaults to ``RetryPolicy()``.
        **kwargs: Keyword arguments for *fn*.

    Returns:
        A :class:`RetryResult` describing the outcome.
    """
    resolved_policy = policy if policy is not None else RetryPolicy()
    executor = RetryExecutor(policy=resolved_policy)
    return await executor.execute(fn, *args, **kwargs)
