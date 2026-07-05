"""Wearable sensor adapter (placeholder) for the Living Autonomy Kernel."""

from __future__ import annotations

from guinevere.life_kernel.sensor_adapters.base import BaseSensorAdapter


class WearableSensorAdapter(BaseSensorAdapter):
    """Placeholder adapter for wearable health data.

    In future milestones this may poll heart rate, steps, and sleep data.
    Real calls require operator consent and a paired wearable service; no
    external API is called in v1.
    """

    SENSOR_NAME = "wearable"
    OBSERVATION_TYPE = "health"
    DEFAULT_CONTENT = (
        "Wearable health data polling placeholder — heart rate, steps, and "
        "sleep are not fetched in v1 (requires paired wearable service)."
    )
