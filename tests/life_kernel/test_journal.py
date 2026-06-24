"""Tests for persistent JournalWriter (T2).

The JournalWriter wraps a PostgresAuditJournal to produce structured
reflective journal entries during the reflect phase. It must be fail-soft:
DB failure never crashes the kernel.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.life_kernel.journal import JournalWriter


@pytest.fixture
def mock_audit_journal():
    """Mock PostgresAuditJournal backend."""
    journal = MagicMock()
    journal.record = AsyncMock(return_value="audit-001")
    return journal


@pytest.fixture
def journal_writer(mock_audit_journal):
    return JournalWriter(audit_journal=mock_audit_journal)


@pytest.mark.asyncio
async def test_journal_writer_creates_entry(journal_writer, mock_audit_journal):
    """JournalWriter must create a structured journal entry and return a dict."""
    state = {
        "cycle_count": 100,
        "current_phase": "reflect",
        "current_focus": "finance_review",
    }

    result = await journal_writer.write_entry(
        state=state,
        reasoning="Chose to review finance records due to recurring pattern",
        lessons_learned="Pattern matching in observations improves recall relevance",
        confidence=0.85,
    )

    # Returns a dict suitable for state journal_entries reducer
    assert isinstance(result, dict)
    assert result["entry_id"] == "audit-001"
    assert result["cycle"] == 100
    assert "finance" in result["reasoning"]
    mock_audit_journal.record.assert_called_once()
    call_args = mock_audit_journal.record.call_args[0][0]
    assert call_args["entry_type"] == "journal"
    assert call_args["cycle"] == 100
    assert call_args["phase"] == "reflect"
    assert "finance" in call_args["reasoning"]
    assert call_args["lessons_learned"].startswith("Pattern matching")
    assert call_args["confidence"] == 0.85


@pytest.mark.asyncio
async def test_journal_writer_handles_failure_gracefully(journal_writer, mock_audit_journal):
    """JournalWriter must not crash the kernel on write failure."""
    mock_audit_journal.record.side_effect = Exception("DB error")

    state = {"cycle_count": 100}

    # Should not raise, returns None on failure
    result = await journal_writer.write_entry(
        state=state,
        reasoning="Test",
        lessons_learned="Test",
        confidence=0.5,
    )

    assert result is None


@pytest.mark.asyncio
async def test_journal_writer_returns_dict_for_state_update(journal_writer):
    """JournalWriter.write_entry returns a dict suitable for state update."""
    state = {"cycle_count": 42}
    result = await journal_writer.write_entry(
        state=state,
        reasoning="test",
        lessons_learned="test",
        confidence=0.7,
    )
    # Returns the entry dict with entry_id for state journal_entries list
    assert isinstance(result, dict)
    assert "entry_id" in result
    assert result["cycle"] == 42
