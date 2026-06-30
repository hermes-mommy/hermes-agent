"""P16-002: Canonical key generation and exact-match lookups for entity resolution.

Layer L1 of the layered deduplication pipeline described in
``research-reports/p16-kg-patterns.md`` §3.3 and the no-embedding research at
``evidence/p16-kg/research-entity-resolution-no-embeddings.md`` §1.

Design:
    1. ``normalize_entity_name`` strips honorifics, lowercases, collapses
       whitespace.  This is the "display-safe" form used for log lines and
       ``EntityResolutionResult`` payloads.
    2. ``generate_canonical_key`` produces a deterministic SHA-256 key over
       the *lowercased + diacritics-stripped* form of the name, prefixed with
       the category.  The first 16 hex chars of the SHA-256 (64 bits of entropy)
       give us 5-billion-item birthday-collision headroom — more than enough
       for the ~1M-memory target scale.
    3. ``find_by_canonical_key`` and ``find_by_alias`` are thin DB lookups over
       the UNIQUE index on ``kg_entities.canonical_key`` and the GIN index on
       ``kg_entities.aliases``.  Both always exclude tombstoned rows.

The SHA-256 / hex-truncation pattern is the same one used in
``guinvere/memory/consolidation.py::make_content_key`` — that is the project's
house style for content-addressable keys.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from collections.abc import Iterable
from typing import Protocol

from sqlalchemy import text as _sa_text

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CANONICAL_KEY_PREFIX: str = "kg"
"""Prefix used to disambiguate canonical keys from other content hashes."""

CANONICAL_KEY_LENGTH: int = 16
"""Number of leading hex chars of the SHA-256 to return (64 bits of entropy)."""

CATEGORY_DEFAULT: str = "entity"
"""Fallback category when caller does not specify one (matches DDL default)."""

KG_TABLE: str = "memory.kg_entities"
"""Fully-qualified table name (per p16-001-schema-ddl.sql)."""

KG_TABLE_SAME_AS: str = "memory.kg_same_as_edges"
"""Same-as edge table (canonical-ordering CHECK)."""

KG_TABLE_CONSENT_AUDIT: str = "memory.kg_consent_audit"
"""Consent audit log (merge events must be recorded here)."""

# Word-anchored honorific stripper — \b boundaries prevent matching inside
# legitimate words (e.g. "Drummond" or "MisterEd").  Matches "the", "dr.",
# "dr", "mr.", "mr", "ms.", "ms" at word boundaries (case-insensitive).
HONORIFIC_PREFIXES: tuple[str, ...] = (
    "the ",
    "dr. ",
    "dr ",
    "mr. ",
    "mr ",
    "ms. ",
    "ms ",
)
"""Honorifics / articles to strip from the *start* of a name (lowercased)."""

HONORIFIC_PREFIX_PATTERN: re.Pattern[str] = re.compile(
    r"^(?:the |dr\.? |mr\.? |ms\.? )+",
    re.IGNORECASE,
)

NAME_NORMALIZE_PATTERN: re.Pattern[str] = re.compile(r"\s+")
"""Whitespace collapse pattern (used by ``normalize_entity_name``)."""

WHITESPACE_PATTERN: re.Pattern[str] = re.compile(r"\s+")
"""Same as ``NAME_NORMALIZE_PATTERN`` (kept as alias for tests)."""

NON_ALNUM_PATTERN: re.Pattern[str] = re.compile(r"[^0-9a-z]+")
"""Forces an ASCII-only slug for the canonical key (used in canonicalize step)."""

# ---------------------------------------------------------------------------
# Session protocol (mirrors guinvere/memory/consolidation.AsyncSessionProtocol)
# ---------------------------------------------------------------------------


class _ScalarResult(Protocol):
    """Minimal subset of SQLAlchemy ``Result.scalars()`` we depend on."""

    def all(self) -> list[object]:
        ...

    def first(self) -> object:
        ...


class _ExecResult(Protocol):
    """Minimal subset of ``AsyncSession.execute()`` return value."""

    def scalars(self) -> _ScalarResult:
        ...


class AsyncSessionProtocol(Protocol):
    """Minimal async DB session surface for entity resolution lookups.

    Mirrors the pattern in ``guinvere.memory.consolidation.AsyncSessionProtocol``
    so the resolver is unit-testable with a fake session.
    """

    async def execute(self, statement: object) -> _ExecResult:
        ...

    def add(self, obj: object) -> None:
        ...

    async def flush(self) -> None:
        ...

    async def commit(self) -> None:
        ...


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def normalize_entity_name(name: str) -> str:
    """Return a *display-safe* normalized form of an entity name.

    The result is suitable for log lines, error messages, and the
    ``EntityResolutionResult`` payload.  For *content-addressable* hashing use
    :func:`generate_canonical_key` instead — it does additional diacritics
    stripping that this function intentionally avoids (so display output
    preserves the operator's original spelling).

    Steps:
        1. Strip leading/trailing whitespace.
        2. Collapse runs of internal whitespace to a single space.
        3. Lowercase (ASCII only — casefold for non-ASCII is the hash layer's job).
        4. Strip leading honorifics/articles ("the ", "dr. ", "mr. ", "ms. ").
        5. Strip a trailing period (covers "Dr." → "Dr" after step 4).

    Parameters
    ----------
    name:
        The raw entity name from extraction.  ``None``-like values are
        coerced to an empty string (no exception).

    Returns
    -------
    str
        Normalized name, never ``None``, never containing leading/trailing
        whitespace or honorific prefixes.
    """
    if name is None:
        return ""
    s = str(name).strip()
    if not s:
        return ""
    s = NAME_NORMALIZE_PATTERN.sub(" ", s)
    s = s.lower()
    # Iterative strip in case "Dr. Mr. Faiz" — repeatedly strip the leading
    # honorific until no more match.
    while True:
        new_s = HONORIFIC_PREFIX_PATTERN.sub("", s)
        if new_s == s:
            break
        s = new_s
    s = s.strip()
    # Drop a single trailing period (e.g. "faiz." → "faiz").
    if s.endswith("."):
        s = s[:-1].rstrip()
    return s


def _strip_diacritics(slug: str) -> str:
    """Strip diacritics and force ASCII-only output for the canonical key.

    This is *intentionally* more aggressive than ``normalize_entity_name``:
    the canonical key must be a stable content address, so "Björn" and
    "Bjorn" must hash to the same value.

    Implementation notes:
        * Use ``NFKD`` (compatibility decomposition) so ligatures and
          full-width characters collapse.
        * Drop combining marks (Unicode category starting with ``M``).
        * Then keep only ``[a-z0-9]`` and collapse separators — this also
          normalises "São Paulo" → "sao paulo".
    """
    decomposed = unicodedata.normalize("NFKD", slug)
    # Remove combining marks (accents) only — leave base characters intact.
    ascii_only = "".join(
        ch for ch in decomposed if not unicodedata.combining(ch)
    ).encode("ascii", "ignore").decode("ascii")
    return NON_ALNUM_PATTERN.sub(" ", ascii_only).strip()


# ---------------------------------------------------------------------------
# Canonical key generation
# ---------------------------------------------------------------------------


def generate_canonical_key(name: str, category: str) -> str:
    """Return the canonical key for an entity name within *category*.

    The key is the first 16 hex chars of the SHA-256 of the formatted string
    ``"{category.lower()}:{normalized_slug}"`` where ``normalized_slug`` is
    the diacritics-stripped, ASCII-only, lowercased form of the name.

    Examples (illustrative, not real hashes)::

        generate_canonical_key("Faiz", "PERSON")
        # formatted = "person:faiz"
        # sha256("person:faiz")[:16] → 16 hex chars

        generate_canonical_key("Björn Müller", "PERSON")
        # formatted = "person:bjorn muller"
        # different from generate_canonical_key("Bjorn Muller", "PERSON")
        # because both collapse to the same slug.

    The 16-hex-char length (64 bits) gives 5×10⁹-item birthday-collision
    headroom — more than enough for the ~1M-memory target scale.

    Parameters
    ----------
    name:
        The entity name.  May contain diacritics, mixed case, honorifics.
    category:
        The entity category ("PERSON", "ORGANIZATION", "PROJECT", etc.).
        Lowercased before use; falls back to ``CATEGORY_DEFAULT`` if blank.

    Returns
    -------
    str
        A 16-character lowercase hex string.  Always exactly 16 chars.
    """
    cat = (category or "").strip().lower() or CATEGORY_DEFAULT
    # Build the slug for hashing: strip whitespace, lowercase, drop diacritics,
    # then collapse non-alphanumeric to a single space and trim.
    raw = (name or "").strip().lower()
    slug = _strip_diacritics(raw)
    formatted = f"{cat}:{slug}"
    digest = hashlib.sha256(formatted.encode("utf-8")).hexdigest()
    return digest[:CANONICAL_KEY_LENGTH]


# ---------------------------------------------------------------------------
# DB lookups
# ---------------------------------------------------------------------------


_SELECT_BY_CANONICAL_KEY_SQL: str = (
    "SELECT id, canonical_key, entity_type, display_name, aliases, attributes, "
    "       merged_into, is_tombstoned, tombstone_reason, tombstoned_at, "
    "       first_seen_at, first_seen_source, last_verified_at, "
    "       valid_from, valid_to, classification, purpose, source, "
    "       retention_class, retention_until, access_policy, encryption_profile, "
    "       deletion_state, key_id, key_version, created_at, updated_at "
    f"FROM {KG_TABLE} "
    "WHERE canonical_key = :canonical_key AND is_tombstoned = FALSE"
)


_SELECT_BY_ALIAS_SQL: str = (
    "SELECT id, canonical_key, entity_type, display_name, aliases, attributes, "
    "       merged_into, is_tombstoned, tombstone_reason, tombstoned_at, "
    "       first_seen_at, first_seen_source, last_verified_at, "
    "       valid_from, valid_to, classification, purpose, source, "
    "       retention_class, retention_until, access_policy, encryption_profile, "
    "       deletion_state, key_id, key_version, created_at, updated_at "
    f"FROM {KG_TABLE} "
    "WHERE :alias = ANY(aliases) AND is_tombstoned = FALSE"
)


def _row_to_entity_dict(row: object) -> dict[str, object]:
    """Convert an ORM row or namedtuple to a plain dict.

    Tries common SQLAlchemy patterns (``_mapping``, ``__dict__``) and falls
    back to per-attribute ``getattr``.  Never raises — extra attributes the
    row may have are preserved as keys.
    """
    # SQLAlchemy 2.x ``Row`` exposes ``_mapping`` (a ``RowMapping`` view).
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        try:
            return {str(k): v for k, v in mapping.items()}
        except (TypeError, ValueError):
            pass
    # Plain ORM instance: take its public attributes.
    result: dict[str, object] = {}
    for attr in (
        "id", "canonical_key", "entity_type", "display_name", "aliases",
        "attributes", "merged_into", "is_tombstoned", "tombstone_reason",
        "tombstoned_at", "first_seen_at", "first_seen_source",
        "last_verified_at", "valid_from", "valid_to", "classification",
        "purpose", "source", "retention_class", "retention_until",
        "access_policy", "encryption_profile", "deletion_state", "key_id",
        "key_version", "created_at", "updated_at",
    ):
        if hasattr(row, attr):
            result[attr] = getattr(row, attr)
    return result


def _bind_params(statement: object, params: dict[str, object]) -> object:
    """Bind named parameters to a SQL string.

    Supports two execution styles:
      * SQLAlchemy ``text()`` — uses ``.bindparams(**kwargs)``.
      * Raw string — returns ``(statement, params)`` for the caller to pass
        to ``session.execute(stmt, params)``.
    """
    bind = getattr(statement, "bindparams", None)
    if callable(bind):
        return bind(**params)
    return statement


async def find_by_canonical_key(
    session: AsyncSessionProtocol,
    canonical_key: str,
) -> dict[str, object] | None:
    """Return the live (non-tombstoned) entity with the given canonical_key.

    Parameters
    ----------
    session:
        Async DB session (see :class:`AsyncSessionProtocol`).
    canonical_key:
        The 16-hex-char key from :func:`generate_canonical_key`.

    Returns
    -------
    dict | None
        A plain-dict representation of the row, or ``None`` if no live entity
        with that key exists.  An entity that is tombstoned is *never*
        returned — call sites must create a new row instead.
    """
    if not canonical_key:
        return None
    stmt = _sa_text(_SELECT_BY_CANONICAL_KEY_SQL)
    bound = _bind_params(stmt, {"canonical_key": canonical_key})
    exec_result = await session.execute(bound)
    row = exec_result.scalars().first()
    if row is None:
        return None
    return _row_to_entity_dict(row)


async def find_by_alias(
    session: AsyncSessionProtocol,
    alias: str,
) -> list[dict[str, object]]:
    """Return all live (non-tombstoned) entities that list *alias* in ``aliases``.

    The lookup uses the GIN-indexed ``aliases`` column so it is O(matches),
    not O(rows).  Tombstoned entities are always excluded.

    Parameters
    ----------
    session:
        Async DB session.
    alias:
        The candidate alias text.  An exact match is performed against
        the ``TEXT[]`` column (case-sensitive, by design — see
        ``generate_canonical_key`` for the lowercased/diacritics-stripped
        content-addressable variant).

    Returns
    -------
    list[dict]
        A list of entity dicts; empty when no live entity has the alias.
    """
    if not alias:
        return []
    stmt = _sa_text(_SELECT_BY_ALIAS_SQL)
    bound = _bind_params(stmt, {"alias": alias})
    exec_result = await session.execute(bound)
    rows = exec_result.scalars().all()
    return [_row_to_entity_dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Public batched lookup helper (used by EntityResolver)
# ---------------------------------------------------------------------------


async def list_entities_by_category(
    session: AsyncSessionProtocol,
    category: str | None,
    *,
    include_merged: bool = False,
) -> list[dict[str, object]]:
    """Return all live (non-tombstoned) entities, optionally filtered by category.

    Used by the L2 fuzzy-match pass in :class:`EntityResolver` to scan the
    entity namespace.  At ~1M memories this is not a "full scan" — the
    resolver is invoked per new entity, and the per-entity cost is bounded
    by the entity-type index on ``kg_entities.entity_type``.

    Parameters
    ----------
    session:
        Async DB session.
    category:
        If non-empty, restrict to ``entity_type = :category``; otherwise
        return all categories.
    include_merged:
        If ``True``, also include entities whose ``merged_into`` is non-null
        (default ``False`` — merged entities are excluded so they do not
        pollute the match candidate set).

    Returns
    -------
    list[dict]
        List of entity dicts (see :func:`_row_to_entity_dict`).
    """
    select_cols = (
        "id, canonical_key, entity_type, display_name, aliases, attributes, "
        "merged_into, is_tombstoned, first_seen_at, last_verified_at, "
        "classification, deletion_state, created_at, updated_at"
    )
    where_clauses: list[str] = ["is_tombstoned = FALSE"]
    params: dict[str, object] = {}
    if category:
        where_clauses.append("entity_type = :category")
        params["category"] = category
    if not include_merged:
        where_clauses.append("merged_into IS NULL")
    sql = (
        f"SELECT {select_cols} FROM {KG_TABLE} "
        f"WHERE {' AND '.join(where_clauses)} "
        "ORDER BY id"
    )
    stmt = _sa_text(sql)
    bound = _bind_params(stmt, params)
    exec_result = await session.execute(bound)
    rows = exec_result.scalars().all()
    return [_row_to_entity_dict(row) for row in rows]


def _entity_uuid(entity: dict[str, object]) -> uuid.UUID | None:
    """Best-effort UUID extractor from an entity dict (or UUID directly)."""
    raw = entity.get("id") if isinstance(entity, dict) else entity
    if raw is None:
        return None
    if isinstance(raw, uuid.UUID):
        return raw
    if isinstance(raw, str):
        try:
            return uuid.UUID(raw)
        except (TypeError, ValueError):
            return None
    return None


def entity_aliases(entity: dict[str, object]) -> Iterable[str]:
    """Return the (possibly empty) list of aliases for an entity dict.

    Tolerates the alias column being a list, a tuple, or ``None``.
    """
    aliases = entity.get("aliases")
    if isinstance(aliases, (list, tuple)):
        for alias in aliases:
            if isinstance(alias, str):
                yield alias
            elif alias is not None:
                yield str(alias)
