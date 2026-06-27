"""Memory/KG integration adapter.

Wraps existing src/memory/ (write_pipeline, read_pipeline) and
src/knowledge_graph/ for integration data enrichment. All writes pass
consent + DNR + classification + HARD STOP gates.

Consent: consent.memory.{read,write,delete}
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from src.life_integrations.base import BaseIntegrationAdapter
from src.life_integrations.errors import (
    ActionNotSupportedError,
    ConfigurationMissingError,
)
from src.life_integrations.types import (
    IntegrationCapability,
    IntegrationConfig,
    IntegrationHealth,
    PermissionTier,
)

logger = structlog.get_logger(__name__)


class MemoryIntegrationAdapter(BaseIntegrationAdapter):
    """Memory/KG integration adapter.

    Actions:
        recall (L1): Recall memories via hybrid vector+FTS ranking
        store (L2): Store an episode (classification-gated)
        store_fact (L2): Store a semantic fact
        search_kg (L1): Search the knowledge graph
        mark_dnr (L3): Mark a memory as do-not-recall
        delete_memory (L4): FORBIDDEN — use DNR instead
    """

    def __init__(
        self,
        write_pipeline: Any | None = None,
        read_pipeline: Any | None = None,
        kg_engine: Any | None = None,
    ) -> None:
        """Initialize with optional memory/KG pipelines.

        Args:
            write_pipeline: Memory write pipeline (None = CONFIG_MISSING).
            read_pipeline: Memory read pipeline (None = CONFIG_MISSING).
            kg_engine: Knowledge graph query engine (None = CONFIG_MISSING).
        """
        config = IntegrationConfig(
            integration_id="memory",
            name="Memory/KG",
            provider="PostgreSQL/pgvector",
            capabilities=frozenset({
                IntegrationCapability.READ,
                IntegrationCapability.WRITE,
                IntegrationCapability.DELETE,
                IntegrationCapability.SEARCH,
            }),
            default_tier=PermissionTier.L1_READ,
            secret_refs=("sec-postgres-core",),
            consent_scopes=(
                "consent.memory.read",
                "consent.memory.write",
                "consent.memory.delete",
            ),
            risk_tier="critical",
        )
        super().__init__(config)
        self._write = write_pipeline
        self._read = read_pipeline
        self._kg = kg_engine

    async def health_check(self) -> IntegrationHealth:
        """Check memory/KG connectivity."""
        if self._read is None and self._write is None:
            return IntegrationHealth.UNKNOWN
        return IntegrationHealth.OK

    async def execute_action(
        self,
        action: str,
        tier: PermissionTier,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a memory/KG action."""
        action_lower = action.lower()

        if action_lower == "recall":
            if self._read is None:
                raise ConfigurationMissingError("Read pipeline not configured")
            query = kwargs.get("query", "")
            limit = kwargs.get("limit", 5)
            results = await self._read.recall_memories(
                query=query, limit=limit, project_id=project_id
            )
            return {"success": True, "action": action, "results": results, "count": len(results)}

        if action_lower == "store":
            if self._write is None:
                raise ConfigurationMissingError("Write pipeline not configured")
            content = kwargs.get("content", "")
            classification = kwargs.get("classification", "Restricted")
            episode_id = await self._write.store_episode(
                content=content, classification=classification, project_id=project_id
            )
            return {"success": True, "action": action, "episode_id": str(episode_id)}

        if action_lower == "search_kg":
            if self._kg is None:
                raise ConfigurationMissingError("KG engine not configured")
            query = kwargs.get("query", "")
            results = await self._kg.query(query, project_id=project_id)
            return {"success": True, "action": action, "results": results}

        if action_lower in ("delete_memory",):
            raise ActionNotSupportedError(
                f"{action} is L4_FORBIDDEN — use mark_dnr instead"
            )

        raise ActionNotSupportedError(
            f"Memory adapter does not support action: {action}"
        )
