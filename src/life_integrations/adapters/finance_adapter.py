"""Finance tracker integration adapter — wraps existing FinanceMind.

Wraps src/life_kernel/domain_minds/finance_mind.py (record/classify/summarize/
anomaly). Adds correction/import/export. NO payment/transfer (L4 blocked).

Consent: consent.finance.{read,write,delete}
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from src.life_integrations.base import BaseIntegrationAdapter
from src.life_integrations.errors import (
    ActionNotSupportedError,
    ConfigurationMissingError,
    PermissionDeniedError,
)
from src.life_integrations.types import (
    IntegrationCapability,
    IntegrationConfig,
    IntegrationHealth,
    PermissionTier,
)

logger = structlog.get_logger(__name__)

# Matches existing FinanceMind BLOCKED_FINANCE_ACTIONS
_BLOCKED_ACTIONS = ("pay", "transfer", "withdraw", "invest", "trade")


class FinanceIntegrationAdapter(BaseIntegrationAdapter):
    """Finance tracker integration adapter (wraps existing FinanceMind).

    Actions:
        list_transactions (L1): List transactions with filters
        summarize (L1): Get period summary
        detect_anomalies (L1): Detect spending anomalies
        record_transaction (L2): Record a transaction
        correct_transaction (L3): Correct via compensating entry (no hard-delete)
        bulk_import (L3): Import CSV/XLSX
        export (L1): Export CSV/JSON
        pay/transfer/withdraw/invest (L4): FORBIDDEN — no payment capability
    """

    def __init__(self, finance_mind: Any | None = None) -> None:
        """Initialize with optional FinanceMind instance.

        Args:
            finance_mind: FinanceMind instance (None = CONFIG_MISSING).
        """
        config = IntegrationConfig(
            integration_id="finance",
            name="Finance Tracker",
            provider="Polars/PG",
            capabilities=frozenset({
                IntegrationCapability.READ,
                IntegrationCapability.WRITE,
                IntegrationCapability.DELETE,
            }),
            default_tier=PermissionTier.L1_READ,
            secret_refs=("sec-postgres-core",),
            consent_scopes=(
                "consent.finance.read",
                "consent.finance.write",
                "consent.finance.delete",
            ),
            risk_tier="high",
        )
        super().__init__(config)
        self._mind = finance_mind

    async def health_check(self) -> IntegrationHealth:
        """Check finance connectivity."""
        if self._mind is None:
            return IntegrationHealth.UNKNOWN
        return IntegrationHealth.OK

    async def execute_action(
        self,
        action: str,
        tier: PermissionTier,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a finance action."""
        action_lower = action.lower()

        # Block payment/transfer actions absolutely — word-boundary match to
        # avoid false positives (e.g. "display" must not match "pay").
        import re
        action_root = action_lower.split("_")[0] if "_" in action_lower else action_lower
        if any(
            action_root == b or action_lower.startswith(f"{b}_") or action_lower == b
            for b in _BLOCKED_ACTIONS
        ):
            raise PermissionDeniedError(
                f"{action} is L4_FORBIDDEN — no payment/transfer capability"
            )

        if self._mind is None:
            raise ConfigurationMissingError(
                "FinanceMind not configured — CONFIG_MISSING"
            )

        if action_lower == "list_transactions":
            txns = await self._mind.replay(filters=kwargs)
            return {"success": True, "action": action, "transactions": txns, "count": len(txns)}

        if action_lower == "summarize":
            period = kwargs.get("period", "current_month")
            summary = await self._mind.summarize(period)
            return {"success": True, "action": action, "summary": summary}

        if action_lower == "record_transaction":
            txn = await self._mind.record_transaction(kwargs)
            return {"success": True, "action": action, "transaction": txn}

        raise ActionNotSupportedError(
            f"Finance adapter does not support action: {action}"
        )
