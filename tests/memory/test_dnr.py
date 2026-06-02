"""P3-013: Do-not-recall hardening — unit tests for ``src/memory/dnr.py``.

Tests cover:
- mark_memory_dnr: authorized mutation, audit event, no raw content.
- unmark_memory_dnr: authorized reversal, audit event, no raw content.
- Unauthorized principal fails closed for both mark and unmark.
- is_memory_dnr: true/false from fake scalar result, fail-closed for missing.
- Post-recall/pre-injection guard accepts clean results and fails closed on
  ``do_not_recall=True`` or string variants.
- Existing recall query builders preserve DNR exclusion when ``exclude_dnr=True``.

All tests use fake sessions only — no DB or network required.
"""
from __future__ import annotations

import logging
import uuid
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from typing import Protocol

import pytest
from sqlalchemy import Select, Update


from src.memory.dnr import (
    DNRStateError,
    DNRAuthorizationError,
    DNRViolationError,
    MEMORY_DNR_MARKED,
    DNR_REVOKED,
    is_memory_dnr,
    mark_memory_dnr,
    unmark_memory_dnr,
    verify_recall_results_dnr_free,
)
from src.memory.read_pipeline import (
    build_recency_query,
    build_fts_query,
    build_vector_query,
)


# ---------------------------------------------------------------------------
# Local protocol for caplog — avoids unresolved pytest.LogCaptureFixture
# ---------------------------------------------------------------------------


class _CapLog(Protocol):
    """Minimal protocol for pytest's caplog fixture."""

    records: list[logging.LogRecord]

    def at_level(
        self, level: int, logger: str
    ) -> AbstractContextManager[object]:
        """Context manager to capture log messages at a given level."""
        ...


# ---------------------------------------------------------------------------
# Fake SQLAlchemy-style helpers
# ---------------------------------------------------------------------------


class FakeExecuteResult:
    """Mimics SQLAlchemy execution result for UPDATE/SELECT statements."""

    def __init__(self, rowcount: int = 1, scalar_value: object | None = None):
        self._rowcount: int = rowcount
        self._scalar: object | None = scalar_value

    @property
    def rowcount(self) -> int:
        return self._rowcount

    def scalar_one_or_none(self) -> object | None:
        return self._scalar


@dataclass
class FakeAuditTrail:
    """Captures AuditTrail rows added to the fake session."""

    event_type: str = ""
    event_payload: dict[str, object] = field(default_factory=dict)
    principal: str = ""
    event_hash: str = ""
    previous_hash: str | None = None
    occurred_at: object = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)


class FakeDNRSession:
    """Fake async session for DNR tests."""

    def __init__(self) -> None:
        self.episodes: dict[uuid.UUID, dict[str, object]] = {}
        self.audit_rows: list[FakeAuditTrail] = []
        self.flush_count: int = 0

    async def execute(self, statement: object) -> FakeExecuteResult:
        if isinstance(statement, Update):
            table = statement.table
            # Use getattr for table name to avoid basedpyright issues
            table_name = getattr(table, "name", None)
            if table_name == "episodes":
                target_id = FakeDNRSession._extract_id_from_where(
                    statement._where_criteria
                )
                if target_id is None:
                    return FakeExecuteResult(rowcount=0)
                ep = self.episodes.get(target_id)
                if ep is None:
                    return FakeExecuteResult(rowcount=0)
                has_is_false = FakeDNRSession._where_has_dnr_is_false(
                    statement._where_criteria
                )
                has_is_true = FakeDNRSession._where_has_dnr_is_true(
                    statement._where_criteria
                )
                if has_is_false:
                    if ep.get("do_not_recall") is True:
                        return FakeExecuteResult(rowcount=0)
                    ep["do_not_recall"] = True
                    return FakeExecuteResult(rowcount=1)
                if has_is_true:
                    if ep.get("do_not_recall") is not True:
                        return FakeExecuteResult(rowcount=0)
                    ep["do_not_recall"] = False
                    return FakeExecuteResult(rowcount=1)
                return FakeExecuteResult(rowcount=0)

        elif isinstance(statement, Select):
            target_id = FakeDNRSession._extract_id_from_where(
                statement._where_criteria
            )
            if target_id is None:
                return FakeExecuteResult(rowcount=0, scalar_value=None)
            ep = self.episodes.get(target_id)
            if ep is None:
                return FakeExecuteResult(rowcount=0, scalar_value=None)
            # Use string-based detection for do_not_recall column
            sql_str = str(statement)
            if "do_not_recall" in sql_str and ".do_not_recall" in sql_str:
                return FakeExecuteResult(
                    rowcount=1, scalar_value=ep.get("do_not_recall", False)
                )
            return FakeExecuteResult(rowcount=1, scalar_value=ep)

        return FakeExecuteResult(rowcount=0)

    async def flush(self) -> None:
        self.flush_count += 1

    def add(self, obj: object) -> None:
        if isinstance(obj, FakeAuditTrail):
            self.audit_rows.append(obj)
        else:
            # Wrap any other object (e.g., real AuditTrail ORM)
            payload_raw = getattr(obj, "event_payload", {})
            self.audit_rows.append(
                FakeAuditTrail(
                    event_type=str(getattr(obj, "event_type", "")),
                    event_payload={str(k): v for k, v in payload_raw.items()} if isinstance(payload_raw, dict) else {},
                    principal=str(getattr(obj, "principal", "")),
                    event_hash=str(getattr(obj, "event_hash", "")),
                    previous_hash=str(getattr(obj, "previous_hash", ""))
                        if getattr(obj, "previous_hash", None) is not None
                        else None,
                    occurred_at=getattr(obj, "occurred_at", None),
                    id=uuid.UUID(str(getattr(obj, "id", uuid.uuid4())))
                        if isinstance(getattr(obj, "id", None), uuid.UUID)
                        else uuid.uuid4(),
                )
            )

    @staticmethod
    def _where_has_dnr_is_false(
        where_criteria: tuple[object, ...] | object,
    ) -> bool:
        """Check if WHERE criteria contains 'do_not_recall IS false'."""
        return FakeDNRSession._where_has_column_value(
            where_criteria, "do_not_recall", "false"
        )

    @staticmethod
    def _where_has_dnr_is_true(
        where_criteria: tuple[object, ...] | object,
    ) -> bool:
        """Check if WHERE criteria contains 'do_not_recall IS true'."""
        return FakeDNRSession._where_has_column_value(
            where_criteria, "do_not_recall", "true"
        )

    @staticmethod
    def _where_has_column_value(
        where_criteria: tuple[object, ...] | object,
        column: str,
        value: str,
    ) -> bool:
        """Check if any BinaryExpression matches column=value."""
        if isinstance(where_criteria, tuple):
            return any(
                FakeDNRSession._where_has_column_value(e, column, value)
                for e in where_criteria
            )
        left_str = str(getattr(where_criteria, "left", ""))
        right_str = str(getattr(where_criteria, "right", ""))
        return column in left_str and value in right_str

    @staticmethod
    def _extract_id_from_where(
        where_criteria: tuple[object, ...] | object,
    ) -> uuid.UUID | None:
        """Extract episode ID from SQLAlchemy WHERE criteria tuple."""
        from sqlalchemy.sql.elements import BinaryExpression, BindParameter

        if isinstance(where_criteria, tuple):
            for expr in where_criteria:
                result = FakeDNRSession._extract_id_from_where(expr)
                if result is not None:
                    return result
            return None

        if isinstance(where_criteria, BinaryExpression):
            left = getattr(where_criteria, "left", None)
            right = getattr(where_criteria, "right", None)
            if left is not None and hasattr(left, "name") and "id" in str(left.name):
                if isinstance(right, BindParameter):
                    val = right.value
                    if isinstance(val, uuid.UUID):
                        return val
                    if isinstance(val, str):
                        try:
                            return uuid.UUID(val)
                        except ValueError:
                            pass
            if (
                right is not None
                and hasattr(right, "name")
                and "id" in str(right.name)
            ):
                if isinstance(left, BindParameter):
                    val = left.value
                    if isinstance(val, uuid.UUID):
                        return val
                    if isinstance(val, str):
                        try:
                            return uuid.UUID(val)
                        except ValueError:
                            pass

        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_session() -> FakeDNRSession:
    return FakeDNRSession()


@pytest.fixture
def seeded_session() -> FakeDNRSession:
    session = FakeDNRSession()
    ep_id = uuid.uuid4()
    session.episodes[ep_id] = {"id": ep_id, "do_not_recall": False}
    return session


@pytest.fixture
def dnr_session() -> FakeDNRSession:
    session = FakeDNRSession()
    ep_id = uuid.uuid4()
    session.episodes[ep_id] = {"id": ep_id, "do_not_recall": True}
    return session


# ---------------------------------------------------------------------------
# mark_memory_dnr tests
# ---------------------------------------------------------------------------


class TestMarkMemoryDNR:
    """Authorized mark emits update, audit event, no raw content."""

    def test_authorized_mark_succeeds(self, seeded_session: FakeDNRSession) -> None:
        ep_id = next(iter(seeded_session.episodes))
        import asyncio
        result = asyncio.run(
            mark_memory_dnr(seeded_session, ep_id, reason="test reason")
        )
        assert result == ep_id
        assert seeded_session.episodes[ep_id]["do_not_recall"] is True

    def test_authorized_mark_emits_audit_event(
        self, seeded_session: FakeDNRSession
    ) -> None:
        ep_id = next(iter(seeded_session.episodes))
        import asyncio
        _ = asyncio.run(
            mark_memory_dnr(seeded_session, ep_id, reason="audit test")
        )
        assert len(seeded_session.audit_rows) == 1
        audit = seeded_session.audit_rows[0]
        assert audit.event_type == MEMORY_DNR_MARKED
        assert audit.principal == "guinevere_core"
        assert audit.event_payload["episode_id"] == str(ep_id)
        # Reason must be hash + length, NOT raw string
        audit_payload = audit.event_payload
        assert isinstance(audit_payload.get("reason_hash"), str)
        assert isinstance(audit_payload.get("reason_length"), int)
        assert audit_payload["reason_length"] == 10  # len("audit test")
        # Verify raw reason string is NOT in payload
        raw_keys = [k for k in audit_payload if k == "reason"]
        assert len(raw_keys) == 0, "raw reason key should not be present"
        assert "audit test" not in str(audit_payload)

    def test_mark_already_dnr_raises_state_error(
        self, dnr_session: FakeDNRSession
    ) -> None:
        ep_id = next(iter(dnr_session.episodes))
        import asyncio
        with pytest.raises(DNRStateError, match="already marked"):
            _ = asyncio.run(
                mark_memory_dnr(dnr_session, ep_id, reason="double mark")
            )

    def test_mark_missing_episode_raises_state_error(
        self, fake_session: FakeDNRSession
    ) -> None:
        missing_id = uuid.uuid4()
        import asyncio
        with pytest.raises(DNRStateError, match="not found"):
            _ = asyncio.run(
                mark_memory_dnr(fake_session, missing_id, reason="missing")
            )


# ---------------------------------------------------------------------------
# unmark_memory_dnr tests
# ---------------------------------------------------------------------------


class TestUnmarkMemoryDNR:
    """Authorized unmark emits update, audit event, no raw content."""

    def test_authorized_unmark_succeeds(self, dnr_session: FakeDNRSession) -> None:
        ep_id = next(iter(dnr_session.episodes))
        import asyncio
        result = asyncio.run(
            unmark_memory_dnr(dnr_session, ep_id, reason="reversal reason")
        )
        assert result == ep_id
        assert dnr_session.episodes[ep_id]["do_not_recall"] is False

    def test_authorized_unmark_emits_audit_event(
        self, dnr_session: FakeDNRSession
    ) -> None:
        ep_id = next(iter(dnr_session.episodes))
        import asyncio
        _ = asyncio.run(
            unmark_memory_dnr(dnr_session, ep_id, reason="reversal audit")
        )
        assert len(dnr_session.audit_rows) == 1
        audit = dnr_session.audit_rows[0]
        assert audit.event_type == DNR_REVOKED
        assert audit.principal == "guinevere_core"
        assert audit.event_payload["episode_id"] == str(ep_id)
        # Reason must be hash + length, NOT raw string
        assert isinstance(audit.event_payload.get("reason_hash"), str)
        assert audit.event_payload.get("reason_length") == 14
        assert "reversal audit" not in str(audit.event_payload)

    def test_unmark_non_dnr_raises_state_error(
        self, seeded_session: FakeDNRSession
    ) -> None:
        ep_id = next(iter(seeded_session.episodes))
        import asyncio
        with pytest.raises(DNRStateError, match="not marked do-not-recall"):
            _ = asyncio.run(
                unmark_memory_dnr(seeded_session, ep_id, reason="oops")
            )


# ---------------------------------------------------------------------------
# Authorization tests
# ---------------------------------------------------------------------------


class TestDNRAuthorization:
    """Unauthorized principals fail closed."""

    @pytest.mark.parametrize(
        "principal",
        ["guinevere_subagent", "default", "unknown", "faiz", ""],
    )
    def test_unauthorized_mark_raises(
        self, seeded_session: FakeDNRSession, principal: str
    ) -> None:
        ep_id = next(iter(seeded_session.episodes))
        import asyncio
        with pytest.raises(DNRAuthorizationError):
            _ = asyncio.run(
                mark_memory_dnr(
                    seeded_session, ep_id, reason="bad", principal=principal
                )
            )

    @pytest.mark.parametrize(
        "principal",
        ["guinevere_subagent", "default", "unknown", "faiz", ""],
    )
    def test_unauthorized_unmark_raises(
        self, dnr_session: FakeDNRSession, principal: str
    ) -> None:
        ep_id = next(iter(dnr_session.episodes))
        import asyncio
        with pytest.raises(DNRAuthorizationError):
            _ = asyncio.run(
                unmark_memory_dnr(
                    dnr_session, ep_id, reason="bad", principal=principal
                )
            )


# ---------------------------------------------------------------------------
# is_memory_dnr tests
# ---------------------------------------------------------------------------


class TestIsMemoryDNR:
    """Query DNR state from fake scalar result."""

    def test_returns_true_when_dnr(self, dnr_session: FakeDNRSession) -> None:
        ep_id = next(iter(dnr_session.episodes))
        import asyncio
        result = asyncio.run(is_memory_dnr(dnr_session, ep_id))
        assert result is True

    def test_returns_false_when_not_dnr(
        self, seeded_session: FakeDNRSession
    ) -> None:
        ep_id = next(iter(seeded_session.episodes))
        import asyncio
        result = asyncio.run(is_memory_dnr(seeded_session, ep_id))
        assert result is False

    def test_returns_false_for_missing_episode(
        self, fake_session: FakeDNRSession
    ) -> None:
        missing_id = uuid.uuid4()
        import asyncio
        result = asyncio.run(is_memory_dnr(fake_session, missing_id))
        assert result is False


# ---------------------------------------------------------------------------
# Query builder DNR filter preservation tests
# ---------------------------------------------------------------------------


class TestQueryBuildersPreserveDNR:
    """Existing recall query builders still include DNR exclusion."""

    def test_vector_query_includes_dnr_filter(self) -> None:
        stmt = build_vector_query([0.1] * 1536, 20, exclude_dnr=True)
        sql = str(stmt)
        assert "do_not_recall IS false" in sql

    def test_vector_query_omits_dnr_when_disabled(self) -> None:
        stmt = build_vector_query([0.1] * 1536, 20, exclude_dnr=False)
        sql = str(stmt)
        assert "do_not_recall IS false" not in sql

    def test_fts_query_includes_dnr_filter(self) -> None:
        stmt = build_fts_query("test query", 20, exclude_dnr=True)
        sql = str(stmt)
        assert "do_not_recall IS false" in sql

    def test_recency_query_includes_dnr_filter(self) -> None:
        stmt = build_recency_query(20, exclude_dnr=True)
        sql = str(stmt)
        assert "do_not_recall IS false" in sql


# ---------------------------------------------------------------------------
# Post-recall / pre-injection guard tests
# ---------------------------------------------------------------------------


class TestVerifyRecallResultsDNRFree:
    """Pre-injection guard accepts clean results and fails closed."""

    def test_clean_results_pass(self) -> None:
        results: list[dict[str, object]] = [
            {"id": "1", "safe_content": "alpha", "do_not_recall": False},
            {"id": "2", "safe_content": "beta"},
        ]
        verify_recall_results_dnr_free(results)

    def test_empty_results_pass(self) -> None:
        verify_recall_results_dnr_free([])

    def test_dnr_true_raises(self) -> None:
        results: list[dict[str, object]] = [
            {"id": "1", "safe_content": "secret", "do_not_recall": True}
        ]
        with pytest.raises(DNRViolationError, match="do_not_recall=True"):
            verify_recall_results_dnr_free(results)

    def test_dnr_string_true_raises(self) -> None:
        results: list[dict[str, object]] = [
            {"id": "1", "safe_content": "secret", "do_not_recall": "true"}
        ]
        with pytest.raises(DNRViolationError, match="string flag"):
            verify_recall_results_dnr_free(results)

    def test_dnr_true_in_middle_of_results(self) -> None:
        results: list[dict[str, object]] = [
            {"id": "1", "safe_content": "ok", "do_not_recall": False},
            {"id": "2", "safe_content": "bad", "do_not_recall": True},
            {"id": "3", "safe_content": "also ok"},
        ]
        with pytest.raises(DNRViolationError, match="index 1"):
            verify_recall_results_dnr_free(results)


# ---------------------------------------------------------------------------
# No raw content in logs/events
# ---------------------------------------------------------------------------


class TestNoRawContentInLogsAndEvents:
    """Zero raw memory content in audit events or log extra dicts."""

    def test_mark_audit_payload_has_no_raw_content(
        self, seeded_session: FakeDNRSession
    ) -> None:
        ep_id = next(iter(seeded_session.episodes))
        import asyncio
        _ = asyncio.run(
            mark_memory_dnr(
                seeded_session, ep_id, reason="contains SECRET_RAW_CONTENT"
            )
        )
        audit = seeded_session.audit_rows[0]
        payload_str = str(audit.event_payload)
        # Verify no raw_content field leaks into audit
        assert "raw_content" not in payload_str
        # Verify reason is hash + length, not raw string
        assert "reason_hash" in str(audit.event_payload)
        assert "reason_length" in str(audit.event_payload)
        assert "SECRET_RAW_CONTENT" not in payload_str

    def test_unmark_audit_payload_has_no_raw_content(
        self, dnr_session: FakeDNRSession
    ) -> None:
        ep_id = next(iter(dnr_session.episodes))
        import asyncio
        _ = asyncio.run(
            unmark_memory_dnr(dnr_session, ep_id, reason="reversal")
        )
        audit = dnr_session.audit_rows[0]
        payload_str = str(audit.event_payload)
        assert "raw_content" not in payload_str
        assert "reversal" not in payload_str

    def test_logger_extra_has_no_raw_content(
        self, seeded_session: FakeDNRSession, caplog: _CapLog
    ) -> None:
        ep_id = next(iter(seeded_session.episodes))
        with caplog.at_level(logging.INFO, logger="src.memory.dnr"):
            import asyncio
            _ = asyncio.run(
                mark_memory_dnr(seeded_session, ep_id, reason="log test")
            )
        for record in caplog.records:
            raw_extra = record.__dict__.get("extra", {})
            extra_str = str(raw_extra) if raw_extra is not None else ""
            assert "log test" not in extra_str
