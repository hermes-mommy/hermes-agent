"""Gateway patch — register Guinevere Discord adapter with Hermes gateway.

Provides a ``wire(agent)`` function that registers the GuinevereBot
as a Discord platform adapter via the gateway's platform_registry.

This is a parent-owned append pattern: the parent calls ``wire()``
from agent_init.py or a startup hook. We do NOT edit agent_init.py
directly.

Usage::

    from guinevere.discord.gateway_patch import wire
    wire(agent)

Or for standalone gateway registration without an agent::

    from guinevere.discord.gateway_patch import register_platform
    register_platform()
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

GUILD_ID: int = 1_510_876_414_671_323_206
PLATFORM_NAME: str = "discord"
PLATFORM_LABEL: str = "Discord"


def register_platform() -> bool:
    """Register the Guinevere Discord adapter with the gateway platform_registry.

    Returns True if registration succeeded, False if gateway components
    are unavailable.
    """
    try:
        from gateway.platform_registry import platform_registry, PlatformEntry
    except ImportError:
        logger.info("gateway_platform_registry_unavailable")
        return False

    def _check_requirements() -> bool:
        """Check if discord.py is available."""
        try:
            import discord
            return True
        except ImportError:
            return False

    def _create_adapter(config: Any) -> Any:
        """Create a GuinevereBot adapter for the gateway."""
        from guinevere.discord.bots import GuinevereBot

        bot = GuinevereBot()
        return bot

    def _validate_config(config: Any) -> bool:
        """Validate Discord platform config — requires DISCORD_BOT_TOKEN."""
        return bool(os.environ.get("DISCORD_BOT_TOKEN"))

    entry = PlatformEntry(
        name=PLATFORM_NAME,
        label=PLATFORM_LABEL,
        adapter_factory=_create_adapter,
        check_fn=_check_requirements,
        validate_config=_validate_config,
        required_env=["DISCORD_BOT_TOKEN"],
        install_hint="pip install discord.py",
        source="plugin",
        plugin_name="guinevere-discord",
        allowed_users_env="DISCORD_ALLOWED_USERS",
        allow_all_env="DISCORD_ALLOW_ALL_USERS",
        max_message_length=2000,
        emoji="\U0001f4ac",
    )

    platform_registry.register(entry)
    logger.info(
        "discord_platform_registered",
        extra={"name": PLATFORM_NAME, "label": PLATFORM_LABEL},
    )
    return True


def wire(agent: object) -> None:
    """Wire the Discord adapter into an agent's startup lifecycle.

    This function is called by the parent (agent_init.py or startup hook).
    It:
    1. Registers the platform with the gateway registry.
    2. Attaches the Discord bot identity to the agent.
    3. Starts the autonomous conversation initiator if enabled.

    Args:
        agent: The parent agent instance. Discord attributes are attached
               as agent._discord_bot and agent._discord_identity.
    """
    # Register with gateway platform_registry
    registered = register_platform()

    # Attach bot identity to agent
    from guinevere.discord.bots import BOT_IDENTITIES

    identity = BOT_IDENTITIES[0]  # Guinevere
    setattr(agent, "_discord_identity", identity)
    setattr(agent, "_discord_platform_registered", registered)

    logger.info(
        "discord_wire_complete",
        extra={
            "identity": identity.name,
            "platform_registered": registered,
            "guild_id": GUILD_ID,
        },
    )


def get_patch_info() -> dict[str, Any]:
    """Return information about the Discord gateway patch status."""
    try:
        from gateway.platform_registry import platform_registry
        entry = platform_registry.get(PLATFORM_NAME)
        registered = entry is not None
    except ImportError:
        registered = False

    token_set = bool(os.environ.get("DISCORD_BOT_TOKEN"))

    return {
        "platform_name": PLATFORM_NAME,
        "platform_registered": registered,
        "token_configured": token_set,
        "guild_id": GUILD_ID,
    }
