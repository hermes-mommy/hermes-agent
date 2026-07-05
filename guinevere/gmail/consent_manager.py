"""Email consent gate wrapping the surveillance consent system.

Every email processing pipeline MUST call ``check_email_consent()``
before proceeding.  This module delegates the primary consent check
to the injected ``ConsentChecker`` (from ``guinevere.surveillance.consent_gate``)
and maintains a secondary Redis metadata store for fast-path status
lookups and command audit trail.

Design decisions:
- **Fail-closed**: any exception during consent evaluation returns
  ``ConsentCheckResult(allowed=False, ...)`` — the pipeline is blocked.
- **Delegation, not duplication**: all consent-verification logic lives
  in ``ConsentChecker``; this module only orchestrates email-specific
  metadata and Redis bookkeeping.
- **Distinct Redis key**: ``guinevere:consent:email`` is separate from
  the surveillance consent cache to avoid cross-scope interference.
- **No TTL on metadata**: the Redis metadata key persists until
  explicitly revoked so ``!email-status`` always returns meaningful data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
import structlog

from guinevere.surveillance.consent_gate import (
    ConsentCheckResult,
    ConsentChecker,
    ConsentStatus,
)

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EMAIL_CONSENT_SCOPE: str = "surveillance.email"
"""Surveillance scope key delegated to the ``ConsentChecker``."""

EMAIL_CONSENT_REDIS_KEY: str = "guinevere:consent:email"
"""Redis key for email consent metadata (secondary store)."""

_GRANT_EVENT: str = "gmail.consent_grant"
_REVOKE_EVENT: str = "gmail.consent_revoke"
_CHECK_EVENT: str = "gmail.consent_check"
_STATUS_EVENT: str = "gmail.consent_status"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsentManagerConfig:
    """Immutable configuration for the email consent manager.

    Attributes:
        scope: The surveillance consent scope to delegate to.
        redis_key: Redis key for the secondary metadata store.
    """

    scope: str = EMAIL_CONSENT_SCOPE
    redis_key: str = EMAIL_CONSENT_REDIS_KEY


# ---------------------------------------------------------------------------
# EmailConsentManager
# ---------------------------------------------------------------------------


class EmailConsentManager:
    """Email-specific consent gate wrapping the surveillance consent system.

    Primary consent verification is delegated to the injected
    ``ConsentChecker``.  A secondary Redis metadata store tracks
    grant/revoke events and supports the ``!email-status`` Discord command.

    Args:
        consent_checker: A ``ConsentChecker`` protocol implementation
            (typically ``consent_gate.check_consent``).
        redis: An ``redis.asyncio.Redis`` client for metadata storage.
        config: Optional override for scope and Redis key names.
    """

    def __init__(
        self,
        consent_checker: ConsentChecker,
        redis: aioredis.Redis,
        config: ConsentManagerConfig | None = None,
    ) -> None:
        self._checker: ConsentChecker = consent_checker
        self._redis: aioredis.Redis = redis
        self._config: ConsentManagerConfig = config or ConsentManagerConfig()

    # -- public API ---------------------------------------------------------

    async def check_email_consent(self) -> ConsentCheckResult:
        """Check if email processing is consented.  **Fail-closed**.

        Any Redis or delegation error results in a ``BLOCK`` verdict so
        the pipeline never proceeds without verified consent.

        Returns:
            A ``ConsentCheckResult`` with the verdict.
        """
        now = datetime.now(timezone.utc)
        try:
            result = await self._checker.check_consent(self._config.scope)
            logger.info(
                _CHECK_EVENT,
                allowed=result.allowed,
                scope=result.scope,
                reason=result.reason,
            )
            return result
        except Exception:
            logger.exception(_CHECK_EVENT, scope=self._config.scope)
            return ConsentCheckResult(
                allowed=False,
                status=None,
                scope=self._config.scope,
                reason="consent check failed — fail-closed block",
                checked_at=now,
            )

    async def grant_consent(self, granted_by: str) -> bool:
        """Grant email processing consent.

        Called by the ``!email-consent-grant`` Discord command (Faiz-only).

        Stores the grant metadata in Redis and then delegates to the
        ``ConsentChecker`` to verify the underlying consent ledger
        acknowledges the grant.

        Args:
            granted_by: Identifier of the operator granting consent.

        Returns:
            ``True`` if consent was granted and verified, ``False`` on error.
        """
        now = datetime.now(timezone.utc)
        try:
            payload = {
                "status": ConsentStatus.ACTIVE.value,
                "granted_by": granted_by,
                "granted_at": now.isoformat(),
                "revoked_at": None,
            }
            _: Any = await self._redis.set(
                self._config.redis_key,
                json.dumps(payload),
            )
            logger.info(
                _GRANT_EVENT,
                granted_by=granted_by,
                granted_at=now.isoformat(),
            )

            # Verify the underlying consent ledger agrees
            result = await self._checker.check_consent(self._config.scope)
            if not result.allowed:
                logger.warning(
                    _GRANT_EVENT,
                    granted_by=granted_by,
                    reason="underlying consent ledger does not confirm grant",
                    ledger_reason=result.reason,
                )
                return False
            return True

        except Exception:
            logger.exception(_GRANT_EVENT, granted_by=granted_by)
            return False

    async def revoke_consent(self, revoked_by: str) -> bool:
        """Revoke email processing consent.

        Called by the ``!email-consent-revoke`` Discord command (Faiz-only).

        Stores the revocation metadata in Redis.  The pipeline will
        fail-closed on the next ``check_email_consent()`` call.

        Args:
            revoked_by: Identifier of the operator revoking consent.

        Returns:
            ``True`` if the revocation metadata was stored, ``False`` on error.
        """
        now = datetime.now(timezone.utc)
        try:
            # Read previous state for audit trail
            prev_raw = await self._redis.get(self._config.redis_key)
            prev_granted_at: str | None = None
            if prev_raw is not None:
                try:
                    prev_data: dict[str, str | None] = json.loads(prev_raw)
                    prev_granted_at = prev_data.get("granted_at")
                except (json.JSONDecodeError, ValueError):
                    pass

            payload = {
                "status": ConsentStatus.WITHDRAWN.value,
                "revoked_by": revoked_by,
                "revoked_at": now.isoformat(),
                "granted_at": prev_granted_at,
            }
            _: Any = await self._redis.set(
                self._config.redis_key,
                json.dumps(payload),
            )
            logger.info(
                _REVOKE_EVENT,
                revoked_by=revoked_by,
                revoked_at=now.isoformat(),
            )
            return True

        except Exception:
            logger.exception(_REVOKE_EVENT, revoked_by=revoked_by)
            return False

    async def get_consent_status(self) -> ConsentCheckResult:
        """Get current consent status for the ``!email-status`` command.

        Returns a best-effort status by reading the Redis metadata first,
        then falling back to the ``ConsentChecker``.  Unlike
        ``check_email_consent()``, this method does **not** treat a Redis
        error as a hard block — it falls through to the checker.

        Returns:
            A ``ConsentCheckResult`` suitable for status display.
        """
        now = datetime.now(timezone.utc)

        # Try Redis metadata first for fast status display
        try:
            raw = await self._redis.get(self._config.redis_key)
            if raw is not None:
                data = json.loads(raw)
                status_str = data.get("status")
                status = (
                    ConsentStatus(status_str) if status_str else None
                )
                allowed = status == ConsentStatus.ACTIVE
                logger.info(
                    _STATUS_EVENT,
                    allowed=allowed,
                    source="redis_metadata",
                )
                return ConsentCheckResult(
                    allowed=allowed,
                    status=status,
                    scope=self._config.scope,
                    reason=f"email consent status: {status_str or 'unknown'}",
                    checked_at=now,
                )
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning(
                _STATUS_EVENT,
                error=str(exc),
                source="redis_metadata_fallback",
            )
        except Exception:
            logger.exception(
                _STATUS_EVENT,
                source="redis_metadata_error",
            )

        # Fall through to ConsentChecker
        try:
            result = await self._checker.check_consent(self._config.scope)
            logger.info(
                _STATUS_EVENT,
                allowed=result.allowed,
                source="consent_checker",
            )
            return result
        except Exception:
            logger.exception(_STATUS_EVENT, source="consent_checker_error")
            return ConsentCheckResult(
                allowed=False,
                status=None,
                scope=self._config.scope,
                reason="status check failed",
                checked_at=now,
            )


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "ConsentManagerConfig",
    "EMAIL_CONSENT_REDIS_KEY",
    "EMAIL_CONSENT_SCOPE",
    "EmailConsentManager",
]
