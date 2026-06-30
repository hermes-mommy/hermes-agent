"""P16-002: L2 fuzzy-match layer for entity resolution.

Implements the second layer of the layered deduplication pipeline described
in ``research-reports/p16-kg-patterns.md`` §3.3.  When L1 (exact canonical
key) misses, the resolver asks this layer for candidates with similarity
above a configurable threshold.  Anything below the threshold is treated as
"new entity".

Backend selection:
    * **Primary** — ``rapidfuzz`` (C++-backed, Unicode-aware ``WRatio``).
      Recommended by the entity-resolution research and used by Neo4j
      Agent Memory.
    * **Fallback** — ``difflib.SequenceMatcher``.  Used automatically when
      rapidfuzz is not importable.  ``rapidfuzz`` is *not* currently listed
      in ``pyproject.toml`` (see note below), so the fallback is the
      production path until the dependency is added.

NOTE on rapidfuzz dependency:
    The P16 design assumes ``rapidfuzz>=3`` (per evidence/p16-kg/
    research-entity-resolution-no-embeddings.md §2).  This module imports it
    defensively so the package does not hard-crash if rapidfuzz has not yet
    been added to ``pyproject.toml``.  TODO(P16-002): add ``rapidfuzz>=3``
    to ``[project.dependencies]`` once the dependency is approved.
"""

from __future__ import annotations

import difflib
import importlib.util
import uuid
from dataclasses import dataclass
from types import ModuleType
from typing import Literal

# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

# ``rapidfuzz`` is not yet a declared project dependency (per
# ``pyproject.toml``); detect at import time and degrade to the stdlib
# ``difflib`` fallback if it is unavailable.  We use ``importlib.util.find_spec``
# to avoid an unconditional import that would crash when the package is
# missing.  The conditional ``from rapidfuzz import fuzz`` inside the
# ``if`` branch is intentional — it lets mypy infer a real ``ModuleType``
# for the hit case and ``None`` for the miss case without any
# type-safety suppression directive.
_rapidfuzz_fuzz_module: ModuleType | None
if importlib.util.find_spec("rapidfuzz") is not None:
    from rapidfuzz import fuzz as _rapidfuzz_fuzz_module
    HAS_RAPIDFUZZ: bool = True
else:
    _rapidfuzz_fuzz_module = None
    HAS_RAPIDFUZZ: bool = False

FUZZY_BACKEND_RAPIDFUZZ: Literal["rapidfuzz"] = "rapidfuzz"
FUZZY_BACKEND_DIFFLIB: Literal["difflib"] = "difflib"

DEFAULT_FUZZY_THRESHOLD: float = 0.85
"""Initial fuzzy-match acceptance threshold (per Neo4j Agent Memory default)."""

DEFAULT_FUZZY_LIMIT: int = 5
"""Max fuzzy candidates returned per call (top-K by score)."""


def get_active_fuzzy_backend() -> Literal["rapidfuzz", "difflib"]:
    """Return the name of the fuzzy-similarity backend currently in use.

    This is exposed for observability (e.g. metrics tags, log lines) so
    operators can tell at a glance whether they are running with the
    production C++ backend or the stdlib fallback.
    """
    return FUZZY_BACKEND_RAPIDFUZZ if HAS_RAPIDFUZZ else FUZZY_BACKEND_DIFFLIB


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FuzzyMatchResult:
    """One L2 fuzzy-match candidate above the configured threshold.

    Attributes
    ----------
    entity_id:
        UUID of the matched ``kg_entities`` row.
    entity_name:
        The ``display_name`` of the matched entity (preserved case).
    canonical_key:
        The matched entity's canonical key (16-hex-char SHA-256 prefix).
    score:
        Similarity score in the range [0.0, 1.0].  1.0 means identical.
    match_type:
        Where the match landed: ``"name"`` (matched against ``display_name``)
        or ``"alias"`` (matched against an entry in ``aliases``).
    matched_text:
        The literal string that scored.  For ``match_type="alias"`` this is
        the alias that scored; for ``match_type="name"`` it equals
        ``entity_name``.
    """

    entity_id: uuid.UUID
    entity_name: str
    canonical_key: str
    score: float
    match_type: Literal["name", "alias"]
    matched_text: str

    def __post_init__(self) -> None:
        # Clamp to the documented [0.0, 1.0] range.  Dataclass is frozen so we
        # cannot mutate; raise on out-of-range instead.
        score = float(self.score)
        if not (0.0 <= score <= 1.0):
            raise ValueError(
                f"FuzzyMatchResult.score must be in [0.0, 1.0]; got {score!r}"
            )
        if self.match_type not in ("name", "alias"):
            raise ValueError(
                f"FuzzyMatchResult.match_type must be 'name' or 'alias'; "
                f"got {self.match_type!r}"
            )


# ---------------------------------------------------------------------------
# Pure similarity helpers
# ---------------------------------------------------------------------------


def _normalize_for_compare(s: str) -> str:
    """Normalize a string for similarity comparison.

    Lowercases (casefold) and collapses whitespace, but does NOT strip
    diacritics — fuzzy matching is the right place to allow "Bjorn" to
    match "Björn" with a small score penalty rather than collapsing them
    silently.  The canonical key is the layer that demands exact diacritic
    equivalence.
    """
    if s is None:
        return ""
    return " ".join(str(s).casefold().split())


def compute_similarity(name_a: str, name_b: str) -> float:
    """Return a similarity score in ``[0.0, 1.0]`` between two entity names.

    Uses :func:`rapidfuzz.fuzz.WRatio` when the rapidfuzz library is
    available (Unicode-aware, weighted best-of-multiple algorithms, returns
    0–100).  Falls back to :func:`difflib.SequenceMatcher.ratio` (0.0–1.0)
    when rapidfuzz is not installed.

    Both inputs are normalized (casefold + whitespace collapse) before
    comparison; callers do not need to pre-normalize.

    Parameters
    ----------
    name_a, name_b:
        The two name strings.  ``None``-like values are coerced to empty
        string; the result for two empty strings is ``1.0``.

    Returns
    -------
    float
        Similarity in the closed interval ``[0.0, 1.0]``.
    """
    a = _normalize_for_compare(name_a)
    b = _normalize_for_compare(name_b)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    if HAS_RAPIDFUZZ and _rapidfuzz_fuzz_module is not None:
        # rapidfuzz returns 0–100.  Score cutoff of 0 keeps the call
        # non-short-circuiting (we need the actual value, not a 0 sentinel).
        score_100: float = float(
            _rapidfuzz_fuzz_module.WRatio(a, b, score_cutoff=0)
        )
        # Clamp into [0.0, 1.0] defensively.
        return max(0.0, min(1.0, score_100 / 100.0))
    # Fallback: stdlib difflib (already 0.0–1.0).
    return difflib.SequenceMatcher(None, a, b).ratio()


# ---------------------------------------------------------------------------
# DB-backed fuzzy candidate scan
# ---------------------------------------------------------------------------

# Import the helper for streaming candidate rows; the runtime type is only
# needed for type-checking, so we import under a TYPE_CHECKING guard.
from guinvere.knowledge_graph.resolution.canonical import (  # noqa: E402
    AsyncSessionProtocol,
    _entity_uuid,
    entity_aliases,
    list_entities_by_category,
)


def _entity_display_name(entity: dict[str, object]) -> str:
    """Return the ``display_name`` of an entity dict (or empty string)."""
    name = entity.get("display_name")
    if isinstance(name, str):
        return name
    if name is None:
        return ""
    return str(name)


def _entity_canonical_key(entity: dict[str, object]) -> str:
    """Return the canonical_key of an entity dict (or empty string)."""
    key = entity.get("canonical_key")
    if isinstance(key, str):
        return key
    if key is None:
        return ""
    return str(key)


async def fuzzy_match_entities(
    session: AsyncSessionProtocol,
    name: str,
    *,
    category: str | None = None,
    threshold: float = DEFAULT_FUZZY_THRESHOLD,
    limit: int = DEFAULT_FUZZY_LIMIT,
) -> list[FuzzyMatchResult]:
    """Return L2 fuzzy-match candidates for *name* above *threshold*.

    Algorithm:
        1. Stream all live (non-tombstoned, non-merged) entities,
           optionally filtered by category.
        2. For each entity, score against ``display_name`` *and* every
           entry in ``aliases``.
        3. Keep the best score per entity (name or alias), and the
           ``match_type`` that produced it.
        4. Drop candidates below *threshold*.
        5. Sort by score descending, then by ``entity_id`` (stable tiebreaker)
           and return the top *limit* entries.

    Tombstoned and merged entities are excluded — this is enforced by
    :func:`list_entities_by_category` and is non-negotiable per the soft-
    delete philosophy in ``research-reports/p16-kg-patterns.md`` §5.2.

    Parameters
    ----------
    session:
        Async DB session (see ``AsyncSessionProtocol``).
    name:
        The candidate entity name to look up.
    category:
        Optional entity-type filter (e.g. ``"person"``).  When ``None``
        all categories are scanned.
    threshold:
        Minimum score in ``[0.0, 1.0]`` for a result to be returned.
        Defaults to :data:`DEFAULT_FUZZY_THRESHOLD` (0.85).
    limit:
        Maximum number of candidates to return.  Defaults to
        :data:`DEFAULT_FUZZY_LIMIT` (5).

    Returns
    -------
    list[FuzzyMatchResult]
        Sorted descending by score; may be empty.

    Raises
    ------
    ValueError
        If ``threshold`` is not in ``[0.0, 1.0]`` or ``limit`` is negative.
    """
    if not (0.0 <= threshold <= 1.0):
        raise ValueError(
            f"threshold must be in [0.0, 1.0]; got {threshold!r}"
        )
    if limit < 0:
        raise ValueError(f"limit must be non-negative; got {limit!r}")

    # Normalize the search name once.
    search_name = _normalize_for_compare(name)
    if not search_name:
        return []

    candidates = await list_entities_by_category(session, category)

    scored: list[FuzzyMatchResult] = []
    for entity in candidates:
        entity_id = _entity_uuid(entity)
        if entity_id is None:
            # Skip rows with malformed primary keys — they cannot participate
            # in resolution (would break provenance / audit later).
            continue
        canonical_key = _entity_canonical_key(entity)
        display_name = _entity_display_name(entity)

        # Score against the display name first.
        best_score: float = 0.0
        best_match_type: Literal["name", "alias"] = "name"
        best_matched_text: str = display_name

        if display_name:
            score = compute_similarity(search_name, display_name)
            if score > best_score:
                best_score = score
                best_match_type = "name"
                best_matched_text = display_name

        # Score against every alias.  Track the best alias match.
        for alias in entity_aliases(entity):
            if not alias:
                continue
            score = compute_similarity(search_name, alias)
            if score > best_score:
                best_score = score
                best_match_type = "alias"
                best_matched_text = alias

        if best_score < threshold:
            continue

        scored.append(
            FuzzyMatchResult(
                entity_id=entity_id,
                entity_name=display_name,
                canonical_key=canonical_key,
                score=best_score,
                match_type=best_match_type,
                matched_text=best_matched_text,
            )
        )

    # Sort: score desc, then entity_id (UUID bytes) asc as a stable tiebreaker.
    scored.sort(key=lambda m: (-m.score, m.entity_id))
    return scored[:limit]
