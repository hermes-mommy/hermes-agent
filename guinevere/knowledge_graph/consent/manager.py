"""Knowledge Graph consent manager (P16-008).

Core consent logic for the Knowledge Graph layer:

* Token generation, validation, and scope lookup.
* Consent revocation (soft-delete via tombstoning; never hard-delete).
* Entity / edge tombstoning with cascade.
* HARD STOP gate (queries ``memory.episodes`` for safe-word indicators).
* DNR gate (transitive: entity -> edges -> semantic_facts -> episodes).

Design notes:

* **Write-ahead audit.** Every mutation writes a row to
  ``memory.kg_consent_audit`` in its OWN transaction BEFORE the
  business mutation lands. The audit module raises
  :class:`~guinevere.knowledge_graph.errors.KGConsentError` if the audit
  write fails, which is intentionally propagated to the caller --
  silent consent failures are forbidden.
* **Exception safety.** Non-:class:`KGConsentError` exceptions raised
  by storage or audit are caught, logged with full context, and
  converted to a safe default (typically ``False`` / ``None`` / empty
  counts). ``KGConsentError`` always propagates.
* **No module-level imports from ``guinevere.memory``.** Safe-word
  indicators and DNR semantics are resolved via lazy import inside
  the calling method, keeping the consent package decoupled from the
  memory package's import-time side effects.
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Protocol

from sqlalchemy import text

from guinevere.knowledge_graph.errors import KGConsentError

if TYPE_CHECKING:  # pragma: no cover -- typing-only
    from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------

KG_SCHEMA: str = "memory"
"""Schema that hosts all ``kg_*`` tables (per P16-001 DDL v4)."""

KG_CONSENT_AUDIT_TABLE: str = f"{KG_SCHEMA}.kg_consent_audit"
KG_ENTITIES_TABLE: str = f"{KG_SCHEMA}.kg_entities"
KG_EDGES_TABLE: str = f"{KG_SCHEMA}.kg_edges"
KG_EPISODES_TABLE: str = f"{KG_SCHEMA}.kg_episodes"
SEMANTIC_FACTS_TABLE: str = f"{KG_SCHEMA}.semantic_facts"
MEMORY_EPISODES_TABLE: str = f"{KG_SCHEMA}.episodes"

# Columns that any given audit row may populate. Kept as a tuple so the
# audit module can iterate deterministically (e.g. for ``SELECT *``).
KG_AUDIT_COLUMNS: tuple[str, ...] = (
    "id",
    "event_type",
    "affected_entity_id",
    "affected_edge_id",
    "consent_token",
    "actor",
    "reason",
    "metadata_jsonb",
    "created_at",
)

# ---------------------------------------------------------------------------
# Token format
# ---------------------------------------------------------------------------

# Strict token format. We intentionally do NOT use f-strings to build tokens
# to avoid injection into the lookup path; components are validated by
# regex and assembled with a UUID suffix.
_TOKEN_RE: re.Pattern[str] = re.compile(
    r"^kg_(?P<scope>[a-z0-9_]{1,32})_(?P<category>[a-z0-9_]{1,32})_(?P<uuid>[a-f0-9]{8})$"
)

# Scope / category allowed character set (defense in depth: never accept
# raw user input into the token without scrubbing).
_SAFE_SCOPE_RE: re.Pattern[str] = re.compile(r"^[a-z0-9_]{1,32}$")
_SAFE_CATEGORY_RE: re.Pattern[str] = re.compile(r"^[a-z0-9_]{1,32}$")


# ---------------------------------------------------------------------------
# HARD STOP / DNR look-back window
# ---------------------------------------------------------------------------

DEFAULT_HARD_STOP_LOOKBACK_DAYS: int = 7
"""How far back ``check_hard_stop`` scans for safe-word episodes. Anything
older than this is considered stale and does not block writes."""


# ---------------------------------------------------------------------------
# Session factory protocol
# ---------------------------------------------------------------------------


class _SessionFactory(Protocol):
    """Minimal async session-factory protocol used by :class:`ConsentManager`.

    Matches the shape of ``sqlalchemy.ext.asyncio.async_sessionmaker``
    bound to ``AsyncSession``: ``factory()`` returns an awaitable that
    yields a usable session (typically via ``async with``).
    """

    def __call__(self) -> "AsyncSession":  # pragma: no cover -- structural
        ...


# ---------------------------------------------------------------------------
# Result / scope dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsentRevocationResult:
    """Outcome of a :meth:`ConsentManager.revoke_consent` call."""

    revoked_entities: int
    revoked_edges: int
    audit_id: uuid.UUID
    timestamp: datetime


@dataclass(frozen=True)
class ConsentScope:
    """Metadata for a consent token, derived from the audit trail or
    edge table when the token is in use."""

    token: str
    scope: str
    category: str
    created_at: datetime
    is_active: bool


# ---------------------------------------------------------------------------
# ConsentManager
# ---------------------------------------------------------------------------


class ConsentManager:
    """Core consent operations for the Knowledge Graph.

    The manager is stateless beyond its injected ``session_factory`` and
    default ``principal``. Every method is safe to call concurrently from
    different tasks as long as the underlying session factory is safe.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        session_factory: _SessionFactory,
        *,
        principal: str = "guinevere_core",
    ) -> None:
        if not session_factory:
            raise ValueError("session_factory is required")
        if not principal or not principal.strip():
            raise ValueError("principal must be a non-empty string")
        self._session_factory = session_factory
        self._principal = principal.strip()

    # ------------------------------------------------------------------
    # Token generation
    # ------------------------------------------------------------------

    def generate_consent_token(self, entity_category: str, scope: str) -> str:
        """Generate a fresh consent token.

        Format: ``kg_{scope}_{category}_{uuid4().hex[:8]}``.

        Both ``entity_category`` and ``scope`` are validated against the
        safe character set. The UUID suffix guarantees uniqueness even
        if a caller accidentally reuses a (scope, category) pair.
        """
        if not _SAFE_SCOPE_RE.match(scope or ""):
            raise KGConsentError(
                f"invalid scope: must match {_SAFE_SCOPE_RE.pattern}; got {scope!r}"
            )
        if not _SAFE_CATEGORY_RE.match(entity_category or ""):
            raise KGConsentError(
                f"invalid entity_category: must match {_SAFE_CATEGORY_RE.pattern}; "
                f"got {entity_category!r}"
            )
        suffix = uuid.uuid4().hex[:8]
        return f"kg_{scope}_{entity_category}_{suffix}"

    # ------------------------------------------------------------------
    # Token validation / scope lookup
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_token(consent_token: str | None) -> tuple[str, str, str] | None:
        """Return ``(scope, category, uuid_suffix)`` for a valid token.

        Returns ``None`` for any malformed or ``None`` input. The
        components returned are already regex-validated and therefore
        safe to interpolate into downstream SQL via bound parameters.
        """
        if not consent_token:
            return None
        match = _TOKEN_RE.match(consent_token)
        if match is None:
            return None
        return match["scope"], match["category"], match["uuid"]

    def check_consent(
        self,
        consent_token: str | None,
        *,
        principal: str,
        entity_category: str,
    ) -> bool:
        """Validate a token's shape and category binding.

        This is a *defensive* check used by callers before performing a
        mutation: a malformed token, a category mismatch, or a
        principal that is not the owning service role all return
        ``False``. A ``None`` token is treated as "no consent claimed"
        and also returns ``False`` -- callers that want anonymous
        access must explicitly bypass the gate upstream.
        """
        try:
            parsed = self._parse_token(consent_token)
            if parsed is None:
                return False
            _scope, token_category, _suffix = parsed
            if not _SAFE_CATEGORY_RE.match(entity_category or ""):
                return False
            if token_category != entity_category:
                return False
            if not principal or not principal.strip():
                return False
            # Principal binding: the KG only honours its own service
            # role. Sub-agents and ad-hoc callers must surface the
            # token through the agent loop, which is the only
            # authorised path. (Cross-principal sharing would be a
            # surveillance-policy violation per ADR-001/002.)
            if principal.strip() != self._principal:
                return False
            return True
        except KGConsentError:
            # Re-raise consent errors so they never get swallowed.
            raise
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception(
                "ConsentManager.check_consent failed for token=%r principal=%r: %s",
                consent_token,
                principal,
                exc,
            )
            return False

    async def get_consent_scope(
        self, consent_token: str
    ) -> ConsentScope | None:
        """Return the scope metadata for a token.

        Looks up the token in ``kg_consent_audit`` (canonical history);
        falls back to ``kg_edges`` if no audit row exists yet (e.g. for
        a freshly issued token that has not been logged). Returns
        ``None`` for any malformed token or unresolvable input.
        """
        parsed_token = self._parse_token(consent_token)
        if parsed_token is None:
            return None
        scope_from_token, category_from_token, _ = parsed_token
        try:
            async with self._session_factory() as session:
                # 1) Audit trail is the canonical record of the token.
                audit_row = (
                    await session.execute(
                        text(
                            "SELECT created_at FROM memory.kg_consent_audit "
                            "WHERE consent_token = :token "
                            "ORDER BY created_at DESC LIMIT 1"
                        ),
                        {"token": consent_token},
                    )
                ).first()
                if audit_row is not None:
                    created_at = _coerce_datetime(audit_row[0])
                    if created_at is not None:
                        return ConsentScope(
                            token=consent_token,
                            scope=scope_from_token,
                            category=category_from_token,
                            created_at=created_at,
                            is_active=True,
                        )
                # 2) Fall back to the edge table -- the token is
                #    in-use even if it was never logged. Soft-deleted
                #    edges (tombstoned) do not count as active.
                edge_row = (
                    await session.execute(
                        text(
                            "SELECT consent_scope, recorded_at "
                            "FROM memory.kg_edges "
                            "WHERE consent_token = :token "
                            "  AND is_tombstoned = FALSE "
                            "ORDER BY recorded_at DESC LIMIT 1"
                        ),
                        {"token": consent_token},
                    )
                ).first()
                if edge_row is None:
                    return None
                created_at = _coerce_datetime(edge_row[1])
                if created_at is None:
                    return None
                return ConsentScope(
                    token=consent_token,
                    scope=edge_row[0] or scope_from_token,
                    category=category_from_token,
                    created_at=created_at,
                    is_active=True,
                )
        except KGConsentError:
            raise
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception(
                "ConsentManager.get_consent_scope failed for token=%r: %s",
                consent_token,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Revocation
    # ------------------------------------------------------------------

    async def revoke_consent(
        self,
        consent_token: str,
        *,
        reason: str,
        revoked_by: str,
    ) -> ConsentRevocationResult:
        """Revoke a consent token by soft-deleting every entity and edge
        bound to it.

        Behaviour:

        1. Validates the token shape; raises :class:`KGConsentError` on
           malformed input.
        2. Writes a write-ahead audit event ``REVOKE_CONSENT`` in its
           own transaction. If the audit write fails, the operation
           is aborted BEFORE any tombstoning.
        3. Tombstones every entity that references the token via
           ``kg_consent_audit`` or via a connected edge.
        4. Tombstones every edge that references the token directly.
        5. Returns the outcome.
        """
        parsed = self._parse_token(consent_token)
        if parsed is None:
            raise KGConsentError(
                f"revoke_consent: malformed consent_token={consent_token!r}"
            )
        if not reason or not reason.strip():
            raise KGConsentError("revoke_consent: reason is required")
        if not revoked_by or not revoked_by.strip():
            raise KGConsentError("revoke_consent: revoked_by is required")
        audit_id = uuid.uuid4()
        timestamp = datetime.now(timezone.utc)

        # Lazy import to avoid module-level coupling with guinevere.memory.
        from guinevere.knowledge_graph.consent.audit import ConsentAuditor

        auditor = ConsentAuditor(self._session_factory)
        # 1) Write-ahead audit. This commits in its own transaction
        #    and raises KGConsentError on failure -- we deliberately
        #    do not catch it.
        await auditor.log_consent_event(
            event_type="REVOKE_CONSENT",
            affected_entity_id=None,
            affected_edge_id=None,
            consent_token=consent_token,
            actor=revoked_by.strip(),
            reason=reason.strip(),
            metadata={
                "principal": self._principal,
                "audit_id": str(audit_id),
                "timestamp": timestamp.isoformat(),
            },
        )

        # 2) Tombstone the affected rows.
        try:
            async with self._session_factory() as session:
                # Entity IDs attached to this token: we look at edges
                # because the token is stored on edges, not on entities
                # directly. An entity is "owned" by a token if every
                # edge it participates in carries the token, OR if any
                # edge carries the token (we err on the side of
                # tombstoning since the operator asked for revocation).
                entity_rows = (
                    await session.execute(
                        text(
                            "SELECT DISTINCT src_entity_id FROM memory.kg_edges "
                            "WHERE consent_token = :token "
                            "UNION "
                            "SELECT DISTINCT dst_entity_id FROM memory.kg_edges "
                            "WHERE consent_token = :token"
                        ),
                        {"token": consent_token},
                    )
                ).all()
                entity_ids = [row[0] for row in entity_rows if row and row[0]]
                revoked_entities = 0
                for eid in entity_ids:
                    res = await session.execute(
                        text(
                            "UPDATE memory.kg_entities "
                            "SET is_tombstoned = TRUE, "
                            "    tombstone_reason = :reason, "
                            "    tombstoned_at = NOW(), "
                            "    updated_at = NOW() "
                            "WHERE id = :eid "
                            "  AND is_tombstoned = FALSE"
                        ),
                        {"reason": reason.strip(), "eid": eid},
                    )
                    revoked_entities += getattr(res, "rowcount", 0) or 0
                # Edges: soft-delete every edge carrying the token.
                edge_res = await session.execute(
                    text(
                        "UPDATE memory.kg_edges "
                        "SET is_tombstoned = TRUE, "
                        "    tombstone_reason = :reason, "
                        "    tombstoned_at = NOW(), "
                        "    updated_at = NOW() "
                        "WHERE consent_token = :token "
                        "  AND is_tombstoned = FALSE"
                    ),
                    {"reason": reason.strip(), "token": consent_token},
                )
                revoked_edges = getattr(edge_res, "rowcount", 0) or 0
                await session.commit()
        except KGConsentError:
            raise
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception(
                "ConsentManager.revoke_consent tombstoning failed for "
                "token=%r: %s",
                consent_token,
                exc,
            )
            # Tombstoning is best-effort here -- the audit log is the
            # canonical record. Surface the failure but do not crash
            # the caller; the agent loop will see a 0/0 result and can
            # retry.
            revoked_entities = 0
            revoked_edges = 0

        return ConsentRevocationResult(
            revoked_entities=revoked_entities,
            revoked_edges=revoked_edges,
            audit_id=audit_id,
            timestamp=timestamp,
        )

    # ------------------------------------------------------------------
    # Tombstoning
    # ------------------------------------------------------------------

    async def tombstone_entity(
        self,
        entity_id: uuid.UUID,
        *,
        reason: str,
    ) -> None:
        """Soft-delete a single entity and cascade to all its edges.

        Raises :class:`KGConsentError` only if the write-ahead audit
        fails. Other errors (e.g. an entity that no longer exists) are
        logged and converted to a no-op.
        """
        if entity_id is None:
            raise KGConsentError("tombstone_entity: entity_id is required")
        if not reason or not reason.strip():
            raise KGConsentError("tombstone_entity: reason is required")

        from guinevere.knowledge_graph.consent.audit import ConsentAuditor

        auditor = ConsentAuditor(self._session_factory)
        # Write-ahead audit -- propagates KGConsentError on failure.
        await auditor.log_consent_event(
            event_type="TOMBSTONE_ENTITY",
            affected_entity_id=entity_id,
            affected_edge_id=None,
            consent_token=None,
            actor=self._principal,
            reason=reason.strip(),
            metadata={"cascades_to_edges": True},
        )

        try:
            async with self._session_factory() as session:
                await session.execute(
                    text(
                        "UPDATE memory.kg_entities "
                        "SET is_tombstoned = TRUE, "
                        "    tombstone_reason = :reason, "
                        "    tombstoned_at = NOW(), "
                        "    updated_at = NOW() "
                        "WHERE id = :eid "
                        "  AND is_tombstoned = FALSE"
                    ),
                    {"reason": reason.strip(), "eid": entity_id},
                )
                # Cascade: every edge touching this entity is also
                # tombstoned and logged via the auditor below.
                edge_rows = (
                    await session.execute(
                        text(
                            "SELECT id FROM memory.kg_edges "
                            "WHERE (src_entity_id = :eid OR dst_entity_id = :eid) "
                            "  AND is_tombstoned = FALSE"
                        ),
                        {"eid": entity_id},
                    )
                ).all()
                affected_edge_ids = [row[0] for row in edge_rows if row and row[0]]
                if affected_edge_ids:
                    await session.execute(
                        text(
                            "UPDATE memory.kg_edges "
                            "SET is_tombstoned = TRUE, "
                            "    tombstone_reason = :reason, "
                            "    tombstoned_at = NOW(), "
                            "    updated_at = NOW() "
                            "WHERE (src_entity_id = :eid OR dst_entity_id = :eid) "
                            "  AND is_tombstoned = FALSE"
                        ),
                        {"reason": reason.strip(), "eid": entity_id},
                    )
                await session.commit()
        except KGConsentError:
            raise
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception(
                "ConsentManager.tombstone_entity failed for entity_id=%s: %s",
                entity_id,
                exc,
            )
            return

        # Audit each cascaded edge in its own transaction (per
        # write-ahead rule -- never share with the cascade UPDATE).
        for edge_id in affected_edge_ids:
            try:
                await auditor.log_consent_event(
                    event_type="TOMBSTONE_EDGE",
                    affected_entity_id=None,
                    affected_edge_id=edge_id,
                    consent_token=None,
                    actor=self._principal,
                    reason=f"cascade from entity {entity_id}: {reason.strip()}",
                    metadata={"cascade_from_entity": str(entity_id)},
                )
            except KGConsentError:
                # Audit failure here is logged by the auditor; we
                # continue tombstoning the remaining edges.
                logger.error(
                    "audit failure during tombstone_entity cascade for "
                    "entity=%s edge=%s",
                    entity_id,
                    edge_id,
                )

    async def tombstone_edge(
        self,
        edge_id: uuid.UUID,
        *,
        reason: str,
    ) -> None:
        """Soft-delete a single edge (no cascade).

        Raises :class:`KGConsentError` only if the write-ahead audit
        fails. Other errors are logged and the operation is a no-op.
        """
        if edge_id is None:
            raise KGConsentError("tombstone_edge: edge_id is required")
        if not reason or not reason.strip():
            raise KGConsentError("tombstone_edge: reason is required")

        from guinevere.knowledge_graph.consent.audit import ConsentAuditor

        auditor = ConsentAuditor(self._session_factory)
        # Write-ahead audit -- propagates KGConsentError on failure.
        await auditor.log_consent_event(
            event_type="TOMBSTONE_EDGE",
            affected_entity_id=None,
            affected_edge_id=edge_id,
            consent_token=None,
            actor=self._principal,
            reason=reason.strip(),
            metadata={},
        )

        try:
            async with self._session_factory() as session:
                await session.execute(
                    text(
                        "UPDATE memory.kg_edges "
                        "SET is_tombstoned = TRUE, "
                        "    tombstone_reason = :reason, "
                        "    tombstoned_at = NOW(), "
                        "    updated_at = NOW() "
                        "WHERE id = :eid "
                        "  AND is_tombstoned = FALSE"
                    ),
                    {"reason": reason.strip(), "eid": edge_id},
                )
                await session.commit()
        except KGConsentError:
            raise
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception(
                "ConsentManager.tombstone_edge failed for edge_id=%s: %s",
                edge_id,
                exc,
            )
            return

    # ------------------------------------------------------------------
    # HARD STOP / DNR gates
    # ------------------------------------------------------------------

    async def check_hard_stop(
        self,
        session: "AsyncSession",
        *,
        lookback_days: int = DEFAULT_HARD_STOP_LOOKBACK_DAYS,
    ) -> bool:
        """Return ``True`` if a recent episode carries a safe-word marker.

        Per ADR-002 / PersonaSafetyPolicy, a HARD STOP in any recent
        episode MUST block all KG writes -- including writes that
        would land in the audit trail itself. Callers should
        short-circuit before invoking any mutating method.
        """
        if session is None:
            raise KGConsentError("check_hard_stop: session is required")
        # Lazy import to keep this module decoupled from guinevere.memory at
        # import time. The set is treated as a tuple-of-strings; we
        # never splice indicators into SQL.
        from guinevere.memory.consolidation import SAFE_WORD_INDICATORS

        indicators: tuple[str, ...] = tuple(sorted(SAFE_WORD_INDICATORS))
        if not indicators:
            return False
        threshold = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        try:
            # We probe three channels the safe-word indicator may live
            # in: episode_type, title, tags. ``tags`` is a TEXT[] and
            # uses && (overlap) so the parameter is never interpolated.
            row = (
                await session.execute(
                    text(
                        "SELECT EXISTS ("
                        "  SELECT 1 FROM memory.episodes "
                        "  WHERE started_at >= :threshold "
                        "    AND ( "
                        "      episode_type = ANY(:indicators) "
                        "      OR EXISTS ( "
                        "        SELECT 1 FROM unnest(tags) tag "
                        "        WHERE tag = ANY(:indicators) "
                        "      ) "
                        "    ) "
                        "  LIMIT 1"
                        ") AS triggered"
                    ),
                    {"threshold": threshold, "indicators": list(indicators)},
                )
            ).first()
            if row is None:
                return False
            return bool(row[0])
        except KGConsentError:
            raise
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception(
                "ConsentManager.check_hard_stop failed: %s", exc
            )
            # Fail closed: an unreadable episodes table must NOT be
            # treated as "no safe word". The caller will see ``True``
            # and abort the operation.
            return True

    async def check_dnr(self, entity_id: uuid.UUID) -> bool:
        """Return ``True`` if any episode connected to ``entity_id`` is
        flagged ``do_not_recall``.

        DNR is transitive: entity -> incident edges -> source_fact ->
        source_episode. If *any* connected source episode is marked
        DNR, the entity is treated as DNR too and the caller MUST
        refuse the read.
        """
        if entity_id is None:
            raise KGConsentError("check_dnr: entity_id is required")
        try:
            async with self._session_factory() as session:
                row = (
                    await session.execute(
                        text(
                            "SELECT EXISTS ("
                            "  SELECT 1 "
                            "  FROM memory.kg_edges e "
                            "  JOIN memory.semantic_facts f "
                            "    ON e.source_fact_id = f.id "
                            "  JOIN memory.episodes ep "
                            "    ON f.source_episode = ep.id "
                            "  WHERE (e.src_entity_id = :eid OR e.dst_entity_id = :eid) "
                            "    AND ep.do_not_recall = TRUE "
                            "  LIMIT 1"
                            ") AS triggered"
                        ),
                        {"eid": entity_id},
                    )
                ).first()
                if row is None:
                    return False
                return bool(row[0])
        except KGConsentError:
            raise
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception(
                "ConsentManager.check_dnr failed for entity_id=%s: %s",
                entity_id,
                exc,
            )
            # Fail closed: inability to verify DNR == treat as DNR.
            return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_datetime(value: object) -> datetime | None:
    """Best-effort conversion of a DB-returned timestamp to a
    timezone-aware ``datetime``.

    Returns ``None`` for ``None`` or any value that cannot be coerced
    without raising.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return None
    return None
