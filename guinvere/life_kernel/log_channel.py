"""Log channel abstraction for the Living Autonomy Kernel.

The kernel writes meaningful *lifecycle* events (heartbeat milestones,
observe/decide/act/reflect summaries, self-directed task creation,
HARD STOP transitions) to an append-only Discord channel via the real
Discord REST API (:class:`DiscordRestClient`).

Design:
  - :class:`LogChannel` is the abstract interface every writer implements.
  - :class:`DiscordLogChannel` posts to a real Discord channel via REST. It is
    **fail-soft**: on any Discord error it logs a warning via structlog and
    returns, so a Discord outage never blocks the heartbeat.
  - :class:`StructlogLogChannel` is the no-network fallback used in tests and
    when Discord is not configured; it preserves the previous placeholder
    behavior so existing tests pass without a live token.

No secrets are ever logged. The channel id is a public snowflake and may be
logged; the bot token lives only inside :class:`DiscordRestClient`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import structlog

if TYPE_CHECKING:
    from guinvere.life_kernel.discord_rest_client import DiscordRestClient

logger = structlog.get_logger(__name__)


@runtime_checkable
class DiscordRestChannelLike(Protocol):
    """Structural protocol for anything that can POST to a Discord channel.

    Lets :class:`DiscordLogChannel` accept either the real
    :class:`DiscordRestClient` or a test double without a hard import cycle.
    """

    enabled: bool

    async def send_message(
        self,
        channel_id: int | str,
        content: str | None = None,
        embed: dict[str, object] | None = None,
        embeds: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        ...


class LogChannel(ABC):
    """Abstract interface for writing kernel log messages to an output channel."""

    @abstractmethod
    async def write(self, message: str) -> None:
        """Write ``message`` to the channel (fail-soft: never raise)."""

    @abstractmethod
    async def flush(self) -> None:
        """Flush any buffered channel messages."""

    @abstractmethod
    async def close(self) -> None:
        """Close the channel and release resources."""


class StructlogLogChannel(LogChannel):
    """No-network log channel that emits via structlog.

    Used in unit tests and as the default when Discord is not configured, so
    the kernel can boot and be exercised without a live token.
    """

    def __init__(self, channel_id: str | int | None = None) -> None:
        self.channel_id = channel_id

    async def write(self, message: str) -> None:
        logger.info("log_channel_write", channel_id=self.channel_id, message=message)

    async def flush(self) -> None:
        """No-op — structlog has no buffer to flush."""

    async def close(self) -> None:
        """No-op."""


class DiscordLogChannel(LogChannel):
    """Append-only Discord log channel backed by :class:`DiscordRestClient`.

    Each :meth:`write` POSTs a new message to the configured channel. The log
    channel is *append-only by design*: we never edit or delete lifecycle
    events, so the channel reads as a chronological narrative of the kernel's
    autonomous behavior.

    P19 Multi-Project Context (P19-005c):
      When a ``project_id`` is provided, each message is prefixed with
      ``[project:slug] `` so that log readers can distinguish which project
      produced each event.  When ``None`` (legacy mode), no prefix is added.

    Fail-soft contract: if the REST client is disabled, or Discord returns an
    error, the message is still recorded via structlog (so it is not lost)
    and the method returns normally. The heartbeat must never block on the
    log channel.
    """

    def __init__(self, rest_client: DiscordRestChannelLike, channel_id: int | str, project_id: str | None = None) -> None:
        """Initialize the Discord log channel.

        Args:
            rest_client: A :class:`DiscordRestClient` (or compatible object
                with ``send_message`` and ``enabled``). May be a disabled
                client — calls then fail-soft to structlog.
            channel_id: Target Discord channel snowflake (the lifecycle log
                channel, e.g. ``#guinevere-logs``).
            project_id: Optional project namespace. When set, a ``[project:slug]``
                prefix is prepended to every message.
        """
        self._client = rest_client
        self._channel_id = channel_id
        self._project_id = project_id

    @property
    def channel_id(self) -> int | str:
        """The target Discord channel snowflake."""
        return self._channel_id

    @property
    def _project_prefix(self) -> str:
        """Return the ``[project:slug] `` prefix if project_id is set."""
        if self._project_id:
            return f"[project:{self._project_id}] "
        return ""

    async def write(self, message: str) -> None:
        """POST ``message`` to the log channel (fail-soft).

        On a disabled client or Discord error, falls back to structlog so the
        event is never silently dropped, and returns without raising.
        """
        prefixed = f"{self._project_prefix}{message}"
        if not getattr(self._client, "enabled", True):
            logger.info(
                "discord_log_channel_fallback_structlog",
                channel_id=self._channel_id,
                message=prefixed,
            )
            return
        try:
            await self._client.send_message(self._channel_id, content=prefixed)
        except Exception as exc:  # noqa: BLE001 — fail-soft, any Discord error
            logger.warning(
                "discord_log_channel_write_failed",
                channel_id=self._channel_id,
                error_type=type(exc).__name__,
                message=prefixed,
            )

    async def flush(self) -> None:
        """No-op — each write is an immediate POST."""

    async def close(self) -> None:
        """No-op — the shared REST client's lifecycle is owned by the core."""
