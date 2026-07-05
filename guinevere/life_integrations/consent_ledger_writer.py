"""P22 consent ledger writer — grants/revokes consent scopes in PG.

Append-only writer for ``consent.consent_ledger``. P22 needs a way to grant
or revoke L2+ consent scopes so that downstream ``P22ConsentChecker``
(which queries the same table for ACTIVE rows) unlocks the actions.

Design:
- ``grant()`` INSERTs a row with ``status='ACTIVE'`` and ``granted_at=now()``.
- ``revoke()`` INSERTs a row with ``status='WITHDRAWN'`` (append-only — the
  checker's ``ORDER BY granted_at DESC LIMIT 1`` picks the newest matching
  row, so a newer WITHDRAWN row overrides a prior ACTIVE row).
- ``list_scopes()`` returns recent rows per (scope, project_id) for
  introspecting ledger state.
- Scope MUST be in the canonical P22 scope set (13 adapters' consent_scopes
  tuples); granting an unknown scope is rejected with ``ValueError``.
- After every grant/revoke an audit row is written via
  ``IntegrationAuditWriter`` (integration_id="consent", action="grant"/"revoke").

Forbidden:
- NO writes to Redis (surveillance domain owns that — see ``cmd_consent.py``).
- NO ``DELETE`` of prior ACTIVE rows on revoke — purely append-only.
- NO type suppression (``# type: ignore``, ``as any``).

Schema reference (e401bb5fd274 + p19_001 project_namespaces):
- ``id`` gen_random_uuid()
- ``consent_type`` TEXT NOT NULL
- ``scope`` TEXT NOT NULL
- ``status`` TEXT NOT NULL  ('ACTIVE' | 'WITHDRAWN' | 'PAUSED' | ...)
- ``granted_by`` TEXT NOT NULL
- ``granted_at`` TIMESTAMPTZ NOT NULL
- ``revoked_at`` TIMESTAMPTZ NULL
- ``revocation_reason`` TEXT NULL
- ``evidence_hash`` TEXT NOT NULL  (sha-256 of canonical row content)
- ``project_id`` UUID NULL
- + ClassificationMetaMixin metadata (classification='Internal', purpose='P22 consent ledger', source='integration_id')
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import text as sa_text

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Canonical P22 scope set — derived from the 13 adapters' consent_scopes.
# Computed once at import time so grant() validation is an O(1) set lookup.
# Hardcoded here (rather than dynamically imported) so a malformed adapter
# cannot add or remove scopes from the validation set silently.
# ---------------------------------------------------------------------------

_CANONICAL_P22_SCOPES: frozenset[str] = frozenset(
    {
        # filesystem
        "consent.filesystem.read",
        "consent.filesystem.write",
        "consent.filesystem.delete",
        # sourcecode (github)
        "consent.sourcecode.github.read",
        "consent.sourcecode.github.write",
        "consent.sourcecode.github.delete",
        # comms (gmail/discord/whatsapp/telegram)
        "consent.comms.gmail.read",
        "consent.comms.gmail.write",
        "consent.comms.gmail.delete",
        "consent.comms.discord.read",
        "consent.comms.discord.write",
        "consent.comms.discord.delete",
        "consent.comms.whatsapp.read",
        "consent.comms.whatsapp.write",
        "consent.comms.whatsapp.delete",
        "consent.comms.telegram.read",
        "consent.comms.telegram.write",
        "consent.comms.telegram.delete",
        # research (browser) — read/write only
        "consent.research.browser.read",
        "consent.research.browser.write",
        # ops (vps)
        "consent.ops.vps.read",
        "consent.ops.vps.write",
        "consent.ops.vps.delete",
        # finance
        "consent.finance.read",
        "consent.finance.write",
        "consent.finance.delete",
        # cloud (calendar/drive)
        "consent.cloud.calendar.read",
        "consent.cloud.calendar.write",
        "consent.cloud.calendar.delete",
        "consent.cloud.drive.read",
        "consent.cloud.drive.write",
        "consent.cloud.drive.delete",
        # notes (notion)
        "consent.notes.notion.read",
        "consent.notes.notion.write",
        "consent.notes.notion.delete",
        # memory
        "consent.memory.read",
        "consent.memory.write",
        "consent.memory.delete",
    }
)


# ---------------------------------------------------------------------------
# SQL — append-only INSERT against consent.consent_ledger
# ---------------------------------------------------------------------------

_INSERT_LEDGER_SQL = sa_text(
    "INSERT INTO consent.consent_ledger ("
    "    consent_type, scope, status, granted_by, granted_at,"
    "    revoked_at, revocation_reason, evidence_hash,"
    "    project_id, classification, purpose, source"
    ") VALUES ("
    "    :consent_type, :scope, :status, :granted_by, :granted_at,"
    "    :revoked_at, :revocation_reason, :evidence_hash,"
    "    :project_id, 'Internal', 'P22 consent ledger', 'P22 integration layer'"
    ")"
)


_SELECT_RECENT_SCOPE_SQL = sa_text(
    "SELECT DISTINCT ON (scope) scope, status, granted_by, granted_at, "
    "       revoked_at, project_id "
    "FROM consent.consent_ledger "
    "WHERE (:project_id IS NULL OR project_id = :project_id OR project_id IS NULL) "
    "ORDER BY scope, granted_at DESC"
)


def _isoformat_or_none(value: Any) -> str | None:
    """Format a datetime or pass through an already-ISO string; None if None."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _canonical_scopes() -> frozenset[str]:
    """Public accessor — for tests that want to assert on the set."""
    return _CANONICAL_P22_SCOPES


def _compute_evidence_hash(
    *,
    consent_type: str,
    scope: str,
    status: str,
    granted_by: str,
    granted_at: datetime,
    project_id: uuid.UUID | None,
) -> str:
    """Compute a deterministic sha-256 evidence_hash for the row content.

    Used to satisfy the NOT-NULL ``evidence_hash`` column without inventing
    arbitrary content. The hash covers the canonical row fields so two rows
    with the same content would still differ on ``granted_at`` (microsecond
    time-of-write), which is sufficient as a tamper-evidence anchor.

    Args:
        consent_type: e.g. ``"integration_action"``.
        scope: canonical scope string.
        status: ``"ACTIVE"`` or ``"WITHDRAWN"``.
        granted_by: principal identifier (``"faiz"``).
        granted_at: granted_at timestamp (timezone-aware).
        project_id: optional project UUID (``None`` → NULL).

    Returns:
        Lower-case hex sha-256 digest.
    """
    payload = {
        "consent_type": consent_type,
        "scope": scope,
        "status": status,
        "granted_by": granted_by,
        "granted_at": granted_at.isoformat(),
        "project_id": str(project_id) if project_id is not None else None,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ConsentLedgerWriter:
    """Append-only writer for ``consent.consent_ledger``.

    Writes ACTIVE rows on grant() and WITHDRAWN rows on revoke() — never
    DELETEs prior rows. Every grant/revoke also produces an audit row via
    the injected ``IntegrationAuditWriter``.

    Args:
        session_factory: SQLAlchemy async_sessionmaker (or callable
            returning an async context-manager session).
        audit_writer: ``IntegrationAuditWriter``-compatible object with
            ``async def log_action(...)`` (i.e. ``AuditLogger``-shaped).
            Pass ``None`` to disable audit emission (test/dev convenience
            ONLY — production MUST inject a real writer).
    """

    def __init__(
        self,
        session_factory: object,
        audit_writer: object | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._audit_writer = audit_writer

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def grant(
        self,
        scope: str,
        project_id: uuid.UUID | None = None,
        principal: str = "faiz",
        consent_type: str = "integration_action",
    ) -> dict[str, Any]:
        """Insert an ACTIVE row into consent_ledger.

        Args:
            scope: Consent scope (must be in the canonical P22 scope set).
            project_id: Optional project UUID for scoping.
            principal: Who is granting — defaults to ``"faiz"``.
            consent_type: Free-form type tag — defaults to
                ``"integration_action"``.

        Returns:
            Result dict with keys ``scope``, ``status``, ``granted_by``,
            ``granted_at``, ``project_id``, ``row_id``.

        Raises:
            ValueError: If ``scope`` is not in the canonical P22 set.
        """
        self._validate_scope(scope)

        granted_at = datetime.now(timezone.utc)
        evidence_hash = _compute_evidence_hash(
            consent_type=consent_type,
            scope=scope,
            status="ACTIVE",
            granted_by=principal,
            granted_at=granted_at,
            project_id=project_id,
        )

        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(
                    "INSERT INTO consent.consent_ledger ("
                    "    consent_type, scope, status, granted_by, granted_at,"
                    "    evidence_hash, project_id, classification, purpose, source"
                    ") VALUES ("
                    "    :consent_type, :scope, 'ACTIVE', :granted_by, :granted_at,"
                    "    :evidence_hash, :project_id,"
                    "    'Internal', 'P22 consent grant', 'integration_id=consent'"
                    ") RETURNING id"
                ),
                {
                    "consent_type": consent_type,
                    "scope": scope,
                    "granted_by": principal,
                    "granted_at": granted_at,
                    "evidence_hash": evidence_hash,
                    "project_id": str(project_id) if project_id else None,
                },
            )
            row = result.first()
            row_id = str(row[0]) if row and row[0] else None
            await session.commit()

        await self._emit_audit(
            action="grant",
            scope=scope,
            principal=principal,
            project_id=project_id,
            extra={"consent_type": consent_type, "row_id": row_id},
        )

        logger.info(
            "p22.consent_ledger_grant",
            scope=scope,
            principal=principal,
            project_id=str(project_id) if project_id else None,
            row_id=row_id,
        )

        return {
            "scope": scope,
            "status": "ACTIVE",
            "granted_by": principal,
            "granted_at": granted_at.isoformat(),
            "project_id": str(project_id) if project_id else None,
            "row_id": row_id,
        }

    async def revoke(
        self,
        scope: str,
        project_id: uuid.UUID | None = None,
        principal: str = "faiz",
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Insert a WITHDRAWN row into consent_ledger (append-only — never DELETE).

        Appends a new row with ``status='WITHDRAWN'`` and ``revoked_at`` set.
        The checker's ``ORDER BY granted_at DESC LIMIT 1`` will then pick
        this WITHDRAWN row over any older ACTIVE row for the same scope+project,
        so revocation takes effect immediately without touching prior rows.

        Args:
            scope: Consent scope (must be in the canonical P22 set).
            project_id: Optional project UUID for scoping.
            principal: Who is revoking — defaults to ``"faiz"``.
            reason: Optional revocation reason string (stored in
                ``revocation_reason``).

        Returns:
            Result dict with keys ``scope``, ``status``, ``granted_by``,
            ``granted_at``, ``revoked_at``, ``project_id``, ``row_id``.

        Raises:
            ValueError: If ``scope`` is not in the canonical P22 set.
        """
        self._validate_scope(scope)

        revoked_at = datetime.now(timezone.utc)
        evidence_hash = _compute_evidence_hash(
            consent_type="integration_action",
            scope=scope,
            status="WITHDRAWN",
            granted_by=principal,
            granted_at=revoked_at,  # row's granted_at = moment of revocation
            project_id=project_id,
        )

        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(
                    "INSERT INTO consent.consent_ledger ("
                    "    consent_type, scope, status, granted_by, granted_at,"
                    "    revoked_at, revocation_reason, evidence_hash,"
                    "    project_id, classification, purpose, source"
                    ") VALUES ("
                    "    'integration_action', :scope, 'WITHDRAWN', :granted_by,"
                    "    :granted_at, :revoked_at, :revocation_reason,"
                    "    :evidence_hash, :project_id,"
                    "    'Internal', 'P22 consent revoke', 'integration_id=consent'"
                    ") RETURNING id"
                ),
                {
                    "scope": scope,
                    "granted_by": principal,
                    "granted_at": revoked_at,
                    "revoked_at": revoked_at,
                    "revocation_reason": reason,
                    "evidence_hash": evidence_hash,
                    "project_id": str(project_id) if project_id else None,
                },
            )
            row = result.first()
            row_id = str(row[0]) if row and row[0] else None
            await session.commit()

        await self._emit_audit(
            action="revoke",
            scope=scope,
            principal=principal,
            project_id=project_id,
            extra={"reason": reason, "row_id": row_id},
        )

        logger.info(
            "p22.consent_ledger_revoke",
            scope=scope,
            principal=principal,
            project_id=str(project_id) if project_id else None,
            row_id=row_id,
        )

        return {
            "scope": scope,
            "status": "WITHDRAWN",
            "granted_by": principal,
            "granted_at": revoked_at.isoformat(),
            "revoked_at": revoked_at.isoformat(),
            "project_id": str(project_id) if project_id else None,
            "row_id": row_id,
        }

    async def list_scopes(
        self,
        project_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Return the most-recent row per scope (optionally project-scoped).

        Mirrors the checker's "newest row wins" semantics so callers can
        introspect the ledger the same way the runtime sees it.

        Args:
            project_id: Optional project UUID filter; ``None`` returns the
                union of scoped + global rows.

        Returns:
            List of dicts with keys ``scope``, ``status``, ``granted_by``,
            ``granted_at``, ``revoked_at``, ``project_id``.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                _SELECT_RECENT_SCOPE_SQL,
                {"project_id": str(project_id) if project_id else None},
            )
            rows = result.fetchall()

        out: list[dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "scope": r[0],
                    "status": r[1],
                    "granted_by": r[2],
                    "granted_at": _isoformat_or_none(r[3]),
                    "revoked_at": _isoformat_or_none(r[4]),
                    "project_id": str(r[5]) if r[5] else None,
                }
            )
        return out

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    async def _emit_audit(
        self,
        *,
        action: str,
        scope: str,
        principal: str,
        project_id: uuid.UUID | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Emit one audit row for every grant/revoke.

        Uses the ``IntegrationAuditWriter`` shape (``async write_event(dict)``).
        Falls back gracefully if no writer is injected.

        Args:
            action: ``"grant"`` or ``"revoke"``.
            scope: consent scope string.
            principal: who performed the grant/revoke.
            project_id: optional project UUID.
            extra: additional metadata to include.
        """
        if self._audit_writer is None:
            logger.info(
                "p22.consent_audit_skipped_no_writer",
                action=action,
                scope=scope,
            )
            return

        try:
            await self._audit_writer.log_action(
                integration_id="consent",
                provider="GuinevereConsentLedger",
                action=action,
                tier="L2_WRITE",
                project_id=project_id,
                result="success",
                actor_type="user",
                actor_id=principal,
                metadata={
                    "scope": scope,
                    "principal": principal,
                    **(extra or {}),
                },
            )
        except Exception as exc:
            # Audit must never block the consent write — log and move on
            # (mirrors the pattern in tests/p22/test_audit_db_writer.py).
            logger.error(
                "p22.consent_audit_write_failed",
                action=action,
                scope=scope,
                error=str(exc),
            )

    @staticmethod
    def _validate_scope(scope: str) -> None:
        """Reject scopes that are not in the canonical P22 set.

        Args:
            scope: scope string to validate.

        Raises:
            ValueError: if ``scope`` is not in ``_CANONICAL_P22_SCOPES``.
        """
        if scope not in _CANONICAL_P22_SCOPES:
            raise ValueError(
                f"Invalid P22 consent scope: {scope!r}. "
                f"Must be one of the canonical 38 scopes (13 adapters). "
                f"See _CANONICAL_P22_SCOPES in consent_ledger_writer.py."
            )


# Re-export for convenience / explicit audit_db_writer coupling
__all__ = [
    "ConsentLedgerWriter",
    "_CANONICAL_P22_SCOPES",
]
