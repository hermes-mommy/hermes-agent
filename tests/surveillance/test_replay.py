"""P7-003: Replay Protection — comprehensive unit and integration tests.

Tests cover:
- validate_timestamp: valid, expired, future, invalid-format
- check_nonce: unique (passes), duplicate (409), Redis failure (503 fail-closed)
- Nonce TTL verification (ex=660)
- Atomic SET NX EX verification (nx=True, no GET-then-SET)
- Integration: full auth flow with replay protection via TestClient
"""

from __future__ import annotations

import hashlib
import hmac as hmac_module
import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

# Ensure project root is on sys.path for ``from src.*`` imports.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.surveillance.replay import (
    NONCE_KEY_PREFIX,
    NONCE_TTL_SECONDS,
    TIMESTAMP_WINDOW_SECONDS,
    _set_redis_for_testing,
    check_nonce,
    validate_timestamp,
)


# ===========================================================================
# validate_timestamp tests
# ===========================================================================


@pytest.mark.asyncio
class TestValidateTimestamp:
    """Unit tests for ``validate_timestamp()``."""

    async def test_valid_timestamp_within_window_passes(self) -> None:
        """A timestamp within the 300-second window should not raise."""
        now = int(time.time())
        ts = str(now - 100)
        await validate_timestamp(ts)

    async def test_valid_timestamp_exact_now_passes(self) -> None:
        """Timestamp equal to current time is valid."""
        await validate_timestamp(str(int(time.time())))

    async def test_valid_timestamp_at_window_boundary_passes(self) -> None:
        """Timestamp exactly at the window boundary (300s) is valid."""
        now = int(time.time())
        await validate_timestamp(str(now - 300))
        await validate_timestamp(str(now + 300))

    async def test_expired_timestamp_raises_401(self) -> None:
        """Timestamp older than 300 seconds raises HTTPException(401)."""
        now = int(time.time())
        old = str(now - 301)
        with pytest.raises(HTTPException) as exc_info:
            await validate_timestamp(old)
        assert exc_info.value.status_code == 401
        assert "Request expired" in exc_info.value.detail

    async def test_future_timestamp_raises_401(self) -> None:
        """Timestamp far in the future raises HTTPException(401)."""
        now = int(time.time())
        future = str(now + 301)
        with pytest.raises(HTTPException) as exc_info:
            await validate_timestamp(future)
        assert exc_info.value.status_code == 401
        assert "Request expired" in exc_info.value.detail

    async def test_far_expired_timestamp_raises_401(self) -> None:
        """Timestamp from years ago raises HTTPException(401)."""
        with pytest.raises(HTTPException) as exc_info:
            await validate_timestamp("1234567890")  # 2009-02-13
        assert exc_info.value.status_code == 401

    async def test_non_numeric_timestamp_raises_401(self) -> None:
        """Non-numeric timestamp string raises HTTPException(401)."""
        with pytest.raises(HTTPException) as exc_info:
            await validate_timestamp("not-a-number")
        assert exc_info.value.status_code == 401

    async def test_empty_timestamp_raises_401(self) -> None:
        """Empty timestamp string raises HTTPException(401)."""
        with pytest.raises(HTTPException) as exc_info:
            await validate_timestamp("")
        assert exc_info.value.status_code == 401

    async def test_timestamp_window_is_300(self) -> None:
        """Timestamp window must be exactly 300 seconds."""
        assert TIMESTAMP_WINDOW_SECONDS == 300, (
            f"TIMESTAMP_WINDOW_SECONDS={TIMESTAMP_WINDOW_SECONDS} must be 300"
        )


# ===========================================================================
# check_nonce tests
# ===========================================================================


@pytest.mark.asyncio
class TestCheckNonce:
    """Unit tests for ``check_nonce()``."""

    @pytest.fixture(autouse=True)
    def _mock_redis(self) -> None:
        """Replace the module-level Redis client with a mock."""
        self.mock_redis = AsyncMock()
        _set_redis_for_testing(self.mock_redis)
        yield
        _set_redis_for_testing(None)

    async def test_unique_nonce_passes(self) -> None:
        """First-time nonce should be accepted (SET NX returns True)."""
        self.mock_redis.set = AsyncMock(return_value=True)

        await check_nonce("unique-nonce-abc123")

        self.mock_redis.set.assert_called_once_with(
            f"{NONCE_KEY_PREFIX}unique-nonce-abc123",
            "1",
            nx=True,
            ex=NONCE_TTL_SECONDS,
        )

    async def test_duplicate_nonce_raises_409(self) -> None:
        """Second use of same nonce raises HTTPException(409)."""
        self.mock_redis.set = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await check_nonce("duplicate-nonce")
        assert exc_info.value.status_code == 409
        assert "Replay detected" in exc_info.value.detail

    async def test_nonce_key_uses_correct_prefix(self) -> None:
        """The Redis key must be prefixed with ``surveillance:nonce:``."""
        self.mock_redis.set = AsyncMock(return_value=True)
        await check_nonce("my-nonce")
        call_args = self.mock_redis.set.call_args[0]
        assert call_args[0].startswith(NONCE_KEY_PREFIX)
        assert call_args[0] == f"{NONCE_KEY_PREFIX}my-nonce"

    async def test_nonce_ttl_is_at_least_600(self) -> None:
        """Nonce TTL must be >= 600 seconds (>= 2x the 5-minute window)."""
        assert NONCE_TTL_SECONDS >= 600, (
            f"NONCE_TTL_SECONDS={NONCE_TTL_SECONDS} must be >= 600"
        )
        self.mock_redis.set = AsyncMock(return_value=True)
        await check_nonce("ttl-test-nonce")
        call_kwargs = self.mock_redis.set.call_args[1]
        assert call_kwargs["ex"] == NONCE_TTL_SECONDS
        assert call_kwargs["ex"] >= 600

    async def test_uses_atomic_set_nx_ex(self) -> None:
        """Must use SET NX EX, not GET then SET."""
        self.mock_redis.set = AsyncMock(return_value=True)
        await check_nonce("atomic-test-nonce")

        self.mock_redis.set.assert_called_once()
        call_kwargs = self.mock_redis.set.call_args[1]
        assert call_kwargs.get("nx") is True, "nx=True required"
        assert "ex" in call_kwargs, "ex= required for TTL"
        self.mock_redis.get.assert_not_called()

    async def test_redis_connection_failure_fail_closed(self) -> None:
        """Redis connection failure raises HTTPException(503)."""
        self.mock_redis.set = AsyncMock(side_effect=ConnectionError("redis down"))

        with pytest.raises(HTTPException) as exc_info:
            await check_nonce("fail-closed-nonce")
        assert exc_info.value.status_code == 503
        assert "Replay protection unavailable" in exc_info.value.detail

    async def test_redis_auth_failure_fail_closed(self) -> None:
        """Redis auth failure also fails closed."""
        self.mock_redis.set = AsyncMock(
            side_effect=OSError("connection refused")
        )

        with pytest.raises(HTTPException) as exc_info:
            await check_nonce("auth-fail-nonce")
        assert exc_info.value.status_code == 503

    async def test_redis_timeout_fail_closed(self) -> None:
        """Redis timeout fails closed."""
        self.mock_redis.set = AsyncMock(
            side_effect=TimeoutError("redis timeout")
        )

        with pytest.raises(HTTPException) as exc_info:
            await check_nonce("timeout-nonce")
        assert exc_info.value.status_code == 503


# ===========================================================================
# Integration tests — full auth flow with replay protection
# ===========================================================================


TEST_SECRET = "test-hmac-secret-for-replay-integration"


def _sign(
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body: bytes,
    secret: str,
) -> str:
    """Compute the expected HMAC-SHA256 signature for a request."""
    signing_string = (
        f"{method}:{path}:{timestamp}:{nonce}:{body.decode('utf-8')}"
    )
    return hmac_module.new(
        secret.encode("utf-8"),
        signing_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _make_payload() -> dict[str, object]:
    """Return a minimal valid surveillance event payload."""
    return {
        "device_id": "test-device-01",
        "event_type": "screen_state",
        "occurred_at": "2026-06-01T12:00:00+00:00",
        "payload": {"state": "on"},
    }


@pytest.fixture
def integration_client() -> TestClient:
    """FastAPI TestClient with the surveillance router mounted."""
    from src.surveillance.router import surveillance_router

    app = FastAPI()
    app.include_router(surveillance_router)
    return TestClient(app)


class TestIntegrationAuthFlow:
    """Integration tests: full auth flow with replay protection active."""

    def test_full_flow_with_valid_everything(
        self, integration_client: TestClient
    ) -> None:
        """Valid timestamp, unique nonce, correct HMAC → 202."""
        ts = str(int(time.time()))
        nonce = "integration-unique-nonce-1"
        payload = _make_payload()
        body = json.dumps(payload).encode("utf-8")
        signature = _sign(
            "POST", "/surveillance/events", ts, nonce, body, TEST_SECRET
        )

        with patch(
            "src.surveillance.auth.get_hmac_secret", return_value=TEST_SECRET
        ), patch(
            "src.surveillance.auth.check_nonce",
        ) as mock_cn:
            headers = {
                "X-Signature": signature,
                "X-Timestamp": ts,
                "X-Nonce": nonce,
                "Content-Type": "application/json",
            }
            response = integration_client.post(
                "/surveillance/events", content=body, headers=headers
            )
            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "accepted"

    def test_expired_timestamp_in_full_flow_returns_401(
        self, integration_client: TestClient
    ) -> None:
        """Expired timestamp → 401 before hitting Redis or HMAC."""
        ts = str(int(time.time()) - 301)
        nonce = "expired-nonce"
        payload = _make_payload()
        body = json.dumps(payload).encode("utf-8")
        signature = _sign(
            "POST", "/surveillance/events", ts, nonce, body, TEST_SECRET
        )

        with patch(
            "src.surveillance.auth.get_hmac_secret", return_value=TEST_SECRET
        ), patch(
            "src.surveillance.auth.check_nonce",
        ):
            headers = {
                "X-Signature": signature,
                "X-Timestamp": ts,
                "X-Nonce": nonce,
                "Content-Type": "application/json",
            }
            response = integration_client.post(
                "/surveillance/events", content=body, headers=headers
            )
            assert response.status_code == 401
            assert "Request expired" in response.json()["detail"]

    def test_duplicate_nonce_in_full_flow_returns_409(
        self, integration_client: TestClient
    ) -> None:
        """Duplicate nonce → 409 (replay detected)."""
        ts = str(int(time.time()))
        nonce = "duplicate-full-flow-nonce"
        payload = _make_payload()
        body = json.dumps(payload).encode("utf-8")
        signature = _sign(
            "POST", "/surveillance/events", ts, nonce, body, TEST_SECRET
        )

        async def _raise_409(n: str) -> None:
            raise HTTPException(status_code=409, detail="Replay detected")

        with patch(
            "src.surveillance.auth.get_hmac_secret", return_value=TEST_SECRET
        ), patch(
            "src.surveillance.auth.check_nonce",
            side_effect=_raise_409,
        ):
            headers = {
                "X-Signature": signature,
                "X-Timestamp": ts,
                "X-Nonce": nonce,
                "Content-Type": "application/json",
            }
            response = integration_client.post(
                "/surveillance/events", content=body, headers=headers
            )
            assert response.status_code == 409
            assert "Replay detected" in response.json()["detail"]

    def test_redis_failure_in_full_flow_returns_503(
        self, integration_client: TestClient
    ) -> None:
        """Redis unavailable → 503 (fail-closed)."""
        ts = str(int(time.time()))
        nonce = "redis-down-nonce"
        payload = _make_payload()
        body = json.dumps(payload).encode("utf-8")
        signature = _sign(
            "POST", "/surveillance/events", ts, nonce, body, TEST_SECRET
        )

        async def _raise_503(n: str) -> None:
            raise HTTPException(
                status_code=503, detail="Replay protection unavailable"
            )

        with patch(
            "src.surveillance.auth.get_hmac_secret", return_value=TEST_SECRET
        ), patch(
            "src.surveillance.auth.check_nonce",
            side_effect=_raise_503,
        ):
            headers = {
                "X-Signature": signature,
                "X-Timestamp": ts,
                "X-Nonce": nonce,
                "Content-Type": "application/json",
            }
            response = integration_client.post(
                "/surveillance/events", content=body, headers=headers
            )
            assert response.status_code == 503
            assert (
                "Replay protection unavailable" in response.json()["detail"]
            )


# ===========================================================================
# Source code verification tests (grep-style checks)
# ===========================================================================


class TestSourceCodePatterns:
    """Verify replay.py uses correct patterns (no GET-then-SET, etc.)."""

    @property
    def _replay_source(self) -> str:
        replay_path = (
            Path(__file__).resolve().parent.parent.parent
            / "src"
            / "surveillance"
            / "replay.py"
        )
        return replay_path.read_text(encoding="utf-8")

    def test_file_contains_nx_equals_true(self) -> None:
        """replay.py must contain ``nx=True`` (atomic SET NX)."""
        assert "nx=True" in self._replay_source, (
            "replay.py must use nx=True for atomic SET NX"
        )

    def test_file_contains_ex_equals(self) -> None:
        """replay.py must contain ``ex=`` (TTL for nonce key)."""
        assert "ex=" in self._replay_source, (
            "replay.py must use ex= for nonce TTL"
        )

    def test_file_does_not_use_get_then_set(self) -> None:
        """replay.py must NOT call redis_client.get() before redis_client.set()."""
        assert "redis_client.get" not in self._replay_source, (
            "replay.py must NOT use GET-then-SET"
        )

    def test_structlog_used_not_logging(self) -> None:
        """replay.py must use structlog, not standard logging."""
        assert "structlog.get_logger" in self._replay_source, (
            "replay.py must use structlog.get_logger()"
        )
        assert "logging.getLogger" not in self._replay_source, (
            "replay.py must NOT use logging.getLogger"
        )

    def test_db2_used(self) -> None:
        """replay.py must connect to Redis DB2."""
        assert "db=2" in self._replay_source, (
            "replay.py must use Redis DB2 (surveillance namespace)"
        )