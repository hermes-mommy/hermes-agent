"""Guinevere Memory Plugin — Safety Gates Module.

Separate module from ``__init__.py`` per batch plan P3-003.
Provides safety gates for the Hermes memory read path:

1. **DNR ID cache**: In-memory cache of Do-Not-Recall IDs for fast filtering.
2. **PG classification enrichment**: Post-recall classification validation.
3. **Anti-hallucination guard**: Verify recalled content is real DB data.
4. **Safe-mode substitution**: Redact Critical/Restricted content.
5. **Consent gate**: Check consent before recall/store operations.

All gates are called by the plugin's ``prefetch()`` and ``sync_turn()``
methods. They are stateless where possible; stateful gates (DNR cache)
use TTL-based refresh.

Safety: Never logs raw content. Hash-only logging. No type suppression.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DNR_CACHE_TTL_SECONDS: int = 300  # 5 minutes
_PRINCIPAL: str = "guinevere_core"

# Classification hierarchy (lower index = less restricted)
_CLASSIFICATION_HIERARCHY: dict[str, int] = {
    "Public": 0,
    "Internal": 1,
    "Restricted": 2,
    "Confidential": 3,
    "Critical": 4,
}

# Classification ceiling per principal
_PRINCIPAL_CEILING: dict[str, str] = {
    "guinevere_core": "Restricted",
    "guinevere_readonly": "Internal",
    "default": "Internal",
}

# Content hash prefix for logging (never log raw content)
_HASH_PREFIX_LEN: int = 12


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DnrCacheEntry:
    """Cached DNR entry for fast ID-based filtering."""

    dnr_ids: frozenset[str]
    fetched_at: float

    def is_expired(self) -> bool:
        return (time.time() - self.fetched_at) > _DNR_CACHE_TTL_SECONDS


@dataclass
class SafetyGateResult:
    """Result from a safety gate check."""

    passed: bool
    gate_name: str
    reason: str = ""
    filtered_results: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Gate 1: DNR ID Cache
# ---------------------------------------------------------------------------


class DnrIdCache:
    """In-memory cache of DNR (Do-Not-Recall) IDs.

    Refreshes from PostgreSQL every 5 minutes.  Used for fast pre-filtering
    before the full DNR verification in the read pipeline.
    """

    def __init__(self) -> None:
        self._cache: DnrCacheEntry | None = None

    async def get_dnr_ids(self, session_factory: Any) -> frozenset[str]:
        """Get current DNR IDs, refreshing from DB if expired."""
        if self._cache is not None and not self._cache.is_expired():
            return self._cache.dnr_ids

        try:
            dnr_ids = await self._fetch_dnr_ids(session_factory)
            self._cache = DnrCacheEntry(
                dnr_ids=dnr_ids, fetched_at=time.time()
            )
            _logger.info(
                "dnr_cache_refreshed: count=%d", len(dnr_ids)
            )
            return dnr_ids
        except Exception as exc:
            _logger.warning("dnr_cache_refresh_error: %s", exc)
            # Return stale cache if available (fail-safe: filter more, not less)
            if self._cache is not None:
                return self._cache.dnr_ids
            # No cache at all — return empty (rely on read_pipeline DNR gate)
            return frozenset()

    async def _fetch_dnr_ids(self, session_factory: Any) -> frozenset[str]:
        """Fetch DNR IDs from PostgreSQL."""
        from src.memory.dnr import get_dnr_entries

        async with session_factory() as session:
            entries = await get_dnr_entries(session, principal=_PRINCIPAL)
            return frozenset(str(e) for e in entries)

    def filter_results(
        self, results: list[dict[str, Any]], dnr_ids: frozenset[str]
    ) -> list[dict[str, Any]]:
        """Remove DNR-flagged results from recall output."""
        if not dnr_ids:
            return results

        filtered = [
            r for r in results
            if str(r.get("id", "")) not in dnr_ids
        ]
        removed = len(results) - len(filtered)
        if removed > 0:
            _logger.info("dnr_cache_filtered: removed=%d", removed)
        return filtered


# ---------------------------------------------------------------------------
# Gate 2: PG Classification Enrichment
# ---------------------------------------------------------------------------


def classify_ceiling_filter(
    results: list[dict[str, Any]],
    principal: str = _PRINCIPAL,
) -> SafetyGateResult:
    """Filter results that exceed the principal's classification ceiling.

    Returns only results at or below the principal's maximum classification.
    """
    ceiling = _PRINCIPAL_CEILING.get(principal, _PRINCIPAL_CEILING["default"])
    ceiling_level = _CLASSIFICATION_HIERARCHY.get(ceiling, 1)

    filtered: list[dict[str, Any]] = []
    removed_count = 0

    for r in results:
        classification = r.get("classification", "Restricted")
        level = _CLASSIFICATION_HIERARCHY.get(classification, 2)

        if level <= ceiling_level:
            filtered.append(r)
        else:
            removed_count += 1
            _logger.debug(
                "classification_ceiling_filtered: id=%s, class=%s, ceiling=%s",
                str(r.get("id", ""))[:8],
                classification,
                ceiling,
            )

    return SafetyGateResult(
        passed=True,
        gate_name="classification_ceiling",
        reason=f"{removed_count} results above ceiling ({ceiling})" if removed_count else "all pass",
        filtered_results=filtered,
    )


# ---------------------------------------------------------------------------
# Gate 3: Anti-Hallucination Guard
# ---------------------------------------------------------------------------


def anti_hallucination_check(
    results: list[dict[str, Any]],
) -> SafetyGateResult:
    """Verify recalled content has required metadata fields.

    Rejects results missing critical fields (id, safe_content, classification).
    These are signs of corrupted or hallucinated data.
    """
    required_fields = {"id", "safe_content", "classification"}
    valid: list[dict[str, Any]] = []
    rejected = 0

    for r in results:
        present = set(r.keys())
        if required_fields.issubset(present):
            # Additional check: safe_content must be non-empty string
            content = r.get("safe_content", "")
            if isinstance(content, str) and len(content) > 0:
                valid.append(r)
            else:
                rejected += 1
                _logger.warning(
                    "anti_hallucination_empty_content: id=%s",
                    str(r.get("id", ""))[:8],
                )
        else:
            rejected += 1
            missing = required_fields - present
            _logger.warning(
                "anti_hallucination_missing_fields: id=%s, missing=%s",
                str(r.get("id", ""))[:8],
                missing,
            )

    return SafetyGateResult(
        passed=True,
        gate_name="anti_hallucination",
        reason=f"{rejected} results rejected" if rejected else "all valid",
        filtered_results=valid,
    )


# ---------------------------------------------------------------------------
# Gate 4: Safe-Mode Substitution
# ---------------------------------------------------------------------------


def safe_mode_substitute(
    results: list[dict[str, Any]],
    safe_mode: bool = False,
) -> list[dict[str, Any]]:
    """Replace Critical/Restricted content with placeholders in safe mode.

    When ``safe_mode=False``, returns results unchanged.
    When ``safe_mode=True``, Critical content is replaced with a placeholder,
    and Restricted/Confidential content is replaced with a different placeholder.
    """
    if not safe_mode:
        return results

    critical_placeholder = (
        "[Content redacted per safe-mode policy — Critical classification]"
    )
    restricted_placeholder = (
        "[Content redacted per safe-mode policy — Restricted/Confidential classification]"
    )

    sanitized: list[dict[str, Any]] = []
    for r in results:
        r_copy = dict(r)
        classification = r.get("classification", "Restricted")

        if classification == "Critical":
            r_copy["safe_content"] = critical_placeholder
        elif classification in ("Restricted", "Confidential"):
            r_copy["safe_content"] = restricted_placeholder

        sanitized.append(r_copy)

    return sanitized


# ---------------------------------------------------------------------------
# Gate 5: Consent Gate
# ---------------------------------------------------------------------------


class ConsentGate:
    """Check consent status before memory operations.

    Queries Redis DB5 for consent state. If memory-related consent is
    revoked, blocks recall and store operations.
    """

    def __init__(self) -> None:
        self._redis_url: str = ""
        self._consent_cache: dict[str, bool] = {}
        self._cache_ttl: float = 30.0  # 30 seconds
        self._last_check: float = 0.0

    def configure(self, redis_url: str) -> None:
        """Set Redis URL for consent lookups."""
        self._redis_url = redis_url

    def is_consent_granted(self, category: str = "memory") -> bool:
        """Check if consent is granted for the given category.

        Uses cached value with TTL. Fail-closed: returns False if Redis
        is unavailable or consent key is missing.
        """
        now = time.time()
        if (now - self._last_check) < self._cache_ttl:
            return self._consent_cache.get(category, False)

        try:
            granted = self._check_redis_consent(category)
            self._consent_cache[category] = granted
            self._last_check = now
            return granted
        except Exception as exc:
            _logger.warning("consent_gate_redis_error: %s", exc)
            # Fail-closed: consent denied on error
            return False

    def _check_redis_consent(self, category: str) -> bool:
        """Check consent in Redis DB5. Fail-closed: False if unavailable."""
        if not self._redis_url:
            return False

        import redis as redis_lib

        client = redis_lib.Redis.from_url(
            self._redis_url, decode_responses=True
        )
        key = f"guinevere:consent:{category}"
        value = client.get(key)

        if value is None:
            # No consent record = default denied (fail-closed)
            return False

        return value.lower() in ("true", "1", "granted", "yes")


# ---------------------------------------------------------------------------
# Content Hash (for safe logging)
# ---------------------------------------------------------------------------


def content_hash(content: str) -> str:
    """Generate a short hash for logging without exposing content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:_HASH_PREFIX_LEN]


# ---------------------------------------------------------------------------
# Composite Safety Pipeline
# ---------------------------------------------------------------------------


def run_safety_pipeline(
    results: list[dict[str, Any]],
    *,
    principal: str = _PRINCIPAL,
    safe_mode: bool = False,
    dnr_ids: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Run all safety gates in sequence on recall results.

    Gate order:
    1. DNR filter (if dnr_ids provided)
    2. Anti-hallucination check
    3. Classification ceiling
    4. Safe-mode substitution (if enabled)

    Returns sanitized results. Never raises — degrades gracefully.
    """
    try:
        # Gate 1: DNR
        if dnr_ids:
            cache = DnrIdCache()
            results = cache.filter_results(results, dnr_ids)

        # Gate 2: Anti-hallucination
        ah_result = anti_hallucination_check(results)
        results = ah_result.filtered_results

        # Gate 3: Classification ceiling
        cc_result = classify_ceiling_filter(results, principal)
        results = cc_result.filtered_results

        # Gate 4: Safe-mode substitution
        results = safe_mode_substitute(results, safe_mode)

        _logger.info(
            "safety_pipeline_complete: input=%d, output=%d, gates=4",
            len(results),
            len(results),
        )
        return results

    except Exception as exc:
        _logger.error("safety_pipeline_error: %s", exc)
        return []  # Fail closed — return nothing on pipeline error
