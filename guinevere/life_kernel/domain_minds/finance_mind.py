"""Finance domain mind (LK-013) for the Living Autonomy Kernel.

FinanceMind is a read-only / record-only financial observer.  It can classify,
summarise, and detect anomalies in transaction observations, but it **MUST NOT**
execute payments, transfers, withdrawals, investments, or trades in v1.  Real
ML classification and anomaly detection are deferred to future milestones;
v1 uses deterministic keyword matching and threshold-based heuristics.
"""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, TypedDict, cast

import structlog

from guinevere.life_kernel.domain_minds.durability import (
    DurabilityBackend,
    InMemoryJournal,
    PostgresAuditJournal,
)

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

FINANCE_CATEGORIES: tuple[str, ...] = (
    "income",
    "expense:food",
    "expense:transport",
    "expense:bills",
    "expense:entertainment",
    "expense:shopping",
    "expense:health",
    "expense:subscription",
    "expense:other",
    "investment",
    "transfer",
    "unknown",
)

BLOCKED_FINANCE_ACTIONS: frozenset[str] = frozenset(
    {"pay", "transfer", "withdraw", "invest", "trade"}
)

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "expense:food": [
        "grab",
        "foodpanda",
        "restaurant",
        "cafe",
        "coffee",
        "lunch",
        "dinner",
        "breakfast",
        "snack",
        "grocery",
        "supermarket",
        "makan",
    ],
    "expense:transport": [
        "bts",
        "mrt",
        "grabcar",
        "gojek",
        "uber",
        "taxi",
        "bus",
        "train",
        "fuel",
        "parking",
        "toll",
        "transport",
    ],
    "expense:bills": [
        "electricity",
        "water",
        "internet",
        "phone",
        "rent",
        "bill",
        "insurance",
        "tax",
        "pln",
    ],
    "expense:entertainment": [
        "netflix",
        "spotify",
        "cinema",
        "movie",
        "concert",
        "game",
        "entertainment",
    ],
    "expense:shopping": [
        "amazon",
        "shopee",
        "tokopedia",
        "lazada",
        "shop",
        "retail",
        "clothing",
        "electronics",
    ],
    "expense:health": [
        "hospital",
        "clinic",
        "pharmacy",
        "doctor",
        "dentist",
        "medicine",
        "health",
        "fitness",
        "gym",
    ],
    "income": [
        "salary",
        "wage",
        "bonus",
        "dividend",
        "refund",
        "deposit",
        "freelance",
        "income",
        "gaji",
    ],
    "expense:subscription": [
        "subscription",
        "membership",
        "monthly",
        "yearly",
        "saas",
    ],
    "investment": [
        "stock",
        "bond",
        "crypto",
        "bitcoin",
        "etf",
        "mutual fund",
        "trading",
        "investment",
    ],
    "transfer": [
        "transfer",
        "sent to",
        "received from",
        "wire",
        "bank transfer",
        "top up",
    ],
}


def create_finance_durability(
    mode: str = "production",
    dsn: str | None = None,
) -> DurabilityBackend:
    """Create the appropriate durability backend for FinanceMind.

    Args:
        mode: "production" uses PostgresAuditJournal, "test" uses InMemoryJournal.
        dsn: Optional PostgreSQL DSN override.

    Returns:
        A DurabilityBackend instance configured for the requested mode.
    """
    if mode == "production":
        return PostgresAuditJournal(dsn=dsn or "postgresql+asyncpg://guinevere_core@localhost:5433/guinevere_core")
    return InMemoryJournal()


class FinanceState(TypedDict, total=False):
    """State representation of a single recorded financial observation."""

    transaction_id: str
    amount: float
    currency: str
    description: str
    category: str
    source: str
    timestamp: str
    status: str


def _safe_float(value: object) -> float | None:
    """Convert a numeric-like value to float, or return None."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    if isinstance(value, Decimal):
        return float(value)
    return None


class FinanceMind:
    """Read-only / record-only finance domain mind.

    FinanceMind observes financial transactions, classifies them, generates
    summaries, and flags anomalies.  It never executes financial actions.

    Args:
        hermes_brain: Optional brain bridge for future ML classification and
            anomaly detection.  In v1 this is stored but not used.
    """

    ALLOWED_PERIODS: frozenset[str] = frozenset({"daily", "weekly", "monthly"})
    DURABILITY_SOURCE: str = "finance_mind"

    def __init__(
        self,
        hermes_brain: object | None = None,
        durability: DurabilityBackend | None = None,
        mode: str = "production",
    ) -> None:
        self.hermes_brain: object | None = hermes_brain
        self.durability: DurabilityBackend = durability or create_finance_durability(mode=mode)
        self._transactions: list[FinanceState] = []
        self._log: Any = logger.bind(mind="finance")

    @property
    def transactions(self) -> list[FinanceState]:
        """Return the list of recorded transactions (read-only view)."""
        return list(self._transactions)

    def _generate_transaction_id(self) -> str:
        return f"txn_{uuid.uuid4().hex[:16]}"

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _normalise_text(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]", " ", text.lower()).strip()

    async def record_transaction(self, transaction: dict[str, object]) -> dict[str, object]:
        """Record a transaction observation.

        Args:
            transaction: Dictionary containing at least ``amount``,
                ``currency``, ``description``, ``source``, and ``timestamp``.

        Returns:
            A result dictionary with ``status``, ``transaction_id``, and
            ``category`` keys.

        Raises:
            ValueError: If a required field is missing or invalid.
        """
        required = {"amount", "currency", "description", "source", "timestamp"}
        missing = required - transaction.keys()
        if missing:
            raise ValueError(f"Missing required fields: {sorted(missing)}")

        amount_value = transaction["amount"]
        amount = _safe_float(amount_value)
        if amount is None:
            raise ValueError(f"amount must be numeric: {amount_value}")

        currency = str(transaction["currency"]).strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError(f"currency must be a 3-letter code: {currency}")

        description = str(transaction["description"]).strip()
        if not description:
            raise ValueError("description must be non-empty")

        source = str(transaction["source"]).strip()
        timestamp = str(transaction["timestamp"]).strip()

        category = self.classify_transaction(transaction)

        record: FinanceState = {
            "transaction_id": self._generate_transaction_id(),
            "amount": amount,
            "currency": currency,
            "description": description,
            "category": category,
            "source": source,
            "timestamp": timestamp,
            "status": "recorded",
        }

        self._transactions.append(record)

        journal_entry = dict(record)
        journal_entry["source"] = self.DURABILITY_SOURCE
        await self.durability.record(journal_entry)

        self._log.info(
            "finance.transaction_recorded",
            transaction_id=record["transaction_id"],
            amount=amount,
            currency=currency,
            category=category,
            source=source,
        )

        return {
            "status": "recorded",
            "transaction_id": record["transaction_id"],
            "category": category,
        }

    async def replay(self) -> list[FinanceState]:
        """Reload transactions from the durability backend.

        Returns:
            The list of restored ``FinanceState`` records.
        """
        entries = await self.durability.list_entries(self.DURABILITY_SOURCE)
        self._transactions = [cast(FinanceState, dict(entry)) for entry in entries]
        self._log.info("finance.replay", restored=len(self._transactions))
        return list(self._transactions)

    async def health(self) -> bool:
        """Return ``True`` if the durability backend is healthy."""
        return await self.durability.health()

    def classify_transaction(self, transaction: dict[str, object]) -> str:
        """Classify a transaction into one of the known categories.

        Classification uses deterministic keyword matching on the description
        and source fields.  The hermes brain is not consulted in v1.

        Args:
            transaction: Transaction-like dictionary.  Uses ``description``
                and ``source`` keys if present.

        Returns:
            A category string such as ``expense:food`` or ``income``.
        """
        text_parts = [
            str(transaction.get("description", "")),
            str(transaction.get("source", "")),
        ]
        text = self._normalise_text(" ".join(text_parts))

        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                return category

        return "unknown"

    def summarize(self, period: str = "daily") -> dict[str, object]:
        """Generate a financial summary for the requested period.

        Args:
            period: One of ``daily``, ``weekly``, or ``monthly``.  The actual
                period filtering is deferred to v1; the summary aggregates all
                recorded transactions.

        Returns:
            Summary dictionary with totals, net, and per-category breakdown.
        """
        if period not in self.ALLOWED_PERIODS:
            raise ValueError(f"Unsupported period: {period}")

        total_income = 0.0
        total_expenses = 0.0
        by_category: dict[str, float] = defaultdict(float)

        for txn in self._transactions:
            category = txn.get("category", "unknown")
            amount = txn.get("amount", 0.0)
            by_category[category] += amount

            if category == "income":
                total_income += amount
            else:
                total_expenses += amount

        summary: dict[str, object] = {
            "period": period,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net": total_income - total_expenses,
            "by_category": dict(by_category),
            "transaction_count": len(self._transactions),
        }

        self._log.info(
            "finance.summary_generated",
            period=period,
            transaction_count=summary["transaction_count"],
            net=summary["net"],
        )
        return summary

    def detect_anomalies(self, transactions: list[dict[str, object]]) -> list[dict[str, object]]:
        """Detect anomalies in a list of transaction observations.

        Detects:
            * unusually large amounts (>= 3x the average amount),
            * duplicate transaction descriptions within the same list,
            * unexpected categories (category == ``unknown``).

        Args:
            transactions: List of transaction dictionaries.  Each dictionary
                should contain ``transaction_id`` and ``amount``; ``category``
                and ``description`` are optional.

        Returns:
            List of anomaly dictionaries.
        """
        anomalies: list[dict[str, object]] = []

        if not transactions:
            return anomalies

        amounts: list[float] = []
        for txn in transactions:
            amount = _safe_float(txn.get("amount", 0.0))
            amounts.append(amount if amount is not None else 0.0)

        average = sum(amounts) / len(amounts) if amounts else 0.0
        seen_descriptions: dict[str, dict[str, object]] = {}

        for idx, txn in enumerate(transactions):
            txn_id = str(txn.get("transaction_id", f"txn_unknown_{idx}"))
            amount = amounts[idx]
            description = str(txn.get("description", ""))
            category = str(txn.get("category", "unknown"))

            if average > 0 and amount >= average * 3:
                anomalies.append(
                    {
                        "transaction_id": txn_id,
                        "anomaly_type": "unusually_large_amount",
                        "severity": "high",
                        "description": (
                            f"Amount {amount:.2f} is >= 3x the average "
                            f"({average:.2f})"
                        ),
                    }
                )

            norm_desc = self._normalise_text(description)
            if norm_desc:
                if norm_desc in seen_descriptions:
                    anomalies.append(
                        {
                            "transaction_id": txn_id,
                            "anomaly_type": "duplicate_transaction",
                            "severity": "medium",
                            "description": (
                                f"Duplicate description with "
                                f"{seen_descriptions[norm_desc]['transaction_id']}"
                            ),
                        }
                    )
                else:
                    seen_descriptions[norm_desc] = {
                        "transaction_id": txn_id,
                        "description": description,
                    }

            if category == "unknown":
                anomalies.append(
                    {
                        "transaction_id": txn_id,
                        "anomaly_type": "unexpected_category",
                        "severity": "low",
                        "description": "Category could not be determined",
                    }
                )

        self._log.info("finance.anomalies_detected", count=len(anomalies))
        return anomalies

    async def execute_action(self, action: dict[str, object]) -> dict[str, object]:
        """Dispatch a finance-domain action.

        Allowed read-only / record-only actions: ``record``, ``summarize``,
        ``detect_anomalies``.  Destructive financial actions are blocked.

        Args:
            action: Action dictionary with an ``action`` key and optional
                ``payload`` / ``period`` keys.

        Returns:
            Result dictionary with ``status``, ``action``, ``result``, and
            optional ``reason``.
        """
        action_name = str(action.get("action", "")).strip().lower()

        if action_name in BLOCKED_FINANCE_ACTIONS:
            self._log.warning(
                "finance.blocked_action",
                action=action_name,
                reason="destructive financial actions are blocked in v1",
            )
            return {
                "status": "blocked",
                "action": action_name,
                "result": {},
                "reason": "destructive financial actions are blocked in v1",
            }

        payload_raw = action.get("payload")
        payload: dict[str, object] = (
            cast(dict[str, object], payload_raw) if isinstance(payload_raw, dict) else {}
        )
        result: dict[str, object] = {}

        if action_name == "record":
            result = await self.record_transaction(payload)
        elif action_name == "summarize":
            result = self.summarize(str(action.get("period", "daily")))
        elif action_name == "detect_anomalies":
            txns = action.get("transactions")
            txns = txns if isinstance(txns, list) else []
            result = {"anomalies": self.detect_anomalies(txns)}
        else:
            self._log.warning("finance.unknown_action", action=action_name)
            return {
                "status": "blocked",
                "action": action_name,
                "result": {},
                "reason": "unknown action",
            }

        return {
            "status": "executed",
            "action": action_name,
            "result": result,
        }
