"""P16 Knowledge Graph recall adapter for the Living Autonomy Kernel.

This adapter lets the life-mind kernel ask the Knowledge Graph (P16) for
relevant concepts given a contextual observation. When a real ``kg_client``
callable is injected (wrapping ``KGQueryEngine.search_entities`` with a
pre-bound session, as wired in ``guinvere/core/main.py``), the adapter calls it
and normalises the results. When no client is injected, or recall fails,
the adapter returns ``_degraded: True`` with empty results so the kernel
runs headless without crashing (graceful offline fallback).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class KGRecallAdapter:
    """Real KG concept recall adapter for the life-mind kernel.

    ``kg_client`` is an async callable accepting ``query_text=`` (and
    optionally ``principal``/``exclude_dnr``) kwargs, returning a list of
    concept dicts/shapes (each exposing ``name``/``display_name``,
    ``relevance``, ``source``). When ``None``, recall degrades gracefully.

    Attributes:
        kg_client: Optional async recall callable wired to the real P16
            query surface. When ``None`` the adapter is offline.
    """

    def __init__(self, kg_client: Any | None = None) -> None:
        """Initialize the adapter with an optional real KG recall callable.

        Args:
            kg_client: Optional async callable wrapping the P16 query
                surface. Defaults to ``None`` (offline/degraded).
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

        When ``context`` contains a ``project_id``, the KG recall is
        scoped to that project's namespace (entities whose
        ``project_id == project_id OR project_scope == 'global'``).

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
            raw_pid = context.get("project_id")
            project_id: uuid.UUID | None = (
                uuid.UUID(str(raw_pid)) if raw_pid is not None else None
            )

            # kg_client is a pre-bound recall_fn (session baked in by
            # core/main.py), accepting (query_text=, ...) kwargs with
            # optional project_id keyword.
            results = await self.kg_client(
                query_text=query_text,
                project_id=project_id,
            )

            # Normalise: each result must expose name, relevance, source.
            concepts = []
            for r in results:
                if isinstance(r, dict):
                    name = r.get("name") or r.get("display_name") or str(r.get("entity_id", ""))
                    relevance = float(r.get("relevance", r.get("score", 0.0)))
                    source = str(r.get("source", "p16"))
                else:
                    # EntityMatch dataclass exposes display_name (not name).
                    name = str(
                        getattr(r, "display_name", None)
                        or getattr(r, "name", "")
                        or getattr(r, "entity_id", "")
                    )
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
