"""Discord sensor adapter (placeholder) for the Living Autonomy Kernel."""

from __future__ import annotations

from guinvere.life_kernel.sensor_adapters.base import BaseSensorAdapter


class DiscordSensorAdapter(BaseSensorAdapter):
    """Placeholder adapter for Discord API polling.

    In future milestones this may poll messages, mentions, and server status.
    Real calls are gated behind bot token configuration and explicit Discord
    intents; no external API is called in v1.
    """

    SENSOR_NAME = "discord"
    OBSERVATION_TYPE = "message"
    DEFAULT_CONTENT = (
        "Discord API polling placeholder — messages, mentions, and server "
        "status are not fetched in v1 (real calls gated by bot token/intent)."
    )
