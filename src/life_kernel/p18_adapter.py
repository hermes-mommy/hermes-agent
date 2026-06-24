"""P18 Memory recall adapter for the Living Autonomy Kernel.

This adapter lets the life-mind kernel ask the Memory subsystem (P18) for
relevant past memories given a contextual observation. When a real
``memory_client`` callable is injected (wrapping
``src.memory.read_pipeline.recall_memories`` with a pre-bound session, as
wired in ``src/core/main.py``), the adapter calls it and normalises the
results (``safe_content``→``content``, ``combined_score``→``relevance``,
``created_at``→``timestamp``). When no client is injected, or recall
fails, the adapter returns ``_degraded: True`` with empty results so the
kernel runs headless without crashing (graceful offline fallback).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class MemoryRecallAdapter:
    """Real P18 memory recall adapter for the life-mind kernel.

    ``memory_client`` is an async callable accepting ``query_text=``,
    ``principal=``, ``exclude_dnr=`` kwargs (matching ``recall_memories``),
    returning a list of result dicts with ``safe_content``/``combined_score``/
    ``created_at``. When ``None``, recall degrades gracefully.

    Attributes:
        memory_client: Optional async recall callable wired to the real P18
            read pipeline. When ``None`` the adapter is offline.
    """

    def __init__(self, memory_client: Any | None = None) -> None:
        """Initialize the adapter with an optional real memory recall callable.

        Args:
            memory_client: Optional async callable wrapping the P18
                ``recall_memories`` read pipeline. Defaults to ``None``
                (offline/degraded).
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
