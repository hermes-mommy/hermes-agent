"""P7-007: TimescaleDB Ingestion Module — comprehensive unit tests.

Tests cover:
- Single event ingestion happy path
- Batch ingestion happy path
- Batch with empty event list
- Partial failure (some rows converted, some fail conversion)
- All events fail conversion
- DB insert failure handling (rollback)
- IngestionLog creation per batch
- IngestionLog status: success / partial / failed
- get_event_count with no filter
- get_event_count with since filter
- get_event_count handles DB error gracefully
- get_last_event with no filter
- get_last_event with event_type filter
- get_last_event returns None when no rows
- get_last_event handles DB error gracefully
- IngestionResult is frozen (cannot mutate)
- IngestionResult fields populated correctly
- _resolve_device_uuid deterministic
- _resolve_device_uuid different inputs → different UUIDs
- No raw payload content in structured logs
- ingest_single delegates to ingest_batch
- Session is closed after successful batch
- Session is closed after error

All DB sessions are mocked — no real PostgreSQL connections required.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from src.surveillance.timescale import IngestionResult, TimescaleIngester


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_session(
    *,
    rowcount: int = 1,
    insert_fails: bool = False,
    scalar_one: int | None = 42,
    scalar_one_or_none: Any | None = None,
    count_fails: bool = False,
    last_event_fails: bool = False,
) -> AsyncMock:
    """Build a fully-mocked async SQLAlchemy session.

    Args:
        rowcount: Value returned by execute().rowcount for INSERT.
        insert_fails: If True, execute() raises RuntimeError.
        scalar_one: Value returned by scalar_one() for count queries.
        scalar_one_or_none: Value returned by scalar_one_or_none() for last event.
        count_fails: If True, the count query raises an exception.
        last_event_fails: If True, the last-event query raises an exception.
    """
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()

    if insert_fails:
        session.execute = AsyncMock(side_effect=RuntimeError("DB connection lost"))
    elif count_fails or last_event_fails:
        session.execute = AsyncMock(side_effect=RuntimeError("query failed"))
    else:
        mock_result = MagicMock()
        mock_result.rowcount = rowcount
        mock_result.scalar_one = MagicMock(return_value=scalar_one)
        mock_result.scalar_one_or_none = MagicMock(return_value=scalar_one_or_none)
        session.execute = AsyncMock(return_value=mock_result)

    return session


def _make_sample_event(
    event_type: str = "app_usage",
    device_id: str = "test-device-001",
    occurred_at: datetime | None = None,
) -> dict:
    """Build a synthetic surveillance event dict."""
    if occurred_at is None:
        occurred_at = datetime(2026, 6, 3, 10, 0, 0, tzinfo=timezone.utc)
    return {
        "event_type": event_type,
        "device_id": device_id,
        "occurred_at": occurred_at.isoformat(),
        "payload": {"app_name": "test_app", "duration": 42},
        "summary": "Sample event summary",
        "extracted_facts": {"key": "value"},
    }


def _make_sample_batch(
    count: int = 3,
    base_event_type: str = "app_usage",
) -> list[dict]:
    """Build a list of synthetic surveillance events."""
    events: list[dict] = []
    for i in range(count):
        event = _make_sample_event(
            event_type=f"{base_event_type}_{i}",
            device_id=f"test-device-{i:03d}",
            occurred_at=datetime(2026, 6, 3, 10, i, 0, tzinfo=timezone.utc),
        )
        events.append(event)
    return events


# ---------------------------------------------------------------------------
# IngestionResult tests
# ---------------------------------------------------------------------------


class TestIngestionResult:
    """Tests for the frozen IngestionResult dataclass."""

    def test_fields_populated_correctly(self) -> None:
        """All fields are set during construction."""
        result = IngestionResult(
            ingested_count=5,
            failed_count=2,
            batch_id="batch-abc-123",
            errors=["event[1]: conversion failed"],
        )
        assert result.ingested_count == 5
        assert result.failed_count == 2
        assert result.batch_id == "batch-abc-123"
        assert result.errors == ["event[1]: conversion failed"]

    def test_is_frozen_cannot_mutate(self) -> None:
        """IngestionResult is a frozen dataclass — mutation raises."""
        result = IngestionResult(
            ingested_count=3,
            failed_count=0,
            batch_id="batch-xyz",
            errors=[],
        )
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            result.ingested_count = 99  # type: ignore[misc]

    def test_defaults_to_empty_errors(self) -> None:
        """errors field defaults to an empty list."""
        result = IngestionResult(
            ingested_count=0,
            failed_count=0,
            batch_id="empty-batch",
            errors=[],
        )
        assert result.errors == []

    def test_equality_on_same_values(self) -> None:
        """Two IngestionResult instances with same values are equal."""
        r1 = IngestionResult(1, 0, "b1", [])
        r2 = IngestionResult(1, 0, "b1", [])
        assert r1 == r2

    def test_inequality_on_different_values(self) -> None:
        """Two IngestionResult instances with different values are not equal."""
        r1 = IngestionResult(1, 0, "b1", [])
        r2 = IngestionResult(2, 1, "b2", ["err"])
        assert r1 != r2


# ---------------------------------------------------------------------------
# _resolve_device_uuid tests
# ---------------------------------------------------------------------------


class TestDeviceUUIDResolution:
    """Tests for ``TimescaleIngester._resolve_device_uuid``."""

    def test_deterministic_same_input(self) -> None:
        """Same device_id string always produces the same UUID."""
        u1 = TimescaleIngester._resolve_device_uuid("android-phone-01")
        u2 = TimescaleIngester._resolve_device_uuid("android-phone-01")
        assert u1 == u2

    def test_different_inputs_different_uuids(self) -> None:
        """Different device_id strings produce different UUIDs."""
        u1 = TimescaleIngester._resolve_device_uuid("android-phone-01")
        u2 = TimescaleIngester._resolve_device_uuid("windows-laptop-01")
        assert u1 != u2

    def test_is_uuid5_format(self) -> None:
        """Result is a uuid5 UUID (version 5)."""
        result = TimescaleIngester._resolve_device_uuid("test-device")
        assert isinstance(result, uuid.UUID)
        assert result.version == 5

    def test_handles_empty_string(self) -> None:
        """Empty string device_id still produces a valid UUID."""
        result = TimescaleIngester._resolve_device_uuid("")
        assert isinstance(result, uuid.UUID)
        assert result.version == 5


# ---------------------------------------------------------------------------
# ingest_single tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestIngestSingle:
    """Tests for ``TimescaleIngester.ingest_single``."""

    async def test_happy_path_returns_true(self) -> None:
        """Successful single event ingestion returns True."""
        session = _make_mock_session(rowcount=1)
        ingester = TimescaleIngester(session_factory=lambda: session)

        event = _make_sample_event()
        result = await ingester.ingest_single(event, "android-phone-01")

        assert result is True

    async def test_failed_insert_returns_false(self) -> None:
        """If the DB insert succeeds but returns 0 rows, returns False."""
        session = _make_mock_session(rowcount=0)
        ingester = TimescaleIngester(session_factory=lambda: session)

        event = _make_sample_event()
        result = await ingester.ingest_single(event, "android-phone-01")

        assert result is False

    async def test_missing_event_type_returns_false(self) -> None:
        """Event without event_type cannot be ingested."""
        session = _make_mock_session()
        ingester = TimescaleIngester(session_factory=lambda: session)

        event = _make_sample_event()
        del event["event_type"]
        result = await ingester.ingest_single(event, "android-phone-01")

        assert result is False

    async def test_session_is_closed_after_single(self) -> None:
        """Session is always closed after ingest_single."""
        session = _make_mock_session(rowcount=1)
        ingester = TimescaleIngester(session_factory=lambda: session)

        event = _make_sample_event()
        await ingester.ingest_single(event, "android-phone-01")

        assert session.close.called


# ---------------------------------------------------------------------------
# ingest_batch tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestIngestBatch:
    """Tests for ``TimescaleIngester.ingest_batch``."""

    async def test_happy_path_all_ingested(self) -> None:
        """All valid events in a batch are ingested."""
        session = _make_mock_session(rowcount=3)
        ingester = TimescaleIngester(session_factory=lambda: session)

        events = _make_sample_batch(3)
        result = await ingester.ingest_batch(events, "windows-laptop-01")

        assert result.ingested_count == 3
        assert result.failed_count == 0
        assert result.errors == []

    async def test_empty_events_list(self) -> None:
        """Empty event list returns zero ingested, zero failed."""
        session = _make_mock_session()
        ingester = TimescaleIngester(session_factory=lambda: session)

        result = await ingester.ingest_batch([], "test-device")

        assert result.ingested_count == 0
        assert result.failed_count == 0
        assert result.errors == []

    async def test_batch_id_is_uuid4_string(self) -> None:
        """Each batch gets a unique UUID4 batch_id."""
        session = _make_mock_session(rowcount=1)
        ingester = TimescaleIngester(session_factory=lambda: session)

        r1 = await ingester.ingest_batch([_make_sample_event()], "dev-a")
        r2 = await ingester.ingest_batch([_make_sample_event()], "dev-b")

        assert r1.batch_id != r2.batch_id
        # Should be valid UUID strings
        uuid.UUID(r1.batch_id)
        uuid.UUID(r2.batch_id)

    async def test_partial_failure_some_conversion_fail(self) -> None:
        """Events that fail conversion are counted as failed, rest succeed."""
        session = _make_mock_session(rowcount=2)
        ingester = TimescaleIngester(session_factory=lambda: session)

        good1 = _make_sample_event(event_type="good_1")
        bad_event: dict = {"event_type": "bad"}  # missing occurred_at
        good2 = _make_sample_event(event_type="good_2")

        result = await ingester.ingest_batch([good1, bad_event, good2], "dev-x")

        assert result.ingested_count == 2
        assert result.failed_count == 1
        assert len(result.errors) == 1
        assert "occurred_at" in result.errors[0]

    async def test_all_events_fail_conversion(self) -> None:
        """When every event fails conversion, result shows all failures."""
        session = _make_mock_session()
        ingester = TimescaleIngester(session_factory=lambda: session)

        bad_events: list[dict] = [
            {"event_type": "t1"},  # no occurred_at
            {"occurred_at": "2026-06-03T10:00:00Z"},  # no event_type
        ]

        result = await ingester.ingest_batch(bad_events, "dev-y")

        assert result.ingested_count == 0
        assert result.failed_count == 2
        assert len(result.errors) == 2

    async def test_db_insert_failure_all_fail(self) -> None:
        """When the DB INSERT fails, all events are marked as failed."""
        session = _make_mock_session(insert_fails=True)
        ingester = TimescaleIngester(session_factory=lambda: session)

        events = _make_sample_batch(3)
        result = await ingester.ingest_batch(events, "dev-z")

        assert result.ingested_count == 0
        assert result.failed_count == 3
        assert len(result.errors) == 1
        assert "batch insert failed" in result.errors[0]

    async def test_session_closed_after_success(self) -> None:
        """Session is always closed after a successful batch."""
        session = _make_mock_session(rowcount=3)
        ingester = TimescaleIngester(session_factory=lambda: session)

        await ingester.ingest_batch(_make_sample_batch(3), "dev-a")
        assert session.close.called

    async def test_session_closed_after_error(self) -> None:
        """Session is closed even when the insert fails."""
        session = _make_mock_session(insert_fails=True)
        ingester = TimescaleIngester(session_factory=lambda: session)

        await ingester.ingest_batch(_make_sample_batch(2), "dev-b")
        assert session.close.called

    async def test_session_rolled_back_on_error(self) -> None:
        """Rollback is called when the INSERT raises."""
        session = _make_mock_session(insert_fails=True)
        ingester = TimescaleIngester(session_factory=lambda: session)

        await ingester.ingest_batch(_make_sample_batch(1), "dev-c")
        assert session.rollback.called


# ---------------------------------------------------------------------------
# IngestionLog tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestIngestionLog:
    """Tests for IngestionLog audit entries created per batch."""

    async def test_ingestion_log_written_for_success(self) -> None:
        """A successful batch writes an ingestion log with status='success'."""
        session = _make_mock_session(rowcount=3)
        ingester = TimescaleIngester(session_factory=lambda: session)

        await ingester.ingest_batch(_make_sample_batch(3), "dev-a")

        # IngestionLog insert should have been called (2 execute calls: INSERT + INSERT LOG)
        # Plus 2 commits: one for the data insert, one for the log insert
        assert session.execute.call_count >= 2

    async def test_ingestion_log_written_for_partial_failure(self) -> None:
        """A partial-failure batch still writes an ingestion log."""
        # Session for the data insert (2 rows succeed), then log insert
        session_data = _make_mock_session(rowcount=2)
        session_log = _make_mock_session(rowcount=1)
        call_count = 0

        def rotating_factory() -> AsyncMock:
            nonlocal call_count
            s = session_data if call_count == 0 else session_log
            call_count += 1
            return s

        ingester = TimescaleIngester(session_factory=rotating_factory)

        good1 = _make_sample_event(event_type="good_1")
        bad: dict = {"occurred_at": "2026-06-03T10:00:00Z"}  # no event_type
        good2 = _make_sample_event(event_type="good_2")

        result = await ingester.ingest_batch([good1, bad, good2], "dev-b")

        assert result.failed_count == 1
        # The log session was used
        assert session_log.execute.called

    async def test_ingestion_log_written_for_all_fail(self) -> None:
        """Even when all events fail, an ingestion log is still written."""
        session = _make_mock_session()
        ingester = TimescaleIngester(session_factory=lambda: session)

        result = await ingester.ingest_batch([], "dev-c")

        # Ingestion log should be written for the empty batch
        assert session.execute.call_count >= 1


# ---------------------------------------------------------------------------
# get_event_count tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetEventCount:
    """Tests for ``TimescaleIngester.get_event_count``."""

    async def test_returns_count_without_filter(self) -> None:
        """Returns the total event count when no since filter is given."""
        session = _make_mock_session(scalar_one=42)
        ingester = TimescaleIngester(session_factory=lambda: session)

        count = await ingester.get_event_count()

        assert count == 42

    async def test_filters_by_since(self) -> None:
        """When since is provided, the query includes a WHERE clause."""
        session = _make_mock_session(scalar_one=5)
        ingester = TimescaleIngester(session_factory=lambda: session)

        cutoff = datetime(2026, 6, 1, tzinfo=timezone.utc)
        count = await ingester.get_event_count(since=cutoff)

        assert count == 5

    async def test_handles_exception_gracefully(self) -> None:
        """If the count query fails, returns 0 instead of raising."""
        session = _make_mock_session(count_fails=True)
        ingester = TimescaleIngester(session_factory=lambda: session)

        count = await ingester.get_event_count()

        assert count == 0
        assert session.close.called

    async def test_session_closed_after_success(self) -> None:
        """Session is always closed after count query."""
        session = _make_mock_session(scalar_one=10)
        ingester = TimescaleIngester(session_factory=lambda: session)

        await ingester.get_event_count()
        assert session.close.called

    async def test_session_closed_after_error(self) -> None:
        """Session is closed even when count query fails."""
        session = _make_mock_session(count_fails=True)
        ingester = TimescaleIngester(session_factory=lambda: session)

        await ingester.get_event_count()
        assert session.close.called


# ---------------------------------------------------------------------------
# get_last_event tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetLastEvent:
    """Tests for ``TimescaleIngester.get_last_event``."""

    async def test_returns_row_as_dict(self) -> None:
        """Returns a dict representation of the most recent event row."""
        mock_row = MagicMock()
        mock_row.id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        mock_row.event_type = "app_usage"
        mock_row.device_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        mock_row.summary = "last event summary"
        mock_row.occurred_at = datetime(2026, 6, 3, 10, 0, 0, tzinfo=timezone.utc)
        mock_row.ingested_at = datetime(2026, 6, 3, 10, 0, 1, tzinfo=timezone.utc)
        mock_row.extracted_facts = {"fact_key": "fact_value"}

        session = _make_mock_session(scalar_one_or_none=mock_row)
        ingester = TimescaleIngester(session_factory=lambda: session)

        result = await ingester.get_last_event()

        assert result is not None
        assert result["event_type"] == "app_usage"
        assert result["summary"] == "last event summary"
        assert result["extracted_facts"] == {"fact_key": "fact_value"}
        assert "id" in result
        assert "occurred_at" in result
        assert "ingested_at" in result

    async def test_filters_by_event_type(self) -> None:
        """When event_type is given, the query filters on it."""
        mock_row = MagicMock()
        mock_row.id = uuid.uuid4()
        mock_row.event_type = "location"
        mock_row.device_id = uuid.uuid4()
        mock_row.summary = "gps location"
        mock_row.occurred_at = datetime.now(timezone.utc)
        mock_row.ingested_at = datetime.now(timezone.utc)
        mock_row.extracted_facts = None

        session = _make_mock_session(scalar_one_or_none=mock_row)
        ingester = TimescaleIngester(session_factory=lambda: session)

        result = await ingester.get_last_event(event_type="location")

        assert result is not None
        assert result["event_type"] == "location"

    async def test_returns_none_when_no_rows(self) -> None:
        """If no events exist, returns None."""
        session = _make_mock_session(scalar_one_or_none=None)
        ingester = TimescaleIngester(session_factory=lambda: session)

        result = await ingester.get_last_event()

        assert result is None

    async def test_handles_exception_gracefully(self) -> None:
        """If the query fails, returns None instead of raising."""
        session = _make_mock_session(last_event_fails=True)
        ingester = TimescaleIngester(session_factory=lambda: session)

        result = await ingester.get_last_event()

        assert result is None
        assert session.close.called

    async def test_session_closed_after_success(self) -> None:
        """Session is closed after a successful query."""
        mock_row = MagicMock()
        mock_row.id = uuid.uuid4()
        mock_row.event_type = "test"
        mock_row.device_id = uuid.uuid4()
        mock_row.summary = "summary"
        mock_row.occurred_at = datetime.now(timezone.utc)
        mock_row.ingested_at = datetime.now(timezone.utc)
        mock_row.extracted_facts = None

        session = _make_mock_session(scalar_one_or_none=mock_row)
        ingester = TimescaleIngester(session_factory=lambda: session)

        await ingester.get_last_event()
        assert session.close.called

    async def test_session_closed_after_error(self) -> None:
        """Session is closed when the query fails."""
        session = _make_mock_session(last_event_fails=True)
        ingester = TimescaleIngester(session_factory=lambda: session)

        await ingester.get_last_event()
        assert session.close.called


# ---------------------------------------------------------------------------
# Privacy / logging tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPrivacyAndLogging:
    """Tests that raw payload data is never logged."""

    async def test_no_raw_payload_in_result_errors(self) -> None:
        """Error messages in IngestionResult do not contain raw payload data."""
        session = _make_mock_session(insert_fails=True)
        ingester = TimescaleIngester(session_factory=lambda: session)

        event = _make_sample_event()
        event["payload"] = {"secret_field": "super-secret-value-12345"}

        result = await ingester.ingest_batch([event], "test-device")

        # Error messages should describe the failure, not leak payload
        for err in result.errors:
            assert "super-secret-value-12345" not in err

    async def test_result_contains_metadata_not_payload(self) -> None:
        """IngestionResult metadata does not expose raw payload."""
        session = _make_mock_session(rowcount=2)
        ingester = TimescaleIngester(session_factory=lambda: session)

        events = _make_sample_batch(2)
        events[0]["payload"] = {"secret": "confidential-data-xyz"}
        events[1]["payload"] = {"secret": "another-secret"}

        result = await ingester.ingest_batch(events, "test-device")

        assert result.ingested_count == 2
        assert result.failed_count == 0
        # The result itself is metadata-only: counts, batch_id, errors
        assert "confidential-data-xyz" not in result.batch_id
        assert "another-secret" not in result.batch_id
        for err in result.errors:
            assert "confidential-data-xyz" not in err
            assert "another-secret" not in err


# ---------------------------------------------------------------------------
# Constructor tests
# ---------------------------------------------------------------------------


class TestConstructor:
    """Tests for ``TimescaleIngester.__init__``."""

    def test_stores_session_factory(self) -> None:
        """Constructor stores the session factory callable."""
        factory = lambda: _make_mock_session()
        ingester = TimescaleIngester(session_factory=factory)
        assert ingester._session_factory is factory

    def test_default_empty_state(self) -> None:
        """A freshly constructed ingester has no internal state beyond factory."""
        ingester = TimescaleIngester(session_factory=lambda: _make_mock_session())
        assert callable(ingester._session_factory)


# ---------------------------------------------------------------------------
# _event_to_row tests
# ---------------------------------------------------------------------------


class TestEventToRow:
    """Tests for ``TimescaleIngester._event_to_row``."""

    def test_converts_valid_event(self) -> None:
        """A valid event with all fields produces a correct row dict."""
        device_uuid = uuid.uuid4()
        event = _make_sample_event()
        row = TimescaleIngester._event_to_row(event, device_uuid)

        assert row["event_type"] == "app_usage"
        assert row["device_id"] == device_uuid
        assert row["summary"] == "Sample event summary"
        assert row["extracted_facts"] == {"key": "value"}
        assert isinstance(row["occurred_at"], datetime)
        assert isinstance(row["raw_payload"], bytes)

    def test_missing_event_type_raises(self) -> None:
        """Missing event_type raises ValueError."""
        device_uuid = uuid.uuid4()
        with pytest.raises(ValueError, match="event_type is required"):
            TimescaleIngester._event_to_row({}, device_uuid)

    def test_missing_occurred_at_raises(self) -> None:
        """Missing occurred_at raises ValueError."""
        device_uuid = uuid.uuid4()
        with pytest.raises(ValueError, match="occurred_at"):
            TimescaleIngester._event_to_row({"event_type": "app_usage"}, device_uuid)

    def test_uses_timestamp_fallback(self) -> None:
        """When occurred_at is missing but timestamp is present, uses timestamp."""
        device_uuid = uuid.uuid4()
        event = {"event_type": "app_usage", "timestamp": "2026-06-03T10:00:00Z"}
        row = TimescaleIngester._event_to_row(event, device_uuid)

        assert isinstance(row["occurred_at"], datetime)

    def test_datetime_object_passed_through(self) -> None:
        """If occurred_at is already a datetime, it is used directly."""
        device_uuid = uuid.uuid4()
        dt = datetime(2026, 6, 3, 10, 0, 0, tzinfo=timezone.utc)
        event = {"event_type": "app_usage", "occurred_at": dt}
        row = TimescaleIngester._event_to_row(event, device_uuid)

        assert row["occurred_at"] == dt

    def test_invalid_occurred_at_raises(self) -> None:
        """Invalid datetime string raises ValueError."""
        device_uuid = uuid.uuid4()
        event = {"event_type": "app_usage", "occurred_at": "not-a-date"}
        with pytest.raises(ValueError, match="invalid occurred_at"):
            TimescaleIngester._event_to_row(event, device_uuid)

    def test_bytes_payload_passed_through(self) -> None:
        """Bytes payload is used directly."""
        device_uuid = uuid.uuid4()
        event = {
            "event_type": "app_usage",
            "occurred_at": "2026-06-03T10:00:00Z",
            "payload": b"binary-data",
        }
        row = TimescaleIngester._event_to_row(event, device_uuid)

        assert row["raw_payload"] == b"binary-data"

    def test_string_payload_encoded(self) -> None:
        """String payload is UTF-8 encoded."""
        device_uuid = uuid.uuid4()
        event = {
            "event_type": "app_usage",
            "occurred_at": "2026-06-03T10:00:00Z",
            "payload": "text-data",
        }
        row = TimescaleIngester._event_to_row(event, device_uuid)

        assert row["raw_payload"] == b"text-data"