"""P22 permission and action classification.

Enforces the L1-L4 permission tier model. L2/L3/L4 actions require
semantic classification (parsed intent + provider operation + side-effect
risk), NOT just AuthLevel. L1 (read) may use AuthLevel as sufficient gate.

This implements the P22-local SemanticActionClassifier scaffold until P23's
SemanticActionClassifier runtime lands (per P22 plan §AuthLevel gating boundary).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from guinevere.life_integrations.types import PermissionTier

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ActionClassification:
    """Result of classifying an action's risk tier.

    Attributes:
        tier: Determined permission tier (L1-L4).
        reason: Human-readable explanation of classification.
        method: How the tier was determined (static_map, semantic, hardcoded).
    """
    tier: PermissionTier
    reason: str
    method: str = "semantic"


class SemanticActionClassifier:
    """P22-local semantic action classifier.

    Classifies actions by parsed intent + provider operation + side-effect
    risk, NOT by MCP AuthLevel alone. This is the bridge classifier until
    P23's SemanticActionClassifier runtime lands.

    For L2/L3/L4 actions, the classifier examines:
    - provider operation (read/write/delete/admin)
    - side-effect risk (state change, reversibility, blast radius)
    - parsed intent from action name
    """

    # Static mapping for known provider operations
    _PROVIDER_TIER_MAP: dict[str, dict[str, PermissionTier]] = {
        "calendar": {
            "list_events": PermissionTier.L1_READ,
            "get_event": PermissionTier.L1_READ,
            "create_event": PermissionTier.L2_WRITE,
            "update_event": PermissionTier.L2_WRITE,
            "delete_event": PermissionTier.L3_DESTRUCTIVE,
            "delete_calendar": PermissionTier.L4_FORBIDDEN,
            "clear_calendar": PermissionTier.L4_FORBIDDEN,
        },
        "drive": {
            "list_files": PermissionTier.L1_READ,
            "get_file": PermissionTier.L1_READ,
            "create_file": PermissionTier.L2_WRITE,
            "update_file": PermissionTier.L2_WRITE,
            "trash_file": PermissionTier.L2_WRITE,
            "delete_file": PermissionTier.L3_DESTRUCTIVE,
            "empty_trash": PermissionTier.L4_FORBIDDEN,
            "public_share": PermissionTier.L3_DESTRUCTIVE,
        },
        "github": {
            "list_repos": PermissionTier.L1_READ,
            "get_file": PermissionTier.L1_READ,
            "create_issue": PermissionTier.L2_WRITE,
            "create_pr": PermissionTier.L2_WRITE,
            "merge_pr": PermissionTier.L3_DESTRUCTIVE,
            "delete_branch": PermissionTier.L3_DESTRUCTIVE,
            "delete_repo": PermissionTier.L4_FORBIDDEN,
            "force_push": PermissionTier.L4_FORBIDDEN,
        },
        "gmail": {
            "list_messages": PermissionTier.L1_READ,
            "get_message": PermissionTier.L1_READ,
            "send_message": PermissionTier.L2_WRITE,
            "trash_message": PermissionTier.L2_WRITE,
            "delete_label": PermissionTier.L3_DESTRUCTIVE,
            "permanent_delete": PermissionTier.L4_FORBIDDEN,
        },
        "discord": {
            "read_history": PermissionTier.L1_READ,
            "send_message": PermissionTier.L2_WRITE,
            "edit_message": PermissionTier.L2_WRITE,
            "delete_message": PermissionTier.L3_DESTRUCTIVE,
            "purge_messages": PermissionTier.L4_FORBIDDEN,
            "kick_member": PermissionTier.L4_FORBIDDEN,
        },
        "telegram": {
            "get_updates": PermissionTier.L1_READ,
            "send_message": PermissionTier.L2_WRITE,
            "delete_message": PermissionTier.L3_DESTRUCTIVE,
            "promote_member": PermissionTier.L4_FORBIDDEN,
        },
        "whatsapp": {
            "send_text": PermissionTier.L2_WRITE,
            "delete_for_everyone": PermissionTier.L3_DESTRUCTIVE,
            "promote_admin": PermissionTier.L4_FORBIDDEN,
        },
        "vps": {
            "list_containers": PermissionTier.L1_READ,
            "restart_container": PermissionTier.L2_WRITE,
            "remove_container": PermissionTier.L3_DESTRUCTIVE,
            "system_prune": PermissionTier.L4_FORBIDDEN,
        },
        "finance": {
            "list_transactions": PermissionTier.L1_READ,
            "record_transaction": PermissionTier.L2_WRITE,
            "correct_transaction": PermissionTier.L3_DESTRUCTIVE,
            "pay_transfer": PermissionTier.L4_FORBIDDEN,
        },
        "notion": {
            "retrieve_page": PermissionTier.L1_READ,
            "create_page": PermissionTier.L2_WRITE,
            "archive_page": PermissionTier.L3_DESTRUCTIVE,
            "delete_view": PermissionTier.L4_FORBIDDEN,
        },
        "browser": {
            "search": PermissionTier.L1_READ,
            "fetch_url": PermissionTier.L1_READ,
            "fill_form": PermissionTier.L2_WRITE,
            "click": PermissionTier.L2_WRITE,
        },
        "memory": {
            "recall": PermissionTier.L1_READ,
            "store": PermissionTier.L2_WRITE,
            "mark_dnr": PermissionTier.L3_DESTRUCTIVE,
            "delete_memory": PermissionTier.L4_FORBIDDEN,
        },
        "filesystem": {
            "read": PermissionTier.L1_READ,
            "list_dir": PermissionTier.L1_READ,
            "write": PermissionTier.L2_WRITE,
            "delete": PermissionTier.L3_DESTRUCTIVE,
        },
    }

    # Destructive action keywords (fallback when no static map entry)
    _DESTRUCTIVE_KEYWORDS = (
        "delete", "remove", "purge", "drop", "truncate", "destroy",
        "force_push", "force-push", "permanent_delete",
    )
    _FORBIDDEN_KEYWORDS = (
        "system_prune", "empty_trash", "clear_calendar", "delete_repo",
        "force_push", "kick", "ban", "promote_admin", "pay", "transfer",
        "withdraw", "invest", "flushall", "drop_table", "rm_rf",
    )
    _WRITE_KEYWORDS = (
        "create", "send", "write", "update", "edit", "modify", "append",
        "insert", "add", "set", "move", "archive", "trash", "record",
        "store", "store_fact",
    )

    def classify(
        self,
        provider: str,
        action: str,
        auth_level: str | None = None,
        integration_id: str | None = None,
        **context: Any,
    ) -> ActionClassification:
        """Classify an action's permission tier semantically.

        Args:
            provider: Integration provider display name (e.g., "Google", "GitHub", "Local").
            action: Action name (e.g., "delete_message").
            auth_level: MCP AuthLevel (informational only, not the gate).
            integration_id: Integration ID (e.g., "filesystem", "calendar").
                The static tier map is keyed by integration_id, so this is
                preferred for lookup when available. Falls back to provider.
            **context: Additional context (side_effects, reversibility).

        Returns:
            ActionClassification with determined tier and reason.

        Note:
            L1 (read) MAY use AuthLevel as sufficient gate. L2/L3/L4 MUST
            be classified semantically — AuthLevel-only gating is a hard FAIL.
        """
        action_lower = action.lower()

        # 1. Check static provider map first (most reliable). The map is keyed
        # by integration_id (e.g. "filesystem", "calendar"), so prefer
        # integration_id for lookup; fall back to provider for callers that
        # only pass the display-name provider.
        lookup_keys: tuple[str, ...] = ()
        if integration_id:
            lookup_keys = (integration_id.lower(), provider.lower())
        else:
            lookup_keys = (provider.lower(),)
        provider_map: dict[str, PermissionTier] = {}
        for _key in lookup_keys:
            _mapped = self._PROVIDER_TIER_MAP.get(_key)
            if _mapped:
                provider_map = _mapped
                break
        if action_lower in provider_map:
            tier = provider_map[action_lower]
            return ActionClassification(
                tier=tier,
                reason=f"static_map: {provider}.{action_lower}",
                method="static_map",
            )

        # 2. Semantic classification by keywords (fallback)
        if any(k in action_lower for k in self._FORBIDDEN_KEYWORDS):
            return ActionClassification(
                tier=PermissionTier.L4_FORBIDDEN,
                reason=f"semantic: forbidden keyword in '{action_lower}'",
                method="semantic",
            )

        if any(k in action_lower for k in self._DESTRUCTIVE_KEYWORDS):
            return ActionClassification(
                tier=PermissionTier.L3_DESTRUCTIVE,
                reason=f"semantic: destructive keyword in '{action_lower}'",
                method="semantic",
            )

        if any(k in action_lower for k in self._WRITE_KEYWORDS):
            return ActionClassification(
                tier=PermissionTier.L2_WRITE,
                reason=f"semantic: write keyword in '{action_lower}'",
                method="semantic",
            )

        # 3. Default to L2_WRITE for unknown actions (F04 brutal-audit fix)
        # Rationale: an unknown action must NOT silently bypass consent by
        # landing in L1_READ. L2_WRITE forces the consent gate (write-notify)
        # so any new/unmapped action is at least surfaced to the operator.
        # L4 would be too restrictive (blocks legitimate unknown reads).
        logger.warning(
            "classifier.unknown_action",
            action=action,
            provider=provider,
            tier="L2_WRITE",
            reason="unknown action — defaulting to L2_WRITE (consent required)",
        )
        return ActionClassification(
            tier=PermissionTier.L2_WRITE,
            reason=f"semantic: default L2_WRITE for unknown action '{action_lower}'",
            method="semantic_default",
        )

    def is_allowed(
        self,
        classification: ActionClassification,
        hard_stop_active: bool = False,
        consent_granted: bool = False,
    ) -> tuple[bool, str]:
        """Check if an action is allowed given current gates.

        Args:
            classification: The action's tier classification.
            hard_stop_active: Whether HARD STOP is currently active.
            consent_granted: Whether consent is granted for this scope.

        Returns:
            Tuple of (allowed, reason).
        """
        tier = classification.tier

        # L4 is always forbidden
        if tier == PermissionTier.L4_FORBIDDEN:
            return False, f"action tier L4_FORBIDDEN — never autonomous"

        # HARD STOP blocks all L2+ actions
        if hard_stop_active and tier >= PermissionTier.L2_WRITE:
            return False, "HARD STOP active — write/delete/execute blocked"

        # L3+ requires consent
        if tier >= PermissionTier.L3_DESTRUCTIVE and not consent_granted:
            return False, "L3 destructive action requires consent"

        # L2 requires consent (write-notify)
        if tier == PermissionTier.L2_WRITE and not consent_granted:
            return False, "L2 write action requires consent"

        return True, "allowed"
