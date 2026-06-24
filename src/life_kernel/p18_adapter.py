"""P18 Memory recall adapter for the Living Autonomy Kernel.

This module provides a lightweight, placeholder-aware adapter that lets the
life-mind kernel ask the Memory subsystem (P18) for relevant past memories
given a contextual observation.  Real memory recall is intentionally stubbed;
wiring to ``src.memory`` is deferred to a later milestone.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class MemoryRecallAdapter:
    """Placeholder adapter for Memory subsystem recall.

    When a real ``memory_client`` is provided it will be used by future
    implementations.  For now the adapter always returns deterministic mock
    results so that ``DecisionContextBuilder`` and downstream graph nodes can be
    tested without a live memory backend.

    Attributes:
        memory_client: Optional memory client/repository instance.  Currently
            unused.
    """

    def __init__(self, memory_client: Any | None = None) -> None:
        """Initialize the adapter with an optional memory client.

        Args:
            memory_client: Optional memory client.  Defaults to ``None``.
        """
        self.memory_client = memory_client

    async def recall(self, context: dict[str, Any]) -> dict[str, Any]:
        """Return relevance-scored memories related to the provided context.

        When ``memory_client`` is a callable (expected to wrap
        ``src.memory.read_pipeline.recall_memories`` with a pre-bound
        async session), calls it with ``query_text=`` and transforms the
        result list into a standardised ``memories`` list. When
        ``memory_client`` is ``None``, returns ``_degraded: True`` with
        empty results (graceful offline fallback).

        Args:
            context: Observation/decision context used to seed the recall query.

        Returns:
            Dict with keys ``memories`` (list), ``count`` (int), and
            optionally ``_degraded`` (bool) when recall failed or is
            unavailable. Never raises.
        """
        if self.memory_client is None:
            logger.warning("memory_recall_no_client")
            return {
                "memories": [],
                "count": 0,
                "_degraded": True,
                "_timestamp": datetime.now().isoformat(),
            }

        try:
            query_text = str(context.get("query", context.get("content", "")))

            # memory_client is a pre-bound recall_fn (session baked in by
            # core/main.py) that accepts the recall_memories keyword args.
            results = await self.memory_client(
                query_text=query_text,
                principal="guinevere_core",
                exclude_dnr=True,
            )

            # The real recall_memories returns a list[dict] with keys:
            # id, safe_content, classification, importance, created_at,
            # combined_score, is_summarized.
            memories = []
            for r in results:
                content = str(r.get("safe_content", ""))
                rel = float(r.get("combined_score", 0.0))
                created = r.get("created_at")
                ts = created.isoformat() if hasattr(created, "isoformat") else (str(created) if created else datetime.now().isoformat())
                memories.append({"content": content, "relevance": rel, "timestamp": ts})

            logger.info("memory_recall_success", count=len(memories))
            return {"memories": memories, "count": len(memories), "_timestamp": datetime.now().isoformat()}

        except Exception as e:
            logger.warning("memory_recall_degraded", error=str(e))
            return {"memories": [], "count": 0, "_degraded": True, "_timestamp": datetime.now().isoformat()}
