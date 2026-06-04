"""P7-001: Unit tests for POST /surveillance/events webhook endpoint.

All test data is SYNTHETIC — no real surveillance data is used.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure project root is on sys.path for ``from src.*`` imports.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.surveillance.auth import HMACVerification, verify_hmac  # noqa: E402
from src.surveillance.router import surveillance_router  # noqa: E402


# ---------------------------------------------------------------------------
# Test application fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient with the surveillance router mounted.

    HMAC auth is overridden via dependency injection so these tests focus
    on payload validation and response shape. Auth is covered by
    ``test_auth.py``. The Redis buffer is mocked to avoid real connections.
    """
    app = FastAPI()
    app.dependency_overrides[verify_hmac] = lambda: HMACVerification(
        nonce="test-nonce", timestamp="1234567890"
    )
    app.include_router(surveillance_router)
    with patch("src.surveillance.router._buffer") as mock_buffer:
        mock_buffer.push_event = AsyncMock(return_value=True)
        yield TestClient(app)


# ---------------------------------------------------------------------------
# Synthetic test payload helpers
# ---------------------------------------------------------------------------


def _valid_payload(**overrides: object) -> dict[str, object]:
    """Return a minimal valid surveillance event payload.

    Any keyword argument overrides the corresponding top-level field.
    """
    base: dict[str, object] = {
        "device_id": "test-device-001",
        "event_type": "app_usage",
        "occurred_at": datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc).isoformat(),
        "payload": {"app_name": "chrome", "duration_seconds": 120},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestValidEvents:
    """Happy-path: valid events are accepted with 202 and proper response shape."""

    def test_valid_event_returns_202(self, client: TestClient) -> None:
        response = client.post("/surveillance/events", json=_valid_payload())
        assert response.status_code == 202

    def test_valid_event_has_accepted_status(self, client: TestClient) -> None:
        response = client.post("/surveillance/events", json=_valid_payload())
        data = response.json()
        assert data["status"] == "accepted"

    def test_valid_event_contains_event_id(self, client: TestClient) -> None:
        response = client.post("/surveillance/events", json=_valid_payload())
        data = response.json()
        assert "event_id" in data
        # Validate UUID format
        try:
            uuid.UUID(data["event_id"])
        except ValueError:
            pytest.fail(f"event_id is not a valid UUID: {data['event_id']}")

    def test_valid_event_contains_received_at(self, client: TestClient) -> None:
        response = client.post("/surveillance/events", json=_valid_payload())
        data = response.json()
        assert "received_at" in data
        # Should be a valid ISO-8601 datetime string
        received = data["received_at"]
        assert isinstance(received, str)
        datetime.fromisoformat(received)

    def test_optional_metadata_accepted(self, client: TestClient) -> None:
        payload = _valid_payload(metadata={"os": "android", "battery": 85})
        response = client.post("/surveillance/events", json=payload)
        assert response.status_code == 202

    def test_all_event_types_accepted(
        self,
        client: TestClient,
        event_type: str,
    ) -> None:
        """Parametrized: each valid event_type value is accepted."""
        payload = _valid_payload(event_type=event_type)
        response = client.post("/surveillance/events", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"


# Register the parametrize marker at class level via a helper.
# (pytest would normally handle @pytest.mark.parametrize on a class method,
#  but parametrize on test_all_event_types directly is cleaner inline.)
# We manually apply it here for clarity.
_VALID_EVENT_TYPES = [
    "app_usage",
    "screen_state",
    "notification",
    "location",
    "clipboard",
    "call_log",
    "health",
    "browser",
    "active_window",
    "idle_time",
    "screenshot",
    "camera",
]

pytest.mark.parametrize("event_type", _VALID_EVENT_TYPES)(TestValidEvents.test_all_event_types_accepted)


# ---------------------------------------------------------------------------
# Validation error tests
# ---------------------------------------------------------------------------


class TestInvalidEvents:
    """Invalid payloads return 422 Unprocessable Entity."""

    def test_invalid_event_type_returns_422(self, client: TestClient) -> None:
        payload = _valid_payload(event_type="invalid_type")
        response = client.post("/surveillance/events", json=payload)
        assert response.status_code == 422

    def test_missing_required_field_returns_422(self, client: TestClient) -> None:
        payload = {
            "event_type": "app_usage",
            "occurred_at": datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc).isoformat(),
            "payload": {},
        }
        response = client.post("/surveillance/events", json=payload)
        assert response.status_code == 422

    def test_extra_field_returns_422(self, client: TestClient) -> None:
        payload = _valid_payload(unknown_field="should_be_rejected")
        response = client.post("/surveillance/events", json=payload)
        assert response.status_code == 422

    def test_empty_device_id_returns_422(self, client: TestClient) -> None:
        payload = _valid_payload(device_id="")
        response = client.post("/surveillance/events", json=payload)
        assert response.status_code == 422

    def test_device_id_too_long_returns_422(self, client: TestClient) -> None:
        payload = _valid_payload(device_id="x" * 129)
        response = client.post("/surveillance/events", json=payload)
        assert response.status_code == 422

    def test_missing_event_type_returns_422(self, client: TestClient) -> None:
        payload = {
            "device_id": "test-device-001",
            "occurred_at": datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc).isoformat(),
            "payload": {},
        }
        response = client.post("/surveillance/events", json=payload)
        assert response.status_code == 422

    def test_invalid_datetime_format_returns_422(self, client: TestClient) -> None:
        payload = _valid_payload(occurred_at="not-a-datetime")
        response = client.post("/surveillance/events", json=payload)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Response shape tests
# ---------------------------------------------------------------------------


class TestResponseShape:
    """The response body has the expected structure."""

    def test_response_is_json(self, client: TestClient) -> None:
        response = client.post("/surveillance/events", json=_valid_payload())
        assert response.headers.get("content-type", "").startswith("application/json")

    def test_response_has_exactly_three_keys(self, client: TestClient) -> None:
        response = client.post("/surveillance/events", json=_valid_payload())
        data = response.json()
        assert set(data.keys()) == {"status", "event_id", "received_at"}


# ---------------------------------------------------------------------------
# Buffer push tests (C1 - Redis DB2 integration)
# ---------------------------------------------------------------------------


class TestBufferPush:
    """Verify that validated events are pushed to the Redis buffer."""

    def test_push_event_called_with_event_data(self, client: TestClient) -> None:
        """push_event is invoked with the serialized event dict after HMAC validation."""
        with patch("src.surveillance.router._buffer") as mock_buffer:
            mock_buffer.push_event = AsyncMock(return_value=True)
            response = client.post(
                "/surveillance/events", json=_valid_payload()
            )
            assert response.status_code == 202
            mock_buffer.push_event.assert_called_once()
            event_data = mock_buffer.push_event.call_args[0][0]
            assert event_data["device_id"] == "test-device-001"
            assert event_data["event_type"] == "app_usage"
            assert "occurred_at" in event_data
            assert "payload" in event_data

    def test_202_returned_when_push_raises(self, client: TestClient) -> None:
        """The 202 response is returned even if buffer push raises an exception."""
        with patch("src.surveillance.router._buffer") as mock_buffer:
            mock_buffer.push_event = AsyncMock(
                side_effect=RuntimeError("Redis connection lost")
            )
            response = client.post(
                "/surveillance/events", json=_valid_payload()
            )
            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "accepted"
            assert "event_id" in data

    def test_push_event_called_for_every_valid_event(
        self, client: TestClient, event_type: str
    ) -> None:
        """Parametrized: push_event is called for each valid event type."""
        with patch("src.surveillance.router._buffer") as mock_buffer:
            mock_buffer.push_event = AsyncMock(return_value=True)
            payload = _valid_payload(event_type=event_type)
            response = client.post("/surveillance/events", json=payload)
            assert response.status_code == 202
            mock_buffer.push_event.assert_called_once()
            event_data = mock_buffer.push_event.call_args[0][0]
            assert event_data["event_type"] == event_type


pytest.mark.parametrize("event_type", _VALID_EVENT_TYPES)(
    TestBufferPush.test_push_event_called_for_every_valid_event
)