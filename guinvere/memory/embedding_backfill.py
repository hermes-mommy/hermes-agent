"""P3 Post-P19 Fix: Idempotent embedding backfill for episodes with NULL embedding.

Reads episodes from ``memory.episodes`` that have a non-NULL ``raw_content``
but NULL ``embedding``, computes 1536-dim embeddings via the 9Router-native
``EmbeddingService``, and updates the ``embedding`` column.

Design:
- Idempotent: safe to re-run; only touches rows where embedding IS NULL.
- Batch-limited: processes at most ``batch_size`` rows per invocation.
- Progress-logged: metadata-only logging (row count, errors, duration).
- Graceful degradation: if the embedding API is unreachable, logs and exits.
- Non-destructive: never modifies content, classification, or DNR flags.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update

from guinvere.memory.embeddings import EmbeddingService, RESTRICTED
from guinvere.memory.models import Episodes

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 50
"""Maximum number of episodes to backfill per invocation."""


@dataclass
class BackfillResult:
    """Typed result from :func:`backfill_null_embeddings`."""

    total_scanned: int = 0
    """Total episodes with NULL embedding scanned this run."""

    backfilled: int = 0
    """Episodes successfully backfilled this run."""

    skipped_no_content: int = 0
    """Episodes skipped because ``raw_content`` is NULL or empty."""

    errors: int = 0
    """Per-episode errors (logged, not re-raised)."""

    remaining: int | None = None
    """Estimated remaining NULL-embedding episodes after this batch (None = unknown)."""


async def backfill_null_embeddings(
    session,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    embedding_service: EmbeddingService | None = None,
) -> BackfillResult:
    """Backfill NULL embedding for episodes with non-NULL raw_content.

    Parameters
    ----------
    session:
        SQLAlchemy ``AsyncSession`` bound to the Guinevere database.
    batch_size:
        Maximum number of episodes to process in this invocation. Default 50.
    embedding_service:
        Optional pre-configured ``EmbeddingService``.  If ``None``, a default
        instance is created (reads ``GUINEVERE_9ROUTER_API_KEY`` from env).

    Returns
    -------
    BackfillResult
        Summary with counts of scanned, backfilled, skipped, errors, remaining.
    """
    if embedding_service is None:
        embedding_service = EmbeddingService()

    result = BackfillResult()

    # Query: non-DNR episodes with non-NULL raw_content but NULL embedding.
    stmt = (
        select(Episodes)
        .where(Episodes.embedding.is_(None))
        .where(Episodes.raw_content.isnot(None))
        .where(Episodes.do_not_recall.is_(False))
        .limit(batch_size)
    )
    exec_result = await session.execute(stmt)
    episodes = list(exec_result.scalars().all())
    result.total_scanned = len(episodes)

    if not episodes:
        logger.info("embedding_backfill_nothing_to_do")
        return result

    for ep in episodes:
        raw_content = ep.raw_content
        if not raw_content or not raw_content.strip():
            result.skipped_no_content += 1
            continue

        classification = getattr(ep, "classification", RESTRICTED)
        if not isinstance(classification, str):
            classification = RESTRICTED

        try:
            vector = embedding_service.embed(
                raw_content,
                classification=classification,
            )
            ep.embedding = vector
            session.add(ep)
            result.backfilled += 1
        except Exception as exc:
            result.errors += 1
            logger.warning(
                "embedding_backfill_episode_failed",
                extra={
                    "episode_id": str(ep.id),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )

    await session.flush()

    # Count remaining NULL-embedding episodes for progress tracking.
    try:
        from sqlalchemy import func as _func
        count_stmt = select(_func.count()).select_from(Episodes).where(
            Episodes.embedding.is_(None),
            Episodes.raw_content.isnot(None),
            Episodes.do_not_recall.is_(False),
        )
        count_result = await session.execute(count_stmt)
        remaining = count_result.scalar()
        result.remaining = remaining if isinstance(remaining, int) else None
    except Exception:
        logger.debug("embedding_backfill_remaining_count_failed", exc_info=True)
        result.remaining = None

    logger.info(
        "embedding_backfill_complete",
        extra={
            "scanned": result.total_scanned,
            "backfilled": result.backfilled,
            "skipped_no_content": result.skipped_no_content,
            "errors": result.errors,
            "remaining": result.remaining,
        },
    )

    return result


async def backfill_all_null_embeddings(
    session_factory,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_batches: int = 20,
    embedding_service: EmbeddingService | None = None,
) -> BackfillResult:
    """Run backfill in a loop until no more NULL-embedding episodes remain.

    Parameters
    ----------
    session_factory:
        Callable returning an async session.
    batch_size:
        Episodes per batch. Default 50.
    max_batches:
        Maximum number of batches (safety limit). Default 20 (1000 episodes).
    embedding_service:
        Optional pre-configured EmbeddingService.

    Returns
    -------
    BackfillResult
        Aggregated summary across all batches.
    """
    if embedding_service is None:
        embedding_service = EmbeddingService()

    aggregated = BackfillResult()

    for batch_num in range(1, max_batches + 1):
        async with session_factory() as session:
            batch_result = await backfill_null_embeddings(
                session,
                batch_size=batch_size,
                embedding_service=embedding_service,
            )
            aggregated.total_scanned += batch_result.total_scanned
            aggregated.backfilled += batch_result.backfilled
            aggregated.skipped_no_content += batch_result.skipped_no_content
            aggregated.errors += batch_result.errors

            if batch_result.total_scanned == 0:
                logger.info(
                    "embedding_backfill_all_done",
                    extra={"batches": batch_num, "total_backfilled": aggregated.backfilled},
                )
                break

            logger.info(
                "embedding_backfill_batch_done",
                extra={
                    "batch": batch_num,
                    "batch_backfilled": batch_result.backfilled,
                    "total_backfilled": aggregated.backfilled,
                    "remaining": batch_result.remaining,
                },
            )

    aggregated.remaining = None  # Aggregate; per-batch remaining is tracked above
    return aggregated