"""Concurrency + Resource Limits Module for Guinevere loops.

Provides:
  * :class:`ConcurrencyLimiter` — controls max parallel loop executions
    using ``asyncio.Semaphore``.
  * :class:`TokenBucket` — Redis-backed or in-memory token bucket for
    rate limiting LLM calls.
  * :class:`ResourceLimits` — frozen dataclass for resource cap config.
  * :class:`ResourceGate` — orchestrates all resource limits before
    a loop phase is allowed to run.

Redis key pattern (when Redis is available) on DB5 (cost tracking DB):

    guinevere:loops:ratelimit:{bucket_name}
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("guinevere.loops.concurrency")


@dataclass(frozen=True)
class ConcurrencyDecision:
    """Immutable decision returned by resource gate / concurrency checks.

    :ivar allowed: Whether the requested operation may proceed.
    :ivar reason: Human or machine readable explanation.
    :ivar active_loops: Number of loops currently holding a slot.
    :ivar max_loops: Maximum number of parallel loops allowed.
    :ivar available_slots: Slots currently free (may be negative if
        callers have temporarily over-claimed during release races).
    """

    allowed: bool
    reason: str
    active_loops: int
    max_loops: int
    available_slots: int


@dataclass(frozen=True)
class ResourceLimits:
    """Immutable configuration for :class:`ResourceGate`."""

    max_parallel_loops: int = 3
    max_tokens_per_minute: int = 100
    max_cost_per_hour_usd: float = 5.0
    max_retries_per_loop: int = 5


class ConcurrencyLimiter:
    """Controls max parallel loop executions using ``asyncio.Semaphore``."""

    def __init__(self, max_parallel_loops: int = 3) -> None:
        if max_parallel_loops < 1:
            raise ValueError(
                f"max_parallel_loops must be >= 1, got {max_parallel_loops}"
            )
        self._semaphore = asyncio.Semaphore(max_parallel_loops)
        self._max = max_parallel_loops
        self._active: set[str] = set()
        self._lock = asyncio.Lock()

    async def acquire(self, loop_id: str) -> ConcurrencyDecision:
        """Try to acquire a slot for *loop_id*.

        The operation is idempotent: if *loop_id* already holds a slot,
        the function succeeds immediately.

        Returns:
            A :class:`ConcurrencyDecision` describing whether the slot
            was granted and the current state of the limiter.
        """
        if not loop_id:
            raise ValueError("loop_id must be a non-empty string")

        async with self._lock:
            if loop_id in self._active:
                return ConcurrencyDecision(
                    allowed=True,
                    reason="idempotent_reentry",
                    active_loops=len(self._active),
                    max_loops=self._max,
                    available_slots=self._max - len(self._active),
                )

        # Wait for a free semaphore slot.  This is done outside the
        # instance lock to avoid blocking status queries while waiting.
        acquired = await self._semaphore.acquire()

        async with self._lock:
            if acquired:
                self._active.add(loop_id)
                return ConcurrencyDecision(
                    allowed=True,
                    reason="acquired",
                    active_loops=len(self._active),
                    max_loops=self._max,
                    available_slots=self._max - len(self._active),
                )

            # Should not happen with asyncio.Semaphore, but keep the
            # contract explicit.
            return ConcurrencyDecision(
                allowed=False,
                reason="semaphore_rejected",
                active_loops=len(self._active),
                max_loops=self._max,
                available_slots=self._max - len(self._active),
            )

    async def release(self, loop_id: str) -> None:
        """Release the slot held by *loop_id*.

        Safe to call multiple times for the same ``loop_id``; releases
        after the first are no-ops and only emit a debug log.
        """
        if not loop_id:
            raise ValueError("loop_id must be a non-empty string")

        async with self._lock:
            removed = loop_id in self._active
            if removed:
                self._active.discard(loop_id)

        if removed:
            try:
                self._semaphore.release()
            except ValueError as exc:
                # The semaphore count would exceed the initial value.
                # Re-add the loop id to keep internal consistency.
                self._active.add(loop_id)
                logger.warning(
                    "concurrency.semaphore_release_failed",
                    loop_id=loop_id,
                    error=str(exc),
                )
                raise
            logger.debug(
                "concurrency.released",
                loop_id=loop_id,
                active_count=len(self._active),
            )
        else:
            logger.debug(
                "concurrency.release_noop",
                loop_id=loop_id,
                reason="not_active",
            )

    @property
    def active_count(self) -> int:
        """Number of loops currently holding a slot."""
        return len(self._active)

    @property
    def available_slots(self) -> int:
        """Best-effort count of remaining slots (clamped at 0)."""
        return max(0, self._max - len(self._active))

    async def status(self) -> dict[str, Any]:
        """Return current concurrency status as a JSON-serialisable dict."""
        async with self._lock:
            active_list = sorted(self._active)
            active = len(self._active)
        return {
            "max_loops": self._max,
            "active_loops": active,
            "available_slots": max(0, self._max - active),
            "active_loop_ids": active_list,
        }


class TokenBucket:
    """Redis-backed or in-memory token bucket for rate limiting LLM calls.

    Redis usage (optional):
        * Redis DB5 (cost tracking DB)
        * Key pattern: ``guinevere:loops:ratelimit:{bucket_name}``
        * A Lua script performs atomic check-and-decrement.

    When ``redis_client`` is omitted, a process-local in-memory bucket
    is used.  Rate limits are therefore not shared across processes in
    that mode.
    """

    def __init__(  # noqa: D417
        self,
        redis_client: Any = None,
        bucket_name: str = "default",
        capacity: int = 100,
        refill_rate: float = 10.0,
    ) -> None:
        if capacity < 0:
            raise ValueError(f"capacity must be >= 0, got {capacity}")
        if refill_rate < 0.0:
            raise ValueError(f"refill_rate must be >= 0.0, got {refill_rate}")
        if not bucket_name:
            raise ValueError("bucket_name must be a non-empty string")

        self._redis = redis_client
        self._bucket_name = bucket_name
        self._capacity = capacity
        self._refill_rate = refill_rate

        # In-memory fallback state
        self._lock = asyncio.Lock()
        self._tokens: float = float(capacity)
        self._last_check: float = time.monotonic()

        if self._redis is None:
            logger.warning(
                "TokenBucket operating in-memory only, "
                "rate limits not shared across processes",
            )
        else:
            # Ensure redis is an async Redis-like client; we do not
            # validate strictly to stay compatible with mocks.
            pass

    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume *tokens* from the bucket.

        Returns:
            ``True`` if the tokens were available, ``False`` if rate
            limited.
        """
        if tokens < 0:
            raise ValueError(f"tokens must be >= 0, got {tokens}")
        if tokens == 0:
            return True

        if self._redis is not None:
            return await self._consume_redis(tokens)
        return await self._consume_in_memory(tokens)

    async def _consume_redis(self, tokens: int) -> bool:
        """Atomic check-and-decrement via Lua on Redis."""
        redis = self._redis
        if redis is None:
            return False

        key = f"guinevere:loops:ratelimit:{self._bucket_name}"
        now = time.time()

        lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local requested = tonumber(ARGV[4])

        local state = redis.call('HMGET', key, 'tokens', 'last_check')
        local tokens = tonumber(state[1])
        local last_check = tonumber(state[2])

        if tokens == nil then
            tokens = capacity
            last_check = now
        end

        local elapsed = now - last_check
        local refill = elapsed * refill_rate
        tokens = math.min(capacity, tokens + refill)

        if tokens >= requested then
            tokens = tokens - requested
            redis.call('HMSET', key, 'tokens', tokens, 'last_check', now)
            redis.call('EXPIRE', key, 3600)
            return 1
        else
            redis.call('HMSET', key, 'tokens', tokens, 'last_check', now)
            redis.call('EXPIRE', key, 3600)
            return 0
        end
        """

        try:
            result = await redis.eval(
                lua_script,
                1,
                key,
                str(self._capacity),
                str(self._refill_rate),
                str(now),
                str(tokens),
            )
            return bool(result)
        except Exception as exc:
            logger.error(
                "token_bucket.redis_consume_failed",
                bucket=self._bucket_name,
                error=str(exc),
            )
            # Degrade gracefully to in-memory bucket on Redis failure.
            return await self._consume_in_memory(tokens)

    async def _consume_in_memory(self, tokens: int) -> bool:
        """Process-local token bucket with time-based refill."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_check
            self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
            self._last_check = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    async def available(self) -> float:
        """Return current available tokens (may be fractional)."""
        if self._redis is not None:
            return await self._available_redis()
        return await self._available_in_memory()

    async def _available_redis(self) -> float:
        key = f"guinevere:loops:ratelimit:{self._bucket_name}"
        try:
            state = await self._redis.hmget(key, "tokens", "last_check")
            if state[0] is None:
                return float(self._capacity)
            tokens = float(state[0])
            last_check = float(state[1]) if state[1] is not None else time.time()
            now = time.time()
            elapsed = now - last_check
            return min(self._capacity, tokens + elapsed * self._refill_rate)
        except Exception as exc:
            logger.error(
                "token_bucket.redis_available_failed",
                bucket=self._bucket_name,
                error=str(exc),
            )
            return await self._available_in_memory()

    async def _available_in_memory(self) -> float:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_check
            return min(self._capacity, self._tokens + elapsed * self._refill_rate)

    async def reset(self) -> None:
        """Reset the bucket to full capacity."""
        if self._redis is not None:
            await self._reset_redis()
        else:
            await self._reset_in_memory()

    async def _reset_redis(self) -> None:
        key = f"guinevere:loops:ratelimit:{self._bucket_name}"
        try:
            await self._redis.hmset(
                key,
                {
                    "tokens": str(self._capacity),
                    "last_check": str(time.time()),
                },
            )
            await self._redis.expire(key, 3600)
        except Exception as exc:
            logger.error(
                "token_bucket.redis_reset_failed",
                bucket=self._bucket_name,
                error=str(exc),
            )
            await self._reset_in_memory()

    async def _reset_in_memory(self) -> None:
        async with self._lock:
            self._tokens = float(self._capacity)
            self._last_check = time.monotonic()


class ResourceGate:
    """Orchestrates all resource limits: concurrency + token bucket + cost cap."""

    def __init__(self, limits: ResourceLimits, redis_client: Any = None) -> None:
        self._concurrency = ConcurrencyLimiter(limits.max_parallel_loops)
        self._token_bucket = TokenBucket(
            redis_client=redis_client,
            bucket_name="llm_calls",
            capacity=limits.max_tokens_per_minute,
            refill_rate=limits.max_tokens_per_minute / 60.0,
        )
        self._limits = limits
        self._hourly_cost: float = 0.0
        self._cost_reset_at = self._next_hour_boundary()
        self._cost_lock = asyncio.Lock()

    @staticmethod
    def _next_hour_boundary() -> datetime:
        """Return the next top-of-the-hour boundary in UTC."""
        now = datetime.now(timezone.utc)
        return now.replace(minute=0, second=0, microsecond=0, hour=(now.hour + 1) % 24)

    async def check(  # noqa: D417
        self,
        loop_id: str,
        estimated_tokens: int = 1,
        estimated_cost_usd: float = 0.0,
    ) -> ConcurrencyDecision:
        """Check ALL resource limits before starting/resuming a loop phase.

        Returns:
            A :class:`ConcurrencyDecision`.  ``allowed`` is ``True`` only
            when the concurrency slot, token bucket, and hourly cost cap
            all permit the operation.
        """
        if not loop_id:
            raise ValueError("loop_id must be a non-empty string")
        if estimated_tokens < 0:
            raise ValueError(f"estimated_tokens must be >= 0, got {estimated_tokens}")
        if estimated_cost_usd < 0.0:
            raise ValueError(
                f"estimated_cost_usd must be >= 0.0, got {estimated_cost_usd}"
            )

        await self._maybe_reset_hourly_cost()

        # 1. Concurrency check (non-blocking query only).
        active = self._concurrency.active_count
        if active >= self._limits.max_parallel_loops:
            return ConcurrencyDecision(
                allowed=False,
                reason="concurrency_limit_reached",
                active_loops=active,
                max_loops=self._limits.max_parallel_loops,
                available_slots=0,
            )

        # 2. Token bucket check.
        if estimated_tokens > 0:
            tokens_available = await self._token_bucket.available()
            if tokens_available < estimated_tokens:
                return ConcurrencyDecision(
                    allowed=False,
                    reason="rate_limit_tokens_exhausted",
                    active_loops=active,
                    max_loops=self._limits.max_parallel_loops,
                    available_slots=self._limits.max_parallel_loops - active,
                )

        # 3. Hourly cost cap check.
        async with self._cost_lock:
            projected = self._hourly_cost + estimated_cost_usd
        if projected > self._limits.max_cost_per_hour_usd:
            return ConcurrencyDecision(
                allowed=False,
                reason="hourly_cost_cap_exceeded",
                active_loops=active,
                max_loops=self._limits.max_parallel_loops,
                available_slots=self._limits.max_parallel_loops - active,
            )

        return ConcurrencyDecision(
            allowed=True,
            reason="resource_limits_ok",
            active_loops=active,
            max_loops=self._limits.max_parallel_loops,
            available_slots=self._limits.max_parallel_loops - active,
        )

    async def acquire(self, loop_id: str) -> ConcurrencyDecision:
        """Acquire resources (concurrency slot + tokens).

        This is a two-step operation: first check that the token bucket
        can accommodate one token, then acquire a concurrency slot.
        """
        if not loop_id:
            raise ValueError("loop_id must be a non-empty string")

        # Acquire one token from the bucket for this loop phase.
        token_ok = await self._token_bucket.consume(tokens=1)
        if not token_ok:
            return ConcurrencyDecision(
                allowed=False,
                reason="rate_limited",
                active_loops=self._concurrency.active_count,
                max_loops=self._limits.max_parallel_loops,
                available_slots=self._concurrency.available_slots,
            )

        return await self._concurrency.acquire(loop_id)

    async def release(self, loop_id: str, actual_cost_usd: float = 0.0) -> None:
        """Release resources and track actual cost."""
        if actual_cost_usd < 0.0:
            raise ValueError(
                f"actual_cost_usd must be >= 0.0, got {actual_cost_usd}"
            )
        await self._maybe_reset_hourly_cost()
        async with self._cost_lock:
            self._hourly_cost += actual_cost_usd
        await self._concurrency.release(loop_id)

    async def status(self) -> dict[str, Any]:
        """Return full resource status as a JSON-serialisable dict."""
        await self._maybe_reset_hourly_cost()
        async with self._cost_lock:
            hourly_cost = self._hourly_cost
        return {
            "limits": {
                "max_parallel_loops": self._limits.max_parallel_loops,
                "max_tokens_per_minute": self._limits.max_tokens_per_minute,
                "max_cost_per_hour_usd": self._limits.max_cost_per_hour_usd,
                "max_retries_per_loop": self._limits.max_retries_per_loop,
            },
            "concurrency": await self._concurrency.status(),
            "tokens_available": await self._token_bucket.available(),
            "hourly_cost_usd": hourly_cost,
            "cost_reset_at": self._cost_reset_at.isoformat(),
        }

    async def _maybe_reset_hourly_cost(self) -> None:
        """Reset the hourly cost accumulator when the hour boundary passes."""
        now = datetime.now(timezone.utc)
        async with self._cost_lock:
            if now >= self._cost_reset_at:
                self._hourly_cost = 0.0
                self._cost_reset_at = self._next_hour_boundary()
