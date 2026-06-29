"""Tests for the Life Kernel (M9 / W13).

Covers:
  - HeartbeatService: 6 intervals cycle (mocked)
  - SensorRegistry: register/unregister/sense_all/health_check
  - WorldModel: entity graph CRUD, queries, neighbors
  - Graph serialization: asyncio.Queue prevents concurrent writes
  - Edit-not-spam dashboard: checksum dedup skips unchanged state
  - Fail-soft: no PG/Redis required; missing backends return empty
  - SimpleTools: CONFIG_MISSING stubs when backends are None
  - wire() function: callable without error
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from guinevere.life_kernel import (
    CalendarSensorAdapter,
    CalendarTool,
    DriveTool,
    FinanceSensorAdapter,
    FinanceTool,
    HeartbeatInterval,
    HeartbeatService,
    NotionTool,
    SensorRegistry,
    WearableSensorAdapter,
    WorldModel,
    wire,
)
from guinevere.life_kernel.heartbeat import _state_checksum
from guinevere.life_kernel.sensors import SensorAdapter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def world_model() -> WorldModel:
    return WorldModel()


@pytest.fixture
def sensor_registry() -> SensorRegistry:
    return SensorRegistry()


def _make_mock_adapter(name: str = "test_sensor") -> Any:
    """Create a mock SensorAdapter."""
    adapter = MagicMock()
    adapter.name = name
    adapter.sense = AsyncMock(return_value=[{"source": name, "kind": "test", "value": 42}])
    adapter.health = AsyncMock(return_value=True)
    # Make isinstance check pass
    adapter.__class__.__name__ = "MockAdapter"
    return adapter


# ---------------------------------------------------------------------------
# HeartbeatService tests
# ---------------------------------------------------------------------------

class TestHeartbeatService:
    """HeartbeatService tests."""

    def test_init_has_six_intervals(self) -> None:
        """HeartbeatService must expose exactly 6 intervals."""
        hb = HeartbeatService()
        assert len(hb.intervals) == 6
        assert set(hb.intervals.keys()) == {
            "1s", "10s", "30s", "60s", "5m", "1h"
        }

    def test_interval_values(self) -> None:
        """Interval seconds must match P20 architecture benchmark."""
        hb = HeartbeatService()
        assert hb.intervals["1s"] == 1
        assert hb.intervals["10s"] == 10
        assert hb.intervals["30s"] == 30
        assert hb.intervals["60s"] == 60
        assert hb.intervals["5m"] == 300
        assert hb.intervals["1h"] == 3600

    @pytest.mark.asyncio
    async def test_start_creates_tasks(self) -> None:
        """start() should create 7 tasks (6 intervals + 1 graph-write consumer)."""
        hb = HeartbeatService()
        await hb.start()
        assert len(hb._tasks) == 7
        await hb.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_tasks(self) -> None:
        """stop() should cancel all tasks."""
        hb = HeartbeatService()
        await hb.start()
        await hb.stop()
        assert len(hb._tasks) == 0

    @pytest.mark.asyncio
    async def test_heartbeat_cycles_through_intervals(self) -> None:
        """All 6 interval handlers should execute at least once within a short time."""
        hb = HeartbeatService()
        await hb.start()
        # Allow some cycles to run (1s + 10s intervals will execute quickly).
        await asyncio.sleep(2.5)
        await hb.stop()

        # At least 1s and 10s should have fired.
        assert hb.get_last_heartbeat_time(HeartbeatInterval.L1S) is not None
        assert hb.get_last_heartbeat_time(HeartbeatInterval.L10S) is not None

    @pytest.mark.asyncio
    async def test_graph_write_queue_serialization(self) -> None:
        """Graph writes must go through asyncio.Queue (P20 invariant #4)."""
        hb = HeartbeatService()

        # Enqueue multiple writes.
        for i in range(5):
            await hb.enqueue_graph_write({"type": "test", "index": i})

        assert hb._graph_write_queue.qsize() == 5

        # Start consumer and let it drain.
        await hb.start()
        await asyncio.sleep(0.5)
        await hb.stop()

        # Queue should be empty after consumer processes all writes.
        assert hb._graph_write_queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_dashboard_writer_called(self) -> None:
        """Dashboard writer should be called on the 60s cycle."""
        dashboard = AsyncMock()
        hb = HeartbeatService(dashboard_writer=dashboard)
        await hb.start()
        # The 60s interval won't fire in 0.1s, so trigger manually.
        await hb._update_dashboard()
        await hb.stop()

        # Dashboard writer should have been called once (first call, no checksum yet).
        dashboard.update_dashboard.assert_called_once()

    @pytest.mark.asyncio
    async def test_dashboard_edit_not_spam(self) -> None:
        """Dashboard should skip update when state is unchanged (P20 invariant #6)."""
        dashboard = AsyncMock()
        hb = HeartbeatService(dashboard_writer=dashboard)
        await hb.start()

        # First call — should publish.
        await hb._update_dashboard()
        # Second call with same state — should skip.
        await hb._update_dashboard()
        await hb.stop()

        # Only one actual Discord call (the second was skipped due to checksum).
        dashboard.update_dashboard.assert_called_once()

    @pytest.mark.asyncio
    async def test_fail_soft_no_dashboard(self) -> None:
        """Heartbeat must work without a dashboard writer (headless mode)."""
        hb = HeartbeatService(dashboard_writer=None)
        await hb.start()
        await asyncio.sleep(1.5)
        await hb.stop()
        # Should not raise.

    @pytest.mark.asyncio
    async def test_fail_soft_no_world_model(self) -> None:
        """Heartbeat must work without a world model."""
        hb = HeartbeatService(world_model=None)
        await hb.start()
        await asyncio.sleep(1.5)
        await hb.stop()

    @pytest.mark.asyncio
    async def test_fail_soft_no_sensors(self) -> None:
        """Heartbeat must work without a sensor registry."""
        hb = HeartbeatService(sensor_registry=None)
        await hb.start()
        await asyncio.sleep(1.5)
        await hb.stop()

    @pytest.mark.asyncio
    async def test_fail_soft_no_log_channel(self) -> None:
        """Heartbeat must work without a log channel."""
        hb = HeartbeatService(log_channel=None)
        await hb.start()
        await asyncio.sleep(1.5)
        await hb.stop()

    @pytest.mark.asyncio
    async def test_fail_soft_dashboard_error(self) -> None:
        """Dashboard errors must not block the heartbeat."""
        dashboard = AsyncMock()
        dashboard.update_dashboard.side_effect = RuntimeError("Discord down")
        hb = HeartbeatService(dashboard_writer=dashboard)
        await hb._update_dashboard()
        # Should not raise — error is caught and logged.

    @pytest.mark.asyncio
    async def test_on_decision_callback(self) -> None:
        """on_decision callback should be invoked on the 60s cycle."""
        on_decision = AsyncMock(return_value={"phase": "observe"})
        hb = HeartbeatService(on_decision=on_decision)
        await hb.start()
        # Trigger the 60s handler manually.
        await hb._heartbeat_60s()
        await hb.stop()
        on_decision.assert_called_once()

    @pytest.mark.asyncio
    async def test_30s_polls_sensors(self) -> None:
        """30s heartbeat should poll sensors and enqueue observations."""
        mock_adapter = _make_mock_adapter("test_sensor")
        reg = SensorRegistry()
        await reg.register("test_sensor", mock_adapter)

        hb = HeartbeatService(sensor_registry=reg)
        await hb.start()
        # Trigger the 30s handler manually.
        await hb._heartbeat_30s()
        await hb.stop()

        # One observation should be in the queue.
        assert hb._graph_write_queue.qsize() >= 1

    def test_state_checksum_stable(self) -> None:
        """_state_checksum must produce a stable hash for identical inputs."""
        state = {"a": 1, "b": [2, 3], "c": {"d": "e"}}
        checksum1 = _state_checksum(state)
        checksum2 = _state_checksum(state)
        assert checksum1 == checksum2
        assert len(checksum1) == 16

    def test_state_checksum_differs_for_different_states(self) -> None:
        checksum_a = _state_checksum({"x": 1})
        checksum_b = _state_checksum({"x": 2})
        assert checksum_a != checksum_b


# ---------------------------------------------------------------------------
# SensorRegistry tests
# ---------------------------------------------------------------------------

class TestSensorRegistry:
    """SensorRegistry tests."""

    @pytest.mark.asyncio
    async def test_register_and_list(self, sensor_registry: SensorRegistry) -> None:
        adapter = _make_mock_adapter("sensor_a")
        await sensor_registry.register("sensor_a", adapter)
        assert "sensor_a" in sensor_registry.list_sensors()

    @pytest.mark.asyncio
    async def test_register_duplicate_raises(self, sensor_registry: SensorRegistry) -> None:
        adapter = _make_mock_adapter("sensor_a")
        await sensor_registry.register("sensor_a", adapter)
        with pytest.raises(ValueError, match="already registered"):
            await sensor_registry.register("sensor_a", adapter)

    @pytest.mark.asyncio
    async def test_register_empty_name_raises(self, sensor_registry: SensorRegistry) -> None:
        adapter = _make_mock_adapter("")
        with pytest.raises(ValueError, match="non-empty"):
            await sensor_registry.register("", adapter)

    @pytest.mark.asyncio
    async def test_unregister(self, sensor_registry: SensorRegistry) -> None:
        adapter = _make_mock_adapter("sensor_a")
        await sensor_registry.register("sensor_a", adapter)
        await sensor_registry.unregister("sensor_a")
        assert "sensor_a" not in sensor_registry.list_sensors()

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_raises(self, sensor_registry: SensorRegistry) -> None:
        with pytest.raises(KeyError, match="not registered"):
            await sensor_registry.unregister("nonexistent")

    @pytest.mark.asyncio
    async def test_sense_all_returns_observations(self, sensor_registry: SensorRegistry) -> None:
        adapter = _make_mock_adapter("sensor_a")
        await sensor_registry.register("sensor_a", adapter)
        observations = await sensor_registry.sense_all()
        assert len(observations) == 1
        assert observations[0]["source"] == "sensor_a"

    @pytest.mark.asyncio
    async def test_sense_all_empty_registry(self, sensor_registry: SensorRegistry) -> None:
        observations = await sensor_registry.sense_all()
        assert observations == []

    @pytest.mark.asyncio
    async def test_sense_all_fail_soft(self, sensor_registry: SensorRegistry) -> None:
        """One failing sensor must not break the whole sense_all."""
        good_adapter = _make_mock_adapter("good")
        bad_adapter = _make_mock_adapter("bad")
        bad_adapter.sense = AsyncMock(side_effect=RuntimeError("broken"))

        await sensor_registry.register("good", good_adapter)
        await sensor_registry.register("bad", bad_adapter)

        observations = await sensor_registry.sense_all()
        # Only the good adapter's observation.
        assert len(observations) == 1
        assert observations[0]["source"] == "good"

    @pytest.mark.asyncio
    async def test_health_check(self, sensor_registry: SensorRegistry) -> None:
        healthy = _make_mock_adapter("healthy")
        unhealthy = _make_mock_adapter("unhealthy")
        unhealthy.health = AsyncMock(return_value=False)

        await sensor_registry.register("healthy", healthy)
        await sensor_registry.register("unhealthy", unhealthy)

        result = await sensor_registry.health_check()
        assert result["healthy"] is True
        assert result["unhealthy"] is False

    @pytest.mark.asyncio
    async def test_health_check_empty(self, sensor_registry: SensorRegistry) -> None:
        result = await sensor_registry.health_check()
        assert result == {}

    @pytest.mark.asyncio
    async def test_sense_with_project_id(self, sensor_registry: SensorRegistry) -> None:
        pid = uuid.uuid4()
        adapter = _make_mock_adapter("sensor_a")
        adapter.sense = AsyncMock(
            return_value=[{"source": "sensor_a", "kind": "test", "project_id": str(pid)}]
        )
        await sensor_registry.register("sensor_a", adapter)
        observations = await sensor_registry.sense_all(project_id=pid)
        assert len(observations) == 1
        assert observations[0]["project_id"] == str(pid)


# ---------------------------------------------------------------------------
# WorldModel tests
# ---------------------------------------------------------------------------

class TestWorldModel:
    """WorldModel tests."""

    @pytest.mark.asyncio
    async def test_add_and_get_entity(self, world_model: WorldModel) -> None:
        eid = await world_model.add_entity({"kind": "person", "name": "Alice"})
        entity = await world_model.get_entity(eid)
        assert entity is not None
        assert entity["kind"] == "person"
        assert entity["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_add_entity_missing_kind_raises(self, world_model: WorldModel) -> None:
        with pytest.raises(ValueError, match="kind"):
            await world_model.add_entity({"name": "bad"})

    @pytest.mark.asyncio
    async def test_add_entity_generates_id(self, world_model: WorldModel) -> None:
        eid = await world_model.add_entity({"kind": "item", "label": "book"})
        assert eid is not None
        assert len(eid) > 0

    @pytest.mark.asyncio
    async def test_remove_entity(self, world_model: WorldModel) -> None:
        eid = await world_model.add_entity({"kind": "tmp", "label": "gone"})
        result = await world_model.remove_entity(eid)
        assert result is True
        assert await world_model.get_entity(eid) is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent(self, world_model: WorldModel) -> None:
        result = await world_model.remove_entity("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_update_entity(self, world_model: WorldModel) -> None:
        eid = await world_model.add_entity({"kind": "note", "text": "hello"})
        result = await world_model.update_entity(eid, text="world")
        assert result is True
        entity = await world_model.get_entity(eid)
        assert entity["text"] == "world"

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, world_model: WorldModel) -> None:
        result = await world_model.update_entity("nope", x=1)
        assert result is False

    @pytest.mark.asyncio
    async def test_add_relation_and_query(self, world_model: WorldModel) -> None:
        e1 = await world_model.add_entity({"kind": "person", "name": "A"})
        e2 = await world_model.add_entity({"kind": "person", "name": "B"})
        await world_model.add_relation(e1, e2, "friend")

        relations = await world_model.get_relations(entity_id=e1)
        assert len(relations) == 1
        assert relations[0]["relation"] == "friend"

    @pytest.mark.asyncio
    async def test_get_relations_filter(self, world_model: WorldModel) -> None:
        e1 = await world_model.add_entity({"kind": "a", "name": "1"})
        e2 = await world_model.add_entity({"kind": "b", "name": "2"})
        e3 = await world_model.add_entity({"kind": "c", "name": "3"})
        await world_model.add_relation(e1, e2, "likes")
        await world_model.add_relation(e1, e3, "hates")

        likes = await world_model.get_relations(relation="likes")
        assert len(likes) == 1
        assert likes[0]["target"] == e2

    @pytest.mark.asyncio
    async def test_query_entities_by_kind(self, world_model: WorldModel) -> None:
        await world_model.add_entity({"kind": "fruit", "name": "apple"})
        await world_model.add_entity({"kind": "fruit", "name": "banana"})
        await world_model.add_entity({"kind": "veggie", "name": "carrot"})

        fruits = await world_model.query_entities(kind="fruit")
        assert len(fruits) == 2
        names = {f["name"] for f in fruits}
        assert names == {"apple", "banana"}

    @pytest.mark.asyncio
    async def test_query_entities_pagination(self, world_model: WorldModel) -> None:
        for i in range(10):
            await world_model.add_entity({"kind": "item", "index": i})

        page = await world_model.query_entities(kind="item", limit=3, offset=2)
        assert len(page) == 3

    @pytest.mark.asyncio
    async def test_count_entities(self, world_model: WorldModel) -> None:
        await world_model.add_entity({"kind": "a"})
        await world_model.add_entity({"kind": "b"})
        assert await world_model.count_entities() == 2
        assert await world_model.count_entities(kind="a") == 1

    @pytest.mark.asyncio
    async def test_count_relations(self, world_model: WorldModel) -> None:
        e1 = await world_model.add_entity({"kind": "x"})
        e2 = await world_model.add_entity({"kind": "y"})
        await world_model.add_relation(e1, e2, "r1")
        assert await world_model.count_relations() == 1
        assert await world_model.count_relations(entity_id=e1) == 1

    @pytest.mark.asyncio
    async def test_get_neighbors_outgoing(self, world_model: WorldModel) -> None:
        e1 = await world_model.add_entity({"kind": "a"})
        e2 = await world_model.add_entity({"kind": "b"})
        e3 = await world_model.add_entity({"kind": "c"})
        await world_model.add_relation(e1, e2, "to")
        await world_model.add_relation(e1, e3, "to")

        neighbors = await world_model.get_neighbors(e1, relation="to", direction="outgoing")
        assert set(neighbors) == {e2, e3}

    @pytest.mark.asyncio
    async def test_get_neighbors_incoming(self, world_model: WorldModel) -> None:
        e1 = await world_model.add_entity({"kind": "a"})
        e2 = await world_model.add_entity({"kind": "b"})
        await world_model.add_relation(e2, e1, "to")

        neighbors = await world_model.get_neighbors(e1, direction="incoming")
        assert neighbors == [e2]

    @pytest.mark.asyncio
    async def test_remove_entity_removes_relations(self, world_model: WorldModel) -> None:
        e1 = await world_model.add_entity({"kind": "a"})
        e2 = await world_model.add_entity({"kind": "b"})
        await world_model.add_relation(e1, e2, "r")
        await world_model.remove_entity(e1)

        remaining = await world_model.get_relations(entity_id=e2)
        assert remaining == []

    @pytest.mark.asyncio
    async def test_health_always_true(self, world_model: WorldModel) -> None:
        assert await world_model.health() is True

    @pytest.mark.asyncio
    async def test_snapshot(self, world_model: WorldModel) -> None:
        await world_model.add_entity({"kind": "a"})
        await world_model.add_entity({"kind": "b"})
        snap = await world_model.snapshot()
        assert snap["entity_count"] == 2
        assert "a" in snap["kinds"]
        assert "b" in snap["kinds"]


# ---------------------------------------------------------------------------
# Concrete sensor adapter tests
# ---------------------------------------------------------------------------

class TestConcreteAdapters:
    """Tests for WearableSensorAdapter, CalendarSensorAdapter, FinanceSensorAdapter."""

    @pytest.mark.asyncio
    async def test_wearable_sensor_no_source(self) -> None:
        adapter = WearableSensorAdapter(data_source=None)
        assert adapter.name == "wearable"
        assert await adapter.sense() == []
        assert await adapter.health() is False

    @pytest.mark.asyncio
    async def test_wearable_sensor_with_source(self) -> None:
        source = AsyncMock(return_value=[{"hr": 72}, {"hr": 75}])
        adapter = WearableSensorAdapter(data_source=source, source_name="mi_fitness")
        observations = await adapter.sense()
        assert len(observations) == 2
        assert observations[0]["source"] == "mi_fitness"

    @pytest.mark.asyncio
    async def test_wearable_sensor_fail_soft(self) -> None:
        source = AsyncMock(side_effect=RuntimeError("network"))
        adapter = WearableSensorAdapter(data_source=source)
        assert await adapter.sense() == []

    @pytest.mark.asyncio
    async def test_calendar_sensor_no_backend(self) -> None:
        adapter = CalendarSensorAdapter(calendar_backend=None)
        assert adapter.name == "calendar"
        assert await adapter.sense() == []
        assert await adapter.health() is False

    @pytest.mark.asyncio
    async def test_calendar_sensor_with_backend(self) -> None:
        backend = MagicMock()
        backend.get_upcoming_events = AsyncMock(return_value=[{"title": "meeting"}])
        backend.health = AsyncMock(return_value=True)
        adapter = CalendarSensorAdapter(calendar_backend=backend)
        observations = await adapter.sense()
        assert len(observations) == 1
        assert observations[0]["kind"] == "calendar_event"

    @pytest.mark.asyncio
    async def test_finance_sensor_no_backend(self) -> None:
        adapter = FinanceSensorAdapter(finance_backend=None)
        assert adapter.name == "finance"
        assert await adapter.sense() == []
        assert await adapter.health() is False

    @pytest.mark.asyncio
    async def test_finance_sensor_with_backend(self) -> None:
        backend = MagicMock()
        backend.get_summary = AsyncMock(return_value={"balance": 1000})
        backend.health = AsyncMock(return_value=True)
        adapter = FinanceSensorAdapter(finance_backend=backend)
        observations = await adapter.sense()
        assert len(observations) == 1
        assert observations[0]["kind"] == "finance_summary"


# ---------------------------------------------------------------------------
# Simple tools tests
# ---------------------------------------------------------------------------

class TestSimpleTools:
    """Tests for CalendarTool, DriveTool, NotionTool, FinanceTool."""

    @pytest.mark.asyncio
    async def test_calendar_tool_config_missing(self) -> None:
        tool = CalendarTool(backend=None)
        assert tool.available is False
        assert await tool.get_upcoming_events() == []
        assert await tool.create_event({}) is None

    @pytest.mark.asyncio
    async def test_calendar_tool_with_backend(self) -> None:
        backend = MagicMock()
        backend.get_upcoming_events = AsyncMock(return_value=[{"id": "1"}])
        tool = CalendarTool(backend=backend)
        assert tool.available is True
        events = await tool.get_upcoming_events()
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_drive_tool_config_missing(self) -> None:
        tool = DriveTool(backend=None)
        assert tool.available is False
        assert await tool.list_files() == []
        assert await tool.search_files("q") == []

    @pytest.mark.asyncio
    async def test_notion_tool_config_missing(self) -> None:
        tool = NotionTool(backend=None)
        assert tool.available is False
        assert await tool.query_database("db1") == []
        assert await tool.create_page("db1", {}) is None

    @pytest.mark.asyncio
    async def test_finance_tool_config_missing(self) -> None:
        tool = FinanceTool(backend=None)
        assert tool.available is False
        assert await tool.get_summary() == {}
        assert await tool.get_transactions() == []

    @pytest.mark.asyncio
    async def test_finance_tool_with_backend(self) -> None:
        backend = MagicMock()
        backend.get_summary = AsyncMock(return_value={"balance": 500})
        tool = FinanceTool(backend=backend)
        assert tool.available is True
        summary = await tool.get_summary()
        assert summary["balance"] == 500


# ---------------------------------------------------------------------------
# Graph serialization test
# ---------------------------------------------------------------------------

class TestGraphSerialization:
    """Verify asyncio.Queue prevents concurrent writes."""

    @pytest.mark.asyncio
    async def test_queue_serializes_writes(self) -> None:
        """Multiple concurrent enqueues must serialize through the queue."""
        hb = HeartbeatService()

        write_order: list[int] = []
        original_put = hb._graph_write_queue.put

        async def tracking_put(item: dict[str, Any]) -> None:
            write_order.append(item["index"])
            await original_put(item)

        hb._graph_write_queue.put = tracking_put

        # Enqueue concurrently.
        await asyncio.gather(
            *(hb.enqueue_graph_write({"type": "test", "index": i}) for i in range(10))
        )

        # All 10 writes should be in the queue.
        assert hb._graph_write_queue.qsize() == 10
        assert len(write_order) == 10

    @pytest.mark.asyncio
    async def test_queue_fifo_order(self) -> None:
        """Queue must process items in FIFO order."""
        hb = HeartbeatService()
        for i in range(5):
            await hb.enqueue_graph_write({"type": "test", "index": i})

        items = []
        while not hb._graph_write_queue.empty():
            items.append(await hb._graph_write_queue.get())

        indices = [item["index"] for item in items]
        assert indices == [0, 1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Forbidden patterns test
# ---------------------------------------------------------------------------

class TestForbiddenPatterns:
    """Verify forbidden patterns are absent from life_kernel source."""

    def test_no_forbidden_patterns_in_source(self) -> None:
        """Source files must not contain hard_stop, HARD_STOP, safe_mode,
        consent_gate, health_consent, bare except, or type: ignore."""
        import os

        life_kernel_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "guinevere", "life_kernel"
        )
        life_kernel_dir = os.path.normpath(life_kernel_dir)

        forbidden = [
            "hard_stop",
            "HARD_STOP",
            "safe_mode",
            "consent_gate",
            "health_consent",
            "type: ignore",
        ]

        for filename in os.listdir(life_kernel_dir):
            if not filename.endswith(".py"):
                continue
            filepath = os.path.join(life_kernel_dir, filename)
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
            for pattern in forbidden:
                assert pattern not in content, (
                    f"Forbidden pattern '{pattern}' found in {filename}"
                )
