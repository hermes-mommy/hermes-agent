from __future__ import annotations

"""P11-011 — Typing / presence wrapper."""

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

import structlog
from neonize.proto import Neonize_pb2 as pb

from .envelope import normalize_jid, to_jid
from .neonize_client import NeonizeClient

logger = structlog.get_logger()

_COMPOSING = getattr(pb, "_CHATPRESENCE_CHATPRESENCE").values_by_name["COMPOSING"].number
_PAUSED = getattr(pb, "_CHATPRESENCE_CHATPRESENCE").values_by_name["PAUSED"].number
_TEXT_MEDIA = getattr(pb, "_CHATPRESENCE_CHATPRESENCEMEDIA").values_by_name["TEXT"].number


@dataclass(slots=True)
class _TypingState:
    task: asyncio.Task[None] | None = None
    active: bool = False


class TypingIndicator:
    """WhatsApp typing indicator wrapper.

    Owns only presence lifecycle. Router decides when to call it.
    """

    def __init__(
        self,
        client: NeonizeClient,
        *,
        watchdog_seconds: float = 25.0,
        sleeper: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ) -> None:
        self._client = client
        self._watchdog_seconds = watchdog_seconds
        self._sleeper = sleeper
        self._states: dict[str, _TypingState] = {}

    async def start_typing(self, jid: str) -> None:
        normalized = self._normalize_private_jid(jid)
        if normalized is None:
            return
        state = self._states.setdefault(normalized, _TypingState())
        if state.active:
            return
        state.active = True
        await self._emit_presence(normalized, composing=True)
        state.task = asyncio.create_task(self._watchdog_clear(normalized))

    async def stop_typing(self, jid: str) -> None:
        normalized = self._normalize_private_jid(jid)
        if normalized is None:
            return
        state = self._states.get(normalized)
        if state is None or not state.active:
            return
        state.active = False
        if state.task is not None:
            state.task.cancel()
            with suppress(asyncio.CancelledError):
                await state.task
        state.task = None
        await self._emit_presence(normalized, composing=False)

    async def force_clear_all(self) -> None:
        for jid in list(self._states):
            await self.stop_typing(jid)

    async def _watchdog_clear(self, jid: str) -> None:
        try:
            await self._sleeper(self._watchdog_seconds)
        except asyncio.CancelledError:
            raise
        await self.stop_typing(jid)

    async def _emit_presence(self, jid: str, *, composing: bool) -> None:
        proto = self._jid_proto(jid)
        state = _COMPOSING if composing else _PAUSED
        try:
            await self._client.send_chat_presence(proto, state, _TEXT_MEDIA)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "whatsapp_typing_presence_failed",
                jid=jid,
                composing=composing,
                error=str(exc),
            )

    def _normalize_private_jid(self, jid: str) -> str | None:
        candidate = to_jid(jid)
        if candidate.endswith("@g.us"):
            return None
        return normalize_jid(candidate)

    def _jid_proto(self, jid: str) -> Any:
        return pb.JID(User=normalize_jid(jid), Server="s.whatsapp.net")
