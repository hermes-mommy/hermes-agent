"""Discord /memory-review command implementation for Guinevere (P18).

Manually triggers an FSRS review of a specific memory episode with a
user-provided grade (again/hard/good/easy).

Usage:
    /memory-review memory_id:str grade:str
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog

from .colors import SUCCESS
from ._embed_utils import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    get_option_value,
    now_wib_str,
    send_denied,
    to_discord_embed,
)

logger = structlog.get_logger()


# ── Constants ───────────────────────────────────────────────────────────────

REVIEW_TITLE: str = "\U0001f504 Memory Review"
REVIEW_OK_DESC: str = "FSRS review applied, Darling."
REVIEW_FAIL_DESC: str = "Gagal memproses review memori."
FOOTER_ICON: str = "\U0001f504 FSRS Review"

GRADE_MAP: dict[str, int] = {
    "again": 1,
    "hard": 2,
    "good": 3,
    "easy": 4,
}


@dataclass(frozen=True)
class ReviewResult:
    """Result of a memory-review operation."""

    memory_id: str
    grade: str
    success: bool
    retrievability: float = 0.0
    next_review: str = ""
    error: str | None = None


# ── Database Operation ──────────────────────────────────────────────────────


async def _review_memory(
    session_factory: Any, memory_id: str, grade_str: str
) -> ReviewResult:
    """Perform an FSRS review on a specific memory episode.

    Args:
        session_factory: Async SQLAlchemy session factory.
        memory_id: UUID of the episode to review.
        grade_str: One of 'again', 'hard', 'good', 'easy'.

    Returns:
        ReviewResult with updated state or error.
    """
    grade_int = GRADE_MAP.get(grade_str)
    if grade_int is None:
        return ReviewResult(
            memory_id=memory_id,
            grade=grade_str,
            success=False,
            error=f"Invalid grade: {grade_str}. Use again/hard/good/easy.",
        )

    try:
        from sqlalchemy import text
        from guinvere.memory.spaced_repetition import FSRSScheduler

        async with session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT id, fsrs_state, retrievability, stability, "
                    "difficulty, last_reviewed_at, next_review_at "
                    "FROM memory.episodes WHERE id = :mid"
                ),
                {"mid": memory_id},
            )
            row = result.fetchone()
            if row is None:
                return ReviewResult(
                    memory_id=memory_id,
                    grade=grade_str,
                    success=False,
                    error="Memory episode not found.",
                )

            # Build a lightweight episode-like object for update_episode_state
            class _EpisodeRow:
                def __init__(self, row_data: Any) -> None:
                    self.id = row_data[0]
                    self.fsrs_state = row_data[1]
                    self.retrievability = row_data[2]
                    self.stability = row_data[3]
                    self.difficulty = row_data[4]
                    self.last_reviewed_at = row_data[5]
                    self.next_review_at = row_data[6]

            episode = _EpisodeRow(row)
            scheduler = FSRSScheduler()
            state = scheduler.update_episode_state(episode, grade_int)

            # Persist updated fields back to DB
            await session.execute(
                text(
                    "UPDATE episodes SET "
                    "fsrs_state = :fsrs_state, "
                    "last_reviewed_at = :last_reviewed_at, "
                    "next_review_at = :next_review_at, "
                    "retrievability = :retrievability, "
                    "stability = :stability, "
                    "difficulty = :difficulty, "
                    "updated_at = NOW() "
                    "WHERE id = :mid"
                ),
                {
                    "fsrs_state": episode.fsrs_state,
                    "last_reviewed_at": episode.last_reviewed_at,
                    "next_review_at": episode.next_review_at,
                    "retrievability": episode.retrievability,
                    "stability": episode.stability,
                    "difficulty": episode.difficulty,
                    "mid": memory_id,
                },
            )
            await session.commit()

            next_review_str = ""
            if episode.next_review_at is not None:
                nr = episode.next_review_at
                if isinstance(nr, datetime):
                    next_review_str = nr.strftime("%Y-%m-%d %H:%M WIB")
                else:
                    next_review_str = str(nr)

            retrievability = float(episode.retrievability or 0.0)

            logger.info(
                "memory_review_success",
                memory_id=memory_id,
                grade=grade_str,
                retrievability=retrievability,
            )
            return ReviewResult(
                memory_id=memory_id,
                grade=grade_str,
                success=True,
                retrievability=retrievability,
                next_review=next_review_str,
            )
    except Exception as exc:
        logger.exception("memory_review_db_error", memory_id=memory_id)
        return ReviewResult(
            memory_id=memory_id,
            grade=grade_str,
            success=False,
            error=str(exc),
        )


# ── Embed Builder ───────────────────────────────────────────────────────────


def _build_embed_data(result: ReviewResult) -> EmbedData:
    """Build embed data from a review result."""
    ts = now_wib_str()

    if result.success:
        fields = (
            EmbedField(name="\U0001f4cb Memory ID", value=f"`{result.memory_id}`", inline=True),
            EmbedField(name="\U0001f3af Grade", value=result.grade.upper(), inline=True),
            EmbedField(
                name="\U0001f4c8 Retrievability",
                value=f"{result.retrievability:.4f}",
                inline=True,
            ),
            EmbedField(
                name="\u23f0 Next Review",
                value=result.next_review or "N/A",
                inline=True,
            ),
            EmbedField(name="\U0001f552 Timestamp", value=ts, inline=False),
        )
        return EmbedData(
            title=REVIEW_TITLE,
            description=REVIEW_OK_DESC,
            color=SUCCESS,
            fields=fields,
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    fields = (
        EmbedField(name="\U0001f4cb Memory ID", value=f"`{result.memory_id}`", inline=True),
        EmbedField(name="\U0001f3af Grade", value=result.grade.upper(), inline=True),
        EmbedField(name="\u274c Error", value=result.error or "Unknown error", inline=False),
    )
    return EmbedData(
        title=REVIEW_TITLE,
        description=REVIEW_FAIL_DESC,
        color=SUCCESS,
        fields=fields,
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


# ── Callback ────────────────────────────────────────────────────────────────


async def memory_review_callback(interaction: Any) -> None:
    """Handle a ``/memory-review`` interaction.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        memory_id = get_option_value(interaction, "memory_id")
        if not memory_id:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Parameter ``memory_id`` diperlukan, Darling.",
            )
            return

        grade_str = get_option_value(interaction, "grade")
        if not grade_str:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Parameter ``grade`` diperlukan, Darling.",
            )
            return

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

        result = await _review_memory(session_factory, memory_id, grade_str)
        data = _build_embed_data(result)
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("memory_review_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Memory review is temporarily unavailable.",
        )


__all__ = ["memory_review_callback"]
