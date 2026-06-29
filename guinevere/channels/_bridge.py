"""M3 Consciousness bridge — wires each channel to Guinevere's autonomous sending.

Each channel adapter exposes a ``send`` method. This bridge provides a
unified interface for the consciousness layer (M3) to send outbound
messages on any registered channel without knowing channel-specific APIs.

The ``wire(agent)`` function is called by the parent-owned agent_init
append — do NOT edit agent_init.py directly.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

import structlog

logger = structlog.get_logger(__name__)


class SendPriority(str, Enum):
    """Priority tiers for autonomous outbound sends."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass(frozen=True, slots=True)
class OutboundMessage:
    """Canonical outbound message DTO for consciousness-initiated sends."""

    channel: str
    target: str
    body: str
    priority: SendPriority = SendPriority.NORMAL
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SendResult:
    """Result of an outbound send attempt."""

    success: bool
    channel: str
    target: str
    message_id: str | None = None
    error: str | None = None


class ChannelSender(Protocol):
    """Protocol for channel adapters that support outbound sending."""

    @property
    def channel_id(self) -> str:
        """Canonical channel identifier."""
        ...

    @property
    def is_config_missing(self) -> bool:
        """True when required credentials are not provisioned."""
        ...

    async def send_message(
        self,
        target: str,
        body: str,
        **kwargs: Any,
    ) -> SendResult:
        """Send a message to *target* on this channel."""
        ...


class ConsciousnessBridge:
    """Unified bridge from M3 consciousness to all channel senders.

    Maintains a registry of channel senders and dispatches outbound
    messages based on channel ID.  All sends are logged via structlog.
    """

    def __init__(self) -> None:
        self._senders: dict[str, ChannelSender] = {}

    def register(self, sender: ChannelSender) -> None:
        """Register a channel sender."""
        self._senders[sender.channel_id] = sender
        logger.info(
            "consciousness_bridge_registered",
            channel=sender.channel_id,
            config_missing=sender.is_config_missing,
        )

    @property
    def available_channels(self) -> list[str]:
        """Return channel IDs with non-missing config."""
        return [
            cid
            for cid, sender in self._senders.items()
            if not sender.is_config_missing
        ]

    @property
    def all_channels(self) -> list[str]:
        """Return all registered channel IDs (including config-missing)."""
        return list(self._senders.keys())

    def get_sender(self, channel: str) -> ChannelSender | None:
        """Return the sender for *channel*, or None."""
        return self._senders.get(channel)

    async def send(self, message: OutboundMessage) -> SendResult:
        """Dispatch an outbound message to the appropriate channel sender.

        Returns a SendResult. If the channel is not registered or has
        CONFIG_MISSING status, returns a failure result (does not raise).
        """
        sender = self._senders.get(message.channel)
        if sender is None:
            logger.warning(
                "consciousness_bridge_channel_not_found",
                channel=message.channel,
                target=message.target,
            )
            return SendResult(
                success=False,
                channel=message.channel,
                target=message.target,
                error=f"Channel '{message.channel}' not registered",
            )

        if sender.is_config_missing:
            logger.info(
                "consciousness_bridge_config_missing",
                channel=message.channel,
                target=message.target,
            )
            return SendResult(
                success=False,
                channel=message.channel,
                target=message.target,
                error=f"Channel '{message.channel}' has CONFIG_MISSING credentials",
            )

        try:
            result = await sender.send_message(
                target=message.target,
                body=message.body,
                priority=message.priority.value,
                **message.metadata,
            )
            logger.info(
                "consciousness_bridge_sent",
                channel=message.channel,
                target=message.target,
                success=result.success,
            )
            return result
        except Exception as exc:
            logger.error(
                "consciousness_bridge_send_failed",
                channel=message.channel,
                target=message.target,
                error=str(exc),
            )
            return SendResult(
                success=False,
                channel=message.channel,
                target=message.target,
                error=str(exc),
            )

    async def broadcast(
        self,
        body: str,
        *,
        channels: list[str] | None = None,
        targets: dict[str, str] | None = None,
        priority: SendPriority = SendPriority.NORMAL,
    ) -> list[SendResult]:
        """Send the same message to multiple channels.

        Args:
            body: Message text.
            channels: Channel IDs to broadcast to (None = all available).
            targets: {channel_id: target} mapping. Required if channels is None.
            priority: Send priority.
        """
        if channels is None and targets is not None:
            channels = list(targets.keys())
        if channels is None:
            channels = self.available_channels

        results: list[SendResult] = []
        for cid in channels:
            target = (targets or {}).get(cid, "")
            if not target:
                results.append(
                    SendResult(
                        success=False,
                        channel=cid,
                        target="",
                        error=f"No target specified for channel '{cid}'",
                    )
                )
                continue
            msg = OutboundMessage(
                channel=cid,
                target=target,
                body=body,
                priority=priority,
            )
            results.append(await self.send(msg))
        return results


# ---- Module-level singleton bridge ----

_bridge: ConsciousnessBridge | None = None


def get_bridge() -> ConsciousnessBridge:
    """Return the module-level singleton ConsciousnessBridge."""
    global _bridge  # noqa: PLW0603
    if _bridge is None:
        _bridge = ConsciousnessBridge()
    return _bridge


def wire(agent: Any) -> None:
    """Wire channel senders into the consciousness bridge.

    Called by the parent-owned agent_init append.  This function:
    1. Imports all channel adapters (triggers CONFIG_MISSING detection).
    2. Registers each adapter's sender into the bridge.
    3. Stores the bridge on the agent for M3 access.

    Do NOT edit agent_init.py — the parent owns that file.
    """
    bridge = get_bridge()

    # Import channel adapters (triggers lazy registration).
    try:
        from . import gmail, telegram, whatsapp, x  # noqa: F401
    except ImportError as exc:
        logger.warning("consciousness_bridge_import_error", error=str(exc))

    # Build senders from registered channel classes.
    from . import get_channel_class, list_channels, ChannelId

    for cid in list_channels():
        cls = get_channel_class(cid)
        if cls is None:
            continue
        try:
            instance = cls()
            if hasattr(instance, "send_message") and hasattr(instance, "channel_id"):
                bridge.register(instance)
        except Exception as exc:
            logger.warning(
                "consciousness_bridge_sender_init_failed",
                channel=cid.value,
                error=str(exc),
            )

    # Attach bridge to agent for M3 access.
    if hasattr(agent, "__dict__"):
        agent.__dict__["_channel_bridge"] = bridge  # noqa: SLF001
    logger.info(
        "consciousness_bridge_wired",
        channels=bridge.all_channels,
        available=bridge.available_channels,
    )
