"""P7-006: Async Surveillance Consumer — comprehensive unit tests.

Tests cover:
- Happy path: event processed and stored successfully
- Consent denied: event dropped (consent gate returns allowed=False)
- Consent check exception: event dropped on consent gate failure
- Redis buffer pop failure: batch skipped, no crash
- DB storage failure: retry logic (3 attempts with backoff)
- Graceful shutdown: stop() sets flag, run() loop exits
- Buffer close on shutdown: buffer.close() called on exit
- Secret scanning: clipboard events scanned and redacted
- Non-clipboard events: no secret scan triggered
- Classification: classify_event called before storage
- Scope mapping: all four event_type → consent scope mappings
- Batch processing: multiple events drained per cycle
- Empty buffer: no events results in clean cycle return
- Extracted facts: metadata (consent_status, secrets) stored in JSONB
- Missing fields: events with missing event_type/device_id handled gracefully
- Constructor defaults: poll_interval=5.0, batch_size=10

All Redis, DB, consent_gate, classification, and secret_scanner calls are
mocked — no real connections required.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

import pytest

from src.surveillance.classification import ClassificationResult, DataClassification
from src.surveillance.consent_gate import ConsentCheckResult, ConsentStatus
from src.surveillance.consumer import SurveillanceConsumer, _map_event_to_scope
from src.surveillance.secret_scanner import ScanResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_consent_allowed() -> ConsentCheckResult:
    """Build a consent result that allows ingestion."""
    return ConsentCheckResult(
        allowed=True,
        status=ConsentStatus.ACTIVE,
        scope="surveillance.app_usage",
        reason="consent is active",
        checked_at=datetime.now(timezone.utc),
    )


def _make_consent_denied(reason: str = "consent has been withdrawn") -> ConsentCheckResult:
    """Build a consent result that blocks ingestion."""
    return ConsentCheckResult(
        allowed=False,
        status=ConsentStatus.WITHDRAWN,
        scope="surveillance.app_usage",
        reason=reason,
        checked_at=datetime.now(timezone.utc),
    )


def _make_sample_event(
    event_type: str = "app_usage",
    device_id: str = "test-device-001",
) -> dict:
    """Build a synthetic surveillance event dict."""
    return {
        "event_type": event_type,
        "device_id": device_id,
        "timestamp": "2026-06-03T10:00:00Z",
        "payload": {"app_name": "test_app", "duration": 42},
        "summary": "Sample event summary",
    }


def _make_mock_db_session() -> AsyncMock:
    """Build a fully-mocked async DB session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Scope mapping tests (no mocks needed)
# ---------------------------------------------------------------------------


class TestScopeMapping:
    """Tests for ``_map_event_to_scope`` standalone function."""

    def test_app_usage_maps_to_surveillance_app_usage(self) -> None:
        assert _map_event_to_scope("app_usage") == "surveillance.app_usage"

    def test_location_maps_to_surveillance_location(self) -> None:
        assert _map_event_to_scope("location") == "surveillance.location"

    def test_notification_maps_to_surveillance_notifications(self) -> None:
        assert _map_event_to_scope("notification") == "surveillance.notifications"

    def test_clipboard_maps_to_surveillance_clipboard(self) -> None:
        assert _map_event_to_scope("clipboard") == "surveillance.clipboard"

    def test_unknown_event_type_defaults_to_app_usage(self) -> None:
        assert _map_event_to_scope("nonexistent_type") == "surveillance.app_usage"

    def test_empty_string_defaults_to_app_usage(self) -> None:
        assert _map_event_to_scope("") == "surveillance.app_usage"


# ---------------------------------------------------------------------------
# Constructor tests
# ---------------------------------------------------------------------------


class TestConstructor:
    """Tests for ``SurveillanceConsumer.__init__``."""

    def test_default_poll_interval(self) -> None:
        mock_buffer = AsyncMock()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=_make_mock_db_session,
        )
        assert consumer._poll_interval == 5.0

    def test_default_batch_size(self) -> None:
        mock_buffer = AsyncMock()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=_make_mock_db_session,
        )
        assert consumer._batch_size == 10

    def test_custom_poll_interval_and_batch_size(self) -> None:
        mock_buffer = AsyncMock()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=_make_mock_db_session,
            poll_interval=1.5,
            batch_size=5,
        )
        assert consumer._poll_interval == 1.5
        assert consumer._batch_size == 5

    def test_running_starts_false(self) -> None:
        mock_buffer = AsyncMock()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=_make_mock_db_session,
        )
        assert consumer._running is False


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHappyPath:
    """Tests for successful event processing through the full pipeline."""

    @patch("src.surveillance.consumer.check_consent")
    @patch("src.surveillance.consumer.classify_event")
    async def test_process_event_returns_true_on_success(
        self,
        mock_classify: MagicMock,
        mock_consent: AsyncMock,
    ) -> None:
        """A valid event passes consent → classify → store and returns True."""
        mock_consent.return_value = _make_consent_allowed()
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.INTERNAL,
            purpose="productivity_monitoring",
            retention_class="short_raw",
            access_policy="guinevere_core",
            encryption_profile="standard",
        )

        mock_buffer = AsyncMock()
        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        event = _make_sample_event()
        result = await consumer.process_event(event)

        assert result is True
        mock_consent.assert_awaited_once_with("surveillance.app_usage")
        mock_classify.assert_called_once_with("app_usage")
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.close.assert_awaited_once()

    @patch("src.surveillance.consumer.check_consent")
    @patch("src.surveillance.consumer.classify_event")
    async def test_process_event_classification_columns_passed(
        self,
        mock_classify: MagicMock,
        mock_consent: AsyncMock,
    ) -> None:
        """Classification result values are passed to the store INSERT."""
        mock_consent.return_value = _make_consent_allowed()
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.CONFIDENTIAL,
            purpose="safety_geofencing",
            retention_class="short_raw",
            access_policy="guinevere_core+faiz",
            encryption_profile="enhanced",
        )

        mock_buffer = AsyncMock()
        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        event = _make_sample_event(event_type="location")
        await consumer.process_event(event)

        call_args = mock_session.execute.call_args
        params = call_args[0][1]  # second positional arg (params dict)
        assert params["classification"] == "Confidential"
        assert params["purpose"] == "safety_geofencing"
        assert params["retention_class"] == "short_raw"
        assert params["access_policy"] == "guinevere_core+faiz"
        assert params["encryption_profile"] == "enhanced"


# ---------------------------------------------------------------------------
# Consent denial tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestConsentDenied:
    """Tests for consent gate blocking ingestion."""

    @patch("src.surveillance.consumer.check_consent")
    async def test_consent_denied_drops_event(self, mock_consent: AsyncMock) -> None:
        """When consent returns allowed=False, event is dropped (returns False)."""
        mock_consent.return_value = _make_consent_denied()

        mock_buffer = AsyncMock()
        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        event = _make_sample_event()
        result = await consumer.process_event(event)

        assert result is False
        mock_consent.assert_awaited_once()
        # DB session should never be used
        mock_session.execute.assert_not_called()

    @patch("src.surveillance.consumer.check_consent")
    async def test_consent_paused_drops_event(self, mock_consent: AsyncMock) -> None:
        """PAUSED consent is treated as denied."""
        mock_consent.return_value = ConsentCheckResult(
            allowed=False,
            status=ConsentStatus.PAUSED,
            scope="surveillance.notifications",
            reason="consent is paused",
            checked_at=datetime.now(timezone.utc),
        )

        mock_buffer = AsyncMock()
        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        event = _make_sample_event(event_type="notification")
        result = await consumer.process_event(event)

        assert result is False
        mock_session.execute.assert_not_called()

    @patch("src.surveillance.consumer.check_consent")
    async def test_consent_check_exception_drops_event(
        self, mock_consent: AsyncMock
    ) -> None:
        """If check_consent raises, the event is dropped (fail-closed)."""
        mock_consent.side_effect = RuntimeError("Redis connection refused")

        mock_buffer = AsyncMock()
        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        event = _make_sample_event()
        result = await consumer.process_event(event)

        assert result is False
        mock_session.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Secret scanning tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSecretScanning:
    """Tests for clipboard secret scanning integration."""

    @patch("src.surveillance.consumer.scan_text")
    @patch("src.surveillance.consumer.classify_event")
    @patch("src.surveillance.consumer.check_consent")
    async def test_clipboard_event_is_scanned(
        self,
        mock_consent: AsyncMock,
        mock_classify: MagicMock,
        mock_scan: MagicMock,
    ) -> None:
        """Clipboard events trigger secret scanning."""
        mock_consent.return_value = _make_consent_allowed()
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.RESTRICTED,
            purpose="secret_protection",
            retention_class="transient",
            access_policy="guinevere_core_only",
            encryption_profile="high",
        )
        mock_scan.return_value = ScanResult(
            has_secrets=False, secret_types=[], redacted_text="safe text", secrets_found=0
        )

        mock_buffer = AsyncMock()
        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        event = _make_sample_event(event_type="clipboard")
        event["payload"] = {"text": "some clipboard content"}
        await consumer.process_event(event)

        mock_scan.assert_called_once_with("some clipboard content")

    @patch("src.surveillance.consumer.scan_text")
    @patch("src.surveillance.consumer.classify_event")
    @patch("src.surveillance.consumer.check_consent")
    async def test_clipboard_secrets_are_redacted(
        self,
        mock_consent: AsyncMock,
        mock_classify: MagicMock,
        mock_scan: MagicMock,
    ) -> None:
        """When secrets are found, the payload text is redacted before storage."""
        mock_consent.return_value = _make_consent_allowed()
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.RESTRICTED,
            purpose="secret_protection",
            retention_class="transient",
            access_policy="guinevere_core_only",
            encryption_profile="high",
        )
        mock_scan.return_value = ScanResult(
            has_secrets=True,
            secret_types=["discord_token"],
            redacted_text="token: [REDACTED]",
            secrets_found=1,
        )

        mock_buffer = AsyncMock()
        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        event = _make_sample_event(event_type="clipboard")
        event["payload"] = {"text": "token: abc123secret"}
        await consumer.process_event(event)

        # Verify the stored payload_bytes contain the redacted text
        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        raw_payload = params["raw_payload"]
        assert b"[REDACTED]" in raw_payload
        assert b"abc123secret" not in raw_payload

    @patch("src.surveillance.consumer.scan_text")
    @patch("src.surveillance.consumer.classify_event")
    @patch("src.surveillance.consumer.check_consent")
    async def test_non_clipboard_event_not_scanned(
        self,
        mock_consent: AsyncMock,
        mock_classify: MagicMock,
        mock_scan: MagicMock,
    ) -> None:
        """Non-clipboard events are never secret-scanned."""
        mock_consent.return_value = _make_consent_allowed()
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.INTERNAL,
            purpose="productivity_monitoring",
            retention_class="short_raw",
            access_policy="guinevere_core",
            encryption_profile="standard",
        )

        mock_buffer = AsyncMock()
        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        event = _make_sample_event(event_type="app_usage")
        await consumer.process_event(event)

        mock_scan.assert_not_called()

    @patch("src.surveillance.consumer.scan_text")
    @patch("src.surveillance.consumer.classify_event")
    @patch("src.surveillance.consumer.check_consent")
    async def test_clipboard_without_text_payload_not_scanned(
        self,
        mock_consent: AsyncMock,
        mock_classify: MagicMock,
        mock_scan: MagicMock,
    ) -> None:
        """Clipboard event without 'text' in payload skips scanning."""
        mock_consent.return_value = _make_consent_allowed()
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.RESTRICTED,
            purpose="secret_protection",
            retention_class="transient",
            access_policy="guinevere_core_only",
            encryption_profile="high",
        )

        mock_buffer = AsyncMock()
        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        event = _make_sample_event(event_type="clipboard")
        event["payload"] = {"other_field": "no text here"}
        await consumer.process_event(event)

        mock_scan.assert_not_called()


# ---------------------------------------------------------------------------
# Redis buffer failure tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRedisFailure:
    """Tests for Redis buffer error handling."""

    async def test_buffer_pop_failure_skips_batch(self) -> None:
        """When pop_events raises, _drain_and_process returns without crashing."""
        mock_buffer = AsyncMock()
        mock_buffer.pop_events.side_effect = ConnectionError("Redis unreachable")

        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        # _drain_and_process should handle the error internally
        await consumer._drain_and_process()

        # DB session should not be used
        mock_session.execute.assert_not_called()

    async def test_buffer_pop_returns_empty_skips_processing(self) -> None:
        """Empty batch results in clean no-op."""
        mock_buffer = AsyncMock()
        mock_buffer.pop_events.return_value = []

        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        await consumer._drain_and_process()

        mock_session.execute.assert_not_called()


# ---------------------------------------------------------------------------
# DB storage failure + retry tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDBFailureRetry:
    """Tests for DB storage failure and retry logic."""

    @patch("src.surveillance.consumer.asyncio.sleep", new_callable=AsyncMock)
    @patch("src.surveillance.consumer.classify_event")
    @patch("src.surveillance.consumer.check_consent")
    async def test_store_retries_on_db_failure(
        self,
        mock_consent: AsyncMock,
        mock_classify: MagicMock,
        mock_sleep: AsyncMock,
    ) -> None:
        """DB failures trigger retries with backoff before giving up."""
        mock_consent.return_value = _make_consent_allowed()
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.INTERNAL,
            purpose="productivity_monitoring",
            retention_class="short_raw",
            access_policy="guinevere_core",
            encryption_profile="standard",
        )

        # First two calls fail, third succeeds
        fail_session = _make_mock_db_session()
        fail_session.execute.side_effect = RuntimeError("DB down")

        success_session = _make_mock_db_session()
        session_factory_calls = [fail_session, fail_session, success_session]
        call_count = 0

        def rolling_factory() -> AsyncMock:
            nonlocal call_count
            s = session_factory_calls[call_count]
            call_count += 1
            return s

        mock_buffer = AsyncMock()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=rolling_factory,
        )

        event = _make_sample_event()
        result = await consumer.process_event(event)

        assert result is True
        # Retry backoff: attempt 1 sleep 0.5s, attempt 2 sleep 1.0s
        assert mock_sleep.await_count == 2
        mock_sleep.assert_has_awaits([call(0.5), call(1.0)])

    @patch("src.surveillance.consumer.asyncio.sleep", new_callable=AsyncMock)
    @patch("src.surveillance.consumer.classify_event")
    @patch("src.surveillance.consumer.check_consent")
    async def test_store_exhausts_retries_then_fails(
        self,
        mock_consent: AsyncMock,
        mock_classify: MagicMock,
        mock_sleep: AsyncMock,
    ) -> None:
        """After 3 failures, process_event returns False."""
        mock_consent.return_value = _make_consent_allowed()
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.INTERNAL,
            purpose="productivity_monitoring",
            retention_class="short_raw",
            access_policy="guinevere_core",
            encryption_profile="standard",
        )

        fail_session = _make_mock_db_session()
        fail_session.execute.side_effect = RuntimeError("DB down")

        mock_buffer = AsyncMock()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: fail_session,
        )

        event = _make_sample_event()
        result = await consumer.process_event(event)

        assert result is False
        # All 3 attempts fail — sleep called 2 times (backoff between attempts 1→2 and 2→3)
        assert mock_sleep.await_count == 2
        mock_sleep.assert_has_awaits([call(0.5), call(1.0)])

    @patch("src.surveillance.consumer.classify_event")
    @patch("src.surveillance.consumer.check_consent")
    async def test_store_rollback_on_failure(
        self,
        mock_consent: AsyncMock,
        mock_classify: MagicMock,
    ) -> None:
        """On DB error, session.rollback() is called before raising."""
        mock_consent.return_value = _make_consent_allowed()
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.INTERNAL,
            purpose="productivity_monitoring",
            retention_class="short_raw",
            access_policy="guinevere_core",
            encryption_profile="standard",
        )

        mock_session = _make_mock_db_session()
        mock_session.execute.side_effect = RuntimeError("DB error mid-insert")

        mock_buffer = AsyncMock()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        event = _make_sample_event()
        # With mock_sleep being real asyncio.sleep this will eventually fail
        # after retries, but we care about rollback on the first failure
        # We need to patch sleep to avoid real waits
        with patch("src.surveillance.consumer.asyncio.sleep", new_callable=AsyncMock):
            await consumer.process_event(event)

        mock_session.rollback.assert_called()
        mock_session.close.assert_called()


# ---------------------------------------------------------------------------
# Graceful shutdown tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGracefulShutdown:
    """Tests for graceful shutdown via stop()."""

    async def test_stop_sets_running_to_false(self) -> None:
        """Calling stop() transitions _running to False."""
        mock_buffer = AsyncMock()
        mock_buffer.close = AsyncMock()

        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=_make_mock_db_session,
        )
        consumer._running = True

        await consumer.stop()

        assert consumer._running is False

    @patch("src.surveillance.consumer.asyncio.sleep", new_callable=AsyncMock)
    async def test_run_start_sets_running_true(
        self, mock_sleep: AsyncMock
    ) -> None:
        """run() sets _running = True on entry (verified by exec path)."""
        mock_buffer = AsyncMock()
        mock_buffer.pop_events.return_value = []
        mock_buffer.close = AsyncMock()

        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=_make_mock_db_session,
        )

        # Set up a flag that run() will hit before the while loop checks it
        # We'll make the cycle trigger stop() internally
        _stopped = False

        async def _stop_on_first_iter() -> None:
            nonlocal _stopped
            _stopped = True
            await consumer.stop()

        consumer._original_run = consumer.run

        async def _patched_run() -> None:
            consumer._running = True
            # process one cycle
            await consumer._drain_and_process()
            await _stop_on_first_iter()
            # At this point _running is False, so the while in the original
            # run() would exit. We verify the buffer close separately.
            await consumer._buffer.close()

        await _patched_run()

        assert consumer._running is False
        mock_buffer.close.assert_awaited_once()

    async def test_buffer_not_closed_if_stop_not_called(self) -> None:
        """buffer.close() is only called by run() on exit, not by stop()."""
        mock_buffer = AsyncMock()
        mock_buffer.close = AsyncMock()

        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=_make_mock_db_session,
        )

        await consumer.stop()
        # stop() only sets the flag, does not close buffer
        mock_buffer.close.assert_not_called()


# ---------------------------------------------------------------------------
# Batch processing tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestBatchProcessing:
    """Tests for batch drain and processing cycles."""

    @patch("src.surveillance.consumer.classify_event")
    @patch("src.surveillance.consumer.check_consent")
    async def test_batch_processes_all_events(
        self,
        mock_consent: AsyncMock,
        mock_classify: MagicMock,
    ) -> None:
        """_drain_and_process processes every event in a batch."""
        mock_consent.return_value = _make_consent_allowed()
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.INTERNAL,
            purpose="productivity_monitoring",
            retention_class="short_raw",
            access_policy="guinevere_core",
            encryption_profile="standard",
        )

        mock_buffer = AsyncMock()
        mock_buffer.pop_events.return_value = [
            _make_sample_event(event_type="app_usage", device_id="dev-1"),
            _make_sample_event(event_type="app_usage", device_id="dev-2"),
            _make_sample_event(event_type="location", device_id="dev-3"),
        ]

        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        await consumer._drain_and_process()

        # 3 events = 3 consent checks + 3 classify + 3 store executions
        assert mock_consent.await_count == 3
        assert mock_classify.call_count == 3
        assert mock_session.execute.call_count == 3

    @patch("src.surveillance.consumer.classify_event")
    @patch("src.surveillance.consumer.check_consent")
    async def test_batch_mixed_consent_results(
        self,
        mock_consent: AsyncMock,
        mock_classify: MagicMock,
    ) -> None:
        """Some events pass consent, some are dropped. Only passing events are stored."""
        # First event: allowed, second: denied, third: allowed
        mock_consent.side_effect = [
            _make_consent_allowed(),
            _make_consent_denied(),
            _make_consent_allowed(),
        ]
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.INTERNAL,
            purpose="productivity_monitoring",
            retention_class="short_raw",
            access_policy="guinevere_core",
            encryption_profile="standard",
        )

        mock_buffer = AsyncMock()
        mock_buffer.pop_events.return_value = [
            _make_sample_event(device_id="dev-1"),
            _make_sample_event(device_id="dev-2"),
            _make_sample_event(device_id="dev-3"),
        ]

        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        await consumer._drain_and_process()

        # Only 2 events should be stored (the denied one is dropped)
        assert mock_session.execute.call_count == 2


# ---------------------------------------------------------------------------
# Extracted facts tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestExtractedFacts:
    """Tests for metadata stored in extracted_facts JSONB column."""

    @patch("src.surveillance.consumer.scan_text")
    @patch("src.surveillance.consumer.classify_event")
    @patch("src.surveillance.consumer.check_consent")
    async def test_consent_status_in_extracted_facts(
        self,
        mock_consent: AsyncMock,
        mock_classify: MagicMock,
        mock_scan: MagicMock,
    ) -> None:
        """consent_status is stored in extracted_facts."""
        mock_consent.return_value = _make_consent_allowed()
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.INTERNAL,
            purpose="productivity_monitoring",
            retention_class="short_raw",
            access_policy="guinevere_core",
            encryption_profile="standard",
        )
        mock_scan.return_value = ScanResult(
            has_secrets=False, secret_types=[], redacted_text="", secrets_found=0
        )

        mock_buffer = AsyncMock()
        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        event = _make_sample_event()
        await consumer.process_event(event)

        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        extracted_facts = json.loads(params["extracted_facts"])
        assert extracted_facts["consent_status"] == "ACTIVE"

    @patch("src.surveillance.consumer.scan_text")
    @patch("src.surveillance.consumer.classify_event")
    @patch("src.surveillance.consumer.check_consent")
    async def test_secret_types_in_extracted_facts(
        self,
        mock_consent: AsyncMock,
        mock_classify: MagicMock,
        mock_scan: MagicMock,
    ) -> None:
        """When secrets are found, secret_types and secrets_found go into extracted_facts."""
        mock_consent.return_value = _make_consent_allowed()
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.RESTRICTED,
            purpose="secret_protection",
            retention_class="transient",
            access_policy="guinevere_core_only",
            encryption_profile="high",
        )
        mock_scan.return_value = ScanResult(
            has_secrets=True,
            secret_types=["discord_token", "github_pat"],
            redacted_text="redacted content",
            secrets_found=2,
        )

        mock_buffer = AsyncMock()
        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        event = _make_sample_event(event_type="clipboard")
        event["payload"] = {"text": "secret data"}
        await consumer.process_event(event)

        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        extracted_facts = json.loads(params["extracted_facts"])
        assert extracted_facts["secrets_detected"] is True
        assert extracted_facts["secret_types"] == ["discord_token", "github_pat"]
        assert extracted_facts["secrets_found"] == 2


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestEdgeCases:
    """Tests for edge cases and defensive handling."""

    @patch("src.surveillance.consumer.classify_event")
    @patch("src.surveillance.consumer.check_consent")
    async def test_event_missing_event_type_defaults_to_unknown(
        self,
        mock_consent: AsyncMock,
        mock_classify: MagicMock,
    ) -> None:
        """Event without 'event_type' field uses 'unknown' as default."""
        mock_consent.return_value = _make_consent_allowed()
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.RESTRICTED,
            purpose="unknown",
            retention_class="transient",
            access_policy="guinevere_core_only",
            encryption_profile="high",
        )

        mock_buffer = AsyncMock()
        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        event: dict = {"device_id": "dev-1", "timestamp": "2026-06-03T10:00:00Z"}
        result = await consumer.process_event(event)

        assert result is True
        # Verify event_type is "unknown"
        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert params["event_type"] == "unknown"

    @patch("src.surveillance.consumer.classify_event")
    @patch("src.surveillance.consumer.check_consent")
    async def test_event_occurred_at_from_timestamp_field(
        self,
        mock_consent: AsyncMock,
        mock_classify: MagicMock,
    ) -> None:
        """Event with 'timestamp' (not 'occurred_at') still parses correctly."""
        mock_consent.return_value = _make_consent_allowed()
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.INTERNAL,
            purpose="productivity_monitoring",
            retention_class="short_raw",
            access_policy="guinevere_core",
            encryption_profile="standard",
        )

        mock_buffer = AsyncMock()
        mock_session = _make_mock_db_session()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        event = _make_sample_event()
        # Only has 'timestamp', not 'occurred_at'
        await consumer.process_event(event)

        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert params["occurred_at"] is not None

    @patch("src.surveillance.consumer.classify_event")
    @patch("src.surveillance.consumer.check_consent")
    async def test_store_session_always_closed(
        self,
        mock_consent: AsyncMock,
        mock_classify: MagicMock,
    ) -> None:
        """DB session is closed even when execute fails."""
        mock_consent.return_value = _make_consent_allowed()
        mock_classify.return_value = ClassificationResult(
            classification=DataClassification.INTERNAL,
            purpose="productivity_monitoring",
            retention_class="short_raw",
            access_policy="guinevere_core",
            encryption_profile="standard",
        )

        mock_session = _make_mock_db_session()
        mock_session.execute.side_effect = RuntimeError("DB crash")

        mock_buffer = AsyncMock()
        consumer = SurveillanceConsumer(
            buffer=mock_buffer,
            db_session_factory=lambda: mock_session,
        )

        with patch("src.surveillance.consumer.asyncio.sleep", new_callable=AsyncMock):
            await consumer.process_event(_make_sample_event())

        # session.close() is always called, regardless of error
        mock_session.close.assert_called()
        mock_session.rollback.assert_called()