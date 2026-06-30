"""Finance Database Layer — PostgreSQL operations for finance tracking.

This module handles:
- Account balance management
- Transaction CRUD operations
- Debt tracking and updates
- Financial reporting queries
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

# WIB timezone (UTC+7)
WIB = timezone(timedelta(hours=7))


class FinanceDB:
    """Database operations for personal finance tracking."""

    def __init__(self):
        """Initialize database connection."""
        self._conn = None
        self._connect()

    def _connect(self):
        """Establish PostgreSQL connection."""
        import psycopg2  # noqa: PLC0415

        # Parse DATABASE_URL from env
        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url:
            logger.error("finance_db_no_database_url")
            return

        # Extract connection params from asyncpg URL
        # Format: postgresql+asyncpg://user:pass@host:port/db
        try:
            # Remove asyncpg driver
            url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            self._conn = psycopg2.connect(url)
            self._conn.autocommit = True
            logger.info("finance_db_connected")
        except Exception:
            logger.exception("finance_db_connection_failed")
            self._conn = None

    def _ensure_conn(self):
        """Ensure connection is alive."""
        if self._conn is None or self._conn.closed:
            self._connect()

    def _execute(self, query: str, params: tuple = ()) -> Optional[list[dict[str, Any]]]:
        """Execute query and return results as list of dicts."""
        self._ensure_conn()
        if self._conn is None:
            return None

        try:
            with self._conn.cursor() as cur:
                cur.execute(query, params)
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    return [dict(zip(columns, row)) for row in cur.fetchall()]
                return []
        except Exception:
            logger.exception("finance_db_query_failed", query=query[:100])
            return None

    # =========================================================================
    # Account Operations
    # =========================================================================

    def get_accounts(self) -> list[dict[str, Any]]:
        """Get all active accounts."""
        result = self._execute(
            "SELECT id, name, type, balance, currency FROM finance.accounts WHERE is_active ORDER BY balance DESC"
        )
        return result or []

    def get_account_by_name(self, name: str) -> Optional[dict[str, Any]]:
        """Get account by name (case-insensitive)."""
        result = self._execute(
            "SELECT id, name, type, balance FROM finance.accounts WHERE LOWER(name) = LOWER(%s) AND is_active",
            (name,)
        )
        return result[0] if result else None

    def update_balance(self, account_id: int, amount: float, tx_type: str) -> bool:
        """Update account balance based on transaction type."""
        if tx_type == "income":
            query = "UPDATE finance.accounts SET balance = balance + %s, updated_at = NOW() WHERE id = %s"
        elif tx_type == "expense":
            query = "UPDATE finance.accounts SET balance = balance - %s, updated_at = NOW() WHERE id = %s"
        elif tx_type == "transfer":
            # Transfers don't change total balance, just move between accounts
            return True
        else:
            return False

        result = self._execute(query, (amount, account_id))
        return result is not None

    # =========================================================================
    # Transaction Operations
    # =========================================================================

    def insert_transaction(
        self,
        tx_type: str,
        amount: float,
        description: str,
        category: str,
        account_id: Optional[int] = None,
        to_account_id: Optional[int] = None,
        debt_id: Optional[int] = None,
        raw_message: Optional[str] = None,
        project_id: Optional[uuid.UUID] = None,
    ) -> Optional[int]:
        """Insert a new transaction and return its ID.

        Args:
            tx_type: Transaction type (income/expense/transfer/debt).
            amount: Transaction amount.
            description: Transaction description.
            category: Transaction category.
            account_id: Optional source account ID.
            to_account_id: Optional destination account ID.
            debt_id: Optional associated debt ID.
            raw_message: Original raw message text.
            project_id: Optional project UUID. When None, operates in legacy
                (non-project-aware) mode. When set, writes to the project_id column.

        Returns:
            The new transaction ID, or None on failure.
        """
        now = datetime.now(tz=WIB)
        wib_date = now.date()

        # Build INSERT dynamically so project_id is included only when set
        # (backward-compatible with rows that predate the column).
        columns = [
            "type", "amount", "description", "category",
            "account_id", "to_account_id", "debt_id",
            "raw_message", "wib_date",
        ]
        values: list[Any] = [
            tx_type, amount, description, category,
            account_id, to_account_id, debt_id,
            raw_message, wib_date,
        ]
        placeholders = ["%s"] * len(columns)

        if project_id is not None:
            columns.append("project_id")
            values.append(project_id)
            placeholders.append("%s")

        query = (
            f"INSERT INTO financial.transactions ({', '.join(columns)}) "
            f"VALUES ({', '.join(placeholders)}) RETURNING id"
        )

        result = self._execute(query, tuple(values))

        if result and len(result) > 0:
            tx_id = result[0]['id']

            # Update account balance
            if account_id:
                if tx_type in ("income", "expense"):
                    self.update_balance(account_id, amount, tx_type)
                elif tx_type == "transfer":
                    # Deduct from source account
                    self.update_balance(account_id, amount, "expense")
                    # Add to destination if specified
                    if to_account_id:
                        self.update_balance(to_account_id, amount, "income")

            return tx_id

        return None

    def get_transactions_today(self) -> list[dict[str, Any]]:
        """Get all transactions for today (WIB)."""
        today = datetime.now(tz=WIB).date()
        return self._execute(
            """SELECT t.*, a.name as account_name 
            FROM financial.transactions t 
            LEFT JOIN finance.accounts a ON t.account_id = a.id
            WHERE t.wib_date = %s 
            ORDER BY t.created_at DESC""",
            (today,)
        ) or []

    def get_transactions_this_week(self) -> list[dict[str, Any]]:
        """Get all transactions for this week (WIB, Monday-Sunday)."""
        now = datetime.now(tz=WIB)
        # Calculate Monday of this week
        monday = now.date() - timedelta(days=now.weekday())
        sunday = monday + timedelta(days=6)

        return self._execute(
            """SELECT t.*, a.name as account_name 
            FROM financial.transactions t 
            LEFT JOIN finance.accounts a ON t.account_id = a.id
            WHERE t.wib_date BETWEEN %s AND %s
            ORDER BY t.wib_date DESC, t.created_at DESC""",
            (monday, sunday)
        ) or []

    def get_transactions_this_month(self) -> list[dict[str, Any]]:
        """Get all transactions for this month (WIB)."""
        now = datetime.now(tz=WIB)
        first_day = now.replace(day=1).date()
        last_day = (now.replace(month=now.month % 12 + 1, day=1) - timedelta(days=1)).date() if now.month < 12 else now.replace(month=12, day=31).date()

        return self._execute(
            """SELECT t.*, a.name as account_name 
            FROM financial.transactions t 
            LEFT JOIN finance.accounts a ON t.account_id = a.id
            WHERE t.wib_date BETWEEN %s AND %s
            ORDER BY t.wib_date DESC, t.created_at DESC""",
            (first_day, last_day)
        ) or []

    def get_last_transactions(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get last N transactions."""
        return self._execute(
            """SELECT t.*, a.name as account_name 
            FROM financial.transactions t 
            LEFT JOIN finance.accounts a ON t.account_id = a.id
            ORDER BY t.created_at DESC 
            LIMIT %s""",
            (limit,)
        ) or []

    # =========================================================================
    # Summary Queries
    # =========================================================================

    def get_summary_today(self) -> dict[str, Any]:
        """Get today's financial summary."""
        today = datetime.now(tz=WIB).date()
        result = self._execute(
            """SELECT 
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as total_income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as total_expense,
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) - 
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as net,
                COUNT(*) as transaction_count
            FROM financial.transactions 
            WHERE wib_date = %s""",
            (today,)
        )
        if result:
            return result[0]
        return {"total_income": 0, "total_expense": 0, "net": 0, "transaction_count": 0}

    def get_summary_this_week(self) -> dict[str, Any]:
        """Get this week's financial summary."""
        now = datetime.now(tz=WIB)
        monday = now.date() - timedelta(days=now.weekday())
        sunday = monday + timedelta(days=6)

        result = self._execute(
            """SELECT 
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as total_income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as total_expense,
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) - 
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as net,
                COUNT(*) as transaction_count
            FROM financial.transactions 
            WHERE wib_date BETWEEN %s AND %s""",
            (monday, sunday)
        )
        if result:
            return result[0]
        return {"total_income": 0, "total_expense": 0, "net": 0, "transaction_count": 0}

    def get_category_summary_this_month(self) -> list[dict[str, Any]]:
        """Get category breakdown for this month."""
        now = datetime.now(tz=WIB)
        first_day = now.replace(day=1).date()

        return self._execute(
            """SELECT 
                category,
                SUM(amount) as total,
                COUNT(*) as count
            FROM financial.transactions 
            WHERE wib_date >= %s AND type = 'expense'
            GROUP BY category
            ORDER BY total DESC
            LIMIT 10""",
            (first_day,)
        ) or []

    # =========================================================================
    # Debt Operations
    # =========================================================================

    def get_active_debts(self) -> list[dict[str, Any]]:
        """Get all unsettled debts."""
        return self._execute(
            """SELECT id, person, amount, paid, remaining, description, direction
            FROM finance.debts 
            WHERE NOT is_settled 
            ORDER BY remaining DESC"""
        ) or []

    def add_debt_payment(self, debt_id: int, payment: float) -> bool:
        """Record a debt payment and check if settled."""
        result = self._execute(
            """UPDATE finance.debts 
            SET paid = paid + %s, updated_at = NOW(),
                is_settled = CASE WHEN (amount - paid - %s) <= 0 THEN TRUE ELSE FALSE END
            WHERE id = %s
            RETURNING id, person, remaining""",
            (payment, payment, debt_id)
        )
        return result is not None and len(result) > 0

    def get_total_debt(self) -> float:
        """Get total remaining debt."""
        result = self._execute(
            "SELECT COALESCE(SUM(remaining), 0) as total FROM finance.debts WHERE NOT is_settled"
        )
        return float(result[0]['total']) if result else 0.0

    # =========================================================================
    # Dashboard Data
    # =========================================================================

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get all data needed for the dashboard embed."""
        accounts = self.get_accounts()
        total_balance = sum(float(a['balance']) for a in accounts)

        today_summary = self.get_summary_today()
        week_summary = self.get_summary_this_week()
        category_summary = self.get_category_summary_this_month()
        debts = self.get_active_debts()
        total_debt = self.get_total_debt()
        recent_transactions = self.get_last_transactions(5)

        return {
            "accounts": accounts,
            "total_balance": total_balance,
            "today": today_summary,
            "week": week_summary,
            "categories": category_summary,
            "debts": debts,
            "total_debt": total_debt,
            "recent_transactions": recent_transactions,
            "last_update": datetime.now(tz=WIB).strftime("%d/%m/%Y %H:%M WIB"),
        }
