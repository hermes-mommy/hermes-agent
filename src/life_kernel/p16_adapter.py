"""P16 Knowledge Graph recall adapter for the Living Autonomy Kernel.

This module provides a lightweight, placeholder-aware adapter that lets the
life-mind kernel ask the Knowledge Graph (P16) for relevant concepts given a
contextual observation.  Real KG traversal is intentionally stubbed; wiring to
``src.knowledge_graph`` is deferred to a later milestone.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class KGRecallAdapter:
    """Placeholder adapter for Knowledge Graph concept recall.

    When a real ``kg_client`` is provided it will be used by future
    implementations.  For now the adapter always returns deterministic mock
    results so that ``DecisionContextBuilder`` and downstream graph nodes can be
    tested without a live KG backend.

    Attributes:
        kg_client: Optional KG client/repository instance.  Currently unused.
    """

    def __init__(self, kg_client: Any | None = None) -> None:
        """Initialize the adapter with an real or placeholder KG client.

        Args:
            kg_client: Optional KG client.  Defaults to ``None``.
        """
        self.kg_client = kg_client

    async def recall(self, context: dict[str, Any]) -> dict[str, Any]:
        """Return relevance-scored KG concepts related to the provided context.

        When ``kg_client`` is a callable (expected to wrap the real P16
        query surface with a pre-bound session), calls it with
        ``query_text=`` and transforms the result list into a
        standardised ``concepts`` list. When ``kg_client`` is ``None``,
        returns ``_degraded: True`` with empty results (graceful offline
        fallback).

        Args:
            context: Observation/decision context used to seed the recall query.

        Returns:
            Dict with keys ``concepts`` (list), ``count`` (int), and
            optionally ``_degraded`` (bool) when recall failed or is
            unavailable. Never raises.
        """
        if self.kg_client is None:
            logger.warning("kg_recall_no_client")
            return {
                "concepts": [],
                "count": 0,
                "_degraded": True,
                "_timestamp": datetime.now().isoformat(),
            }

        try:
            query_text = str(context.get("query", context.get("content", "")))

            # kg_client is a pre-bound recall_fn (session baked in by
            # core/main.py), accepting (query_text=, ...) kwargs.
            results = await self.kg_client(query_text=query_text)

            # Normalise: each result must expose name, relevance, source.
            concepts = []
            for r in results:
                if isinstance(r, dict):
                    name = r.get("name") or r.get("display_name") or str(r.get("entity_id", ""))
                    relevance = float(r.get("relevance", r.get("score", 0.0)))
                    source = str(r.get("source", "p16"))
                else:
                    name = str(getattr(r, "name", ""))
                    relevance = float(getattr(r, "relevance", 0.0))
                    source = str(getattr(r, "source", "p16"))
                concepts.append({"name": name, "relevance": relevance, "source": source})

            logger.info("kg_recall_success", count=len(concepts))
            return {
                "concepts": concepts,
                "count": len(concepts),
                "_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.warning("kg_recall_degraded", error=str(e))
            return {
                "concepts": [],
                "count": 0,
                "_degraded": True,
                "_timestamp": datetime.now().isoformat(),
            }
