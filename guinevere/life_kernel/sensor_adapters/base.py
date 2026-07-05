"""Base sensor adapter for the Living Autonomy Kernel.

All daily-life sensor adapters inherit from :class:`BaseSensorAdapter`.  The
base class defines the minimal contract expected by :class:`SensorRegistry`
while keeping every real integration as a safe placeholder.
"""

from __future__ import annotations

import uuid
from abc import ABC
from datetime import datetime
from typing import Any

import structlog


class BaseSensorAdapter(ABC):
    """Abstract base class for LK daily-life sensor adapters.

    Subclasses declare a sensor name, default observation type, and a default
    placeholder content string.  The public API is intentionally tiny:

    * :meth:`sense` — poll the sensor and return observation dicts.
    * :meth:`health` — return whether the (placeholder) adapter is healthy.

    Attributes:
        SENSOR_NAME: Short sensor identifier used in observation sources
            (e.g. ``"discord"`` produces ``"sensor:discord"``).
        OBSERVATION_TYPE: Default value for the ``type`` field of an
            observation.
        DEFAULT_CONTENT: Human-readable placeholder text explaining that real
            API calls are intentionally not performed.
    """

    SENSOR_NAME: str = "base"
    OBSERVATION_TYPE: str = "generic"
    DEFAULT_CONTENT: str = "Placeholder observation."

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the adapter with optional configuration.

        Args:
            config: Optional configuration dictionary.  Real credentials or
                API tokens are never stored in this dict; they are expected
                to be injected via environment or secret stores in future
                milestones.
        """
        self.config = config or {}
        self._healthy = True
        self._logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return self.SENSOR_NAME

    async def sense(
        self, project_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        """Poll the sensor and return a list of observation dicts.

        Args:
            project_id: Optional project UUID to tag the observation with.
                When ``None`` (legacy), the observation has no project scope.

        Returns:
            A list containing a single placeholder observation dict matching
            the sensor observation schema.
        """
        self._logger.info("sensor.poll", sensor=self.name, status="ok")
        observation: dict[str, Any] = {
            "source": f"sensor:{self.name}",
            "type": self.OBSERVATION_TYPE,
            "content": self.DEFAULT_CONTENT,
            "timestamp": datetime.now().isoformat(),
            "additional": {},
        }
        if project_id is not None:
            observation["project_id"] = str(project_id)
        return [observation]

    async def health(self) -> bool:
        """Return True if the adapter is healthy.

        Returns:
            ``True`` by default.  Subclasses may override to reflect real
            connectivity checks in future milestones.
        """
        self._logger.debug("sensor.health", sensor=self.name, healthy=self._healthy)
        return self._healthy
