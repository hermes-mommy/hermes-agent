"""Global sub-agent concurrency limiter and depth exception.

ADR-065 hard cap: 10 concurrent sub-agents per Hermes instance.
Spawn rate limit: 30/hour per ADR-065  65 "Spawn rate limit".
MaxDepthReached: raised when delegation depth exceeds the configured cap.

This module is distinct from ``agent/iteration_budget.py`` (per-agent
iteration counter).  The global semaphore here caps total concurrent
sub-agent threads across the *entire process*, preventing runaway trees
from exhausting API rate limits or OS thread pools.
"""

from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)

# ADR-065 hard cap: 10 active sub-agents per Hermes instance.
_MAX_CONCURRENT_SUBAGENTS: int = 10

# ADR-065 spawn rate limit: 30 spawns per rolling hour.
_SPAWN_RATE_LIMIT: int = 30
_SPAWN_RATE_WINDOW_SECONDS: float = 3600.0

# --- Exceptions ---


class MaxDepthReached(Exception):
    """Raised when a delegation would exceed the configured spawn depth.

    Callers that expect a JSON error string (the legacy behaviour) should
    catch this and serialise it at the ``delegate_task`` entry point.
    """

    def __init__(self, depth: int, max_spawn_depth: int, cap: int) -> None:
        self.depth = depth
        self.max_spawn_depth = max_spawn_depth
        self.cap = cap
        super().__init__(
            f"Delegation depth limit reached (depth={depth}, "
            f"max_spawn_depth={max_spawn_depth}). Raise "
            f"delegation.max_spawn_depth in config.yaml if deeper "
            f"nesting is required (cap: {cap})."
        )


# --- Global concurrency semaphore ---

_global_semaphore = threading.Semaphore(_MAX_CONCURRENT_SUBAGENTS)
_semaphore_lock = threading.Lock()


def acquire_subagent_slot(timeout: float | None = 30.0) -> bool:
    """Acquire one slot from the global sub-agent semaphore.

    Returns True if a slot was acquired, False on timeout.
    """
    return _global_semaphore.acquire(timeout=timeout)


def release_subagent_slot() -> None:
    """Release one slot back to the global sub-agent semaphore."""
    _global_semaphore.release()


# --- Context manager ---


class SubagentSlot:
    """Context manager for the global sub-agent semaphore.

    Usage::

        with SubagentSlot() as acquired:
            if not acquired:
                raise MaxDepthReached(...)
            # ... run child ...
    """

    def __init__(self, timeout: float | None = 30.0) -> None:
        self._timeout = timeout
        self._acquired = False

    def __enter__(self) -> SubagentSlot:
        self._acquired = acquire_subagent_slot(self._timeout)
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._acquired:
            release_subagent_slot()
            self._acquired = False


# --- Spawn rate limiter ---

_spawn_timestamps_lock = threading.Lock()
_spawn_timestamps: list[float] = []


def check_spawn_rate() -> bool:
    """Return True if a new spawn is within the rate limit (30/hour).

    Prunes timestamps older than the rolling window before checking.
    Does NOT record the spawn -- call :func:`record_spawn` after the
    spawn actually starts.
    """
    now = time.monotonic()
    cutoff = now - _SPAWN_RATE_WINDOW_SECONDS
    with _spawn_timestamps_lock:
        # Prune stale entries
        while _spawn_timestamps and _spawn_timestamps[0] < cutoff:
            _spawn_timestamps.pop(0)
        return len(_spawn_timestamps) < _SPAWN_RATE_LIMIT


def record_spawn() -> None:
    """Record a spawn timestamp for rate limiting."""
    now = time.monotonic()
    with _spawn_timestamps_lock:
        _spawn_timestamps.append(now)


__all__ = [
    "MaxDepthReached",
    "SubagentSlot",
    "acquire_subagent_slot",
    "release_subagent_slot",
    "check_spawn_rate",
    "record_spawn",
]
