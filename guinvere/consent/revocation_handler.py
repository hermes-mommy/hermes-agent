"""Consent revocation handler for Guinevere.

This module provides centralized consent state management and ensures that
consent revocation propagates to all persona/surveillance consumers within
one event cycle.

Architecture:
- Consent state is authoritative in PostgreSQL (consent.consent_ledger)
- Redis DB0 key 'consent:grants' is a hot-path cache
- 'consent:revoked_at' timestamp tracks last revocation for consumer checks
- SafeModeController is activated on persona consent revocation

Fail-closed design:
- Redis unavailable → assume no consent (deny persona injection)
- PostgreSQL unavailable → log warning, continue with Redis state
- Consent data missing → deny persona injection (safe default)
"""

from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()

# Redis key constants
REDIS_KEY_CONSENT_GRANTS = "consent:grants"
REDIS_KEY_CONSENT_REVOKED_AT = "consent:revoked_at"

# Redis connection defaults
REDIS_HOST = "localhost"
REDIS_PORT = 6380
REDIS_DB = 0
REDIS_USERNAME = "guinevere_core"
REDIS_SOCKET_TIMEOUT = 2.0


@dataclass
class ConsentState:
    """Current consent state snapshot."""
    grants: set[str]
    revoked_at: datetime | None
    persona_allowed: bool
    surveillance_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "grants": list(self.grants),
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "persona_allowed": self.persona_allowed,
            "surveillance_allowed": self.surveillance_allowed,
        }


class ConsentRevocationHandler:
    """Coordinates consent state across persona, surveillance, and tool consumers.

    Responsibilities:
    - Read consent state from Redis (hot path) and PostgreSQL (audit trail)
    - Activate SafeModeController on persona consent revocation
    - Provide check_consent() API for PersonaPlugin
    - Maintain audit log in consent.consent_ledger table
    """

    def __init__(self) -> None:
        self._safe_mode_controller: Any = None
        self._pg_session_factory: Any = None
        logger.info("consent_handler_initialized")

    def set_safe_mode_controller(self, controller: Any) -> None:
        """Register SafeModeController for activation on consent revoke."""
        self._safe_mode_controller = controller
        logger.info("consent_handler_safe_mode_registered")

    def set_pg_session_factory(self, factory: Any) -> None:
        """Register PostgreSQL session factory for audit logging."""
        self._pg_session_factory = factory
        logger.info("consent_handler_pg_registered")

    def check_consent(self, scope: str = "persona") -> bool:
        """Check if consent is currently granted for the given scope.

        Fail-closed: returns False if Redis is unavailable or consent data missing.

        Args:
            scope: Consent scope to check (e.g., "persona", "surveillance")

        Returns:
            True if consent is granted, False otherwise
        """
        try:
            redis_mod = importlib.import_module("redis")
            r = redis_mod.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                username=REDIS_USERNAME,
                password=os.environ.get("REDIS_PASSWORD", ""),
                socket_timeout=REDIS_SOCKET_TIMEOUT,
                decode_responses=True,
            )

            grants_raw = r.get(REDIS_KEY_CONSENT_GRANTS)
            r.close()

            if grants_raw is None:
                logger.warning("consent_check_no_grants_key", scope=scope)
                return False

            grants = json.loads(grants_raw)
            if not isinstance(grants, list):
                logger.warning("consent_check_malformed_grants", scope=scope)
                return False

            is_granted = scope in grants

            if not is_granted:
                logger.info("consent_check_denied", scope=scope)
            else:
                logger.debug("consent_check_allowed", scope=scope)

            return is_granted

        except Exception as e:
            logger.error("consent_check_failed", scope=scope, error=str(e), exc_info=True)
            return False  # Fail-closed on any error

    def get_state(self) -> ConsentState:
        """Get current consent state snapshot.

        Returns:
            ConsentState with current grants and revocation timestamp
        """
        grants = set()
        revoked_at = None

        try:
            redis_mod = importlib.import_module("redis")
            r = redis_mod.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                username=REDIS_USERNAME,
                password=os.environ.get("REDIS_PASSWORD", ""),
                socket_timeout=REDIS_SOCKET_TIMEOUT,
                decode_responses=True,
            )

            grants_raw = r.get(REDIS_KEY_CONSENT_GRANTS)
            if grants_raw:
                grants_data = json.loads(grants_raw)
                if isinstance(grants_data, list):
                    grants = set(grants_data)

            revoked_raw = r.get(REDIS_KEY_CONSENT_REVOKED_AT)
            if revoked_raw:
                try:
                    revoked_at = datetime.fromisoformat(revoked_raw)
                except (ValueError, TypeError):
                    logger.warning("consent_state_invalid_revoked_timestamp")

            r.close()

        except Exception as e:
            logger.error("consent_state_read_failed", error=str(e), exc_info=True)

        return ConsentState(
            grants=grants,
            revoked_at=revoked_at,
            persona_allowed="persona" in grants,
            surveillance_allowed="surveillance" in grants,
        )

    async def on_consent_revoked(
        self,
        scope: str,
        project: str | None = None,
        revoked_by: str = "user",
    ) -> None:
        """Handle consent revocation event.

        This method is called by cmd_consent when a revoke command is executed.
        It coordinates the revocation across all consumers:

        1. Updates Redis consent:grants (already done by caller)
        2. Sets consent:revoked_at timestamp for consumer checks
        3. Activates SafeModeController if persona scope revoked
        4. Writes audit row to consent.consent_ledger (PostgreSQL)

        Args:
            scope: Consent scope being revoked (e.g., "persona")
            project: Optional project identifier
            revoked_by: Actor who revoked consent
        """
        now = datetime.now(timezone.utc)

        # Step 1: Update Redis revocation timestamp
        try:
            redis_mod = importlib.import_module("redis")
            r = redis_mod.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                username=REDIS_USERNAME,
                password=os.environ.get("REDIS_PASSWORD", ""),
                socket_timeout=REDIS_SOCKET_TIMEOUT,
                decode_responses=True,
            )
            r.set(REDIS_KEY_CONSENT_REVOKED_AT, now.isoformat())
            r.close()
            logger.info("consent_revoked_timestamp_set", scope=scope)
        except Exception as e:
            logger.error("consent_revoked_timestamp_failed", error=str(e), exc_info=True)

        # Step 2: Activate SafeModeController if persona revoked
        if scope == "persona" and self._safe_mode_controller is not None:
            try:
                # Use force_safe_mode (bypasses SAFE_MODE_THRESHOLD)
                # because consent revocation is an explicit operator action
                self._safe_mode_controller.force_safe_mode(
                    context=f"consent_revoked:{scope}"
                )
                logger.warning(
                    "consent_revoked_safe_mode_activated",
                    scope=scope,
                    revoked_by=revoked_by,
                )
            except Exception as e:
                logger.error(
                    "consent_revoked_safe_mode_failed",
                    scope=scope,
                    error=str(e),
                    exc_info=True,
                )

        # Step 3: Write PostgreSQL audit row
        if self._pg_session_factory is not None:
            try:
                await self._write_pg_audit(
                    scope=scope,
                    project=project,
                    revoked_by=revoked_by,
                    revoked_at=now,
                )
            except Exception as e:
                logger.error(
                    "consent_revoked_pg_audit_failed",
                    scope=scope,
                    error=str(e),
                    exc_info=True,
                )

        logger.info(
            "consent_revocation_complete",
            scope=scope,
            project=project,
            revoked_by=revoked_by,
        )

    async def _write_pg_audit(
        self,
        scope: str,
        project: str | None,
        revoked_by: str,
        revoked_at: datetime,
    ) -> None:
        """Write consent revocation audit row to PostgreSQL.

        Inserts a new row into consent.consent_ledger with status='revoked'.
        """
        from sqlalchemy import text

        # Import ConsentLedger ORM model
        from guinvere.memory.models import ConsentLedger

        async with self._pg_session_factory() as session:
            # Check if there's an existing granted row for this scope
            stmt = text("""
                SELECT id FROM consent.consent_ledger
                WHERE scope = :scope AND status = 'granted'
                ORDER BY granted_at DESC
                LIMIT 1
            """)
            result = await session.execute(stmt, {"scope": scope})
            existing_row = result.scalar_one_or_none()

            if existing_row:
                # Update existing row to revoked
                update_stmt = text("""
                    UPDATE consent.consent_ledger
                    SET status = 'revoked',
                        revoked_at = :revoked_at,
                        revocation_reason = :reason
                    WHERE id = :id
                """)
                await session.execute(
                    update_stmt,
                    {
                        "revoked_at": revoked_at,
                        "reason": f"Revoked by {revoked_by}",
                        "id": existing_row,
                    },
                )
            else:
                # Insert new revoked row (no prior grant found)
                import uuid
                new_row = ConsentLedger(
                    id=uuid.uuid4(),
                    scope=scope,
                    status="revoked",
                    granted_by=revoked_by,
                    granted_at=revoked_at,
                    revoked_at=revoked_at,
                    revocation_reason=f"Revoked by {revoked_by}",
                    evidence_hash="",
                )
                session.add(new_row)

            await session.commit()
            logger.info("consent_revoked_pg_audit_written", scope=scope)


# Singleton instance
_consent_handler: ConsentRevocationHandler | None = None


def get_consent_handler() -> ConsentRevocationHandler:
    """Get or create the global ConsentRevocationHandler singleton."""
    global _consent_handler
    if _consent_handler is None:
        _consent_handler = ConsentRevocationHandler()
    return _consent_handler
