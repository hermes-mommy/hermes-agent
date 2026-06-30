"""VPS sensor adapter (placeholder) for the Living Autonomy Kernel."""

from __future__ import annotations

from guinvere.life_kernel.sensor_adapters.base import BaseSensorAdapter


class VPSSensorAdapter(BaseSensorAdapter):
    """Placeholder adapter for VPS metrics polling.

    In future milestones this may report CPU, memory, disk, and service
    status. Real calls require SSH or monitoring endpoint credentials; no
    external API is called in v1.
    """

    SENSOR_NAME = "vps"
    OBSERVATION_TYPE = "metric"
    DEFAULT_CONTENT = (
        "VPS metrics polling placeholder — CPU, memory, disk, and services "
        "are not fetched in v1 (requires SSH/monitoring credentials)."
    )
