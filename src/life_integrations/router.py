"""P22 action router — central dispatch for integration actions.

Routes actions to the correct adapter after passing through:
1. Semantic classification (permission tier)
2. Consent gate (L2+ requires consent)
3. HARD STOP check (blocks all L2+)
4. Project context resolution
5. Audit logging

Domain minds call the router instead of adapters directly, preserving
V-002 (sensors-not-triggers) — actions go through decide_node priority engine.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from src.life_integrations.audit import AuditLogger
from src.life_integrations.consent import ConsentGate
from src.life_integrations.errors import (
    ActionNotSupportedError,
    ConsentDeniedError,
    HardStopBlockedError,
    PermissionDeniedError,
)
from src.life_integrations.permissions import SemanticActionClassifier
from src.life_integrations.project_context import ProjectContext
from src.life_integrations.registry import IntegrationRegistry
from src.life_integrations.types import PermissionTier

logger = structlog.get_logger(__name__)


class ActionRouter:
    """Central action dispatch for P22 integration actions.

    All integration actions flow through this router, ensuring:
    - Semantic tier classification (not AuthLevel-only)
    - Consent + HARD STOP enforcement
    - Project context propagation
    - Audit trail on every action

    Usage:
        router = ActionRouter(
            registry=registry,
            classifier=classifier,
            consent_gate=consent_gate,
            audit_logger=audit_logger,
            project_context=project_context,
        )
        result = await router.execute(
            integration_id="discord",
            action="send_message",
            project_id=project_id,
            kwargs={"channel_id": "123", "content": "hello"},
        )
    """

    def __init__(
        self,
        registry: IntegrationRegistry,
        classifier: SemanticActionClassifier | None = None,
        consent_gate: ConsentGate | None = None,
        audit_logger: AuditLogger | None = None,
        project_context: ProjectContext | None = None,
    ) -> None:
        """Initialize the action router.

        Args:
            registry: Integration registry for adapter lookup.
            classifier: Semantic action classifier (auto-created if None).
            consent_gate: Consent enforcement gate (auto-created if None).
            audit_logger: Audit logger (auto-created if None).
            project_context: Project context resolver (auto-created if None).
        """
        self._registry = registry
        self._classifier = classifier or SemanticActionClassifier()
        self._consent_gate = consent_gate or ConsentGate()
        self._audit_logger = audit_logger or AuditLogger()
        self._project_context = project_context or ProjectContext()

    async def execute(
        self,
        integration_id: str,
        action: str,
        project_id: uuid.UUID | None = None,
        consent_scope: str | None = None,
        actor_type: str = "system",
        actor_id: str = "agent:guinevere",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute an integration action through the full gate pipeline.

        Args:
            integration_id: Target integration (e.g., "discord").
            action: Action name (e.g., "send_message").
            project_id: Project UUID for scoping (default project if None).
            consent_scope: Override consent scope (auto-derived if None).
            actor_type: Who initiated (user/agent/system).
            actor_id: Actor identifier.
            **kwargs: Action-specific parameters passed to adapter.

        Returns:
            Dict with: success, action, integration_id, tier, result, event_id.

        Raises:
            PermissionDeniedError: L4 forbidden action.
            HardStopBlockedError: HARD STOP active.
            ConsentDeniedError: Consent not granted.
            ActionNotSupportedError: Adapter doesn't support action.
        """
        # Resolve project context
        resolved_project = await self._project_context.resolve_or_default(
            project_id
        )

        # Get adapter
        try:
            adapter = self._registry.get(integration_id)
        except KeyError as e:
            return {
                "success": False,
                "action": action,
                "integration_id": integration_id,
                "error": f"integration not registered: {e}",
                "tier": "UNKNOWN",
            }

        provider = adapter.config.provider

        # Classify action semantically (NOT AuthLevel-only). Pass integration_id
        # so the static tier map (keyed by integration_id) is consulted.
        classification = self._classifier.classify(
            provider=provider,
            action=action,
            integration_id=integration_id,
        )
        tier = classification.tier

        # Derive consent scope if not provided
        if consent_scope is None:
            consent_scope = self._derive_consent_scope(
                integration_id, action, tier
            )

        # Pass through consent + HARD STOP gate
        allowed, reason = await self._consent_gate.check(
            tier=tier,
            consent_scope=consent_scope,
            project_id=resolved_project,
        )

        if not allowed:
            # Log blocked action
            await self._audit_logger.log_action(
                integration_id=integration_id,
                provider=provider,
                action=action,
                tier=tier.name,
                project_id=resolved_project,
                result="blocked",
                actor_type=actor_type,
                actor_id=actor_id,
                metadata={"reason": reason, "scope": consent_scope},
            )

            # Raise appropriate error
            if "HARD STOP" in reason:
                raise HardStopBlockedError(reason)
            if "L4_FORBIDDEN" in reason:
                raise PermissionDeniedError(reason)
            raise ConsentDeniedError(reason)

        # Execute action via adapter
        try:
            result = await adapter.execute_action(
                action=action,
                tier=tier,
                project_id=resolved_project,
                **kwargs,
            )
        except ActionNotSupportedError:
            raise
        except Exception as e:
            # Log failure
            await self._audit_logger.log_action(
                integration_id=integration_id,
                provider=provider,
                action=action,
                tier=tier.name,
                project_id=resolved_project,
                result="failed",
                actor_type=actor_type,
                actor_id=actor_id,
                metadata={"error": str(e), "scope": consent_scope},
            )
            raise

        success = result.get("success", False)

        # Log successful action
        await self._audit_logger.log_action(
            integration_id=integration_id,
            provider=provider,
            action=action,
            tier=tier.name,
            project_id=resolved_project,
            result="success" if success else "failed",
            actor_type=actor_type,
            actor_id=actor_id,
            metadata={
                "scope": consent_scope,
                "classification": classification.method,
            },
        )

        result["tier"] = tier.name
        result["integration_id"] = integration_id
        return result

    async def dry_run(
        self,
        integration_id: str,
        action: str,
        project_id: uuid.UUID | None = None,
        consent_scope: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run the gate pipeline WITHOUT executing the adapter (A6).

        Performs classify -> derive_scope -> consent_gate.check but stops
        short of calling the adapter. No audit row is written. Returns
        {tier, consent_scope, allowed, reason, would_execute:False, ...}.
        """
        resolved_project = await self._project_context.resolve_or_default(
            project_id
        )
        try:
            adapter = self._registry.get(integration_id)
        except KeyError as e:
            return {
                "tier": "UNKNOWN",
                "consent_scope": consent_scope or "",
                "allowed": False,
                "reason": f"integration not registered: {e}",
                "error": f"integration not registered: {e}",
                "would_execute": False,
                "integration_id": integration_id,
                "action": action,
            }
        provider = adapter.config.provider
        classification = self._classifier.classify(
            provider=provider, action=action,
            integration_id=integration_id,
        )
        tier = classification.tier
        if consent_scope is None:
            consent_scope = self._derive_consent_scope(
                integration_id, action, tier
            )
        allowed, reason = await self._consent_gate.check(
            tier=tier,
            consent_scope=consent_scope,
            project_id=resolved_project,
        )
        return {
            "tier": tier.name,
            "consent_scope": consent_scope,
            "allowed": allowed,
            "reason": reason,
            "would_execute": False,
            "integration_id": integration_id,
            "action": action,
        }

    def _derive_consent_scope(
        self,
        integration_id: str,
        action: str,
        tier: PermissionTier,
    ) -> str:
        """Derive a consent scope from integration + action + tier.

        Args:
            integration_id: Integration ID.
            action: Action name.
            tier: Permission tier.

        Returns:
            Consent scope string (e.g., "consent.comms.discord.write").
        """
        tier_suffix = {
            PermissionTier.L1_READ: "read",
            PermissionTier.L2_WRITE: "write",
            PermissionTier.L3_DESTRUCTIVE: "delete",
            PermissionTier.L4_FORBIDDEN: "forbidden",
        }.get(tier, "read")

        # Map integration to domain
        domain_map = {
            "discord": "comms",
            "gmail": "comms",
            "whatsapp": "comms",
            "telegram": "comms",
            "github": "sourcecode",
            "calendar": "cloud",
            "drive": "cloud",
            "notion": "notes",
            "vps": "ops",
            "finance": "finance",
            "browser": "research",
            "memory": "memory",
            "filesystem": "filesystem",
        }
        if integration_id not in domain_map:
            logger.warning(
                "router.unknown_integration_domain",
                integration_id=integration_id,
                fallback="using integration_id as domain",
            )
        domain = domain_map.get(integration_id, integration_id)

        # A1 fix: canonical scope collapses to 3-segment when domain ==
        # integration_id (memory/finance/filesystem), matching the adapter
        # declarations; 4-segment otherwise. Without this collapse the derived
        # scope (e.g. consent.memory.memory.write) mismatches the adapter-declared
        # scope (consent.memory.write) and the exact-match consent SQL denies.
        if domain == integration_id:
            return f"consent.{domain}.{tier_suffix}"
        return f"consent.{domain}.{integration_id}.{tier_suffix}"
