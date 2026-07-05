"""Browser sensor adapter (placeholder) for the Living Autonomy Kernel."""

from __future__ import annotations

from guinevere.life_kernel.sensor_adapters.base import BaseSensorAdapter


class BrowserSensorAdapter(BaseSensorAdapter):
    """Placeholder adapter for browser interaction data.

    In future milestones this may summarize active browser sessions or
    interaction signals. Real calls require a browser automation bridge; no
    external API is called in v1.
    """

    SENSOR_NAME = "browser"
    OBSERVATION_TYPE = "web"
    DEFAULT_CONTENT = (
        "Browser interaction data placeholder — no browser automation "
        "bridge is active in v1."
    )
