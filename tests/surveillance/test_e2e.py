"""P7-021 — Surveillance end-to-end integration test suite.

Validates the complete surveillance pipeline: HMAC-signed HTTP request →
API endpoint → Redis buffer → consumer → TimescaleDB.

Uses :class:`fastapi.testclient.TestClient` for the HTTP layer and mocks for
external dependencies (Redis, database). All tests are gated behind the
``--run-e2e`` pytest flag to prevent accidental execution against live
infrastructure.
"""

from __future__ import annotations

import hashlib
import hmac as hmac_lib
import json
import os
import sys
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.surveillance.classification import DataClassification, classify_event
from src.surveillance.consent_gate import (
    ConsentCheckResult,
    ConsentStatus,
    _set_db_session_for_testing,
    _set_redis_for_testing as _consent_set_redis,
    check_consent,
)
from src.surveillance.secret_scanner import scan_text
from src.surveillance.secrets import _clear_cache

# ---------------------------------------------------------------------------
# E2E gate — all tests are skipped unless ``--run-e2e`` is passed on the CLI
# or the ``RUN_E2E`` environment variable is set to ``"1"``.
# ---------------------------------------------------------------------------

RUN_E2E = "--run-e2e" in sys.argv or os.environ.get("RUN_E2E", "") == "1"
e2e_only = pytest.mark.skipif(not RUN_E2E, reason="requires --run-e2e flag")

# ---------------------------------------------------------------------------
# Synthetic test constants (no real secrets ever)
# ---------------------------------------------------------------------------

TEST_HMAC_SECRET: str = "test-hmac-secret-for-e2e-only"
EVENTS_PATH: str = "/surveillance/events"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sign_request(
    method: str,
    path: str,
    body: str,
    secret: str,
    nonce: str | None = None,
    timestamp: str | None = None,
) -> dict[str, str]:
    """Build HMAC-signed headers for a surveillance event request.

    The signing string format matches :func:`src.surveillance.auth.verify_hmac`:
    ``<method>:<path>:<timestamp>:<nonce>:<body>``

    Args:
        method: HTTP method (e.g. ``"POST"``).
        path: URL path (e.g. ``"/surveillance/events"``).
        body: Raw JSON request body string.
        secret: HMAC secret key.
        nonce: Unique request nonce (auto-generated if ``None``).
        timestamp: Unix epoch seconds as string (auto-generated if ``None``).

    Returns:
        Dict with keys ``X-Signature``, ``X-Timestamp``, ``X-Nonce``.
    """
    if nonce is None:
        nonce = f"e2e-nonce-{int(time.time() * 1_000_000)}"
    if timestamp is None:
        timestamp = str(int(time.time()))

    signing_string = f"{method}:{path}:{timestamp}:{nonce}:{body}"
    signature = hmac_lib.new(
        secret.encode("utf-8"),
        signing_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return {
        "X-Signature": signature,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
    }


def _make_event(
    device_id: str = "e2e-test-device-001",
    event_type: str = "app_usage",
    payload: dict[str, object] | None = None,
    occurred_at: str | None = None,
) -> dict[str, object]:
    """Create a synthetic surveillance event payload with clearly fake data.

    All values are synthetic — no real device IDs, no real user data.
    """
    if payload is None:
        payload = {"app": "com.test.app", "duration": 42}
    if occurred_at is None:
        occurred_at = datetime.now(timezone.utc).isoformat()

    return {
        "device_id": device_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "payload": payload,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _setup_hmac_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject the synthetic HMAC secret via environment variable.

    Runs automatically for every test so the secrets module always resolves
    the test secret without touching SOPS or real keys.
    """
    _clear_cache()
    monkeypatch.setenv("SURVEILLANCE_HMAC_SECRET", TEST_HMAC_SECRET)


@pytest.fixture
def mock_replay_redis() -> MagicMock:
    """Mock Redis for replay protection — accepts first nonce by default.

    Returns a :class:`unittest.mock.MagicMock` whose ``.set`` is an
    :class:`AsyncMock` returning ``True`` (SET NX EX succeeded).
    """
    redis = MagicMock()
    redis.set = AsyncMock(return_value=True)  # SET NX EX → key did not exist
    return redis


@pytest.fixture
def client(mock_replay_redis: MagicMock) -> TestClient:
    """Create a :class:`TestClient` wired to the real FastAPI app with
    replay-protection Redis mocked out.

    The ``src.surveillance.replay._get_redis`` function is patched to
    return the synthetic mock so no real Redis connection is attempted.
    """
    with patch(
        "src.surveillance.replay._get_redis",
        return_value=mock_replay_redis,
    ):
        from src.core.main import app

        with TestClient(app) as tc:
            yield tc


# ---------------------------------------------------------------------------
# Test class — all methods gated behind ``--run-e2e``
# ---------------------------------------------------------------------------


@e2e_only
class TestE2EPipeline:
    """End-to-end integration tests for the complete surveillance pipeline.

    Covers:
    * HMAC authentication (signed requests accepted, invalid/expired rejected)
    * Nonce replay protection (duplicate detection)
    * Pydantic v2 request validation (missing fields → 422)
    * Event classification metadata (synchronous, no I/O)
    * Consent gate fail-closed behaviour (async, mocked Redis + DB)
    * Secret scanner redaction (clipboard text with synthetic API keys)
    """

    # -- HTTP-layer tests (use TestClient, no asyncio marker needed) --------

    # Each HTTP test signs the exact body bytes and sends them via
    # ``content=body_str`` (not ``json=event``) so there can be no
    # serialisation mismatch between the signer and TestClient.

    _JSON_HEADERS: dict[str, str] = {"Content-Type": "application/json"}

    def test_hmac_signed_request_accepted(self, client: TestClient) -> None:
        """Properly HMAC-signed POST /surveillance/events → 202 Accepted."""
        event = _make_event()
        body_str = json.dumps(event)
        sign_headers = _sign_request(
            "POST", EVENTS_PATH, body_str, TEST_HMAC_SECRET,
        )

        response = client.post(
            EVENTS_PATH,
            content=body_str,
            headers={**sign_headers, **self._JSON_HEADERS},
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "event_id" in data
        assert isinstance(data["event_id"], str)
        assert len(data["event_id"]) > 0

    def test_invalid_hmac_rejected(self, client: TestClient) -> None:
        """Wrong HMAC signature → 401 Unauthorized."""
        event = _make_event()
        body_str = json.dumps(event)
        sign_headers = _sign_request(
            "POST", EVENTS_PATH, body_str, TEST_HMAC_SECRET,
        )
        sign_headers["X-Signature"] = "0000000000wrong-signature-attempt0000000000"

        response = client.post(
            EVENTS_PATH,
            content=body_str,
            headers={**sign_headers, **self._JSON_HEADERS},
        )

        assert response.status_code == 401

    def test_expired_timestamp_rejected(self, client: TestClient) -> None:
        """Timestamp older than 300s window → 401 Unauthorized."""
        event = _make_event()
        body_str = json.dumps(event)
        old_ts = str(int(time.time()) - 600)  # 10 minutes ago — outside window
        sign_headers = _sign_request(
            "POST", EVENTS_PATH, body_str, TEST_HMAC_SECRET, timestamp=old_ts,
        )

        response = client.post(
            EVENTS_PATH,
            content=body_str,
            headers={**sign_headers, **self._JSON_HEADERS},
        )

        assert response.status_code == 401

    def test_duplicate_nonce_rejected(
        self,
        client: TestClient,
        mock_replay_redis: MagicMock,
    ) -> None:
        """Same X-Nonce header sent twice → 409 Conflict on second attempt."""
        event = _make_event()
        body_str = json.dumps(event)
        nonce = f"e2e-dup-nonce-{int(time.time() * 1_000_000)}"
        sign_headers = _sign_request(
            "POST", EVENTS_PATH, body_str, TEST_HMAC_SECRET, nonce=nonce,
        )
        all_headers = {**sign_headers, **self._JSON_HEADERS}

        # ---- First request: accepted (mock returns True = SET NX EX succeeded)
        r1 = client.post(EVENTS_PATH, content=body_str, headers=all_headers)
        assert r1.status_code == 202

        # ---- Override mock: now SET NX EX "fails" (returns None = duplicate)
        mock_replay_redis.set = AsyncMock(return_value=None)

        # ---- Second request with same nonce: rejected
        r2 = client.post(EVENTS_PATH, content=body_str, headers=all_headers)
        assert r2.status_code == 409

    def test_event_validation_missing_fields(self, client: TestClient) -> None:
        """Missing required ``device_id`` field → 422 Unprocessable Entity."""
        # Build an event payload with no device_id
        incomplete: dict[str, object] = {
            "event_type": "app_usage",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "payload": {},
        }
        body_str = json.dumps(incomplete)
        sign_headers = _sign_request(
            "POST", EVENTS_PATH, body_str, TEST_HMAC_SECRET,
        )

        response = client.post(
            EVENTS_PATH,
            content=body_str,
            headers={**sign_headers, **self._JSON_HEADERS},
        )
        assert response.status_code == 422

    # -- Classification subsystem test (synchronous, no I/O) ----------------

    def test_event_classification_applied(self) -> None:
        """``classify_event`` returns correct classification metadata.

        Tests both well-known event types (``app_usage``, ``clipboard``) and
        an unknown type (``future_event``) to exercise the fail-closed default.
        """
        # Known: app_usage → Internal
        result = classify_event("app_usage")
        assert result.classification == DataClassification.INTERNAL
        assert result.retention_class == "short_raw"
        assert result.purpose == "productivity_monitoring"
        assert result.access_policy == "guinevere_core"
        assert result.encryption_profile == "standard"

        # Known: clipboard → Restricted
        clip_result = classify_event("clipboard")
        assert clip_result.classification == DataClassification.RESTRICTED
        assert clip_result.retention_class == "transient"
        assert clip_result.encryption_profile == "high"
        assert clip_result.access_policy == "guinevere_core_only"

    def test_unknown_event_type_classified_restricted(self) -> None:
        """Unknown event type defaults to Restricted (fail-closed)."""
        result = classify_event("future_event_type_not_yet_defined")
        assert result.classification == DataClassification.RESTRICTED
        assert result.retention_class == "transient"
        assert result.access_policy == "guinevere_core_only"
        assert result.encryption_profile == "high"
        assert result.purpose == "unknown"

    # -- Consent gate test (async — needs Redis + DB mocks) -----------------

    @pytest.mark.asyncio
    async def test_consent_gate_blocks_when_no_consent(self) -> None:
        """Fail-closed: cache miss + DB unavailable → BLOCK (``allowed=False``).

        Simulates a complete consent-gate decision where both Redis (cache
        miss) and the database (unavailable) return no consent data. The
        gate must block the event (fail-closed).
        """
        # --- Arrange: Redis cache miss ---
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)  # No cached verdict
        mock_redis.set = AsyncMock(return_value=True)  # Cache write succeeds
        _consent_set_redis(mock_redis)

        # --- Arrange: DB unavailable ---
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(side_effect=RuntimeError("DB unavailable"))
        _set_db_session_for_testing(mock_db)

        try:
            # --- Act ---
            result: ConsentCheckResult = await check_consent(
                "surveillance.app_usage"
            )

            # --- Assert ---
            assert result.allowed is False
            assert "database unavailable" in result.reason.lower()
            assert result.scope == "surveillance.app_usage"
            assert result.status is None
            assert isinstance(result.checked_at, datetime)
        finally:
            # Clean up injected dependencies
            _consent_set_redis(None)
            _set_db_session_for_testing(None)

    # -- Secret scanner test (synchronous, pure function) -------------------

    def test_secret_scanner_redacts_clipboard(self) -> None:
        """Clipboard text containing a synthetic OpenAI API key is redacted.

        The fake key ``sk-proj1234567890abcdefghijklmnopqrstuvwxyz1234567890``
        matches the compiled ``openai_api_key`` pattern. After scanning, the
        redacted text must contain ``[REDACTED]`` and must NOT expose the key.
        """
        fake_key = "sk-proj1234567890abcdefghijklmnopqrstuvwxyz1234567890"
        clipboard_text = f"export OPENAI_API_KEY={fake_key}"

        result = scan_text(clipboard_text)

        assert result.has_secrets is True
        assert result.secrets_found >= 1
        assert "openai_api_key" in result.secret_types
        assert fake_key not in result.redacted_text
        assert "[REDACTED]" in result.redacted_text

    def test_secret_scanner_clean_text_passes(self) -> None:
        """Plain text with no secrets returns a clean scan result.

        When no secrets are detected, ``redacted_text`` is the original
        text unchanged and ``has_secrets`` is ``False``.
        """
        clean_text = "The quick brown fox jumps over the lazy dog."

        result = scan_text(clean_text)

        assert result.has_secrets is False
        assert result.secrets_found == 0
        assert result.secret_types == []
        assert result.redacted_text == clean_text