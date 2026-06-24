"""JournalWriter for persistent reflective entries.

Wraps PostgresAuditJournal to produce structured journal entries during
the reflect phase. Fail-soft: DB failure never crashes the kernel.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class JournalWriter:
    """Creates reflective journal entries via PostgresAuditJournal.

    Args:
        audit_journal: PostgresAuditJournal instance (or compatible).
    """

    def __init__(self, audit_journal: Any) -> None:
        self._audit_journal = audit_journal

    async def write_entry(
        self,
        state: dict[str, Any],
        reasoning: str,
        lessons_learned: str,
        confidence: float,
    ) -> dict[str, Any] | None:
        """Write a journal entry and return a dict for state update.

        Args:
            state: Current kernel state (cycle_count, current_phase, etc.)
            reasoning: Why this action was chosen
            lessons_learned: What was learned
            confidence: 0.0-1.0 confidence score

        Returns:
            Dict with entry_id, cycle, reasoning, lessons_learned, confidence
            (suitable for journal_entries reducer), or None on failure.
        """
        try:
            entry = {
                "entry_type": "journal",
                "cycle": state.get("cycle_count", 0),
                "phase": state.get("current_phase", "unknown"),
                "focus": state.get("current_focus"),
                "reasoning": reasoning,
                "lessons_learned": lessons_learned,
                "confidence": confidence,
                "timestamp": datetime.utcnow().isoformat(),
            }

            entry_id = await self._audit_journal.record(entry)
            entry["entry_id"] = entry_id

            logger.info("journal_entry_written", entry_id=entry_id, cycle=entry["cycle"])
            return entry

        except Exception as e:
            logger.warning("journal_entry_failed", error=str(e), exc_info=True)
            return None
