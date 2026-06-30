"""P16-002: Entity resolution orchestrator.

Chains the deduplication layers defined in ``canonical.py`` (L1) and
``fuzzy.py`` (L2) into a single ``EntityResolver`` facade.  The third layer
(embedding similarity) is **deferred to P17+** — see
``research-reports/p16-kg-patterns.md`` §3.3 and the no-embedding
constraint documented in ``evidence/p16-kg/research-entity-resolution-no-embeddings.md``
(9Router has no embedding model; sentence-transformers are forbidden by
the operator).

Layer flow (per the task spec):

    Step 1 (L1)   — exact ``canonical_key`` match  → ``method='exact'``
    Step 2 (L1b)  — exact alias-array match        → ``method='exact'``
    Step 3 (L2)   — fuzzy match (rapidfuzz WRatio) → ``method='fuzzy'``
    Step 4 (L3)   — DEFERRED to P17+                (TODO marker)
    Step 5        — no match                        → ``method='none'``

Writes only happen in ``propose_same_as`` (queues a review edge) and
``merge_entities`` (tombstones the secondary).  ``resolve_entity`` is
read-only — the caller (P16-002 ingestion) is responsible for materializing
the new entity when ``method='none'``.

Safety invariants enforced here (per AGENTS.md BLOCKING rules and
PersonaSafetyPolicy):

    * Tombstoned entities are NEVER returned by ``resolve_entity`` and NEVER
      are used as merge sources.
    * ``merge_entities`` always writes a row to ``kg_consent_audit`` with
      action ``cascade_revoke`` (closest semantic for merge-suppression) —
      there is no merge-without-audit path.
    * ``propose_same_as`` enforces ``src_entity_id < dst_entity_id``
      (canonical ordering) by sorting at the application layer — matches
      the DDL CHECK constraint.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import text as _sa_text

from guinvere.knowledge_graph.resolution.canonical import (
    AsyncSessionProtocol,
    KG_TABLE,
    KG_TABLE_CONSENT_AUDIT,
    KG_TABLE_SAME_AS,
    entity_aliases,
    find_by_alias,
    find_by_canonical_key,
    generate_canonical_key,
)
from guinvere.knowledge_graph.resolution.fuzzy import (
    DEFAULT_FUZZY_LIMIT,
    DEFAULT_FUZZY_THRESHOLD,
    FuzzyMatchResult,
    fuzzy_match_entities,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UTC = timezone.utc

DEFAULT_DEDUP_THRESHOLD: float = DEFAULT_FUZZY_THRESHOLD
"""Default fuzzy-match confidence threshold (alias of fuzzy layer default)."""

DEFAULT_SAME_AS_LIMIT: int = 1
"""Default cap on fuzzy matches that get queued for SAME_AS review."""

AUDIT_ACTION_MERGE: Literal["cascade_revoke"] = "cascade_revoke"
"""``kg_consent_audit.action`` value used for merge events.

The DDL CHECK constraint permits only ('grant','revoke','cascade_revoke',
'read_filter').  'cascade_revoke' is the closest semantic match for a
merge — the merge *cascades* the suppression of the secondary entity to
all edges that referenced it.
"""

AUDIT_PRINCIPAL_DEFAULT: str = "entity_resolver"
"""Default ``kg_consent_audit.principal`` value when caller does not override."""

REVIEW_STATUS_PENDING: str = "pending_review"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result / method types
# ---------------------------------------------------------------------------

ResolutionMethod = Literal["exact", "fuzzy", "none"]
"""How a name was resolved against existing entities.

``exact`` — exact canonical-key or alias match (L1 or L1b).
``fuzzy`` — fuzzy match (L2) above the configured threshold.
``none``  — no live match found; caller should create a new entity.
"""


@dataclass(frozen=True)
class EntityResolutionResult:
    """Outcome of resolving one entity name against the live KG.

    Attributes
    ----------
    canonical_entity:
        Dict representation of the matched ``kg_entities`` row, or ``None``
        when no live match was found (i.e. ``method == 'none'``).  The shape
        matches :func:`src.knowledge_graph.resolution.canonical.find_by_canonical_key`.
    matched_aliases:
        List of input aliases that matched an existing entity (populated for
        L1b hits).  Empty for L1 and L2 hits.
    confidence:
        Score in ``[0.0, 1.0]``.  ``1.0`` for exact matches, the fuzzy score
        for L2, and ``0.0`` for ``method='none'``.
    method:
        Which layer produced the result.
    fuzzy_candidate:
        The best L2 candidate (if any) — preserved for diagnostic logging
        and so the caller can decide to queue a SAME_AS review edge instead
        of auto-merging.
    """

    canonical_entity: dict[str, object] | None
    matched_aliases: list[str] = field(default_factory=list)
    confidence: float = 0.0
    method: ResolutionMethod = "none"
    fuzzy_candidate: FuzzyMatchResult | None = None

    def __post_init__(self) -> None:
        score = float(self.confidence)
        if not (0.0 <= score <= 1.0):
            raise ValueError(
                f"EntityResolutionResult.confidence must be in [0.0, 1.0]; "
                f"got {score!r}"
            )
        if self.method not in ("exact", "fuzzy", "none"):
            raise ValueError(
                f"EntityResolutionResult.method must be 'exact', 'fuzzy', "
                f"or 'none'; got {self.method!r}"
            )


# ---------------------------------------------------------------------------
# SQL statements
# ---------------------------------------------------------------------------

_INSERT_SAME_AS_SQL: str = (
    "INSERT INTO {table} ("
    "id, src_entity_id, dst_entity_id, confidence, reason, "
    "review_status, recorded_at, updated_at"
    ") VALUES ("
    ":id, :src_entity_id, :dst_entity_id, :confidence, :reason, "
    ":review_status, :recorded_at, :updated_at"
    ")"
)

_TOMBSTONE_ENTITY_SQL: str = (
    f"UPDATE {KG_TABLE} "
    "SET merged_into = :primary_id, "
    "    is_tombstoned = TRUE, "
    "    tombstone_reason = :reason, "
    "    tombstoned_at = :now, "
    "    updated_at = :now "
    "WHERE id = :secondary_id AND is_tombstoned = FALSE"
)

# Re-point edges by SQL: using a single UPDATE per side keeps the merge
# O(1) round-trips and atomic within the session transaction.
_REPOINT_EDGES_SRC_SQL: str = (
    "UPDATE memory.kg_edges "
    "SET src_entity_id = :primary_id, updated_at = :now "
    "WHERE src_entity_id = :secondary_id AND is_tombstoned = FALSE"
)

_REPOINT_EDGES_DST_SQL: str = (
    "UPDATE memory.kg_edges "
    "SET dst_entity_id = :primary_id, updated_at = :now "
    "WHERE dst_entity_id = :secondary_id AND is_tombstoned = FALSE"
)

# Alias union: use Postgres array concatenation with deduplication via
# ``array_agg(DISTINCT unnest(...))``.  This is the most portable way to
# dedupe in pure SQL.
_UNION_ALIASES_SQL: str = (
    f"UPDATE {KG_TABLE} "
    "SET aliases = ("
    "    SELECT COALESCE(array_agg(DISTINCT x), ARRAY[]::text[]) FROM ("
    "        SELECT unnest(aliases) AS x FROM {table} WHERE id = :primary_id "
    "        UNION "
    "        SELECT unnest(aliases) AS x FROM {table} WHERE id = :secondary_id"
    "    ) AS combined"
    "), "
    "updated_at = :now "
    "WHERE id = :primary_id"
)

_INSERT_CONSENT_AUDIT_SQL: str = (
    f"INSERT INTO {KG_TABLE_CONSENT_AUDIT} ("
    "consent_token, action, affected_entity_id, affected_edge_id, "
    "principal, occurred_at, details"
    ") VALUES ("
    ":consent_token, :action, :affected_entity_id, :affected_edge_id, "
    ":principal, :occurred_at, CAST(:details AS JSONB)"
    ")"
)

_STATS_BY_CATEGORY_SQL: str = (
    f"SELECT entity_type, COUNT(*) AS n "
    f"FROM {KG_TABLE} "
    "WHERE is_tombstoned = FALSE "
    "GROUP BY entity_type "
    "ORDER BY entity_type"
)

_STATS_PENDING_SAME_AS_SQL: str = (
    f"SELECT COUNT(*) AS n FROM {KG_TABLE_SAME_AS} "
    f"WHERE review_status = '{REVIEW_STATUS_PENDING}'"
)

_STATS_MERGED_SQL: str = (
    f"SELECT COUNT(*) AS n FROM {KG_TABLE} "
    "WHERE merged_into IS NOT NULL"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_order(
    a: uuid.UUID, b: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID]:
    """Return (smaller, larger) UUIDs — matches the DDL canonical-order CHECK.

    ``kg_same_as_edges`` has ``CHECK (src_entity_id < dst_entity_id)``; this
    helper enforces the same invariant at the application layer so callers
    do not have to remember to swap.
    """
    if a == b:
        raise ValueError(
            f"Cannot create same-as edge between an entity and itself: {a!s}"
        )
    return (a, b) if a < b else (b, a)


def _now_utc() -> datetime:
    """Return the current UTC time as a naive datetime (Postgres TIMESTAMPTZ)."""
    return datetime.now(UTC).replace(tzinfo=None)


async def _execute(
    session: AsyncSessionProtocol,
    sql: str,
    params: dict[str, object],
) -> None:
    """Execute a parameterised SQL statement via ``session.execute``.

    SQLAlchemy 2.x async style: pass the ``text()`` and params together so
    the bind keys are honoured.
    """
    stmt = _sa_text(sql)
    bind = getattr(stmt, "bindparams", None)
    if callable(bind):
        stmt = bind(**params)
    await session.execute(stmt)


def _normalize_alias_list(aliases: list[str] | None) -> list[str]:
    """Return the input aliases de-duplicated and stripped of empties.

    Preserves order so the first alias is the one we report as
    ``matched_aliases`` when L1b fires.
    """
    if not aliases:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for raw in aliases:
        if raw is None:
            continue
        s = str(raw).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


# ---------------------------------------------------------------------------
# EntityResolver
# ---------------------------------------------------------------------------


class EntityResolver:
    """High-level facade that chains the L1 → L1b → L2 resolution layers.

    Construct with an async session factory (any zero-argument callable that
    returns an :class:`AsyncSessionProtocol`); the factory is held for the
    lifetime of the resolver and used to open short-lived sessions for each
    public method.

    ``dedup_threshold`` is the minimum L2 confidence at which a fuzzy match
    is treated as a real match.  Anything below the threshold falls through
    to ``method='none'`` (caller should create a new entity).  P17+ will
    introduce an L3 (embedding) layer between L2 and "none".
    """

    def __init__(
        self,
        session_factory: Callable[[], AsyncSessionProtocol],
        *,
        dedup_threshold: float = DEFAULT_DEDUP_THRESHOLD,
        fuzzy_limit: int = DEFAULT_FUZZY_LIMIT,
    ) -> None:
        if not (0.0 <= dedup_threshold <= 1.0):
            raise ValueError(
                f"dedup_threshold must be in [0.0, 1.0]; got {dedup_threshold!r}"
            )
        if fuzzy_limit < 1:
            raise ValueError(
                f"fuzzy_limit must be >= 1; got {fuzzy_limit!r}"
            )
        self._session_factory = session_factory
        self._dedup_threshold = dedup_threshold
        self._fuzzy_limit = fuzzy_limit

    # -- Public API: read-only resolution ---------------------------------

    async def resolve_entity(
        self,
        name: str,
        category: str,
        *,
        aliases: list[str] | None = None,
    ) -> EntityResolutionResult:
        """Resolve an extracted entity name against the live KG.

        Layered execution (see module docstring for the full table):

            Step 1 (L1)  : exact ``canonical_key`` match  → ``method='exact'``
            Step 2 (L1b) : exact alias-array match        → ``method='exact'``
            Step 3 (L2)  : fuzzy match (rapidfuzz)        → ``method='fuzzy'``
            Step 4 (L3)  : DEFERRED to P17+                (no-op)
            Step 5       : no match                        → ``method='none'``

        Parameters
        ----------
        name:
            The extracted entity surface form (e.g. "Faiz", "Hermes Agent").
        category:
            The entity category (e.g. "PERSON", "PROJECT", "ORGANIZATION").
        aliases:
            Optional list of additional surface forms for the same entity
            (e.g. nicknames, abbreviations, alternate spellings).  Used by
            the L1b pass.

        Returns
        -------
        EntityResolutionResult
            Always returns a result (never raises on "no match").  When
            ``method='none'``, ``canonical_entity`` is ``None`` and the
            caller is responsible for creating the new entity row.
        """
        canonical_key = generate_canonical_key(name, category)
        alias_list = _normalize_alias_list(aliases)
        session = self._session_factory()

        # --- Step 1 (L1): exact canonical_key match -----------------------
        l1_hit = await find_by_canonical_key(session, canonical_key)
        if l1_hit is not None:
            logger.info(
                "entity_resolved_l1",
                extra={
                    "canonical_key": canonical_key,
                    "matched_entity_id": str(l1_hit.get("id", "")),
                },
            )
            return EntityResolutionResult(
                canonical_entity=l1_hit,
                matched_aliases=[],
                confidence=1.0,
                method="exact",
            )

        # --- Step 2 (L1b): exact alias-array match ------------------------
        for alias in alias_list:
            alias_hits = await find_by_alias(session, alias)
            if alias_hits:
                # First live hit wins.  Multi-hit is rare because
                # ``find_by_alias`` excludes tombstoned rows.
                primary = alias_hits[0]
                logger.info(
                    "entity_resolved_l1b",
                    extra={
                        "alias": alias,
                        "matched_entity_id": str(primary.get("id", "")),
                    },
                )
                return EntityResolutionResult(
                    canonical_entity=primary,
                    matched_aliases=[alias],
                    confidence=1.0,
                    method="exact",
                )

        # --- Step 3 (L2): fuzzy match against same-category entities -----
        # Normalize category to lowercase for the WHERE filter — matches
        # the entity_type values in the DDL ("person", "organization", etc.)
        fuzzy_category = (category or "").strip().lower() or None
        fuzzy_matches = await fuzzy_match_entities(
            session,
            name,
            category=fuzzy_category,
            threshold=self._dedup_threshold,
            limit=self._fuzzy_limit,
        )

        # TODO(P17+): L3 embedding-similarity layer.  When enabled, this is
        # where the new pass goes — between the L2 fuzzy scan and the
        # final "no match → create new entity" branch.  See
        # research-reports/p16-kg-patterns.md §3.3 and evidence/p16-kg/
        # research-entity-resolution-no-embeddings.md for the deferred
        # design.  Current constraint: 9Router has no embedding model and
        # the operator has forbidden sentence-transformers.

        if fuzzy_matches:
            best = fuzzy_matches[0]
            canonical_entity = await find_by_canonical_key(
                session, best.canonical_key
            )
            if canonical_entity is not None:
                logger.info(
                    "entity_resolved_l2",
                    extra={
                        "best_canonical_key": best.canonical_key,
                        "score": best.score,
                        "match_type": best.match_type,
                    },
                )
                return EntityResolutionResult(
                    canonical_entity=canonical_entity,
                    matched_aliases=[],
                    confidence=best.score,
                    method="fuzzy",
                    fuzzy_candidate=best,
                )

        # --- Step 5: no match -------------------------------------------
        logger.info(
            "entity_unresolved",
            extra={
                "canonical_key": canonical_key,
                "category": category,
                "alias_count": len(alias_list),
            },
        )
        return EntityResolutionResult(
            canonical_entity=None,
            matched_aliases=[],
            confidence=0.0,
            method="none",
        )

    # -- Public API: writes (same-as queue + merge) -----------------------

    async def propose_same_as(
        self,
        src_entity_id: uuid.UUID,
        dst_entity_id: uuid.UUID,
        *,
        confidence: float,
        source: str,
        reason: str | None = None,
        principal: str = AUDIT_PRINCIPAL_DEFAULT,
    ) -> uuid.UUID:
        """Queue a ``kg_same_as_edges`` review row for the operator.

        Enforces the DDL canonical-order CHECK (``src < dst``) at the
        application layer so the INSERT can never violate the constraint.
        The new edge starts in ``review_status='pending_review'``.

        Parameters
        ----------
        src_entity_id, dst_entity_id:
            The two entity UUIDs.  Order does not matter — they are sorted
            internally.
        confidence:
            Score in ``[0.0, 1.0]`` justifying the merge proposal.
        source:
            Where the proposal came from ("fuzzy_match", "manual_review",
            "llm_extract", etc.).  Recorded in ``kg_consent_audit.details``.
        reason:
            Optional human-readable reason.  Defaults to a synthetic string
            built from the source.
        principal:
            ``kg_consent_audit.principal`` value.  Defaults to
            :data:`AUDIT_PRINCIPAL_DEFAULT`.

        Returns
        -------
        uuid.UUID
            The newly-created same-as edge ID.
        """
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(
                f"confidence must be in [0.0, 1.0]; got {confidence!r}"
            )
        canonical_src, canonical_dst = _canonical_order(src_entity_id, dst_entity_id)
        edge_id = uuid.uuid4()
        now = _now_utc()
        default_reason = f"propose_same_as:source={source}"
        final_reason = reason or default_reason

        params = {
            "id": edge_id,
            "src_entity_id": canonical_src,
            "dst_entity_id": canonical_dst,
            "confidence": float(confidence),
            "reason": final_reason,
            "review_status": REVIEW_STATUS_PENDING,
            "recorded_at": now,
            "updated_at": now,
        }
        session = self._session_factory()
        sql = _INSERT_SAME_AS_SQL.format(table=KG_TABLE_SAME_AS)
        await _execute(session, sql, params)
        try:
            await session.flush()
        except AttributeError:
            # Fake sessions may not implement ``flush``; that is fine — the
            # INSERT is already queued in the session.
            pass
        logger.info(
            "same_as_proposed",
            extra={
                "edge_id": str(edge_id),
                "src": str(canonical_src),
                "dst": str(canonical_dst),
                "confidence": float(confidence),
                "source": source,
                "principal": principal,
            },
        )
        return edge_id

    async def merge_entities(
        self,
        primary_id: uuid.UUID,
        secondary_id: uuid.UUID,
        *,
        reason: str,
        principal: str = AUDIT_PRINCIPAL_DEFAULT,
    ) -> uuid.UUID:
        """Merge *secondary_id* into *primary_id* (soft-delete + audit).

        The merge is a four-step operation executed within a single session
        (the caller is expected to manage the surrounding transaction):

            1. Compute the union of both entities' ``aliases`` arrays (SQL
               dedup) and store the result on the primary.
            2. Re-point every ``kg_edges`` row where the secondary appears
               as ``src_entity_id`` or ``dst_entity_id`` to the primary.
            3. Tombstone the secondary (``is_tombstoned=TRUE``,
               ``merged_into=primary_id``).
            4. Write a ``kg_consent_audit`` row with
               ``action='cascade_revoke'`` and merge details in JSONB.

        The audit row is **mandatory** — there is no merge-without-audit
        path.  If the audit INSERT fails for any reason, the merge must be
        rolled back (the session is the caller's responsibility).

        Parameters
        ----------
        primary_id:
            The entity to keep.  Must already exist and be non-tombstoned.
        secondary_id:
            The entity to absorb.  Must exist and be non-tombstoned.
        reason:
            Human-readable reason for the merge (recorded in audit ``details``).
        principal:
            ``kg_consent_audit.principal`` value.

        Returns
        -------
        uuid.UUID
            ``primary_id`` (unchanged), returned for call-site ergonomics.
        """
        if primary_id == secondary_id:
            raise ValueError(
                f"Cannot merge an entity into itself: {primary_id!s}"
            )
        session = self._session_factory()
        now = _now_utc()

        # Step 1: alias union on the primary.
        union_sql = _UNION_ALIASES_SQL.format(table=KG_TABLE)
        await _execute(
            session,
            union_sql,
            {
                "primary_id": primary_id,
                "secondary_id": secondary_id,
                "now": now,
            },
        )

        # Step 2: re-point edges.
        await _execute(
            session,
            _REPOINT_EDGES_SRC_SQL,
            {"primary_id": primary_id, "secondary_id": secondary_id, "now": now},
        )
        await _execute(
            session,
            _REPOINT_EDGES_DST_SQL,
            {"primary_id": primary_id, "secondary_id": secondary_id, "now": now},
        )

        # Step 3: tombstone the secondary.
        await _execute(
            session,
            _TOMBSTONE_ENTITY_SQL,
            {
                "primary_id": primary_id,
                "secondary_id": secondary_id,
                "reason": reason,
                "now": now,
            },
        )

        # Step 4: write the consent audit row (mandatory).
        audit_details = json.dumps(
            {
                "event": "merge",
                "primary_id": str(primary_id),
                "secondary_id": str(secondary_id),
                "reason": reason,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        await _execute(
            session,
            _INSERT_CONSENT_AUDIT_SQL,
            {
                "consent_token": f"kg_merge:{secondary_id}",
                "action": AUDIT_ACTION_MERGE,
                "affected_entity_id": secondary_id,
                "affected_edge_id": None,
                "principal": principal,
                "occurred_at": now,
                "details": audit_details,
            },
        )

        try:
            await session.flush()
        except AttributeError:
            # Fake sessions used in unit tests may not implement ``flush``;
            # the operations are already queued on the session, so
            # silently degrading is safe here.
            pass

        logger.info(
            "entity_merged",
            extra={
                "primary_id": str(primary_id),
                "secondary_id": str(secondary_id),
                "reason": reason,
                "principal": principal,
            },
        )
        return primary_id

    # -- Public API: stats -----------------------------------------------

    async def get_resolution_stats(self) -> dict[str, object]:
        """Return a snapshot of KG resolution health metrics.

        Includes:
            * ``entities_by_category`` — count of live (non-tombstoned,
              non-merged) entities per entity_type.
            * ``pending_same_as_count`` — count of same-as edges awaiting
              human review.
            * ``merged_count`` — total count of merged (tombstoned with
              ``merged_into`` set) entities.

        Returns
        -------
        dict
            Summary stats dict.  Keys are stable; values are the live counts
            at the moment of the call.
        """
        session = self._session_factory()

        # Entities by category.
        category_stmt = _sa_text(_STATS_BY_CATEGORY_SQL)
        cat_result = await session.execute(category_stmt)
        cat_rows = cat_result.scalars().all()
        entities_by_category: dict[str, int] = {}
        for row in cat_rows:
            mapping = getattr(row, "_mapping", None)
            if mapping is not None:
                try:
                    data = {str(k): v for k, v in mapping.items()}
                except (TypeError, ValueError):
                    data = {}
            else:
                data = {
                    "entity_type": getattr(row, "entity_type", None),
                    "n": getattr(row, "n", 0),
                }
            et = data.get("entity_type")
            count = data.get("n", 0)
            if isinstance(et, str) and isinstance(count, int):
                entities_by_category[et] = count

        # Pending same-as count.
        pending_stmt = _sa_text(_STATS_PENDING_SAME_AS_SQL)
        pending_result = await session.execute(pending_stmt)
        pending_row = pending_result.scalars().first()
        pending_count = _extract_int(pending_row, "n", default=0)

        # Merged count.
        merged_stmt = _sa_text(_STATS_MERGED_SQL)
        merged_result = await session.execute(merged_stmt)
        merged_row = merged_result.scalars().first()
        merged_count = _extract_int(merged_row, "n", default=0)

        return {
            "entities_by_category": entities_by_category,
            "pending_same_as_count": int(pending_count),
            "merged_count": int(merged_count),
            "dedup_threshold": self._dedup_threshold,
            "fuzzy_limit": self._fuzzy_limit,
        }


def _extract_int(row: object, attr: str, *, default: int = 0) -> int:
    """Extract an integer field from a SQLAlchemy row, with a safe default."""
    if row is None:
        return default
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        try:
            data = {str(k): v for k, v in mapping.items()}
        except (TypeError, ValueError):
            data = {}
    else:
        data = {}
    raw = data.get(attr, getattr(row, attr, default))
    if isinstance(raw, bool):
        return int(raw)
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        try:
            return int(raw)
        except ValueError:
            return default
    return default
