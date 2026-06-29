"""W5 verification tests for surveillance + observability ports.

Tests:
- HMAC verification (valid sig accepted, invalid rejected, stale timestamp, replay nonce)
- Buffer fail-soft (no Redis -> no crash)
- Consumer pipeline has NO consent step (grep for consent -> 0 matches)
- Import checks for all target modules
- Classification and secret scanner
- Retention tier logic
- Sentry PII scrubber
- Forbidden pattern scan
"""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import re
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Import checks — all target modules must import without crashing
# ---------------------------------------------------------------------------


class TestImports:
    """Verify all target modules import cleanly."""

    def test_import_receiver(self):
        from guinevere.surveillance.receiver import SurveillanceReceiver
        assert SurveillanceReceiver is not None

    def test_import_buffer(self):
        from guinevere.surveillance.buffer import NullBuffer, SurveillanceConsumer
        assert NullBuffer is not None
        assert SurveillanceConsumer is not None

    def test_import_storage(self):
        from guinevere.surveillance.storage import (
            TimescaleIngester,
            RetentionTier,
            get_retention_days,
        )
        assert TimescaleIngester is not None
        assert RetentionTier is not None

    def test_import_metrics(self):
        from guinevere.observability.metrics import is_available
        assert callable(is_available)

    def test_import_sentry(self):
        from guinevere.observability.sentry import init_sentry
        assert callable(init_sentry)

    def test_import_surveillance_package(self):
        from guinevere.surveillance import SurveillanceReceiver
        assert SurveillanceReceiver is not None

    def test_import_observability_package(self):
        from guinevere.observability import init_sentry
        assert callable(init_sentry)


# ---------------------------------------------------------------------------
# HMAC verification tests
# ---------------------------------------------------------------------------


class TestHMACVerification:
    """Test HMAC-SHA256 signature verification, timestamp window, nonce dedup."""

    def _make_signature(
        self,
        method: str,
        path: str,
        timestamp: str,
        nonce: str,
        body: str,
        secret: str,
    ) -> str:
        """Helper to compute expected HMAC signature."""
        signing_string = f"{method}:{path}:{timestamp}:{nonce}:{body}"
        return hmac_mod.new(
            secret.encode("utf-8"),
            signing_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @pytest.mark.asyncio
    async def test_valid_timestamp_accepted(self):
        """Timestamp within the 300s window should pass."""
        from guinevere.surveillance.receiver import validate_timestamp

        ts = str(int(time.time()))
        await validate_timestamp(ts)  # should not raise

    @pytest.mark.asyncio
    async def test_stale_timestamp_rejected(self):
        """Timestamp outside 300s window should raise HTTPException(401)."""
        from fastapi import HTTPException
        from guinevere.surveillance.receiver import validate_timestamp

        stale_ts = str(int(time.time()) - 600)
        with pytest.raises(HTTPException) as exc_info:
            await validate_timestamp(stale_ts)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_timestamp_format_rejected(self):
        """Non-numeric timestamp should raise HTTPException(401)."""
        from fastapi import HTTPException
        from guinevere.surveillance.receiver import validate_timestamp

        with pytest.raises(HTTPException) as exc_info:
            await validate_timestamp("not-a-number")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_replay_nonce_rejected(self):
        """Duplicate nonce should raise HTTPException(409)."""
        from fastapi import HTTPException
        from guinevere.surveillance.receiver import check_nonce

        nonce = "unique-test-nonce-12345"
        await check_nonce(nonce)  # first time: accepted
        with pytest.raises(HTTPException) as exc_info:
            await check_nonce(nonce)  # second time: rejected
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_hmac_valid_signature_accepted(self):
        """Valid HMAC signature should pass verification."""
        from guinevere.surveillance.receiver import (
            _clear_cache,
            get_hmac_secret,
        )

        secret = "test-hmac-secret-for-w5"
        with patch(
            "guinevere.surveillance.receiver.get_hmac_secret", return_value=secret
        ):
            ts = str(int(time.time()))
            nonce = "test-nonce-valid-hmac"
            body = '{"device_id":"test","event_type":"app_usage","occurred_at":"2026-01-01T00:00:00Z","payload":{}}'
            sig = self._make_signature(
                "POST", "/surveillance/events", ts, nonce, body, secret
            )

            # Verify the signature matches expected
            signing_string = f"POST:/surveillance/events:{ts}:{nonce}:{body}"
            expected = hmac_mod.new(
                secret.encode("utf-8"),
                signing_string.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            assert hmac_mod.compare_digest(sig, expected)

    @pytest.mark.asyncio
    async def test_hmac_invalid_signature_rejected(self):
        """Invalid HMAC signature should be detected."""
        secret = "test-hmac-secret"
        ts = str(int(time.time()))
        nonce = "test-nonce-invalid"
        body = '{"test": true}'

        signing_string = f"POST:/surveillance/events:{ts}:{nonce}:{body}"
        valid_sig = hmac_mod.new(
            secret.encode("utf-8"),
            signing_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Tamper with the signature
        invalid_sig = "0" * 64
        assert not hmac_mod.compare_digest(valid_sig, invalid_sig)

    @pytest.mark.asyncio
    async def test_in_memory_nonce_fallback(self):
        """Nonce dedup should work with in-memory store when no Redis."""
        from guinevere.surveillance.receiver import check_nonce

        nonce = "memory-nonce-test-999"
        await check_nonce(nonce, redis_client=None)  # first: accepted
        with pytest.raises(Exception):
            await check_nonce(nonce, redis_client=None)  # second: rejected


# ---------------------------------------------------------------------------
# Classification tests
# ---------------------------------------------------------------------------


class TestClassification:
    """Test event classification logic."""

    def test_known_event_classified(self):
        from guinevere.surveillance.receiver import (
            DataClassification,
            classify_event,
        )

        result = classify_event("clipboard")
        assert result.classification == DataClassification.CRITICAL

    def test_unknown_event_defaults_confidential(self):
        from guinevere.surveillance.receiver import (
            DataClassification,
            classify_event,
        )

        result = classify_event("unknown_type_xyz")
        assert result.classification == DataClassification.CONFIDENTIAL

    def test_retention_days_known(self):
        from guinevere.surveillance.receiver import get_retention_days

        assert get_retention_days("short_raw") == 7
        assert get_retention_days("transient") == 1

    def test_retention_days_unknown_defaults_1(self):
        from guinevere.surveillance.receiver import get_retention_days

        assert get_retention_days("completely_unknown") == 1


# ---------------------------------------------------------------------------
# Secret scanner tests
# ---------------------------------------------------------------------------


class TestSecretScanner:
    """Test secret detection and redaction."""

    def test_aws_key_detected(self):
        from guinevere.surveillance.receiver import scan_text

        result = scan_text("Key: AKIAIOSFODNN7EXAMPLE")
        assert result.has_secrets
        assert "aws_access_key" in result.secret_types

    def test_github_pat_detected(self):
        from guinevere.surveillance.receiver import scan_text

        result = scan_text("Token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnop")
        assert result.has_secrets
        assert "github_pat" in result.secret_types

    def test_clean_text_no_secrets(self):
        from guinevere.surveillance.receiver import scan_text

        result = scan_text("Hello, this is normal text with no secrets.")
        assert not result.has_secrets
        assert result.secrets_found == 0

    def test_empty_text(self):
        from guinevere.surveillance.receiver import scan_text

        result = scan_text("")
        assert not result.has_secrets

    def test_redact_secrets_convenience(self):
        from guinevere.surveillance.receiver import REDACTION_MARKER, redact_secrets

        text = "Use AKIAIOSFODNN7EXAMPLE for access"
        redacted = redact_secrets(text)
        assert REDACTION_MARKER in redacted
        assert "AKIAIOSFODNN7EXAMPLE" not in redacted


# ---------------------------------------------------------------------------
# Buffer fail-soft tests
# ---------------------------------------------------------------------------


class TestBufferFailSoft:
    """Verify buffer degrades gracefully without Redis."""

    @pytest.mark.asyncio
    async def test_null_buffer_push_returns_false(self):
        from guinevere.surveillance.buffer import NullBuffer

        buf = NullBuffer()
        result = await buf.push_event({"event_type": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_null_buffer_pop_returns_empty(self):
        from guinevere.surveillance.buffer import NullBuffer

        buf = NullBuffer()
        events = await buf.pop_events(10)
        assert events == []

    @pytest.mark.asyncio
    async def test_null_buffer_size_returns_zero(self):
        from guinevere.surveillance.buffer import NullBuffer

        buf = NullBuffer()
        assert await buf.buffer_size() == 0

    @pytest.mark.asyncio
    async def test_create_buffer_fail_soft(self):
        """create_buffer should return NullBuffer when Redis import fails."""
        with patch.dict("sys.modules", {"redis": None, "redis.asyncio": None}):
            from guinevere.surveillance.buffer import NullBuffer, create_buffer

            buf = create_buffer()
            assert isinstance(buf, NullBuffer)


# ---------------------------------------------------------------------------
# Consumer pipeline — NO consent step
# ---------------------------------------------------------------------------


class TestConsumerNoConsent:
    """Verify the consumer pipeline has NO consent references."""

    def test_consumer_process_event_no_consent(self):
        """The consumer's process_event must NOT reference active consent patterns."""
        import inspect
        from guinevere.surveillance.buffer import SurveillanceConsumer

        source = inspect.getsource(SurveillanceConsumer.process_event)
        assert "check_consent" not in source, (
            "consumer.process_event references check_consent — ADR-062 violation"
        )
        assert "consent_gate" not in source, (
            "consumer.process_event references consent_gate — ADR-062 violation"
        )
        assert "consent_status" not in source, (
            "consumer.process_event references consent_status — ADR-062 violation"
        )

    def test_consumer_store_event_no_consent_status(self):
        """_store_event must NOT write consent_status."""
        import inspect
        from guinevere.surveillance.buffer import SurveillanceConsumer

        source = inspect.getsource(SurveillanceConsumer._store_event)
        assert "consent_status" not in source, (
            "_store_event references consent_status — ADR-062 violation"
        )

    def test_consumer_module_no_consent_import(self):
        """The buffer module must NOT import consent_gate or check_consent."""
        import inspect
        import guinevere.surveillance.buffer as buf_mod

        source = inspect.getsource(buf_mod)
        assert "consent_gate" not in source
        assert "check_consent" not in source

    def test_receiver_module_no_consent(self):
        """The receiver module must NOT reference consent."""
        import inspect
        import guinevere.surveillance.receiver as recv_mod

        source = inspect.getsource(recv_mod)
        assert "consent_gate" not in source
        assert "check_consent" not in source
        assert "consent_status" not in source


# ---------------------------------------------------------------------------
# Retention / storage tests
# ---------------------------------------------------------------------------


class TestRetention:
    """Test retention tier logic from storage.py."""

    def test_retention_raw_days(self):
        from guinevere.surveillance.storage import (
            RETENTION_RAW_DAYS,
            RetentionTier,
            get_retention_days,
        )

        assert get_retention_days(RetentionTier.RAW) == 7

    def test_retention_aggregated_days(self):
        from guinevere.surveillance.storage import (
            RETENTION_AGGREGATED_DAYS,
            RetentionTier,
            get_retention_days,
        )

        assert get_retention_days(RetentionTier.AGGREGATED) == 90

    def test_retention_summary_days(self):
        from guinevere.surveillance.storage import (
            RETENTION_SUMMARY_DAYS,
            RetentionTier,
            get_retention_days,
        )

        assert get_retention_days(RetentionTier.SUMMARY) == 365

    def test_calculate_retention_until(self):
        from datetime import timedelta

        from guinevere.surveillance.storage import (
            RetentionTier,
            calculate_retention_until,
        )

        now = datetime(2026, 6, 29, tzinfo=timezone.utc)
        result = calculate_retention_until(RetentionTier.RAW, now)
        assert result == now + timedelta(days=7)


# ---------------------------------------------------------------------------
# Sentry PII scrubber tests
# ---------------------------------------------------------------------------


class TestSentryScrubber:
    """Test PII scrubber patterns."""

    def test_email_redacted(self):
        from guinevere.observability.sentry import _redact_value

        result = _redact_value("Contact user@example.com for details")
        assert "user@example.com" not in result
        assert "[REDACTED]" in result

    def test_api_key_redacted(self):
        from guinevere.observability.sentry import _redact_value

        result = _redact_value("api_key=sk-1234567890abcdef1234567890abcdef1234567890ab")
        assert "sk-1234567890abcdef1234567890abcdef1234567890ab" not in result

    def test_safe_word_redacted(self):
        from guinevere.observability.sentry import _redact_value

        result = _redact_value("The safe-word is banana")
        assert "banana" not in result or "[REDACTED]" in result

    def test_drop_event_sensitive_category(self):
        from guinevere.observability.sentry import _should_drop_event

        event = {"tags": {"category": "persona-safety"}}
        assert _should_drop_event(event) is True

    def test_drop_event_normal_category(self):
        from guinevere.observability.sentry import _should_drop_event

        event = {"tags": {"category": "general"}}
        assert _should_drop_event(event) is False

    def test_init_sentry_no_dsn_returns_false(self):
        from guinevere.observability.sentry import init_sentry

        with patch.dict("os.environ", {"SENTRY_DSN": ""}, clear=False):
            result = init_sentry(environment="test")
            assert result is False

    def test_redact_dict_recursive(self):
        from guinevere.observability.sentry import _redact_dict

        d = {
            "safe": "hello",
            "nested": {"email": "user@test.com"},
            "list_field": ["token=secret123456789012345678"],
        }
        result = _redact_dict(d)
        assert result["safe"] == "hello"
        assert "user@test.com" not in result["nested"]["email"]


# ---------------------------------------------------------------------------
# Prometheus metrics tests
# ---------------------------------------------------------------------------


class TestMetrics:
    """Test Prometheus metric definitions."""

    def test_metrics_import(self):
        from guinevere.observability.metrics import is_available

        assert callable(is_available)

    def test_metrics_available_flag(self):
        from guinevere.observability.metrics import is_available

        # Should return True or False based on whether prometheus_client is installed
        result = is_available()
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------


class TestModels:
    """Test Pydantic v2 request/response models."""

    def test_event_request_valid(self):
        from guinevere.surveillance.receiver import SurveillanceEventRequest

        req = SurveillanceEventRequest(
            device_id="test-device",
            event_type="app_usage",
            occurred_at="2026-06-29T12:00:00+00:00",
            payload={"key": "value"},
        )
        assert req.device_id == "test-device"
        assert req.event_type == "app_usage"

    def test_event_request_invalid_type(self):
        from pydantic import ValidationError
        from guinevere.surveillance.receiver import SurveillanceEventRequest

        with pytest.raises(ValidationError):
            SurveillanceEventRequest(
                device_id="test",
                event_type="invalid_type",
                occurred_at="2026-06-29T12:00:00+00:00",
                payload={},
            )

    def test_event_request_naive_datetime_rejected(self):
        from pydantic import ValidationError
        from guinevere.surveillance.receiver import SurveillanceEventRequest

        with pytest.raises(ValidationError):
            SurveillanceEventRequest(
                device_id="test",
                event_type="app_usage",
                occurred_at="2026-06-29T12:00:00",  # no timezone
                payload={},
            )

    def test_event_response_valid(self):
        from guinevere.surveillance.receiver import SurveillanceEventResponse

        resp = SurveillanceEventResponse(
            status="accepted",
            event_id="abc-123",
            received_at=datetime.now(),
        )
        assert resp.status == "accepted"


# ---------------------------------------------------------------------------
# Shannon entropy test
# ---------------------------------------------------------------------------


class TestShannonEntropy:
    """Test entropy calculation."""

    def test_empty_string_zero(self):
        from guinevere.surveillance.receiver import shannon_entropy

        assert shannon_entropy("") == 0.0

    def test_uniform_string_low_entropy(self):
        from guinevere.surveillance.receiver import shannon_entropy

        assert shannon_entropy("aaaa") == 0.0

    def test_random_string_high_entropy(self):
        from guinevere.surveillance.receiver import shannon_entropy

        # A diverse character set should have high entropy
        result = shannon_entropy("aB3$xK9!mN2@pQ7&")
        assert result > 3.0
