"""HARD STOP Safety Guard — Redis-based safety mechanism for consciousness loop.

Provides the HardStopGuard class that checks a Redis key before each thought
generation cycle. When the HARD STOP signal is active, the guard instructs
the caller to halt thought generation and enter safe idle mode.

Design decisions:
  - Fail-open on Redis connectivity: if Redis is unreachable, assume no HARD
    STOP (log warning). This is safer than fail-stop because connectivity
    issues should not permanently block the consciousness loop.
  - Async Redis client (redis.asyncio) for non-blocking operations.
  - Cached state via `active` property for fast synchronous checks.
  - `wait_for_clear()` provides an async polling loop for blocking until
    the HARD STOP signal is cleared (e.g., by operator or recovery process).

Safety contract:
  - The caller (ThoughtStream, consciousness loop) MUST check `check()` at
    the START of each thought cycle.
  - If `check()` returns True, the caller MUST NOT proceed with thought
    generation and MUST enter safe idle mode.
  - The guard does NOT itself stop the loop — it only reports the signal.
    The caller is responsible for honoring the signal.

Replaces HeartbeatService._heartbeat_1s() HARD STOP detection (A6 deprecation).
"""

from __future__ import annotations

import asyncio

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = structlog.get_logger("guinevere.consciousness.safety")

# Redis key for the HARD STOP signal.
# Truthy value = HARD STOP active; absent/falsy = normal operation.
HARD_STOP_KEY: str = "life_kernel:hard_stop"

# Default polling interval for wait_for_clear() in seconds.
_DEFAULT_POLL_INTERVAL: float = 5.0


class HardStopGuard:
    """Redis-based safety guard for the consciousness loop.

    Checks the ``life_kernel:hard_stop`` Redis key before each thought
    generation cycle. Returns True when HARD STOP is active (caller must
    halt), False when safe to proceed.

    Attributes:
        _redis: Async Redis client for HARD STOP signal lookup.
        _active: Cached state of the HARD STOP signal.
    """

    def __init__(self, redis_client: Redis) -> None:
        """Initialize the HardStopGuard.

        Args:
            redis_client: An async Redis client (redis.asyncio.Redis) instance.
                Must be connected or connectable. The guard does not own the
                client's lifecycle — the caller is responsible for closing it.
        """
        self._redis: Redis = redis_client
        self._active: bool = False

        logger.info(
            "hard_stop_guard.initialized",
            hard_stop_key=HARD_STOP_KEY,
        )

    @property
    def active(self) -> bool:
        """Return the cached HARD STOP state.

        This is a fast, synchronous check based on the last `check()` call.
        It does NOT query Redis — call `check()` to refresh the state.

        Returns:
            True if the last `check()` detected an active HARD STOP signal.
        """
        return self._active

    async def check(self) -> bool:
        """Check Redis for the HARD STOP signal.

        Queries the ``life_kernel:hard_stop`` key in Redis. If the key
        exists and has a truthy value, HARD STOP is active.

        On Redis connectivity failure: logs a warning and returns False
        (fail-open). This ensures a transient Redis outage does not
        permanently block the consciousness loop.

        Returns:
            True if HARD STOP is active (caller must halt thought generation).
            False if safe to proceed (or Redis is unreachable).
        """
        try:
            value = await self._redis.get(HARD_STOP_KEY)
        except RedisError as exc:
            logger.warning(
                "hard_stop_guard.redis_unreachable",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            # Fail-open: assume no HARD STOP when Redis is unreachable.
            # This is safer than fail-stop because connectivity issues
            # should not permanently block the consciousness loop.
            self._active = False
            return False
        except Exception as exc:
            logger.warning(
                "hard_stop_guard.unexpected_error",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            self._active = False
            return False

        # Redis returns bytes or None. Truthy = HARD STOP active.
        is_active = bool(value)
        self._active = is_active

        if is_active:
            decoded = value.decode() if isinstance(value, bytes) else str(value)
            logger.warning(
                "hard_stop_guard.signal_active",
                hard_stop_value=decoded,
            )

        return is_active

    async def wait_for_clear(self, interval: float = _DEFAULT_POLL_INTERVAL) -> None:
        """Block until the HARD STOP signal is cleared.

        Polls Redis at the specified interval until the HARD STOP key
        is absent or falsy. This is the ONLY method that uses
        ``asyncio.sleep`` — all other sleep points are in the caller.

        This method is intended for the consciousness loop to call when
        it detects a HARD STOP and needs to wait for the operator or
        recovery process to clear it before resuming.

        Args:
            interval: Seconds between Redis polls. Defaults to 5.0s.
                Must be > 0. Lower values increase Redis load but reduce
                recovery latency.

        Raises:
            ValueError: If interval <= 0.
        """
        if interval <= 0:
            raise ValueError(f"interval must be > 0, got {interval}")

        logger.info(
            "hard_stop_guard.waiting_for_clear",
            poll_interval=interval,
        )

        while True:
            is_active = await self.check()
            if not is_active:
                logger.info("hard_stop_guard.signal_cleared")
                return

            await asyncio.sleep(interval)
