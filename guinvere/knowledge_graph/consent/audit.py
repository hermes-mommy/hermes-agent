"""Knowledge Graph consent audit trail (P16-008).

Every consent-bearing mutation in the Knowledge Graph writes a row to
``memory.kg_consent_audit`` BEFORE the mutation lands. The trail is the
canonical record of:

* Token issuance (``CREATE_CONSENT_TOKEN``).
* Soft-delete tombstones (``TOMBSTONE_ENTITY`` / ``TOMBSTONE_EDGE``).
* Consent revocations and their cascades (``REVOKE_CONSENT``).
* Safety gate events (``HARD_STOP_TRIGGERED`` / ``DNR_DETECTED``).
* Failed consent checks (``CONSENT_CHECK_FAILED``).

Design contract:

* Audit writes use their OWN session/transaction -- they are NEVER
  entangled with the business mutation. If the audit write fails, the
  operation is aborted BEFORE the business mutation, so the audit
  trail can never lie by omission.
* Audit write failures raise :class:`KGConsentError` so that consent
  failures are never silent. Callers may choose to translate this
  into a user-facing message or escalation event.
* Read queries are best-effort: errors return an empty list so that a
  degraded audit table does not break the agent loop.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import TYPE_CHECKING, Protocol

from sqlalchemy import text

from guinvere.knowledge_graph.errors import KGConsentError

if TYPE_CHECKING:  # pragma: no cover -- typing-only
    from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event-type enum
# ---------------------------------------------------------------------------

CONSENT_EVENT_TYPES: frozenset[str] = frozenset({
    "TOMBSTONE_ENTITY",
    "TOMBSTONE_EDGE",
    "REVOKE_CONSENT",
    "CREATE_CONSENT_TOKEN",
    "HARD_STOP_TRIGGERED",
    "DNR_DETECTED",
    "CONSENT_CHECK_FAILED",
})
"""Canonical set of audit event types. Any value outside this set is
rejected by :meth:`ConsentAuditor.log_consent_event` with
:class:`KGConsentError` -- this prevents audit log pollution by
callers that mistype an event name."""


# ---------------------------------------------------------------------------
# Session factory protocol
# ---------------------------------------------------------------------------


class _SessionFactory(Protocol):
    """Minimal async session-factory protocol used by
    :class:`ConsentAuditor`."""

    def __call__(self) -> "AsyncSession":  # pragma: no cover -- structural
        ...


# ---------------------------------------------------------------------------
# ConsentAuditor
# ---------------------------------------------------------------------------


class ConsentAuditor:
    """Write-ahead audit trail for the Knowledge Graph consent layer."""

    def __init__(self, session_factory: _SessionFactory) -> None:
        if not session_factory:
            raise ValueError("session_factory is required")
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    async def log_consent_event(
        self,
        *,
        event_type: str,
        affected_entity_id: uuid.UUID | None,
        affected_edge_id: uuid.UUID | None,
        consent_token: str | None,
        actor: str,
        reason: str,
        metadata: dict[str, object] | None,
    ) -> uuid.UUID:
        """Insert a row into ``memory.kg_consent_audit``.

        Behaviour:

        * Uses its own session/transaction. The caller is expected to
          invoke this BEFORE the business mutation lands; once this
          method returns, the audit row is committed.
        * Raises :class:`KGConsentError` if the event_type is unknown
          or if the database write fails. The error is intentionally
          not caught -- audit failures are never silent.
        """
        if event_type not in CONSENT_EVENT_TYPES:
            raise KGConsentError(
                f"log_consent_event: unknown event_type={event_type!r}; "
                f"allowed={sorted(CONSENT_EVENT_TYPES)}"
            )
        if not actor or not actor.strip():
            raise KGConsentError("log_consent_event: actor is required")
        if not reason or not reason.strip():
            raise KGConsentError("log_consent_event: reason is required")

        audit_id = uuid.uuid4()
        # JSONB column expects a JSON string; SQLAlchemy text() with
        # bound params does not auto-serialise. We serialise here so
        # we never need to embed user input in the SQL string.
        if metadata is None:
            metadata_jsonb: str | None = None
        else:
            try:
                metadata_jsonb = json.dumps(metadata, default=str)
            except (TypeError, ValueError) as exc:
                raise KGConsentError(
                    f"log_consent_event: metadata is not JSON-serialisable: {exc}"
                ) from exc

        try:
            async with self._session_factory() as session:
                await session.execute(
                    text(
                        "INSERT INTO memory.kg_consent_audit ("
                        "    id, event_type, affected_entity_id, "
                        "    affected_edge_id, consent_token, actor, "
                        "    reason, metadata_jsonb, created_at"
                        ") VALUES ("
                        "    :id, :event_type, :affected_entity_id, "
                        "    :affected_edge_id, :consent_token, :actor, "
                        "    :reason, CAST(:metadata_jsonb AS JSONB), NOW()"
                        ")"
                    ),
                    {
                        "id": audit_id,
                        "event_type": event_type,
                        "affected_entity_id": affected_entity_id,
                        "affected_edge_id": affected_edge_id,
                        "consent_token": consent_token,
                        "actor": actor.strip(),
                        "reason": reason.strip(),
                        "metadata_jsonb": metadata_jsonb,
                    },
                )
                await session.commit()
        except KGConsentError:
            # Re-raise consent errors -- never swallow them.
            raise
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            # Audit write failure is ALWAYS escalated. We log context
            # (event_type, actor, audit_id) but the structured error
            # carries the exception so the caller can re-raise.
            logger.error(
                "ConsentAuditor.log_consent_event FAILED: audit_id=%s "
                "event_type=%s actor=%s reason=%r exc=%s",
                audit_id,
                event_type,
                actor.strip(),
                reason.strip(),
                exc,
            )
            raise KGConsentError(
                f"log_consent_event: audit write failed for "
                f"event_type={event_type!r}: {exc}"
            ) from exc
        return audit_id

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    async def get_audit_trail(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        consent_token: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        """Return audit rows filtered by ``entity_id`` and/or
        ``consent_token`` (either filter is optional; both may be
        combined). Ordered newest-first.

        On any database error the method returns an empty list -- a
        degraded audit table must not break the calling pipeline.
        """
        if limit <= 0:
            return []
        clauses: list[str] = []
        params: dict[str, object] = {"limit": int(limit)}
        if entity_id is not None:
            clauses.append("affected_entity_id = :entity_id")
            params["entity_id"] = entity_id
        if consent_token is not None:
            clauses.append("consent_token = :consent_token")
            params["consent_token"] = consent_token
        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        # The LIMIT is bound as a parameter so a malicious caller
        # cannot inject SQL. The column list is a constant.
        sql = (
            "SELECT id, event_type, affected_entity_id, affected_edge_id, "
            "       consent_token, actor, reason, metadata_jsonb, created_at "
            "FROM memory.kg_consent_audit "
            f"{where_sql} "
            "ORDER BY created_at DESC "
            "LIMIT :limit"
        )
        try:
            async with self._session_factory() as session:
                rows = (
                    await session.execute(text(sql), params)
                ).all()
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception(
                "ConsentAuditor.get_audit_trail failed: entity_id=%s "
                "consent_token=%s limit=%s exc=%s",
                entity_id,
                consent_token,
                limit,
                exc,
            )
            return []
        results: list[dict[str, object]] = []
        for row in rows:
            if row is None:
                continue
            results.append(
                {
                    "id": row[0],
                    "event_type": row[1],
                    "affected_entity_id": row[2],
                    "affected_edge_id": row[3],
                    "consent_token": row[4],
                    "actor": row[5],
                    "reason": row[6],
                    "metadata": row[7],
                    "created_at": row[8],
                }
            )
        return results

    # ------------------------------------------------------------------
    # Integrity check
    # ------------------------------------------------------------------

    async def verify_audit_integrity(self) -> dict[str, object]:
        """Check the audit trail for orphaned tombstones.

        An *orphan* is a row in ``memory.kg_entities`` or
        ``memory.kg_edges`` that is tombstoned (``is_tombstoned = TRUE``)
        but has NO matching ``TOMBSTONE_*`` event in
        ``memory.kg_consent_audit``. This is a fail-closed integrity
        check: if any orphan is found, the result is ``{"ok": False}``
        and the operator is expected to investigate.

        Returns a dict with the following keys:

        * ``ok`` -- ``True`` iff no orphans were detected.
        * ``orphaned_entities`` -- list of orphan entity IDs.
        * ``orphaned_edges`` -- list of orphan edge IDs.
        * ``checked_at`` -- timestamp of the check (UTC).
        """
        from datetime import datetime, timezone

        checked_at = datetime.now(timezone.utc)
        result: dict[str, object] = {
            "ok": True,
            "orphaned_entities": [],
            "orphaned_edges": [],
            "checked_at": checked_at,
        }
        try:
            async with self._session_factory() as session:
                # Tombstoned entities with no matching TOMBSTONE_ENTITY.
                entity_rows = (
                    await session.execute(
                        text(
                            "SELECT e.id "
                            "FROM memory.kg_entities e "
                            "WHERE e.is_tombstoned = TRUE "
                            "  AND NOT EXISTS ( "
                            "    SELECT 1 FROM memory.kg_consent_audit a "
                            "    WHERE a.event_type = 'TOMBSTONE_ENTITY' "
                            "      AND a.affected_entity_id = e.id "
                            "  )"
                        )
                    )
                ).all()
                orphaned_entities = [row[0] for row in entity_rows if row and row[0]]
                # Tombstoned edges with no matching TOMBSTONE_EDGE.
                edge_rows = (
                    await session.execute(
                        text(
                            "SELECT e.id "
                            "FROM memory.kg_edges e "
                            "WHERE e.is_tombstoned = TRUE "
                            "  AND NOT EXISTS ( "
                            "    SELECT 1 FROM memory.kg_consent_audit a "
                            "    WHERE a.event_type = 'TOMBSTONE_EDGE' "
                            "      AND a.affected_edge_id = e.id "
                            "  )"
                        )
                    )
                ).all()
                orphaned_edges = [row[0] for row in edge_rows if row and row[0]]
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception(
                "ConsentAuditor.verify_audit_integrity failed: %s", exc
            )
            result["ok"] = False
            result["error"] = repr(exc)
            return result
        if orphaned_entities or orphaned_edges:
            result["ok"] = False
            result["orphaned_entities"] = orphaned_entities
            result["orphaned_edges"] = orphaned_edges
        return result


# ---------------------------------------------------------------------------
# Re-export for typing helpers used by other modules
# ---------------------------------------------------------------------------

__all__: list[str] = [
    "CONSENT_EVENT_TYPES",
    "ConsentAuditor",
]
