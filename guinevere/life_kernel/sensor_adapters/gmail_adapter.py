"""Gmail sensor adapter (placeholder) for the Living Autonomy Kernel."""

from __future__ import annotations

from guinevere.life_kernel.sensor_adapters.base import BaseSensorAdapter


class GmailSensorAdapter(BaseSensorAdapter):
    """Placeholder adapter for Gmail inbox polling.

    In future milestones this may report unread count and important emails.
    Real calls require OAuth consent and Gmail API credentials; no external
    API is called in v1.
    """

    SENSOR_NAME = "gmail"
    OBSERVATION_TYPE = "email"
    DEFAULT_CONTENT = (
        "Gmail inbox polling placeholder — unread count and important emails "
        "are not fetched in v1 (real calls require OAuth/Gmail API)."
    )
