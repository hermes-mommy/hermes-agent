"""Fail-closed consent verification gate for surveillance data ingestion.

P7-010: Provides ``check_consent(scope)`` which performs a fail-closed consent
check against the ``consent.consent_ledger`` table, with a Redis DB2 cache
layer (TTL 300s) for fast lookups.

Design decisions:
- **Fail-closed**: any uncertainty (DB down after cache miss, no ledger entry,
  WITHDRAWN, PAUSED) results in ``allowed=False`` (BLOCK).
- **Redis cache first**: lookups hit Redis DB2 cache before falling through to
  the database. Cache miss alone is safe — it falls through. Only a DB failure
  after a cache miss triggers fail-closed.
- **Cache alone failure is not fail-closed**: if Redis is unavailable the
  check falls through to the database. Only database unavailability (after
  cache miss) blocks the request.
- **Module-level injectable singletons**: ``_set_redis_for_testing()`` and
  ``_set_db_session_for_testing()`` follow the same test-injection pattern as
  ``replay.py``.
- **Cache value**: JSON with ``status`` and ``checked_at`` fields.
- **Cache TTL**: 300 seconds (configurable via ``CACHE_TTL_SECONDS``).
- **Consent scopes**: ``surveillance.app_usage``, ``surveillance.location``,
  ``surveillance.notifications``, ``surveillance.clipboard``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CACHE_KEY_PREFIX: str = "consent:surveillance:"
"""Redis key prefix for consent cache entries."""

CACHE_TTL_SECONDS: int = 300
"""Default TTL for cached consent lookups (seconds)."""

VALID_SURVEILLANCE_SCOPES: frozenset[str] = frozenset({
    "surveillance.app_usage",
    "surveillance.location",
    "surveillance.notifications",
    "surveillance.clipboard",
})
"""All valid surveillance consent scopes."""


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class ConsentStatus(StrEnum):
    """Consent ledger status values."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    WITHDRAWN = "WITHDRAWN"


@dataclass(frozen=True)
class ConsentCheckResult:
    """Immutable result from a consent gate check.

    Attributes:
        allowed: ``True`` if ingestion is permitted for this scope.
        status: The consent status from the ledger, or ``None`` if unknown.
        scope: The surveillance scope that was checked.
        reason: Human-readable explanation of the decision.
        checked_at: UTC timestamp when the check was performed.
    """

    allowed: bool
    status: ConsentStatus | None
    scope: str
    reason: str
    checked_at: datetime


_BLOCK_NO_LEDGER = "no consent ledger entry found — never consented"
_BLOCK_WITHDRAWN = "consent has been withdrawn"
_BLOCK_PAUSED = "consent is paused"
_BLOCK_DB_FAILURE = "database unavailable — fail-closed block"
_BLOCK_UNKNOWN_SCOPE = "unknown surveillance scope"


# ---------------------------------------------------------------------------
# ConsentChecker Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ConsentChecker(Protocol):
    """Protocol for consent verification backends."""

    async def check_consent(self, scope: str) -> ConsentCheckResult:
        """Check whether consent exists for *scope* and return a verdict."""
        ...


class _AsyncDBSession(Protocol):
    """Minimal protocol for an async DB session — supports ``execute()``."""

    async def execute(self, statement: Any, params: dict[str, str] | None = None) -> Any:
        """Execute a SQL statement and return a result."""
        ...


# ---------------------------------------------------------------------------
# Module-level injectables (lazy singletons, overridable for tests)
# ---------------------------------------------------------------------------

_redis: aioredis.Redis | None = None
"""Module-level Redis client connected to DB2."""


def _get_redis() -> aioredis.Redis:
    """Return the module-level Redis client, creating it if necessary."""
    global _redis
    if _redis is None:
        _redis = aioredis.Redis(
            host="localhost",
            port=6380,
            db=2,
            decode_responses=True,
            password=os.environ.get("REDIS_PASSWORD", ""),
        )
    return _redis


def _set_redis_for_testing(client: aioredis.Redis | None) -> None:
    """Replace the module-level Redis client (for test injection).

    Intended **only** for test isolation.
    """
    global _redis
    _redis = client


_db_session: _AsyncDBSession | None = None
"""Module-level async DB session or session-factory callable for testing."""


def _get_db_session() -> _AsyncDBSession | None:
    """Return the module-level DB session.

    In production this should be set via dependency injection (e.g., a
    ``create_async_engine``-backed session). For tests, use
    ``_set_db_session_for_testing()`` to inject a mock.
    """
    global _db_session
    return _db_session


def _set_db_session_for_testing(session: _AsyncDBSession | None) -> None:
    """Replace the module-level DB session (for test injection).

    Intended **only** for test isolation.
    """
    global _db_session
    _db_session = session


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def check_consent(scope: str) -> ConsentCheckResult:
    """Fail-closed consent verification gate.

    Decision matrix (implemented in order):

    1. **Cache hit** (Redis DB2): deserialise and return cached verdict.
    2. **Cache miss → DB query**: query ``consent.consent_ledger`` for the
       latest entry matching *scope*.
    3. **Cache miss + DB failure**: BLOCK (fail-closed).
    4. **No ledger entry**: BLOCK (never consented).
    5. **Status WITHDRAWN**: BLOCK.
    6. **Status PAUSED**: BLOCK.
    7. **Status ACTIVE**: ALLOW + cache the result in Redis.

    Args:
        scope: The surveillance scope to check (e.g.
               ``surveillance.app_usage``).

    Returns:
        A ``ConsentCheckResult`` with the verdict.
    """
    now = datetime.now(timezone.utc)

    # ---- Validate scope ----
    if scope not in VALID_SURVEILLANCE_SCOPES:
        logger.warning("consent_check_unknown_scope", scope=scope)
        return ConsentCheckResult(
            allowed=False,
            status=None,
            scope=scope,
            reason=_BLOCK_UNKNOWN_SCOPE,
            checked_at=now,
        )

    # ---- Step 1: Try Redis cache ----
    cache_key = f"{CACHE_KEY_PREFIX}{scope}"
    cached = await _try_cache_lookup(cache_key)
    if cached is not None and cached.allowed:
        logger.debug("consent_check_cache_hit", scope=scope, allowed=True)
        return cached
    if cached is not None and not cached.allowed:
        # Negative cache hit — cached block decision
        logger.debug("consent_check_cache_hit_blocked", scope=scope, reason=cached.reason)
        return cached

    # ---- Step 2: Cache miss — fall through to DB ----
    logger.debug("consent_check_cache_miss", scope=scope)

    try:
        db_result = await _query_ledger(scope)
    except Exception:
        logger.exception("consent_check_db_failure", scope=scope)
        # ---- Step 3: DB failure → BLOCK (fail-closed) ----
        return ConsentCheckResult(
            allowed=False,
            status=None,
            scope=scope,
            reason=_BLOCK_DB_FAILURE,
            checked_at=now,
        )

    # ---- Step 4: No ledger entry → BLOCK ----
    if db_result is None:
        logger.warning("consent_check_no_ledger_entry", scope=scope)
        block_result = ConsentCheckResult(
            allowed=False,
            status=None,
            scope=scope,
            reason=_BLOCK_NO_LEDGER,
            checked_at=now,
        )
        await _cache_result(cache_key, block_result)
        return block_result

    # ---- Step 5: WITHDRAWN → BLOCK ----
    if db_result == ConsentStatus.WITHDRAWN:
        logger.warning("consent_check_withdrawn", scope=scope)
        block_result = ConsentCheckResult(
            allowed=False,
            status=ConsentStatus.WITHDRAWN,
            scope=scope,
            reason=_BLOCK_WITHDRAWN,
            checked_at=now,
        )
        await _cache_result(cache_key, block_result)
        return block_result

    # ---- Step 6: PAUSED → BLOCK ----
    if db_result == ConsentStatus.PAUSED:
        logger.info("consent_check_paused", scope=scope)
        block_result = ConsentCheckResult(
            allowed=False,
            status=ConsentStatus.PAUSED,
            scope=scope,
            reason=_BLOCK_PAUSED,
            checked_at=now,
        )
        await _cache_result(cache_key, block_result)
        return block_result

    # ---- Step 7: ACTIVE → ALLOW ----
    logger.info("consent_check_active", scope=scope)
    allow_result = ConsentCheckResult(
        allowed=True,
        status=ConsentStatus.ACTIVE,
        scope=scope,
        reason="consent is active",
        checked_at=now,
    )
    await _cache_result(cache_key, allow_result)
    return allow_result


async def invalidate_cache(scope: str) -> None:
    """Invalidate the cached consent state for *scope*.

    Called when consent events (grant, pause, withdrawal, revocation) occur
    so the next ``check_consent`` call picks up the latest state from the DB.

    Args:
        scope: The surveillance scope whose cache entry should be removed.
    """
    cache_key = f"{CACHE_KEY_PREFIX}{scope}"
    redis_client = _get_redis()
    try:
        await redis_client.delete(cache_key)
        logger.info("consent_cache_invalidated", scope=scope, cache_key=cache_key)
    except Exception:
        logger.exception("consent_cache_invalidation_failed", scope=scope)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _try_cache_lookup(cache_key: str) -> ConsentCheckResult | None:
    """Attempt to read a cached consent verdict from Redis.

    Returns:
        A ``ConsentCheckResult`` if found, ``None`` on cache miss, deserialisation
        failure, or Redis error (all fall through to DB).
    """
    redis_client = _get_redis()
    try:
        raw = await redis_client.get(cache_key)
    except Exception:
        logger.exception("consent_cache_redis_error", cache_key=cache_key)
        return None  # Cache failure → fall through to DB

    if raw is None:
        return None  # Cache miss

    try:
        data = json.loads(raw)
        status_raw = data.get("status")
        status = ConsentStatus(status_raw) if status_raw else None
        checked_at = datetime.fromisoformat(data.get("checked_at", ""))
        allowed = data.get("allowed", False)
        reason = data.get("reason", "cached")
        scope = data.get("scope", "unknown")
        return ConsentCheckResult(
            allowed=allowed,
            status=status,
            scope=scope,
            reason=reason,
            checked_at=checked_at,
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        logger.warning("consent_cache_bad_json", cache_key=cache_key, error=str(exc))
        return None  # Corrupt cache → fall through to DB


async def _cache_result(cache_key: str, result: ConsentCheckResult) -> None:
    """Write a consent verdict to Redis cache with TTL.

    Best-effort: cache write failures are logged but never propagate.
    """
    redis_client = _get_redis()
    payload = {
        "allowed": result.allowed,
        "status": result.status.value if result.status else None,
        "scope": result.scope,
        "reason": result.reason,
        "checked_at": result.checked_at.isoformat(),
    }
    try:
        await redis_client.set(
            cache_key, json.dumps(payload), ex=CACHE_TTL_SECONDS
        )
        logger.debug("consent_cache_written", cache_key=cache_key, allowed=result.allowed)
    except Exception:
        logger.exception("consent_cache_write_failed", cache_key=cache_key)


async def _query_ledger(scope: str) -> ConsentStatus | None:
    """Query ``consent.consent_ledger`` for the latest consent status.

    Returns:
        The ``ConsentStatus`` enum value matching the most recent ledger
        entry for *scope*, or ``None`` if no entry exists.

    Raises:
        Exception: Any SQLAlchemy or connectivity error (caller handles
            fail-closed).
    """
    session = _get_db_session()
    if session is None:
        raise RuntimeError("No DB session configured for consent gate")

    from sqlalchemy import text

    # Resolve the schema-qualified table name for raw query
    stmt = text(
        "SELECT status FROM consent.consent_ledger "
        + "WHERE scope = :scope "
        + "ORDER BY granted_at DESC "
        + "LIMIT 1"
    )
    result = await session.execute(stmt, {"scope": scope})
    row = result.fetchone()

    if row is None:
        return None

    status_str = row[0] if isinstance(row, tuple) else row.status
    return ConsentStatus(status_str)


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "CACHE_KEY_PREFIX",
    "CACHE_TTL_SECONDS",
    "VALID_SURVEILLANCE_SCOPES",
    "ConsentChecker",
    "ConsentCheckResult",
    "ConsentStatus",
    "check_consent",
    "invalidate_cache",
    "_set_redis_for_testing",
    "_set_db_session_for_testing",
]