"""P7-005: Redis DB2 Surveillance Buffer — comprehensive unit tests.

Tests cover:
- push_event success path (RPUSH + EXPIRE + metadata logging)
- push_event failure paths (Redis error, non-serializable data via ``default=str``)
- pop_events FIFO atomic read-and-trim via pipeline
- pop_events edge cases (empty buffer, bad JSON, Redis error)
- buffer_size and close operations
- Factory ``create_buffer`` configuration (DB2, port 6380, password resolution)
- Protocol conformance (``isinstance`` check against ``SurveillanceBuffer``)

All Redis interaction is mocked via ``unittest.mock.AsyncMock`` — no real
Redis connection is required.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.surveillance.redis_buffer import (
    RedisSurveillanceBuffer,
    SurveillanceBuffer,
    create_buffer,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_event() -> dict:
    """A representative surveillance event dict."""
    return {
        "event_type": "clipboard",
        "device_id": "test-device-001",
        "timestamp": "2026-06-03T10:00:00Z",
    }


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Build a fully-mocked ``redis.asyncio.Redis`` client."""
    mock = AsyncMock()
    mock.rpush = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    mock.llen = AsyncMock(return_value=5)
    mock.aclose = AsyncMock()

    # Pipeline mock — returns raw JSON strings in lrange, bool for ltrim
    pipe_mock = AsyncMock()
    pipe_mock.lrange = MagicMock(return_value=pipe_mock)
    pipe_mock.ltrim = MagicMock(return_value=pipe_mock)
    pipe_mock.execute = AsyncMock(return_value=[[], True])
    mock.pipeline = MagicMock(return_value=pipe_mock)

    return mock


@pytest.fixture
def buffer(mock_redis: AsyncMock) -> RedisSurveillanceBuffer:
    """A ``RedisSurveillanceBuffer`` wired to the mocked Redis client."""
    return RedisSurveillanceBuffer(_redis=mock_redis)


# ---------------------------------------------------------------------------
# TestPushEvent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPushEvent:
    """Unit tests for ``RedisSurveillanceBuffer.push_event()``."""

    async def test_push_event_returns_true_on_success(
        self, buffer: RedisSurveillanceBuffer, sample_event: dict
    ) -> None:
        result = await buffer.push_event(sample_event)
        assert result is True

    async def test_push_event_calls_rpush_with_correct_key(
        self, buffer: RedisSurveillanceBuffer, mock_redis: AsyncMock, sample_event: dict
    ) -> None:
        await buffer.push_event(sample_event)
        call_args = mock_redis.rpush.call_args
        assert call_args[0][0] == "surveillance:buffer"

    async def test_push_event_serializes_dict_to_json(
        self, buffer: RedisSurveillanceBuffer, mock_redis: AsyncMock, sample_event: dict
    ) -> None:
        await buffer.push_event(sample_event)
        call_args = mock_redis.rpush.call_args
        serialized = call_args[0][1]
        deserialized = json.loads(serialized)
        assert deserialized["event_type"] == "clipboard"
        assert deserialized["device_id"] == "test-device-001"

    async def test_push_event_handles_non_serializable_via_default_str(
        self, buffer: RedisSurveillanceBuffer, mock_redis: AsyncMock
    ) -> None:
        """``default=str`` should serialise non-JSON-safe types without error."""
        import datetime

        event = {"event_type": "test", "at": datetime.datetime(2026, 6, 3, 10, 0, 0)}
        result = await buffer.push_event(event)
        assert result is True
        # Verify the datetime was serialised as its ISO string
        serialized = mock_redis.rpush.call_args[0][1]
        assert "2026-06-03" in serialized

    async def test_push_event_sets_ttl(
        self, buffer: RedisSurveillanceBuffer, mock_redis: AsyncMock, sample_event: dict
    ) -> None:
        await buffer.push_event(sample_event)
        mock_redis.expire.assert_called_once_with("surveillance:buffer", 300)

    async def test_push_event_returns_false_on_redis_error(
        self, mock_redis: AsyncMock, sample_event: dict
    ) -> None:
        mock_redis.rpush.side_effect = ConnectionError("redis down")
        buf = RedisSurveillanceBuffer(_redis=mock_redis)
        result = await buf.push_event(sample_event)
        assert result is False

    async def test_push_event_logs_metadata_not_payload(
        self, buffer: RedisSurveillanceBuffer, mock_redis: AsyncMock
    ) -> None:
        """Log record must include event_type/device_id/buffer_size, never raw data."""
        with patch("src.surveillance.redis_buffer.logger.info") as mock_log:
            event = {
                "event_type": "clipboard",
                "device_id": "dev-X",
                "secret": "should-not-appear",
            }
            await buffer.push_event(event)
            # Find the push log call (there may be multiple logger.info calls)
            push_calls = [
                c for c in mock_log.call_args_list
                if c[0][0] == "surveillance_buffer_push"
            ]
            assert len(push_calls) == 1
            kwargs = push_calls[0][1]
            assert "secret" not in str(kwargs)
            assert kwargs["event_type"] == "clipboard"
            assert kwargs["device_id"] == "dev-X"
            assert "buffer_size" in kwargs


# ---------------------------------------------------------------------------
# TestPopEvents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPopEvents:
    """Unit tests for ``RedisSurveillanceBuffer.pop_events()``."""

    async def test_pop_events_returns_deserialized_dicts(
        self, buffer: RedisSurveillanceBuffer, mock_redis: AsyncMock
    ) -> None:
        event1 = json.dumps({"event_type": "clipboard", "device_id": "d1"})
        event2 = json.dumps({"event_type": "keystroke", "device_id": "d2"})
        pipe = mock_redis.pipeline.return_value
        pipe.execute = AsyncMock(return_value=[[event1, event2], True])

        result = await buffer.pop_events(count=2)
        assert len(result) == 2
        assert result[0]["event_type"] == "clipboard"
        assert result[1]["event_type"] == "keystroke"

    async def test_pop_events_calls_ltrim_to_remove_popped(
        self, buffer: RedisSurveillanceBuffer, mock_redis: AsyncMock
    ) -> None:
        pipe = mock_redis.pipeline.return_value
        await buffer.pop_events(count=3)

        # ltrim(surveillance:buffer, 3, -1) removes the first 3 items
        pipe.ltrim.assert_called_once_with("surveillance:buffer", 3, -1)

    async def test_pop_events_empty_buffer_returns_empty_list(
        self, buffer: RedisSurveillanceBuffer, mock_redis: AsyncMock
    ) -> None:
        pipe = mock_redis.pipeline.return_value
        pipe.execute = AsyncMock(return_value=[[], True])

        result = await buffer.pop_events()
        assert result == []

    async def test_pop_events_handles_bad_json_gracefully(
        self, buffer: RedisSurveillanceBuffer, mock_redis: AsyncMock
    ) -> None:
        pipe = mock_redis.pipeline.return_value
        pipe.execute = AsyncMock(
            return_value=[
                [json.dumps({"good": 1}), "not-json-at-all", json.dumps({"also": "good"})],
                True,
            ]
        )

        with patch("src.surveillance.redis_buffer.logger.warning") as mock_warn:
            result = await buffer.pop_events(count=3)
            assert len(result) == 2
            assert result[0] == {"good": 1}
            assert result[1] == {"also": "good"}
            mock_warn.assert_called_once()

    async def test_pop_events_default_count_is_10(
        self, buffer: RedisSurveillanceBuffer, mock_redis: AsyncMock
    ) -> None:
        pipe = mock_redis.pipeline.return_value
        await buffer.pop_events()
        # lrange called with 0..9 (count=10)
        pipe.lrange.assert_called_once_with("surveillance:buffer", 0, 9)

    async def test_pop_events_handles_redis_error(
        self, mock_redis: AsyncMock
    ) -> None:
        pipe = mock_redis.pipeline.return_value
        pipe.execute.side_effect = ConnectionError("redis down")
        buf = RedisSurveillanceBuffer(_redis=mock_redis)
        result = await buf.pop_events()
        assert result == []

    async def test_pop_events_handles_non_list_first_result(
        self, buffer: RedisSurveillanceBuffer, mock_redis: AsyncMock
    ) -> None:
        """If LRANGE returns something unexpected, still handles gracefully."""
        pipe = mock_redis.pipeline.return_value
        pipe.execute = AsyncMock(return_value=[None, True])

        result = await buffer.pop_events()
        assert result == []


# ---------------------------------------------------------------------------
# TestBufferSize
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestBufferSize:
    """Unit tests for ``RedisSurveillanceBuffer.buffer_size()``."""

    async def test_buffer_size_returns_llen_result(
        self, buffer: RedisSurveillanceBuffer, mock_redis: AsyncMock
    ) -> None:
        mock_redis.llen = AsyncMock(return_value=42)
        size = await buffer.buffer_size()
        assert size == 42
        mock_redis.llen.assert_called_once_with("surveillance:buffer")

    async def test_buffer_size_handles_redis_error(
        self, mock_redis: AsyncMock
    ) -> None:
        mock_redis.llen.side_effect = ConnectionError("redis down")
        buf = RedisSurveillanceBuffer(_redis=mock_redis)
        size = await buf.buffer_size()
        assert size == 0


# ---------------------------------------------------------------------------
# TestClose
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestClose:
    """Unit tests for ``RedisSurveillanceBuffer.close()``."""

    async def test_close_calls_aclose(
        self, buffer: RedisSurveillanceBuffer, mock_redis: AsyncMock
    ) -> None:
        await buffer.close()
        mock_redis.aclose.assert_called_once()

    async def test_close_handles_redis_error(
        self, mock_redis: AsyncMock
    ) -> None:
        mock_redis.aclose.side_effect = ConnectionError("redis down")
        buf = RedisSurveillanceBuffer(_redis=mock_redis)
        # Should not raise
        await buf.close()


# ---------------------------------------------------------------------------
# TestCreateBuffer
# ---------------------------------------------------------------------------


class TestCreateBuffer:
    """Unit tests for the ``create_buffer()`` factory function."""

    def test_create_buffer_uses_db2(self) -> None:
        with patch("redis.asyncio.Redis") as mock_redis_cls:
            create_buffer()
            call_kwargs = mock_redis_cls.call_args[1]
            assert call_kwargs["db"] == 2

    def test_create_buffer_default_port_6380(self) -> None:
        with patch("redis.asyncio.Redis") as mock_redis_cls:
            create_buffer()
            call_kwargs = mock_redis_cls.call_args[1]
            assert call_kwargs["port"] == 6380

    def test_create_buffer_password_from_explicit_arg(self) -> None:
        with patch("redis.asyncio.Redis") as mock_redis_cls:
            create_buffer(password="explicit-pass")
            call_kwargs = mock_redis_cls.call_args[1]
            assert call_kwargs["password"] == "explicit-pass"

    def test_create_buffer_password_from_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("REDIS_PASSWORD", "env-pass")
        with patch("redis.asyncio.Redis") as mock_redis_cls:
            create_buffer()
            call_kwargs = mock_redis_cls.call_args[1]
            assert call_kwargs["password"] == "env-pass"

    def test_create_buffer_decodes_responses(self) -> None:
        with patch("redis.asyncio.Redis") as mock_redis_cls:
            create_buffer()
            call_kwargs = mock_redis_cls.call_args[1]
            assert call_kwargs["decode_responses"] is True


# ---------------------------------------------------------------------------
# TestProtocol
# ---------------------------------------------------------------------------


class TestProtocol:
    """Tests confirming ``RedisSurveillanceBuffer`` conforms to the Protocol."""

    def test_redis_buffer_implements_protocol(self, mock_redis: AsyncMock) -> None:
        buf = RedisSurveillanceBuffer(_redis=mock_redis)
        assert isinstance(buf, SurveillanceBuffer)

    def test_redis_buffer_has_correct_default_attributes(self, mock_redis: AsyncMock) -> None:
        buf = RedisSurveillanceBuffer(_redis=mock_redis)
        assert buf._buffer_key == "surveillance:buffer"
        assert buf._ttl_seconds == 300


# ---------------------------------------------------------------------------
# TestPushEvent edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPushEventEdgeCases:
    """Additional edge-case tests for ``push_event()``."""

    async def test_push_event_when_buffer_is_empty(
        self, buffer: RedisSurveillanceBuffer, mock_redis: AsyncMock, sample_event: dict
    ) -> None:
        """LLEN returns 1 after first push (rpush returns next index)."""
        mock_redis.llen = AsyncMock(return_value=1)
        result = await buffer.push_event(sample_event)
        assert result is True