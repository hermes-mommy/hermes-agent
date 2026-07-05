"""Wearable health consent scopes and fail-closed consent gate.

Follows the surveillance consent pattern from guinevere/surveillance/consent_gate.py.
New scopes are independent from surveillance — users can grant wearable consent
without granting surveillance, and vice versa.

Scopes:
- wearable-health.hr — heart rate data
- wearable-health.activity — steps and activity
- wearable-health.spo2 — blood oxygen saturation
- wearable-health.stress — stress level
- wearable-health.sleep — sleep analysis
- wearable-health.ghi — global health index
- wearable-health.alerts — health anomaly alerts
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
from sqlalchemy import text
from structlog.stdlib import BoundLogger

from guinevere.wearable.models import HealthMetricType

logger: BoundLogger = structlog.get_logger(__name__)

CACHE_KEY_PREFIX: str = "consent:wearable-health:"
CACHE_TTL_SECONDS: int = 300

VALID_WEARABLE_SCOPES: frozenset[str] = frozenset({
    "wearable-health.hr",
    "wearable-health.activity",
    "wearable-health.spo2",
    "wearable-health.stress",
    "wearable-health.sleep",
    "wearable-health.ghi",
    "wearable-health.alerts",
})

METRIC_TO_SCOPE: dict[HealthMetricType, str] = {
    HealthMetricType.HEART_RATE: "wearable-health.hr",
    HealthMetricType.STEPS: "wearable-health.activity",
    HealthMetricType.SPO2: "wearable-health.spo2",
    HealthMetricType.STRESS: "wearable-health.stress",
    HealthMetricType.SLEEP: "wearable-health.sleep",
    HealthMetricType.ACTIVITY: "wearable-health.activity",
}


class ConsentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    WITHDRAWN = "WITHDRAWN"


@dataclass(frozen=True)
class WearableConsentCheckResult:
    allowed: bool
    status: ConsentStatus | None
    scope: str
    reason: str
    checked_at: datetime


_BLOCK_NO_LEDGER = "no consent ledger entry found — never consented"
_BLOCK_WITHDRAWN = "consent has been withdrawn"
_BLOCK_PAUSED = "consent is paused"
_BLOCK_DB_FAILURE = "database unavailable — fail-closed block"
_BLOCK_UNKNOWN_SCOPE = "unknown wearable consent scope"


@runtime_checkable
class ConsentChecker(Protocol):
    async def check_consent(self, scope: str) -> WearableConsentCheckResult:
        ...


class _AsyncDBSession(Protocol):
    async def execute(self, statement: Any, params: dict[str, str] | None = None) -> Any:
        ...


_redis: aioredis.Redis | None = None
_db_session: _AsyncDBSession | None = None


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.Redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", "6380")),
            db=2,
            decode_responses=True,
            password=os.environ.get("REDIS_PASSWORD", ""),
        )
    return _redis


def _set_redis_for_testing(client: aioredis.Redis | None) -> None:
    global _redis
    _redis = client


def _get_db_session() -> _AsyncDBSession | None:
    global _db_session
    if _db_session is None:
        _db_session = _create_default_db_session()
    return _db_session


def _create_default_db_session() -> _AsyncDBSession | None:
    """Auto-initialize SQLAlchemy async session from WEARABLE_DATABASE_URL."""
    db_url = os.environ.get("WEARABLE_DATABASE_URL", "")
    if not db_url:
        return None
    try:
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker

        # Convert postgresql:// to postgresql+asyncpg:// if needed
        if db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
        factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        class _SessionWrapper:
            """Thin wrapper that exposes execute() for the consent gate."""

            async def execute(self, statement: Any, params: dict[str, str] | None = None) -> Any:
                async with factory() as session:
                    return await session.execute(statement, params or {})

        return _SessionWrapper()
    except Exception:
        logger.exception("wearable_consent_db_init_failed")
        return None


def _set_db_session_for_testing(session: _AsyncDBSession | None) -> None:
    global _db_session
    _db_session = session


async def check_wearable_consent(scope: str) -> WearableConsentCheckResult:
    now = datetime.now(timezone.utc)
    if scope not in VALID_WEARABLE_SCOPES:
        logger.warning("wearable_consent_check_unknown_scope", scope=scope)
        return WearableConsentCheckResult(False, None, scope, _BLOCK_UNKNOWN_SCOPE, now)

    cache_key = f"{CACHE_KEY_PREFIX}{scope}"
    cached = await _try_cache_lookup(cache_key)
    if cached is not None:
        return cached

    try:
        db_result = await _query_ledger(scope)
    except Exception:
        logger.exception("wearable_consent_check_db_failure", scope=scope)
        return WearableConsentCheckResult(False, None, scope, _BLOCK_DB_FAILURE, now)

    if db_result is None:
        block_result = WearableConsentCheckResult(False, None, scope, _BLOCK_NO_LEDGER, now)
        await _cache_result(cache_key, block_result)
        return block_result

    if db_result == ConsentStatus.WITHDRAWN:
        block_result = WearableConsentCheckResult(False, ConsentStatus.WITHDRAWN, scope, _BLOCK_WITHDRAWN, now)
        await _cache_result(cache_key, block_result)
        return block_result

    if db_result == ConsentStatus.PAUSED:
        block_result = WearableConsentCheckResult(False, ConsentStatus.PAUSED, scope, _BLOCK_PAUSED, now)
        await _cache_result(cache_key, block_result)
        return block_result

    allow_result = WearableConsentCheckResult(True, ConsentStatus.ACTIVE, scope, "consent is active", now)
    await _cache_result(cache_key, allow_result)
    return allow_result


async def check_metric_consent(metric: HealthMetricType) -> WearableConsentCheckResult:
    scope = METRIC_TO_SCOPE[metric]
    return await check_wearable_consent(scope)


async def check_all_metrics_consent() -> dict[HealthMetricType, WearableConsentCheckResult]:
    results: dict[HealthMetricType, WearableConsentCheckResult] = {}
    for metric in HealthMetricType:
        results[metric] = await check_metric_consent(metric)
    return results


async def grant_consent(scope: str) -> bool:
    return await _write_consent_entry(scope, ConsentStatus.ACTIVE)


async def revoke_consent(scope: str) -> bool:
    return await _write_consent_entry(scope, ConsentStatus.WITHDRAWN)


async def pause_consent(scope: str) -> bool:
    return await _write_consent_entry(scope, ConsentStatus.PAUSED)


async def withdraw_consent(scope: str) -> bool:
    return await revoke_consent(scope)


async def invalidate_consent_cache(scope: str) -> None:
    cache_key = f"{CACHE_KEY_PREFIX}{scope}"
    try:
        await _get_redis().delete(cache_key)
        logger.info("wearable_consent_cache_invalidated", scope=scope, cache_key=cache_key)
    except Exception:
        logger.exception("wearable_consent_cache_invalidation_failed", scope=scope)


async def wac_consent_check(owner_id: str, scope: str) -> dict[str, Any]:
    result = await check_wearable_consent(scope)
    cached = result.reason not in (_BLOCK_DB_FAILURE, _BLOCK_UNKNOWN_SCOPE)
    return {
        "owner_id": owner_id,
        "allowed": result.allowed,
        "scope": result.scope,
        "reason": result.reason,
        "cached": cached,
        "status": result.status.value if result.status is not None else None,
        "checked_at": result.checked_at.isoformat(),
    }


async def _try_cache_lookup(cache_key: str) -> WearableConsentCheckResult | None:
    try:
        raw = await _get_redis().get(cache_key)
    except Exception:
        logger.exception("wearable_consent_cache_redis_error", cache_key=cache_key)
        return None
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        status_raw = data.get("status")
        status = ConsentStatus(status_raw) if status_raw else None
        return WearableConsentCheckResult(
            allowed=bool(data.get("allowed", False)),
            status=status,
            scope=str(data.get("scope", "unknown")),
            reason=str(data.get("reason", "cached")),
            checked_at=datetime.fromisoformat(str(data.get("checked_at"))),
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        logger.warning("wearable_consent_cache_bad_json", cache_key=cache_key, error=str(exc))
        return None


async def _cache_result(cache_key: str, result: WearableConsentCheckResult) -> None:
    payload = {
        "allowed": result.allowed,
        "status": result.status.value if result.status else None,
        "scope": result.scope,
        "reason": result.reason,
        "checked_at": result.checked_at.isoformat(),
    }
    try:
        await _get_redis().set(cache_key, json.dumps(payload), ex=CACHE_TTL_SECONDS)
    except Exception:
        logger.exception("wearable_consent_cache_write_failed", cache_key=cache_key)


async def _query_ledger(scope: str) -> ConsentStatus | None:
    session = _get_db_session()
    if session is None:
        logger.error("wearable_consent_no_db_session", scope=scope)
        return None
    stmt = text("SELECT status FROM consent.consent_ledger WHERE scope = :scope ORDER BY granted_at DESC LIMIT 1")
    result = await session.execute(stmt, {"scope": scope})
    row = result.fetchone()
    if row is None:
        return None
    status_str: Any = row[0] if isinstance(row, tuple) else row.status
    return ConsentStatus(status_str)


async def _write_consent_entry(scope: str, status: ConsentStatus) -> bool:
    try:
        session = _get_db_session()
        if session is None:
            raise RuntimeError("No DB session configured for wearable consent write")
        stmt = text("INSERT INTO consent.consent_ledger (scope, status, granted_at) VALUES ($1, $2, NOW()) RETURNING id")
        await session.execute(stmt, {"scope": scope, "status": status})
        await invalidate_consent_cache(scope)
        return True
    except Exception:
        logger.exception("wearable_consent_write_failed", scope=scope, status=status)
        return False


__all__ = [
    "CACHE_KEY_PREFIX",
    "CACHE_TTL_SECONDS",
    "VALID_WEARABLE_SCOPES",
    "METRIC_TO_SCOPE",
    "ConsentChecker",
    "WearableConsentCheckResult",
    "ConsentStatus",
    "check_wearable_consent",
    "check_metric_consent",
    "check_all_metrics_consent",
    "grant_consent",
    "revoke_consent",
    "pause_consent",
    "withdraw_consent",
    "invalidate_consent_cache",
    "wac_consent_check",
    "_set_redis_for_testing",
    "_set_db_session_for_testing",
]
