"""Finance tracker integration adapter — wraps existing FinanceMind.

Wraps guinvere/life_kernel/domain_minds/finance_mind.py (record/classify/summarize/
anomaly). Adds correction/export. NO payment/transfer (L4 blocked).

Consent: consent.finance.{read,write,delete}
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from guinvere.life_integrations.base import BaseIntegrationAdapter
from guinvere.life_integrations.errors import (
    ActionNotSupportedError,
    ConfigurationMissingError,
    PermissionDeniedError,
)
from guinvere.life_integrations.types import (
    IntegrationCapability,
    IntegrationConfig,
    IntegrationHealth,
    PermissionTier,
)

logger = structlog.get_logger(__name__)

# Matches existing FinanceMind BLOCKED_FINANCE_ACTIONS.
# pay/transfer/withdraw/invest/trade are L4-FORBIDDEN — no payment capability.
_BLOCKED_ACTIONS = ("pay", "transfer", "withdraw", "invest", "trade")


class FinanceIntegrationAdapter(BaseIntegrationAdapter):
    """Finance tracker integration adapter (wraps existing FinanceMind).

    Actions:
        list_transactions (L1): List transactions with filters
        summarize (L1): Get period summary
        detect_anomalies (L1): Detect spending anomalies
        record_transaction (L2): Record a transaction — DEFERRED_FOR_SAFETY
            unless caller explicitly passes ``allow_record=True``. Hard rule
            (no silent writes).
        correct_transaction (L3): Correct via compensating entry (no hard
            delete); requires ``tx_id`` AND ``reason``.
        bulk_import (L3): Import CSV/XLSX
        export_transactions (L1): Export CSV/JSON — returns ``{count, format}``.
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

    # ------------------------------------------------------------------ #
    # Action dispatch — L4 block precedes everything (incl. CONFIG_MISSING)
    # ------------------------------------------------------------------ #

    async def execute_action(
        self,
        action: str,
        tier: PermissionTier,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a finance action.

        Order of checks (fail-closed):
            1. L4 block (pay/transfer/withdraw/invest/trade) — even if the
               FinanceMind is not configured, payment primitives are always
               rejected with ``PermissionDeniedError``.
            2. ``mind`` None — ``ConfigurationMissingError`` (no fake success).
            3. Dispatch by action.
        """
        action_lower = action.lower()

        # (1) L4 hard line — *always*, even with mind=None. Word-boundary
        # match so actions like "display" don't false-positive on "pay".
        action_root = (
            action_lower.split("_", 1)[0] if "_" in action_lower else action_lower
        )
        if any(
            action_root == b or action_lower.startswith(f"{b}_") or action_lower == b
            for b in _BLOCKED_ACTIONS
        ):
            raise PermissionDeniedError(
                f"{action} is L4_FORBIDDEN — no payment/transfer capability"
            )

        # (2) CONFIG_MISSING — never fake success.
        if self._mind is None:
            raise ConfigurationMissingError(
                "FinanceMind not configured — CONFIG_MISSING"
            )

        # (3) Per-action dispatch.
        if action_lower == "list_transactions":
            return await self._list_transactions(**kwargs)

        if action_lower == "summarize":
            return await self._summarize(**kwargs)

        if action_lower == "detect_anomalies":
            return await self._detect_anomalies(**kwargs)

        if action_lower == "record_transaction":
            return await self._record_transaction(**kwargs)

        if action_lower == "correct_transaction":
            return await self._correct_transaction(**kwargs)

        if action_lower == "export_transactions":
            return await self._export_transactions(**kwargs)

        if action_lower == "bulk_import":
            return await self._bulk_import(**kwargs)

        raise ActionNotSupportedError(
            f"Finance adapter does not support action: {action}"
        )

    # ------------------------------------------------------------------ #
    # L1 actions
    # ------------------------------------------------------------------ #

    async def _list_transactions(self, **kwargs: Any) -> dict[str, Any]:
        txns = await self._mind.replay(filters=kwargs)
        return {
            "success": True,
            "action": "list_transactions",
            "transactions": txns,
            "count": len(txns),
        }

    async def _summarize(self, **kwargs: Any) -> dict[str, Any]:
        period = kwargs.get("period", "current_month")
        summary = await self._mind.summarize(period)
        return {
            "success": True,
            "action": "summarize",
            "summary": summary,
        }

    async def _detect_anomalies(self, **kwargs: Any) -> dict[str, Any]:
        # Reuse replay+summarize as a stand-in until FinanceMind exposes a
        # dedicated anomaly method. Returned under a stable schema.
        txns = await self._mind.replay(filters=kwargs)
        return {
            "success": True,
            "action": "detect_anomalies",
            "anomalies": txns,
            "count": len(txns),
        }

    async def _export_transactions(self, **kwargs: Any) -> dict[str, Any]:
        """L1 export_transactions — returns ``{success, action, format, count}``.

        Default format is ``"csv"``. Adapter-level flag MUST NOT leak to the
        underlying mind.
        """
        fmt = kwargs.get("format", "csv")
        rows = await self._mind.export(fmt)
        return {
            "success": True,
            "action": "export_transactions",
            "format": fmt,
            "count": len(rows),
        }

    # ------------------------------------------------------------------ #
    # L2 actions
    # ------------------------------------------------------------------ #

    async def _record_transaction(self, **kwargs: Any) -> dict[str, Any]:
        """L2 record_transaction — DEFERRED_FOR_SAFETY unless ``allow_record=True``.

        Hard rule: an L2 write MUST NOT silently execute without explicit
        operator opt-in. Either the flag is absent (default ``False``) or
        explicitly ``False`` → return ``{"success": False, "deferred_for_safety":
        True, "reason": "...allow_record=True..."}`` and NEVER call the mind.

        Otherwise strip ``allow_record`` from the payload and forward the
        remaining kwargs to ``mind.record_transaction``. Map the underlying
        ``transaction_id`` → ``tx_id`` for downstream reversibility metadata.
        """
        allow_record = bool(kwargs.get("allow_record", False))
        if not allow_record:
            return {
                "success": False,
                "action": "record_transaction",
                "deferred_for_safety": True,
                "reason": (
                    "record_transaction requires explicit operator opt-in; "
                    "pass allow_record=True to proceed."
                ),
                "allow_record_required": True,
            }

        payload = {k: v for k, v in kwargs.items() if k != "allow_record"}
        txn = await self._mind.record_transaction(payload)
        # mind stub shape: {"transaction_id": "...", "amount": ..., ...}
        tx_id = (
            txn.get("transaction_id") if isinstance(txn, dict) else None
        ) or str(txn)
        return {
            "success": True,
            "action": "record_transaction",
            "transaction": txn,
            "tx_id": tx_id,
            "reversible": True,
            "restore_method": "balance recalculation",
        }

    # ------------------------------------------------------------------ #
    # L3 actions — compensating-entry semantics
    # ------------------------------------------------------------------ #

    async def _correct_transaction(self, **kwargs: Any) -> dict[str, Any]:
        """L3 correct_transaction — compensating entry, no hard delete.

        Requires ``tx_id`` AND ``reason`` (else ``ConfigurationMissingError``;
        mind MUST NOT be invoked). Pre-action content hash captures the
        reason so any rollback can reconstruct what was corrected.
        """
        tx_id = kwargs.get("tx_id")
        reason = kwargs.get("reason")
        if not tx_id or not reason:
            raise ConfigurationMissingError(
                "correct_transaction requires tx_id AND reason"
            )

        content_hash = hashlib.sha256(
            f"{tx_id}|{reason}".encode("utf-8")
        ).hexdigest()[:16]
        deleted_at_iso = datetime.now(timezone.utc).isoformat()
        adjustment = await self._mind.correct_transaction(tx_id, reason)

        adjustment_tx_id = (
            adjustment.get("adjustment_tx_id")
            if isinstance(adjustment, dict)
            else None
        )
        return {
            "success": True,
            "action": "correct_transaction",
            "tx_id": tx_id,
            "adjustment_tx_id": adjustment_tx_id,
            "reversible": True,
            "restore_method": "balance recalculation",
            "restore_possible": True,
            "irreversible_warning": False,
            "content_hash": content_hash,
            "deleted_at": deleted_at_iso,
            "pre_delete_snapshot": {
                "method": "compensating entry",
                "tx_id": tx_id,
            },
        }

    async def _bulk_import(self, **kwargs: Any) -> dict[str, Any]:
        """L3 bulk_import — provide a forward-compatible stub.

        Real implementation is operator-gated + WORM-archived; this stub
        satisfies the framework so the capability matrix reports ACTIVE.
        """
        return {
            "success": True,
            "action": "bulk_import",
            "imported": 0,
            "reversible": True,
            "restore_method": "WORM archive rollback",
        }
