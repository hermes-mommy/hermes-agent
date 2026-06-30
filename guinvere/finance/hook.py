"""Finance Hermes Hook — intercepts messages from #finance channel.

This module:
- Monitors #finance channel for messages from Faiz
- Parses messages using FinanceParser
- Stores transactions in PostgreSQL
- Updates the dashboard embed

Registration:
    Add to Hermes config or register via plugin system.
"""

from __future__ import annotations

import os
import re
import uuid
from typing import Any, Optional

import structlog

from guinvere.finance.parser import FinanceParser
from guinvere.finance.db import FinanceDB

logger = structlog.get_logger(__name__)

# Finance channel ID
FINANCE_CHANNEL_ID = "1513833533032894494"

# Patterns that indicate this is NOT a finance message (skip these)
SKIP_PATTERNS = [
    r'^/finance',  # Commands
    r'^!',  # Bot commands
    r'^\?',  # Questions
    r'help',  # Help requests
    r'status',  # Status checks
]


class FinanceHook:
    """Hermes hook for finance message processing."""

    def __init__(self):
        """Initialize finance hook."""
        self.parser = FinanceParser()
        self.db = FinanceDB()

    def should_process(self, message: str, channel_id: str, author_id: str) -> bool:
        """Determine if a message should be processed as a finance message.

        Args:
            message: The message text.
            channel_id: The channel ID.
            author_id: The author's user ID.

        Returns:
            True if the message should be processed.
        """
        # Only process messages from #finance channel
        if channel_id != FINANCE_CHANNEL_ID:
            return False

        # Skip empty or very short messages
        if not message or len(message.strip()) < 3:
            return False

        # Skip commands and help requests
        for pattern in SKIP_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return False

        # Check if it looks like a finance message (has a number)
        if not re.search(r'\d+', message):
            return False

        return True

    def process(self, message: str, channel_id: str, author_id: str) -> Optional[dict[str, Any]]:
        """Process a finance message.

        Args:
            message: The message text.
            channel_id: The channel ID.
            author_id: The author's user ID.

        Returns:
            Dictionary with result, or None if not processed.
        """
        if not self.should_process(message, channel_id, author_id):
            return None

        # Parse the message
        result = self.parser.parse(message)

        if not result.is_finance:
            logger.debug("finance_hook_not_finance", message=message[:50])
            return None

        # Determine account
        account_id = None
        accounts = self.db.get_accounts()

        # First, try to use account from parser (e.g., "dari s", "pakai blu")
        if result.account and accounts:
            matched = [a for a in accounts if a['name'].lower() == result.account.lower()]
            if matched:
                account_id = matched[0]['id']
                logger.info("finance_account_matched", account=result.account, account_id=account_id)

        # Fallback to default (first bank account)
        if account_id is None and accounts:
            bank_accounts = [a for a in accounts if a['type'] == 'bank']
            if bank_accounts:
                account_id = bank_accounts[0]['id']
            else:
                account_id = accounts[0]['id']

        # Determine to_account for transfers and income destination
        to_account_id = None
        if result.to_account and accounts:
            matched = [a for a in accounts if a['name'].lower() == result.to_account.lower()]
            if matched:
                to_account_id = matched[0]['id']
                logger.info("finance_to_account_matched", to_account=result.to_account, to_account_id=to_account_id)

        # For income with to_account, set account_id to the destination
        if result.type == "income" and to_account_id:
            account_id = to_account_id
            to_account_id = None  # Not needed for income

        # Insert transaction
        tx_id = self.db.insert_transaction(
            tx_type=result.type,
            amount=result.amount,
            description=result.description,
            category=result.category,
            account_id=account_id,
            to_account_id=to_account_id,
            raw_message=result.raw_message,
            project_id=None,  # Hook operates on raw Discord channel; project_id is set by caller
        )

        if tx_id:
            logger.info(
                "finance_hook_transaction_recorded",
                tx_id=tx_id,
                type=result.type,
                amount=result.amount,
                category=result.category,
                confidence=result.confidence,
            )

            # Trigger dashboard update
            self._update_dashboard()

            return {
                "success": True,
                "transaction_id": tx_id,
                "type": result.type,
                "amount": result.amount,
                "category": result.category,
                "description": result.description,
            }

        logger.warning("finance_hook_insert_failed", message=message[:50])
        return {"success": False, "error": "Failed to insert transaction"}

    def _update_dashboard(self):
        """Update dashboard synchronously — waits for completion before returning.

        This ensures the dashboard embed is updated BEFORE the caller
        proceeds to delete the source Discord message.
        """
        import subprocess  # noqa: S404, PLC0415
        import sys  # noqa: PLC0415

        script_path = os.path.expanduser("~/code/guinevere/scripts/finance_dashboard_update.py")
        if os.path.exists(script_path):
            try:
                result = subprocess.run(  # noqa: S603, S607
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    logger.info(
                        "finance_dashboard_updated",
                        stdout=result.stdout.strip()[:200],
                    )
                else:
                    logger.warning(
                        "finance_dashboard_update_failed",
                        returncode=result.returncode,
                        stderr=result.stderr.strip()[:200],
                    )
            except subprocess.TimeoutExpired:
                logger.warning("finance_dashboard_update_timeout", timeout=30)
            except Exception:
                logger.exception("finance_hook_dashboard_update_failed")


# Global instance
_finance_hook: Optional[FinanceHook] = None


def get_finance_hook() -> FinanceHook:
    """Get or create the global finance hook instance."""
    global _finance_hook
    if _finance_hook is None:
        _finance_hook = FinanceHook()
    return _finance_hook


def on_message(message: str, channel_id: str, author_id: str) -> Optional[dict[str, Any]]:
    """Hermes hook entry point. Called for every message.

    Returns:
        Dictionary with result if processed, None otherwise.
    """
    hook = get_finance_hook()
    return hook.process(message, channel_id, author_id)
