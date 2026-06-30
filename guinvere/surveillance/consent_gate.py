"""Fail-closed consent verification gate for surveillance data ingestion.

P7-010: Provides ``check_consent(scope)`` which performs a fail-closed consent
check against the ``consent.consent_ledger`` table, with a Redis DB2 cache
layer (TTL 300s) for fast lookups.

P19-009: Adds project-scoped consent enforcement.  ``check_consent(scope,
project_id)`` checks project-scoped rows first (when *project_id* is set),
falling back to global.  New scopes: ``consent.autonomy.high_blast`` (per-
project), ``consent.memory.cross_project`` (global-only),
``consent.emergency.break_glass_project`` (project-scoped, time-bound 4h).

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
- **Cache value**: JSON with ``status``, ``checked_at``, and ``project_id``
  fields.
- **Cache TTL**: 300 seconds (configurable via ``CACHE_TTL_SECONDS``).
- **Consent scopes**: ``surveillance.app_usage``, ``surveillance.location``,
  ``surveillance.notifications``, ``surveillance.clipboard``, ``surveillance.email``
  (5 scopes; ``surveillance.email`` is used by the Gmail consent manager
  ``guinvere/gmail/consent_manager.py``).
- **P19-009 project scoping**: project-scoped consent rows (with non-NULL
  ``project_id``) take precedence over global rows.  Global-only scopes
  ignore ``project_id``.  Project-only scopes have no global fallback.
- **HARD STOP**: remains global (separate mechanism in life_kernel / safe_mode).
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
    "surveillance.email",
})
"""All valid surveillance consent scopes."""

VALID_CONSENT_SCOPES: frozenset[str] = frozenset({
    "consent.autonomy.high_blast",
    "consent.memory.cross_project",
    "consent.emergency.break_glass_project",
})
"""P19-009: Non-surveillance consent scopes (project-scoped where applicable)."""

_ALL_VALID_SCOPES: frozenset[str] = VALID_SURVEILLANCE_SCOPES | VALID_CONSENT_SCOPES
"""Union of all valid scopes accepted by ``check_consent``."""

_GLOBAL_ONLY_SCOPES: frozenset[str] = frozenset({
    "consent.memory.cross_project",
})
"""Scopes that must always be global — project_id is ignored if passed."""

_PROJECT_ONLY_SCOPES: frozenset[str] = frozenset({
    "consent.emergency.break_glass_project",
})
"""Scopes that are project-only — no global fallback."""

_TIME_BOUND_SCOPES: dict[str, int] = {
    "consent.emergency.break_glass_project": 4,
}
"""Scopes with time-bound consent (scope -> max age in hours)."""

BREAK_GLASS_MAX_HOURS: int = 4
"""Maximum hours for break-glass project consent (SEC-04)."""


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
        project_id: P19-009: Project UUID for project-scoped consent,
            ``None`` for global consent.
    """

    allowed: bool
    status: ConsentStatus | None
    scope: str
    reason: str
    checked_at: datetime
    project_id: uuid.UUID | None = None


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

    async def check_consent(self, scope: str, project_id: uuid.UUID | None = None) -> ConsentCheckResult:
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


async def check_consent(scope: str, project_id: uuid.UUID | None = None) -> ConsentCheckResult:
    """Fail-closed consent verification gate.

    Decision matrix (implemented in order):

    1. **Cache hit** (Redis DB2): deserialise and return cached verdict.
    2. **Cache miss → DB query**: query ``consent.consent_ledger`` for the
       latest entry matching *scope*.
       - When *project_id* is set: check project-scoped row first (wins).
         If not found and scope allows global fallback, check global row.
       - When *project_id* is None: legacy behaviour (no project filter).
    3. **Cache miss + DB failure**: BLOCK (fail-closed).
    4. **No ledger entry**: BLOCK (never consented).
    5. **Status WITHDRAWN**: BLOCK.
    6. **Status PAUSED**: BLOCK.
    7. **Status ACTIVE**: ALLOW + cache the result in Redis.

    P19-009: ``project_id`` parameter enables project-scoped consent checks.
    When set, project-scoped rows take precedence over global rows.
    Global-only scopes (``consent.memory.cross_project``) ignore project_id.
    Time-bound scopes (``consent.emergency.break_glass_project``) require
    consent granted within the configured window.

    Args:
        scope: The consent scope to check (e.g.
               ``surveillance.app_usage``, ``consent.autonomy.high_blast``).
        project_id: Optional project UUID for project-scoped consent.
               When ``None`` (default), legacy global behaviour.

    Returns:
        A ``ConsentCheckResult`` with the verdict.
    """
    now = datetime.now(timezone.utc)

    # ---- Validate scope ----
    if scope not in _ALL_VALID_SCOPES:
        logger.warning("consent_check_unknown_scope", scope=scope)
        return ConsentCheckResult(
            allowed=False,
            status=None,
            scope=scope,
            reason=_BLOCK_UNKNOWN_SCOPE,
            checked_at=now,
            project_id=project_id,
        )

    # ---- Global-only scope: ignore project_id ----
    effective_project_id = project_id
    if effective_project_id is not None and scope in _GLOBAL_ONLY_SCOPES:
        logger.warning(
            "consent_global_only_scope_project_ignored",
            scope=scope,
            project_id=str(effective_project_id),
        )
        effective_project_id = None

    # ---- Determine time bound ----
    max_age_hours = _TIME_BOUND_SCOPES.get(scope)

    # ---- Step 1: Try Redis cache ----
    cache_key = _build_cache_key(scope, effective_project_id)
    cached = await _try_cache_lookup(cache_key)
    if cached is not None and cached.allowed:
        logger.debug(
            "consent_check_cache_hit",
            scope=scope,
            allowed=True,
            project_id=str(effective_project_id),
        )
        return cached
    if cached is not None and not cached.allowed:
        logger.debug(
            "consent_check_cache_hit_blocked",
            scope=scope,
            reason=cached.reason,
            project_id=str(effective_project_id),
        )
        return cached

    # ---- Step 2: Cache miss — fall through to DB ----
    logger.debug(
        "consent_check_cache_miss",
        scope=scope,
        project_id=str(effective_project_id),
    )

    if effective_project_id is not None:
        # ---- Project-scoped query (wins over global) ----
        try:
            db_result = await _query_ledger(
                scope,
                project_id=effective_project_id,
                max_age_hours=max_age_hours,
            )
        except Exception:
            logger.exception(
                "consent_check_db_failure",
                scope=scope,
                project_id=str(effective_project_id),
            )
            return await _block_db_failure(scope, now, effective_project_id)

        if db_result is not None:
            return await _handle_db_status(
                db_result, scope, now, cache_key, effective_project_id,
            )

        # ---- Project-scoped miss: project-only scope → block ----
        if scope in _PROJECT_ONLY_SCOPES:
            return await _block_no_entry(
                scope, now, cache_key, effective_project_id,
            )

        # ---- Fall back to global (project_id IS NULL) ----
        logger.debug(
            "consent_check_fallback_global",
            scope=scope,
            project_id=str(effective_project_id),
        )
        try:
            db_result = await _query_ledger(
                scope,
                global_only=True,
                max_age_hours=max_age_hours,
            )
        except Exception:
            logger.exception("consent_check_db_failure_global_fallback", scope=scope)
            return await _block_db_failure(scope, now, effective_project_id)

        if db_result is None:
            return await _block_no_entry(
                scope, now, cache_key, effective_project_id,
            )

        return await _handle_db_status(
            db_result, scope, now, cache_key, effective_project_id,
        )
    else:
        # ---- Legacy query (no project_id filter) ----
        # BUG-1 FIX (P19 audit round-2): pass global_only=True so that
        # project-scoped rows do not contaminate the legacy result set.
        # Without this, a project-scoped ACTIVE row with a recent
        # granted_at would be returned over a global WITHDRAWN row,
        # bypassing safe-word withdrawal.
        try:
            db_result = await _query_ledger(
                scope, global_only=True, max_age_hours=max_age_hours,
            )
        except Exception:
            logger.exception("consent_check_db_failure", scope=scope)
            return await _block_db_failure(scope, now, None)

        if db_result is None:
            return await _block_no_entry(scope, now, cache_key, None)

        return await _handle_db_status(db_result, scope, now, cache_key, None)


async def invalidate_cache(scope: str, project_id: uuid.UUID | None = None) -> None:
    """Invalidate the cached consent state for *scope*.

    Called when consent events (grant, pause, withdrawal, revocation) occur
    so the next ``check_consent`` call picks up the latest state from the DB.

    P19-009: Accepts optional *project_id* for project-scoped cache entries.

    Args:
        scope: The consent scope whose cache entry should be removed.
        project_id: Optional project UUID for project-scoped cache invalidation.
    """
    cache_key = _build_cache_key(scope, project_id)
    redis_client = _get_redis()
    try:
        await redis_client.delete(cache_key)
        logger.info(
            "consent_cache_invalidated",
            scope=scope,
            cache_key=cache_key,
            project_id=str(project_id),
        )
    except Exception:
        logger.exception("consent_cache_invalidation_failed", scope=scope)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_cache_key(scope: str, project_id: uuid.UUID | None = None) -> str:
    """Build a Redis cache key for a consent scope, optionally project-scoped."""
    base = f"{CACHE_KEY_PREFIX}{scope}"
    if project_id is not None:
        return f"{base}:{project_id}"
    return base


async def _handle_db_status(
    db_status: ConsentStatus,
    scope: str,
    now: datetime,
    cache_key: str,
    project_id: uuid.UUID | None,
) -> ConsentCheckResult:
    """Process a DB consent status into a result and cache it.

    Handles WITHDRAWN (block), PAUSED (block), and ACTIVE (allow).
    """
    if db_status == ConsentStatus.WITHDRAWN:
        logger.warning(
            "consent_check_withdrawn",
            scope=scope,
            project_id=str(project_id),
        )
        result = ConsentCheckResult(
            allowed=False,
            status=ConsentStatus.WITHDRAWN,
            scope=scope,
            reason=_BLOCK_WITHDRAWN,
            checked_at=now,
            project_id=project_id,
        )
    elif db_status == ConsentStatus.PAUSED:
        logger.info(
            "consent_check_paused",
            scope=scope,
            project_id=str(project_id),
        )
        result = ConsentCheckResult(
            allowed=False,
            status=ConsentStatus.PAUSED,
            scope=scope,
            reason=_BLOCK_PAUSED,
            checked_at=now,
            project_id=project_id,
        )
    else:
        logger.info(
            "consent_check_active",
            scope=scope,
            project_id=str(project_id),
        )
        result = ConsentCheckResult(
            allowed=True,
            status=ConsentStatus.ACTIVE,
            scope=scope,
            reason="consent is active",
            checked_at=now,
            project_id=project_id,
        )
    await _cache_result(cache_key, result)
    return result


async def _block_no_entry(
    scope: str,
    now: datetime,
    cache_key: str,
    project_id: uuid.UUID | None,
) -> ConsentCheckResult:
    """Build a BLOCK result for missing ledger entry and cache it."""
    logger.warning(
        "consent_check_no_ledger_entry",
        scope=scope,
        project_id=str(project_id),
    )
    block = ConsentCheckResult(
        allowed=False,
        status=None,
        scope=scope,
        reason=_BLOCK_NO_LEDGER,
        checked_at=now,
        project_id=project_id,
    )
    await _cache_result(cache_key, block)
    return block


async def _block_db_failure(
    scope: str,
    now: datetime,
    project_id: uuid.UUID | None,
) -> ConsentCheckResult:
    """Build a BLOCK result for DB failure (fail-closed)."""
    return ConsentCheckResult(
        allowed=False,
        status=None,
        scope=scope,
        reason=_BLOCK_DB_FAILURE,
        checked_at=now,
        project_id=project_id,
    )


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
        project_id_raw = data.get("project_id")
        project_id = uuid.UUID(project_id_raw) if project_id_raw else None
        return ConsentCheckResult(
            allowed=allowed,
            status=status,
            scope=scope,
            reason=reason,
            checked_at=checked_at,
            project_id=project_id,
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
        "project_id": str(result.project_id) if result.project_id else None,
    }
    try:
        await redis_client.set(
            cache_key, json.dumps(payload), ex=CACHE_TTL_SECONDS
        )
        logger.debug("consent_cache_written", cache_key=cache_key, allowed=result.allowed)
    except Exception:
        logger.exception("consent_cache_write_failed", cache_key=cache_key)


async def _query_ledger(
    scope: str,
    project_id: uuid.UUID | None = None,
    global_only: bool = False,
    max_age_hours: int | None = None,
) -> ConsentStatus | None:
    """Query ``consent.consent_ledger`` for the latest consent status.

    P19-009: Supports project-scoped queries.

    Args:
        scope: The consent scope to query.
        project_id: If set, filter by this project UUID.
        global_only: If True, filter for ``project_id IS NULL`` (global rows).
        max_age_hours: If set, only return entries granted within this window.

    Returns:
        The ``ConsentStatus`` enum value matching the most recent ledger
        entry, or ``None`` if no entry exists.

    Raises:
        Exception: Any SQLAlchemy or connectivity error (caller handles
            fail-closed).
    """
    session = _get_db_session()
    if session is None:
        raise RuntimeError("No DB session configured for consent gate")

    from sqlalchemy import text

    where_parts: list[str] = ["scope = :scope"]
    params: dict[str, Any] = {"scope": scope}

    if global_only:
        where_parts.append("project_id IS NULL")
    elif project_id is not None:
        where_parts.append("project_id = :project_id")
        params["project_id"] = str(project_id)

    if max_age_hours is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        where_parts.append("granted_at >= :cutoff")
        params["cutoff"] = cutoff.isoformat()

    where_sql = " AND ".join(where_parts)
    sql = (
        f"SELECT status FROM consent.consent_ledger "
        f"WHERE {where_sql} "
        f"ORDER BY granted_at DESC "
        f"LIMIT 1"
    )
    stmt = text(sql)
    result = await session.execute(stmt, params)
    row = result.fetchone()

    if row is None:
        return None

    status_str = row[0] if isinstance(row, tuple) else row.status
    return ConsentStatus(status_str)


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "BREAK_GLASS_MAX_HOURS",
    "CACHE_KEY_PREFIX",
    "CACHE_TTL_SECONDS",
    "VALID_CONSENT_SCOPES",
    "VALID_SURVEILLANCE_SCOPES",
    "ConsentChecker",
    "ConsentCheckResult",
    "ConsentStatus",
    "check_consent",
    "invalidate_cache",
    "_set_redis_for_testing",
    "_set_db_session_for_testing",
]
