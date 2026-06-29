"""Sensor registry for the Life Kernel.

Manages daily-life sensor adapters and exposes a single async interface
for the heartbeat / observer loop to collect observations and check
adapter health.

Ported from src/life_kernel/sensors.py + sensor_adapters/ and
src/wearable/ (19 files — sensor adapter patterns; stale consent
imports cleaned by M2 paradigm shift).

P20 invariant: fail-soft — one misbehaving sensor never breaks the loop.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Protocol, runtime_checkable

import structlog

logger = structlog.get_logger(__name__)


# --- Sensor adapter protocol ------------------------------------------------

@runtime_checkable
class SensorAdapter(Protocol):
    """Minimal protocol expected from a registered sensor adapter."""

    @property
    def name(self) -> str:
        """Short sensor name used for logging and observation sources."""
        ...

    async def sense(self, project_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
        """Poll the sensor and return observation dicts."""
        ...

    async def health(self) -> bool:
        """Return ``True`` when the adapter is healthy."""
        ...


def _adapter_name(adapter: SensorAdapter) -> str:
    """Return an adapter's name, falling back to its class name."""
    try:
        return adapter.name
    except AttributeError:
        return adapter.__class__.__name__


# --- Sensor registry --------------------------------------------------------

class SensorRegistry:
    """Thread-safe registry for daily-life sensor adapters.

    All mutating operations are protected by an ``asyncio.Lock`` so the
    registry can be safely used from multiple concurrent heartbeat loops.

    Attributes:
        _adapters: Mapping of registered sensor names to adapter instances.
        _lock: Lock serializing register/unregister operations.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, SensorAdapter] = {}
        self._lock = asyncio.Lock()

    async def register(self, name: str, adapter: SensorAdapter) -> None:
        """Register a sensor adapter by name.

        Args:
            name: Unique sensor name used as the registry key.
            adapter: Object implementing the ``SensorAdapter`` protocol.

        Raises:
            ValueError: If ``name`` is empty or already registered.
            TypeError: If ``adapter`` does not satisfy the protocol.
        """
        if not name:
            raise ValueError("Sensor name must be non-empty")
        if not isinstance(adapter, SensorAdapter):
            raise TypeError(
                f"Adapter for '{name}' does not implement the sensor protocol"
            )

        async with self._lock:
            if name in self._adapters:
                raise ValueError(f"Sensor '{name}' is already registered")
            self._adapters[name] = adapter

        logger.info("sensor_registered", sensor=name)

    async def unregister(self, name: str) -> None:
        """Remove a previously registered sensor adapter.

        Raises:
            KeyError: If ``name`` is not registered.
        """
        async with self._lock:
            if name not in self._adapters:
                raise KeyError(f"Sensor '{name}' is not registered")
            del self._adapters[name]

        logger.info("sensor_unregistered", sensor=name)

    def list_sensors(self) -> list[str]:
        """Return a snapshot of registered sensor names."""
        return list(self._adapters.keys())

    async def sense_all(
        self, project_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        """Call ``sense()`` on every registered adapter and collect results.

        Individual adapter failures are logged and skipped so that one
        misbehaving sensor does not break the observer loop.

        Returns:
            Flattened list of observation dicts from all successful sensors.
        """
        async with self._lock:
            adapters = list(self._adapters.items())

        if not adapters:
            return []

        names, instances = zip(*adapters)

        results = await asyncio.gather(
            *(inst.sense(project_id=project_id) for inst in instances),
            return_exceptions=True,
        )

        observations: list[dict[str, Any]] = []
        for sensor_name, result in zip(names, results):
            if isinstance(result, BaseException):
                logger.error(
                    "sensor_sense_failed",
                    sensor=sensor_name,
                    error=str(result),
                )
                continue
            if not isinstance(result, list):
                logger.error(
                    "sensor_sense_invalid",
                    sensor=sensor_name,
                    result_type=type(result).__name__,
                )
                continue
            observations.extend(result)

        return observations

    async def health_check(self) -> dict[str, bool]:
        """Check the health of every registered adapter.

        Returns:
            Mapping of sensor name to ``True`` (healthy) or ``False``.
        """
        async with self._lock:
            adapters = list(self._adapters.items())

        if not adapters:
            return {}

        names, instances = zip(*adapters)

        results = await asyncio.gather(
            *(inst.health() for inst in instances),
            return_exceptions=True,
        )

        return {
            sensor_name: (result is True)
            for sensor_name, result in zip(names, results)
        }


# --- Concrete sensor adapters (ported from src/wearable/) --------------------
# These are thin sensor adapters that wrap wearable data sources.
# Stale consent imports have been CLEANED (W13 requirement).
# Consent checking is removed (M2 paradigm shift — no consent gate).


class WearableSensorAdapter:
    """Sensor adapter for wearable health data.

    Thin adapter that reads from a wearable data source and returns
    observations.  Consent checking removed (M2 paradigm shift).

    Args:
        data_source: Async callable returning raw health samples.
        source_name: Name of the wearable data source (e.g. "mi_fitness").
    """

    def __init__(
        self,
        data_source: Any | None = None,
        source_name: str = "wearable",
    ) -> None:
        self._data_source = data_source
        self._source_name = source_name

    @property
    def name(self) -> str:
        return self._source_name

    async def sense(
        self, project_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        """Poll the wearable data source for observations.

        Returns a list of observation dicts.  Returns an empty list
        when no data source is configured (fail-soft).
        """
        if self._data_source is None:
            return []

        try:
            raw = await self._data_source()
            if not isinstance(raw, list):
                return []

            observations: list[dict[str, Any]] = []
            for sample in raw:
                obs: dict[str, Any] = {
                    "source": self._source_name,
                    "kind": "wearable_health",
                    "data": sample,
                }
                if project_id is not None:
                    obs["project_id"] = str(project_id)
                observations.append(obs)
            return observations
        except Exception as exc:
            logger.error(
                "wearable_sensor_error",
                sensor=self._source_name,
                error_type=type(exc).__name__,
            )
            return []

    async def health(self) -> bool:
        """Return ``True`` if the data source is reachable."""
        if self._data_source is None:
            return False
        try:
            result = await self._data_source()
            return result is not None
        except Exception:
            return False


class CalendarSensorAdapter:
    """Sensor adapter for calendar events (desktop / M8)."""

    def __init__(self, calendar_backend: Any | None = None) -> None:
        self._backend = calendar_backend

    @property
    def name(self) -> str:
        return "calendar"

    async def sense(
        self, project_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        if self._backend is None:
            return []
        try:
            events = await self._backend.get_upcoming_events()
            return [
                {"source": "calendar", "kind": "calendar_event", "data": ev}
                for ev in (events or [])
            ]
        except Exception as exc:
            logger.error("calendar_sensor_error", error_type=type(exc).__name__)
            return []

    async def health(self) -> bool:
        if self._backend is None:
            return False
        try:
            return bool(await self._backend.health())
        except Exception:
            return False


class FinanceSensorAdapter:
    """Sensor adapter for finance data (finance / M8)."""

    def __init__(self, finance_backend: Any | None = None) -> None:
        self._backend = finance_backend

    @property
    def name(self) -> str:
        return "finance"

    async def sense(
        self, project_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        if self._backend is None:
            return []
        try:
            data = await self._backend.get_summary()
            return [{"source": "finance", "kind": "finance_summary", "data": data}]
        except Exception as exc:
            logger.error("finance_sensor_error", error_type=type(exc).__name__)
            return []

    async def health(self) -> bool:
        if self._backend is None:
            return False
        try:
            return bool(await self._backend.health())
        except Exception:
            return False
