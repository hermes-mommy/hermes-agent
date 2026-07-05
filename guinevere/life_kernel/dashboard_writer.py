"""Dashboard writer for the Living Autonomy Kernel.

Owns the *single* dashboard message in the configured Discord status channel.
On each heartbeat cycle it renders the current :class:`LifeMindState` as a
Discord embed and **edits** the existing message in place (PATCH), rather
than posting a new one (POST). This satisfies the "edit-not-spam" hard
requirement: one dashboard message, updated in place, never duplicated.

Message-id persistence:
  The dashboard message id is stored in Redis under
  ``life_kernel:dashboard_message_id`` (no TTL — it survives restarts).
  On startup, if the key is absent the writer *recovers* by listing recent
  messages in the channel and finding the most recent bot-authored message
  whose embed title matches the dashboard; if none exists it POSTs a new one
  and stores the id.

P19 Multi-Project Context (P19-005c):
  When ``feature:projects:enabled`` is ON and a ``project_id`` was provided at
  construction, the Redis key becomes
  ``life_kernel:dashboard_message_id:{project_id}``, providing per-project
  dashboard message isolation.  When the flag is OFF (or no ``project_id`` is
  set), the legacy global key ``life_kernel:dashboard_message_id`` is used
  unchanged — the P20 contract is preserved.

Fail-soft:
  Every Discord call is wrapped in try/except. On any failure the writer logs
  a warning and returns; the heartbeat never blocks on the dashboard. If the
  stored message id becomes invalid (message deleted), the next edit fails,
  the writer detects the "not found" condition, and re-creates the message.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from guinevere.life_kernel.dashboard import DashboardRenderer
from guinevere.life_kernel.state import LifeMindState

if TYPE_CHECKING:
    import redis.asyncio as aioredis  # noqa: F401

    from guinevere.life_kernel.discord_rest_client import DiscordRestClient

logger = structlog.get_logger(__name__)

_DASHBOARD_MESSAGE_ID_KEY = "life_kernel:dashboard_message_id"
_FEATURE_FLAG_KEY = "feature:projects:enabled"


def _dashboard_message_id_key(project_id: str | None = None) -> str:
    """Return the Redis key for the dashboard message id.

    When ``project_id`` is provided AND the feature flag is active, scopes
    the key to the project.  Otherwise returns the legacy global key.
    """
    if project_id:
        return f"{_DASHBOARD_MESSAGE_ID_KEY}:{project_id}"
    return _DASHBOARD_MESSAGE_ID_KEY
_DASHBOARD_EMBED_TITLE = "Guinevere — Living Autonomy Dashboard"
# Discord error code 10008: "Unknown Message" — the stored id was deleted.
# Also matches the HTTP 404 path when the message is gone.
# All hints MUST be strings: ``hint in text`` requires a str left operand,
# and an int here raises ``'in <string>' requires string as left operand``.
_NOT_FOUND_HINTS = ("10008", "Unknown Message")


class DashboardWriter:
    """Manages the single edited dashboard message with Redis persistence.

    Args:
        rest_client: A :class:`DiscordRestClient` (may be disabled → no-ops).
        renderer: A :class:`DashboardRenderer` instance.
        redis_client: Redis client for message-id persistence.
        channel_id: The dashboard (status) channel snowflake.
        project_id: Optional project namespace. When set, the Redis key becomes
            ``life_kernel:dashboard_message_id:{project_id}`` (feature-flagged).
    """

    def __init__(
        self,
        rest_client: DiscordRestClient,
        renderer: DashboardRenderer,
        redis_client: Any,
        channel_id: int | str,
        project_id: str | None = None,
    ) -> None:
        self._client = rest_client
        self._renderer = renderer
        self._redis = redis_client
        self._channel_id = channel_id
        self._project_id = project_id
        # Last checksum we published, so we skip a Discord round-trip entirely
        # when the state has not changed since the last successful publish.
        self._last_published_checksum: str | None = None

    @property
    def _message_id_key(self) -> str:
        """Redis key for the dashboard message id, project-scoped."""
        return _dashboard_message_id_key(self._project_id)

    @property
    def channel_id(self) -> int | str:
        """The target dashboard channel snowflake."""
        return self._channel_id

    async def _get_message_id(self) -> int | str | None:
        """Read the stored dashboard message id from Redis (or None)."""
        try:
            raw = await self._redis.get(self._message_id_key)
            if raw is None:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode()
            return str(raw)
        except Exception as exc:  # noqa: BLE001 — fail-soft
            logger.warning("dashboard_message_id_read_failed", error_type=type(exc).__name__)
            return None

    async def _set_message_id(self, message_id: int | str) -> None:
        """Persist the dashboard message id to Redis."""
        try:
            await self._redis.set(self._message_id_key, str(message_id))
        except Exception as exc:  # noqa: BLE001 — fail-soft
            logger.warning("dashboard_message_id_write_failed", error_type=type(exc).__name__)

    async def _recover_message_id(self) -> int | str | None:
        """Find an existing bot-authored dashboard message in the channel.

        Lists the most recent messages and returns the id of the newest one
        authored by the bot whose embed title matches the dashboard title.
        Used at startup (no stored id) so we resume editing instead of duping.
        """
        try:
            messages = await self._client.get_recent_messages(self._channel_id, limit=20)
        except Exception as exc:  # noqa: BLE001 — fail-soft
            logger.warning("dashboard_recover_list_failed", error_type=type(exc).__name__)
            return None
        for msg in messages:
            author = msg.get("author", {}) or {}
            if not author.get("bot"):
                continue
            for embed in msg.get("embeds", []) or []:
                if embed.get("title") == _DASHBOARD_EMBED_TITLE:
                    return str(msg.get("id"))
        return None

    @staticmethod
    def _is_not_found(exc: Exception) -> bool:
        """True if ``exc`` indicates the stored message id no longer exists."""
        text = str(exc)
        return any(hint in text for hint in _NOT_FOUND_HINTS)

    async def update_dashboard(self, state: LifeMindState) -> None:
        """Render ``state`` and edit the dashboard message (edit-not-spam).

        - Skips the Discord round-trip entirely if the state checksum is
          unchanged since the last successful publish.
        - If a message id is stored, PATCH it (edit in place).
        - If no id is stored, recover one; if recovery fails, POST a new
          message and store its id.
        - If a PATCH fails with "unknown message", re-create and re-store.

        Fail-soft: never raises; logs on failure.
        """
        if not getattr(self._client, "enabled", True):
            return

        checksum = self._renderer._state_checksum(state)  # noqa: SLF001 — reuse the renderer's stable checksum
        if checksum == self._last_published_checksum:
            # State unchanged since last successful publish — skip entirely.
            return

        embed = self._renderer.render_embed(state)

        message_id = await self._get_message_id()
        if message_id is None:
            message_id = await self._recover_message_id()
            if message_id is not None:
                await self._set_message_id(message_id)

        if message_id is not None:
            try:
                await self._client.edit_message(
                    self._channel_id, message_id, embed=embed
                )
                self._last_published_checksum = checksum
                logger.debug("dashboard_edited", message_id=message_id)
                return
            except Exception as exc:  # noqa: BLE001 — fail-soft
                if self._is_not_found(exc):
                    logger.info("dashboard_message_gone_recreating")
                else:
                    logger.warning(
                        "dashboard_edit_failed",
                        error_type=type(exc).__name__,
                        error_message=str(exc)[:400],
                    )
                    return

        # No valid stored id (or it was deleted): create a new dashboard message.
        try:
            result = await self._client.send_message(self._channel_id, embed=embed)
            new_id = result.get("id")
            if new_id:
                await self._set_message_id(new_id)
                self._last_published_checksum = checksum
                logger.info("dashboard_created", message_id=new_id)
        except Exception as exc:  # noqa: BLE001 — fail-soft
            logger.warning("dashboard_create_failed", error_type=type(exc).__name__)

    async def publish_hard_stop(self, state: LifeMindState) -> None:
        """Force-publish a HARD STOP dashboard update immediately.

        Called from the 1s safety heartbeat when a live HARD STOP is detected,
        *before* the heartbeat stops itself, so the dashboard visibly reflects
        the halt. Bypasses the checksum-skip so the hard-stop state always
        reaches Discord. Fail-soft: never raises.
        """
        if not getattr(self._client, "enabled", True):
            return
        embed = self._renderer.render_embed(state)
        message_id = await self._get_message_id()
        if message_id is None:
            message_id = await self._recover_message_id()
            if message_id is not None:
                await self._set_message_id(message_id)
        if message_id is not None:
            try:
                await self._client.edit_message(self._channel_id, message_id, embed=embed)
                self._last_published_checksum = self._renderer._state_checksum(state)  # noqa: SLF001
                logger.warning("dashboard_hard_stop_published", message_id=message_id)
                return
            except Exception as exc:  # noqa: BLE001 — fail-soft
                if not self._is_not_found(exc):
                    logger.warning("dashboard_hard_stop_edit_failed", error_type=type(exc).__name__)
                    return
        try:
            result = await self._client.send_message(self._channel_id, embed=embed)
            new_id = result.get("id")
            if new_id:
                await self._set_message_id(new_id)
                self._last_published_checksum = self._renderer._state_checksum(state)  # noqa: SLF001
                logger.warning("dashboard_hard_stop_created", message_id=new_id)
        except Exception as exc:  # noqa: BLE001 — fail-soft
            logger.warning("dashboard_hard_stop_create_failed", error_type=type(exc).__name__)
