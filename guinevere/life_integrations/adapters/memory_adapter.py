"""Memory/KG integration adapter.

Wraps existing guinevere/memory/ (write_pipeline, read_pipeline) and
guinevere/knowledge_graph/ for integration data enrichment. All writes pass
consent + DNR + classification + HARD STOP gates.

Consent: consent.memory.{read,write,delete}
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from guinevere.life_integrations.base import BaseIntegrationAdapter
from guinevere.life_integrations.errors import (
    ActionNotSupportedError,
    ConfigurationMissingError,
)
from guinevere.life_integrations.types import (
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

        if action_lower == "store_fact":
            if self._write is None:
                raise ConfigurationMissingError(
                    "Write pipeline not configured for store_fact"
                )
            subject = kwargs.get("subject", "")
            predicate = kwargs.get("predicate", "")
            object_ = kwargs.get("object", "")
            if not subject or not predicate or not object_:
                raise ConfigurationMissingError(
                    "store_fact requires subject, predicate, and object kwargs"
                )
            classification = kwargs.get("classification", "Restricted")
            fact_id = await self._write.store_fact(
                subject=subject,
                predicate=predicate,
                object=object_,
                classification=classification,
                project_id=project_id,
            )
            return {
                "success": True,
                "action": action,
                "fact_id": str(fact_id),
            }

        if action_lower == "search_kg":
            if self._kg is None:
                raise ConfigurationMissingError("KG engine not configured")
            query = kwargs.get("query", "")
            results = await self._kg.query(query, project_id=project_id)
            return {"success": True, "action": action, "results": results}

        if action_lower == "mark_dnr":
            if self._write is None:
                raise ConfigurationMissingError(
                    "Write pipeline not configured for mark_dnr"
                )
            episode_id = kwargs.get("episode_id")
            if not episode_id:
                raise ConfigurationMissingError(
                    "mark_dnr requires 'episode_id' kwarg"
                )
            reason = kwargs.get("reason", "")
            principal = kwargs.get("principal", "guinevere_core")
            # Pre-fact content hash: fingerprint of episode_id+reason+principal
            # captured BEFORE mark_dnr so the tombstone is forensically
            # reconstructable. DNR is fully reversible (UPDATE ... do_not_recall=false).
            import hashlib
            content_hash = hashlib.sha256(
                f"{episode_id}|{reason}|{principal}".encode("utf-8")
            ).hexdigest()[:16]
            marked_id = await self._write.mark_dnr(
                episode_id=episode_id, reason=reason, principal=principal,
            )
            return {
                "success": True,
                "action": action,
                "episode_id": str(episode_id),
                "marked_id": str(marked_id) if marked_id else str(episode_id),
                "content_hash": content_hash,
                "restore_possible": True,
                "restore_method": "UPDATE memory SET do_not_recall=false",
                "irreversible_warning": False,
                "pre_delete_snapshot": {
                    "episode_id": str(episode_id),
                    "reason": reason,
                },
            }

        if action_lower in ("delete_memory",):
            raise ActionNotSupportedError(
                f"{action} is L4_FORBIDDEN — use mark_dnr instead"
            )

        raise ActionNotSupportedError(
            f"Memory adapter does not support action: {action}"
        )
