"""TimescaleDB retention policy module -- constants and helpers for data lifecycle.

Defines the 3-tier retention architecture (raw, aggregated, summary) with
TimescaleDB-specific configuration: chunk intervals, compression timing, and
expiry calculation.

Consumed by:
- TimescaleDB ``add_retention_policy()`` and ``add_compression_policy()`` calls
- ``drop_chunks()`` automation jobs
- Data classification retention mapping (SurveillanceDataPolicy Section 5/9)

Design decisions:
- Enum-gated tiers: ``RetentionTier`` is a StrEnum, never free-text.
- Fail-safe: unknown tier strings default to RAW (shortest retention).
- Structlog: policy changes logged at info level.
- Datetime-aware: expiry calculation preserves timezone information.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Final

import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Retention constants -- aligned with ADR-010 and SurveillanceDataPolicy
# ---------------------------------------------------------------------------

RETENTION_RAW_DAYS: Final[int] = 7
"""Raw event retention in days. Applies to ``surveillance.events`` hypertable."""

RETENTION_AGGREGATED_DAYS: Final[int] = 90
"""Continuous aggregate / materialized view retention in days."""

RETENTION_SUMMARY_DAYS: Final[int] = 365
"""Curated long-term summary retention in days."""

COMPRESSION_AFTER_DAYS: Final[int] = 7
"""Days after which TimescaleDB compression kicks in for a chunk."""

CHUNK_INTERVAL_DAYS: Final[int] = 1
"""TimescaleDB hypertable chunk interval in days."""


# ---------------------------------------------------------------------------
# RetentionTier -- StrEnum for tier-safe dispatch
# ---------------------------------------------------------------------------


class RetentionTier(StrEnum):
    """TimescaleDB retention tiers.

    Mirrors the 3-tier architecture from ADR-010 and SurveillanceDataPolicy:
    raw (7d), aggregated (90d), summary (365d).
    """

    RAW = "raw"
    AGGREGATED = "aggregated"
    SUMMARY = "summary"


# ---------------------------------------------------------------------------
# Tier → days mapping
# ---------------------------------------------------------------------------

_TIER_DAYS: Final[dict[RetentionTier, int]] = {
    RetentionTier.RAW: RETENTION_RAW_DAYS,
    RetentionTier.AGGREGATED: RETENTION_AGGREGATED_DAYS,
    RetentionTier.SUMMARY: RETENTION_SUMMARY_DAYS,
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_retention_days(tier: RetentionTier) -> int:
    """Return the retention period in days for a given tier.

    Args:
        tier: A ``RetentionTier`` enum member.

    Returns:
        Number of days for the tier. Unknown/empty tier defaults to
        ``RETENTION_RAW_DAYS`` (fail-safe).
    """
    return _TIER_DAYS.get(tier, RETENTION_RAW_DAYS)


def calculate_retention_until(
    tier: RetentionTier,
    occurred_at: datetime,
) -> datetime:
    """Calculate the expiry datetime for an event given its retention tier.

    Args:
        tier: The retention tier (raw, aggregated, summary).
        occurred_at: The event's original occurrence timestamp.

    Returns:
        ``occurred_at + timedelta(days=<tier retention>)``, preserving timezone.
    """
    days = get_retention_days(tier)
    return occurred_at + timedelta(days=days)


def get_retention_policy_summary() -> dict[str, Any]:
    """Return a human-readable summary of all retention policies.

    Returns:
        Dict with tier names as keys and sub-dicts describing days,
        description, compression, and chunk interval information.
    """
    logger.info("retention_policy_summary_requested")
    return {
        "raw": {
            "tier": RetentionTier.RAW.value,
            "retention_days": RETENTION_RAW_DAYS,
            "description": "Raw events in surveillance.events hypertable",
            "compression_after_days": COMPRESSION_AFTER_DAYS,
            "chunk_interval_days": CHUNK_INTERVAL_DAYS,
        },
        "aggregated": {
            "tier": RetentionTier.AGGREGATED.value,
            "retention_days": RETENTION_AGGREGATED_DAYS,
            "description": "Continuous aggregates and materialized views",
            "compression_after_days": COMPRESSION_AFTER_DAYS,
            "chunk_interval_days": CHUNK_INTERVAL_DAYS,
        },
        "summary": {
            "tier": RetentionTier.SUMMARY.value,
            "retention_days": RETENTION_SUMMARY_DAYS,
            "description": "Curated long-term summaries",
        },
    }


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "CHUNK_INTERVAL_DAYS",
    "COMPRESSION_AFTER_DAYS",
    "RETENTION_AGGREGATED_DAYS",
    "RETENTION_RAW_DAYS",
    "RETENTION_SUMMARY_DAYS",
    "RetentionTier",
    "calculate_retention_until",
    "get_retention_days",
    "get_retention_policy_summary",
]