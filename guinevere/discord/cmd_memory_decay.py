"""Discord /memory-decay command implementation for Guinevere (P18).

Shows active forgetting statistics and tier decay rates. Queries archived
episodes and reads decay configuration from memory modules.

Usage:
    /memory-decay
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from .colors import WARNING
from ._embed_utils import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    now_wib_str,
    send_denied,
    to_discord_embed,
)

logger = structlog.get_logger()


# ── Constants ───────────────────────────────────────────────────────────────

DECAY_TITLE: str = "\U0001f4c9 Memory Decay"
DECAY_DESC: str = "Statistik active forgetting dan decay rate per tier Mommy."
DECAY_FAIL_DESC: str = "Gagal mengambil statistik decay memori."
FOOTER_ICON: str = "\U0001f4c9 Active Forgetting"


@dataclass(frozen=True)
class DecayStats:
    """Aggregated decay/archival statistics."""

    total_archived: int
    working_archived: int
    episodic_archived: int
    semantic_archived: int
    untyped_archived: int


# ── Database Operation ──────────────────────────────────────────────────────


async def _fetch_decay_stats(session_factory: Any) -> DecayStats | None:
    """Query archived episodes grouped by tier.

    Args:
        session_factory: Async SQLAlchemy session factory.

    Returns:
        DecayStats or None on failure.
    """
    try:
        from sqlalchemy import text

        async with session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT "
                    "  COUNT(*) AS total_archived, "
                    "  COUNT(*) FILTER (WHERE tier = 'working') AS working_archived, "
                    "  COUNT(*) FILTER (WHERE tier = 'episodic') AS episodic_archived, "
                    "  COUNT(*) FILTER (WHERE tier = 'semantic') AS semantic_archived, "
                    "  COUNT(*) FILTER (WHERE tier IS NULL) AS untyped_archived "
                    "FROM memory.episodes "
                    "WHERE archived = true AND tier IS NOT NULL OR archived = true"
                )
            )
            row = result.fetchone()
            if row is None:
                return None

            return DecayStats(
                total_archived=row[0],
                working_archived=row[1],
                episodic_archived=row[2],
                semantic_archived=row[3],
                untyped_archived=row[4],
            )
    except Exception:
        logger.exception("memory_decay_db_error")
        return None


# ── Decay Config Reader ─────────────────────────────────────────────────────


def _get_decay_config() -> dict[str, Any]:
    """Read decay configuration from memory modules.

    Returns:
        Dict with threshold, tier rates, and sweep config.
    """
    try:
        from guinevere.memory.consolidation import (
            ACTIVE_FORGETTING_THRESHOLD,
            DECAY_SWEEP_INTERVAL_HOURS,
            DECAY_SWEEP_HOUR,
            DECAY_SWEEP_MINUTE,
        )
        from guinevere.memory.tiers import TIER_DECAY_RATES, MemoryTier

        tier_rates = {}
        for tier_enum, rate in TIER_DECAY_RATES.items():
            tier_rates[tier_enum.value] = rate

        return {
            "threshold": ACTIVE_FORGETTING_THRESHOLD,
            "tier_rates": tier_rates,
            "sweep_interval_hours": DECAY_SWEEP_INTERVAL_HOURS,
            "sweep_hour": DECAY_SWEEP_HOUR,
            "sweep_minute": DECAY_SWEEP_MINUTE,
        }
    except Exception:
        logger.exception("memory_decay_config_error")
        return {
            "threshold": 0.1,
            "tier_rates": {"working": 0.3, "episodic": 0.05, "semantic": 0.01},
            "sweep_interval_hours": 6,
            "sweep_hour": 0,
            "sweep_minute": 0,
        }


# ── Embed Builder ───────────────────────────────────────────────────────────


def _build_embed_data(
    stats: DecayStats | None, config: dict[str, Any]
) -> EmbedData:
    """Build embed data from decay stats and config."""
    ts = now_wib_str()

    if stats is None:
        return EmbedData(
            title=DECAY_TITLE,
            description=DECAY_FAIL_DESC,
            color=WARNING,
            fields=(EmbedField(
                name="\u274c Error",
                value="Could not retrieve decay statistics.",
                inline=False,
            ),),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    tier_rates = config.get("tier_rates", {})
    working_rate = tier_rates.get("working", 0.3)
    episodic_rate = tier_rates.get("episodic", 0.05)
    semantic_rate = tier_rates.get("semantic", 0.01)
    threshold = config.get("threshold", 0.1)
    sweep_hours = config.get("sweep_interval_hours", 6)

    fields = (
        EmbedField(
            name="\U0001f4cb Total Archived",
            value=str(stats.total_archived),
            inline=True,
        ),
        EmbedField(
            name="\U0001f7e2 Working Archived",
            value=str(stats.working_archived),
            inline=True,
        ),
        EmbedField(
            name="\U0001f535 Episodic Archived",
            value=str(stats.episodic_archived),
            inline=True,
        ),
        EmbedField(
            name="\U0001f7e3 Semantic Archived",
            value=str(stats.semantic_archived),
            inline=True,
        ),
        EmbedField(
            name="\u2699\ufe0f Untyped Archived",
            value=str(stats.untyped_archived),
            inline=True,
        ),
        EmbedField(
            name="\U0001f4cf Forgetting Threshold",
            value=f"{threshold}",
            inline=True,
        ),
        EmbedField(
            name="\U0001f4c9 Working Decay",
            value=f"{working_rate}/day",
            inline=True,
        ),
        EmbedField(
            name="\U0001f4c9 Episodic Decay",
            value=f"{episodic_rate}/day",
            inline=True,
        ),
        EmbedField(
            name="\U0001f4c9 Semantic Decay",
            value=f"{semantic_rate}/day",
            inline=True,
        ),
        EmbedField(
            name="\U0001f504 Sweep Interval",
            value=f"Every {sweep_hours}h",
            inline=True,
        ),
        EmbedField(
            name="\U0001f552 Timestamp",
            value=ts,
            inline=False,
        ),
    )
    return EmbedData(
        title=DECAY_TITLE,
        description=DECAY_DESC,
        color=WARNING,
        fields=fields,
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


# ── Callback ────────────────────────────────────────────────────────────────


async def memory_decay_callback(interaction: Any) -> None:
    """Handle a ``/memory-decay`` interaction.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        bot = getattr(interaction, "client", None)
        if bot is None or not hasattr(bot, "get_session_factory"):
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Database session not available.",
            )
            return

        session_factory = bot.get_session_factory()
        if session_factory is None:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Database URL not configured.",
            )
            return

        stats = await _fetch_decay_stats(session_factory)
        config = _get_decay_config()
        data = _build_embed_data(stats, config)
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("memory_decay_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Memory decay stats are temporarily unavailable.",
        )


__all__ = ["memory_decay_callback"]
