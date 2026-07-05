"""Finance Hermes Plugin — processes casual finance messages.

This plugin:
- Detects if a message is a finance transaction
- Parses the message using FinanceParser
- Stores the transaction in PostgreSQL
- Updates the #finance dashboard embed

Registration:
    Register via hermes config or plugin manifest.
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Optional

import structlog

from guinevere.finance.parser import FinanceParser, ParseResult
from guinevere.finance.db import FinanceDB

logger = structlog.get_logger(__name__)


class FinancePlugin:
    """Hermes plugin for casual finance tracking."""

    def __init__(self):
        """Initialize finance plugin."""
        self.parser = FinanceParser()
        self.db = FinanceDB()
        self._dashboard_msg_id: Optional[int] = None

    def process_message(
        self,
        message: str,
        channel_id: Optional[str] = None,
        project_id: Optional[uuid.UUID] = None,
    ) -> Optional[dict[str, Any]]:
        """Process a message and return finance data if applicable.

        Args:
            message: The raw message text from the user.
            channel_id: Optional channel ID for context.
            project_id: Optional project UUID. When set, the transaction is
                associated with this project (P19 multi-project context).
                When None, the transaction is recorded in legacy mode.

        Returns:
            Dictionary with parse result and transaction ID, or None if not finance.
        """
        # Parse the message
        result = self.parser.parse(message)

        if not result.is_finance:
            return None

        # Determine account (default to first bank account if not specified)
        account_id = None
        accounts = self.db.get_accounts()
        if accounts:
            # Default to Blu BCA (bank account)
            bank_accounts = [a for a in accounts if a['type'] == 'bank']
            if bank_accounts:
                account_id = bank_accounts[0]['id']
            else:
                account_id = accounts[0]['id']

        # Insert transaction
        tx_id = self.db.insert_transaction(
            tx_type=result.type,
            amount=result.amount,
            description=result.description,
            category=result.category,
            account_id=account_id,
            raw_message=result.raw_message,
            project_id=project_id,
        )

        if tx_id:
            logger.info(
                "finance_transaction_recorded",
                tx_id=tx_id,
                type=result.type,
                amount=result.amount,
                category=result.category,
            )

            return {
                "success": True,
                "transaction_id": tx_id,
                "type": result.type,
                "amount": result.amount,
                "category": result.category,
                "description": result.description,
                "confidence": result.confidence,
            }

        return {"success": False, "error": "Failed to insert transaction"}

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get data for the dashboard embed."""
        return self.db.get_dashboard_data()

    def format_dashboard_embed(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format dashboard data into Discord embed structure."""
        accounts = data.get("accounts", [])
        total_balance = data.get("total_balance", 0)
        today = data.get("today", {})
        week = data.get("week", {})
        categories = data.get("categories", [])
        debts = data.get("debts", [])
        total_debt = data.get("total_debt", 0)
        recent = data.get("recent_transactions", [])
        last_update = data.get("last_update", "")

        # Format account balances
        account_lines = []
        for acc in accounts:
            balance = float(acc['balance'])
            if acc['type'] == 'investment':
                account_lines.append(f"  📈 {acc['name']}: Rp {balance:,.0f}")
            else:
                account_lines.append(f"  🏦 {acc['name']}: Rp {balance:,.0f}")

        # Format today's transactions
        today_lines = []
        for tx in recent[:5]:
            if tx.get('wib_date') and str(tx['wib_date']) == str(today.get('wib_date', '')):
                amount = float(tx['amount'])
                prefix = "+" if tx['type'] == 'income' else "-"
                today_lines.append(f"  {tx['description'][:20]:20s} {prefix}{amount:,.0f}")

        # Format week summary
        week_income = float(week.get('total_income', 0))
        week_expense = float(week.get('total_expense', 0))
        week_net = float(week.get('net', 0))

        # Format categories
        cat_lines = []
        icons = {
            'Food': '🍽️', 'Transport': '🚗', 'Bills': '📱', 'Shopping': '🛍️',
            'Entertainment': '🎮', 'Health': '💊', 'Education': '📚',
            'Social': '🤝', 'Other': '📦'
        }
        for cat in categories[:5]:
            icon = icons.get(cat['category'], '📦')
            total = float(cat['total'])
            cat_lines.append(f"  {icon} {cat['category']}: Rp {total:,.0f}")

        # Format debts
        debt_lines = []
        for debt in debts[:5]:
            remaining = float(debt['remaining'])
            debt_lines.append(f"  ⚠️ {debt['person']}: Rp {remaining:,.0f}")

        # Build embed fields
        fields = [
            {
                "name": "📊 SALDO PER AKUN",
                "value": "\n".join(account_lines) + f"\n  ─────────────────\n  **TOTAL: Rp {total_balance:,.0f}**",
                "inline": False
            },
            {
                "name": f"📅 HARI INI",
                "value": "\n".join(today_lines) if today_lines else "  Belum ada transaksi",
                "inline": False
            },
            {
                "name": "📈 MINGGU INI",
                "value": f"  Pemasukan: +Rp {week_income:,.0f}\n  Pengeluaran: -Rp {week_expense:,.0f}\n  ─────────────────\n  **Net: Rp {week_net:,.0f}**",
                "inline": False
            },
            {
                "name": "📊 TOP KATEGORI (Bulan Ini)",
                "value": "\n".join(cat_lines) if cat_lines else "  Belum ada data",
                "inline": False
            },
            {
                "name": "💳 HUTANG",
                "value": "\n".join(debt_lines) + f"\n  ─────────────────\n  **Total: Rp {total_debt:,.0f}**",
                "inline": False
            },
            {
                "name": "🔄 5 TRANSAKSI TERAKHIR",
                "value": self._format_recent_transactions(recent),
                "inline": False
            },
        ]

        return {
            "title": "💰 FINANCE DASHBOARD — Faiz",
            "color": 0x00FF00,  # Green
            "fields": fields,
            "footer": {"text": f"Last update: {last_update}"},
        }

    def _format_recent_transactions(self, transactions: list[dict]) -> str:
        """Format recent transactions list."""
        if not transactions:
            return "  Belum ada transaksi"

        lines = []
        for tx in transactions[:5]:
            amount = float(tx['amount'])
            prefix = "+" if tx['type'] == 'income' else "-"
            date = tx.get('wib_date', '')
            desc = tx.get('description', '')[:15]
            lines.append(f"  {date} {desc:15s} {prefix}{amount:,.0f}")

        return "\n".join(lines)


# Global instance for Hermes integration
_finance_plugin: Optional[FinancePlugin] = None


def get_finance_plugin() -> FinancePlugin:
    """Get or create the global finance plugin instance."""
    global _finance_plugin
    if _finance_plugin is None:
        _finance_plugin = FinancePlugin()
    return _finance_plugin


def process_finance_message(
    message: str,
    channel_id: Optional[str] = None,
    project_id: Optional[uuid.UUID] = None,
) -> Optional[dict[str, Any]]:
    """Process a potential finance message. Called from Hermes hook or message handler.

    Args:
        message: The raw message text.
        channel_id: Optional channel ID for context.
        project_id: Optional project UUID for P19 multi-project awareness.
    """
    plugin = get_finance_plugin()
    return plugin.process_message(message, channel_id, project_id=project_id)
