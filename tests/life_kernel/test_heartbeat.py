"""Tests for Guinevere's Heartbeat Service (LK-005).

This module tests the heartbeat service's heartbeat scheduling, HARD STOP detection,
state transitions, and autonomous cycle management.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as aioredis

from src.life_kernel.heartbeat import HeartbeatInterval, HeartbeatService


class TestHeartbeatIntervalEnum:
    """Test heartbeat interval enum."""

    def test_interval_enum_values(self) -> None:
        """Verify all 6 enum values are present."""
        expected_values = ["1s", "10s", "30s", "60s", "5m", "1h"]
        actual_values = [interval.value for interval in HeartbeatInterval]

        assert actual_values == expected_values, (
            f"Interval enum values mismatch. Expected {expected_values}, "
            f"got {actual_values}"
        )

    def test_interval_enum_length(self) -> None:
        """Verify exactly 6 interval types exist."""
        assert len(HeartbeatInterval) == 6, (
            f"Expected exactly 6 interval types, got {len(HeartbeatInterval)}"
        )


class TestHeartbeatConstructor:
    """Test HeartbeatService initialization."""

    @pytest.fixture
    def mock_graph(self) -> MagicMock:
        """Create a mock graph."""
        graph = MagicMock()
        graph.aget_state = AsyncMock(return_value=None)
        return graph

    @pytest.fixture
    def mock_redis_client(self) -> MagicMock:
        """Create a mock Redis client."""
        redis_client = MagicMock(spec=aioredis.Redis)
        redis_client.get = AsyncMock(return_value=None)
        return redis_client

    @pytest.fixture
    def heartbeat_service(
        self,
        mock_graph: MagicMock,
        mock_redis_client: MagicMock,
    ) -> HeartbeatService:
        """Create a HeartbeatService instance."""
        return HeartbeatService(
            graph=mock_graph,
            redis_client=mock_redis_client,
            checkpointer=None,
        )

    def test_constructor_sets_attributes(
        self,
        heartbeat_service: HeartbeatService,
        mock_graph: MagicMock,
        mock_redis_client: MagicMock,
    ) -> None:
        """Verify all attributes are set correctly."""
        assert heartbeat_service.graph is mock_graph
        assert heartbeat_service.redis_client is mock_redis_client
        assert heartbeat_service.checkpointer is None
        assert len(heartbeat_service._tasks) == 0
        assert len(heartbeat_service._last_heartbeats) == 0

    def test_constructor_heartbeat_intervals(
        self,
        heartbeat_service: HeartbeatService,
    ) -> None:
        """Verify heartbeat intervals are set correctly."""
        expected_intervals = {
            HeartbeatInterval.L1S: 1,
            HeartbeatInterval.L10S: 10,
            HeartbeatInterval.L30S: 30,
            HeartbeatInterval.L60S: 60,
            HeartbeatInterval.L5M: 300,
            HeartbeatInterval.L1H: 3600,
        }

        assert heartbeat_service._heartbeat_intervals == expected_intervals, (
            "Heartbeat intervals mismatch"
        )

    def test_get_last_heartbeat_time_not_executed(self, heartbeat_service: HeartbeatService) -> None:
        """Verify get_last_heartbeat_time returns None for unexecuted intervals."""
        result = heartbeat_service.get_last_heartbeat_time(HeartbeatInterval.L1S)
        assert result is None, "Expected None for unexecuted interval"


@pytest.mark.asyncio
class TestHeartbeatStartStop:
    """Test HeartbeatService start and stop functionality."""

    @pytest.fixture
    def mock_graph(self) -> MagicMock:
        """Create a mock graph."""
        graph = MagicMock()
        graph.aget_state = AsyncMock(return_value=None)
        return graph

    @pytest.fixture
    def mock_redis_client(self) -> MagicMock:
        """Create a mock Redis client."""
        redis_client = MagicMock(spec=aioredis.Redis)
        redis_client.get = AsyncMock(return_value=None)
        return redis_client

    @pytest.fixture
    def heartbeat_service(
        self,
        mock_graph: MagicMock,
        mock_redis_client: MagicMock,
    ) -> HeartbeatService:
        """Create a HeartbeatService instance."""
        return HeartbeatService(
            graph=mock_graph,
            redis_client=mock_redis_client,
            checkpointer=None,
        )

    @pytest.mark.asyncio
    async def test_start_creates_tasks(self, heartbeat_service: HeartbeatService) -> None:
        """Verify start creates tasks for all 6 heartbeat types."""
        await heartbeat_service.start()

        try:
            assert len(heartbeat_service._tasks) == 6, (
                f"Expected 6 tasks, got {len(heartbeat_service._tasks)}"
            )
        finally:
            await heartbeat_service.stop()

    @pytest.mark.asyncio
    async def test_start_logs_debug(self, heartbeat_service: HeartbeatService) -> None:
        """Verify start logs debug messages."""
        with patch("src.life_kernel.heartbeat.logger") as mock_logger:
            await heartbeat_service.start()

            try:
                assert mock_logger.debug.called
                debug_calls = [call for call in mock_logger.debug.call_args_list]
                assert any("heartbeat_service_starting" in str(call) for call in debug_calls), (
                    "Expected debug log for service starting"
                )
            finally:
                await heartbeat_service.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_tasks(self, heartbeat_service: HeartbeatService) -> None:
        """Verify stop cancels all tasks."""
        await heartbeat_service.start()

        task_count_before = len(heartbeat_service._tasks)
        assert task_count_before == 6

        await heartbeat_service.stop()

        assert len(heartbeat_service._tasks) == 0

    @pytest.mark.asyncio
    async def test_stop_waits_for_tasks(self, heartbeat_service: HeartbeatService) -> None:
        """Verify stop waits for tasks to complete gracefully."""
        await heartbeat_service.start()

        # Give tasks a moment to start
        await asyncio.sleep(0.1)

        task_count_before = len(heartbeat_service._tasks)
        assert task_count_before == 6

        await heartbeat_service.stop()

        # Tasks should be cancelled and cleared
        assert len(heartbeat_service._tasks) == 0


@pytest.mark.asyncio
class TestHeartbeat1SHardStopDetection:
    """Test 1s heartbeat HARD STOP detection."""

    @pytest.fixture
    def mock_graph(self) -> MagicMock:
        """Create a mock graph."""
        graph = MagicMock()
        # Return a fully-populated dict so the 60s heartbeat's sanitized
        # _summary log (heartbeat.py:477-492) can call result.get(...) on a
        # real dict instead of an AsyncMock coroutine — prevents the
        # "coroutine was never awaited" RuntimeWarning when the full service
        # is started (test_no_hard_stop_continues runs all 6 loops).
        graph.ainvoke = AsyncMock(return_value={
            "decision": "continue",
            "current_phase": "idle",
            "last_autonomous_decision": "test",
            "cycle_count": 0,
            "act_count": 0,
            "goals": [],
            "commitments": [],
            "concerns": [],
            "observations": [],
            "recalled_memories": [],
            "recalled_concepts": [],
            "journal_entries": [],
            "world_model_status": "active",
            "hard_stop_requested": False,
        })
        graph.aget_state = AsyncMock(return_value=None)
        return graph

    @pytest.fixture
    def mock_redis_client(self) -> MagicMock:
        """Create a mock Redis client."""
        redis_client = MagicMock(spec=aioredis.Redis)
        return redis_client

    @pytest.fixture
    def heartbeat_service(self, mock_graph: MagicMock, mock_redis_client: MagicMock) -> HeartbeatService:
        """Create a HeartbeatService instance."""
        return HeartbeatService(
            graph=mock_graph,
            redis_client=mock_redis_client,
            checkpointer=None,
        )

    @pytest.mark.asyncio
    async def test_hard_stop_detected(self, heartbeat_service: HeartbeatService) -> None:
        """Test that HARD STOP detection stops the service."""
        # Set HARD STOP flag in Redis
        heartbeat_service.redis_client.get = AsyncMock(return_value=b"true")

        # Start the service
        await heartbeat_service.start()

        try:
            # Give 1s heartbeat a moment to execute
            await asyncio.sleep(1.5)

            # Verify all tasks are done (stop cancels them)
            assert all(t.done() for t in heartbeat_service._tasks)
        finally:
            await heartbeat_service.stop()

    @pytest.mark.asyncio
    async def test_no_hard_stop_continues(self, heartbeat_service: HeartbeatService) -> None:
        """Test that service continues when no HARD STOP flag."""
        # No HARD STOP flag (Redis returns None)
        heartbeat_service.redis_client.get = AsyncMock(return_value=None)

        # Start the service
        await heartbeat_service.start()

        try:
            # Give 1s heartbeat a moment to execute
            await asyncio.sleep(1.5)

            # Verify service is still running
            assert len(heartbeat_service._tasks) == 6
        finally:
            await heartbeat_service.stop()

    @pytest.mark.asyncio
    async def test_hard_stop_sets_flag_in_state(self, heartbeat_service: HeartbeatService) -> None:
        """Test that HARD STOP sets hard_stop_requested in graph state."""
        # Set HARD STOP flag in Redis
        heartbeat_service.redis_client.get = AsyncMock(return_value=b"true")

        # Start the service
        await heartbeat_service.start()

        # Give 1s heartbeat a moment to execute
        await asyncio.sleep(1.5)

        # Verify graph.ainvoke was called with hard_stop_requested=True
        heartbeat_service.graph.ainvoke.assert_called_once()
        call_args = heartbeat_service.graph.ainvoke.call_args
        assert call_args[1]["config"]["configurable"]["thread_id"] == "heartbeat"
        # call_args[0] is the positional-args tuple: ({"hard_stop_requested": True},)
        assert call_args[0][0]["hard_stop_requested"] is True


@pytest.mark.asyncio
class TestHeartbeat60SGraphInvocation:
    """Test 60s heartbeat graph invocation."""

    @pytest.fixture
    def mock_graph(self) -> MagicMock:
        """Create a mock graph with aget_state returning IDLE phase."""
        graph = MagicMock()
        # Mock ainvoke to return a dict with all expected fields to avoid
        # RuntimeWarning from unawaited coroutines when heartbeat.py:483
        # calls result.get("goals", [])
        graph.ainvoke = AsyncMock(return_value={
            "decision": "continue",
            "current_phase": "idle",
            "last_autonomous_decision": "test",
            "cycle_count": 0,
            "act_count": 0,
            "goals": [],
            "commitments": [],
            "concerns": [],
            "observations": [],
            "recalled_memories": [],
            "recalled_concepts": [],
            "journal_entries": [],
            "world_model_status": "active",
            "hard_stop_requested": False,
        })
        # aget_state returns None → phase gate skipped → ainvoke proceeds
        graph.aget_state = AsyncMock(return_value=None)
        return graph

    @pytest.fixture
    def mock_redis_client(self) -> MagicMock:
        """Create a mock Redis client."""
        redis_client = MagicMock(spec=aioredis.Redis)
        return redis_client

    @pytest.fixture
    def heartbeat_service(self, mock_graph: MagicMock, mock_redis_client: MagicMock) -> HeartbeatService:
        """Create a HeartbeatService instance."""
        return HeartbeatService(
            graph=mock_graph,
            redis_client=mock_redis_client,
            checkpointer=None,
        )

    @pytest.mark.asyncio
    async def test_heartbeat_60s_invokes_graph(self, heartbeat_service: HeartbeatService) -> None:
        """Test that 60s heartbeat invokes graph with decision signal.

        Calls _heartbeat_60s() directly — no sleep timer needed.
        """
        await heartbeat_service._heartbeat_60s()

        heartbeat_service.graph.ainvoke.assert_called_once()
        call_args = heartbeat_service.graph.ainvoke.call_args
        assert call_args[0][0]["decision"] == "continue"
        assert call_args[1]["config"]["configurable"]["thread_id"] == "heartbeat"

    @pytest.mark.asyncio
    async def test_heartbeat_60s_skips_when_no_graph(self, heartbeat_service: HeartbeatService) -> None:
        """Test that 60s heartbeat skips when graph is None.

        Calls _heartbeat_60s() directly — no sleep timer needed.
        """
        heartbeat_service.graph = None
        await heartbeat_service._heartbeat_60s()


@pytest.mark.asyncio
class TestHeartbeat10SHealthCheck:
    """Test 10s heartbeat health check."""

    @pytest.fixture
    def mock_graph(self) -> MagicMock:
        """Create a mock graph."""
        return MagicMock()

    @pytest.fixture
    def mock_redis_client(self) -> MagicMock:
        """Create a mock Redis client."""
        redis_client = MagicMock(spec=aioredis.Redis)
        return redis_client

    @pytest.fixture
    def heartbeat_service(self, mock_graph: MagicMock, mock_redis_client: MagicMock) -> HeartbeatService:
        """Create a HeartbeatService instance."""
        return HeartbeatService(
            graph=mock_graph,
            redis_client=mock_redis_client,
            checkpointer=None,
        )

    @pytest.mark.asyncio
    async def test_heartbeat_10s_executes(self, heartbeat_service: HeartbeatService) -> None:
        """Test that 10s heartbeat executes without errors.

        Calls _heartbeat_10s() directly — no sleep timer needed.
        """
        await heartbeat_service._heartbeat_10s()


@pytest.mark.asyncio
class TestHeartbeat30SAwarenessRefresh:
    """Test 30s heartbeat awareness refresh."""

    @pytest.fixture
    def mock_graph(self) -> MagicMock:
        """Create a mock graph."""
        return MagicMock()

    @pytest.fixture
    def mock_redis_client(self) -> MagicMock:
        """Create a mock Redis client."""
        redis_client = MagicMock(spec=aioredis.Redis)
        return redis_client

    @pytest.fixture
    def heartbeat_service(self, mock_graph: MagicMock, mock_redis_client: MagicMock) -> HeartbeatService:
        """Create a HeartbeatService instance."""
        return HeartbeatService(
            graph=mock_graph,
            redis_client=mock_redis_client,
            checkpointer=None,
        )

    @pytest.mark.asyncio
    async def test_heartbeat_30s_executes(self, heartbeat_service: HeartbeatService) -> None:
        """Test that 30s heartbeat executes without errors.

        Calls _heartbeat_30s() directly — no sleep timer needed.
        """
        await heartbeat_service._heartbeat_30s()


@pytest.mark.asyncio
class TestHeartbeat5MDeepScan:
    """Test 5m heartbeat deep scan."""

    @pytest.fixture
    def mock_graph(self) -> MagicMock:
        """Create a mock graph."""
        return MagicMock()

    @pytest.fixture
    def mock_redis_client(self) -> MagicMock:
        """Create a mock Redis client."""
        redis_client = MagicMock(spec=aioredis.Redis)
        return redis_client

    @pytest.fixture
    def heartbeat_service(self, mock_graph: MagicMock, mock_redis_client: MagicMock) -> HeartbeatService:
        """Create a HeartbeatService instance."""
        return HeartbeatService(
            graph=mock_graph,
            redis_client=mock_redis_client,
            checkpointer=None,
        )

    @pytest.mark.asyncio
    async def test_heartbeat_5m_executes(self, heartbeat_service: HeartbeatService) -> None:
        """Test that 5m heartbeat executes without errors.

        Calls _heartbeat_5m() directly — no sleep timer needed.
        """
        await heartbeat_service._heartbeat_5m()


@pytest.mark.asyncio
class TestHeartbeat1HReflection:
    """Test 1h heartbeat reflection."""

    @pytest.fixture
    def mock_graph(self) -> MagicMock:
        """Create a mock graph."""
        return MagicMock()

    @pytest.fixture
    def mock_redis_client(self) -> MagicMock:
        """Create a mock Redis client."""
        redis_client = MagicMock(spec=aioredis.Redis)
        return redis_client

    @pytest.fixture
    def heartbeat_service(self, mock_graph: MagicMock, mock_redis_client: MagicMock) -> HeartbeatService:
        """Create a HeartbeatService instance."""
        return HeartbeatService(
            graph=mock_graph,
            redis_client=mock_redis_client,
            checkpointer=None,
        )

    @pytest.mark.asyncio
    async def test_heartbeat_1h_executes(self, heartbeat_service: HeartbeatService) -> None:
        """Test that 1h heartbeat executes without errors.

        Calls _heartbeat_1h() directly — no sleep timer needed.
        """
        await heartbeat_service._heartbeat_1h()


@pytest.mark.asyncio
class TestHeartbeatErrorHandling:
    """Test heartbeat error handling and continuity."""

    @pytest.fixture
    def mock_graph(self) -> MagicMock:
        """Create a mock graph."""
        graph = MagicMock()
        graph.ainvoke = AsyncMock(side_effect=Exception("Test error"))
        graph.aget_state = AsyncMock(return_value=None)
        return graph

    @pytest.fixture
    def mock_redis_client(self) -> MagicMock:
        """Create a mock Redis client."""
        redis_client = MagicMock(spec=aioredis.Redis)
        redis_client.get = AsyncMock(return_value=None)
        return redis_client

    @pytest.fixture
    def heartbeat_service(self, mock_graph: MagicMock, mock_redis_client: MagicMock) -> HeartbeatService:
        """Create a HeartbeatService instance."""
        return HeartbeatService(
            graph=mock_graph,
            redis_client=mock_redis_client,
            checkpointer=None,
        )

    @pytest.mark.asyncio
    async def test_heartbeats_continue_on_error(self, heartbeat_service: HeartbeatService) -> None:
        """Test that heartbeat methods handle errors gracefully.

        Calls _heartbeat_60s() directly — graph raises, heartbeat logs and returns.
        Service remains functional.
        """
        await heartbeat_service._heartbeat_60s()
        # Service didn't crash — error was logged, not propagated

    @pytest.mark.asyncio
    async def test_stop_with_running_heartbeats(self, heartbeat_service: HeartbeatService) -> None:
        """Test that stop cancels all running heartbeats."""
        await heartbeat_service.start()

        # Give heartbeats a moment to start
        await asyncio.sleep(0.1)

        # Verify tasks are running
        task_count_before = len(heartbeat_service._tasks)
        assert task_count_before == 6

        # Stop the service
        await heartbeat_service.stop()

        # Verify tasks are cancelled
        assert len(heartbeat_service._tasks) == 0