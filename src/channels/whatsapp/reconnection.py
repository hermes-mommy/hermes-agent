from __future__ import annotations

"""Reconnect / recovery state machine for WhatsApp transport.

Wave 1 owner for P11-003 + P11-020 reconnect semantics.
"""

import asyncio
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Awaitable, Callable

import redis.asyncio as aioredis
import structlog
logger = structlog.get_logger()

from .metrics import (
    DEFAULT_DEVICE,
    WHATSAPP_CONNECTED,
    WHATSAPP_MESSAGES_RECEIVED_TOTAL,
    WHATSAPP_MESSAGES_SENT_TOTAL,
    WHATSAPP_RATE_LIMIT_HITS_TOTAL,
    WHATSAPP_RECONNECT_ATTEMPTS_TOTAL,
    WHATSAPP_RESPONSE_LATENCY_SECONDS,
    WHATSAPP_SESSION_AGE_SECONDS,
)

REDIS_CONNECTION_STATE_KEY = "guinevere:wa:connection:state"
REDIS_RECONNECT_MANUAL_KEY = "guinevere:wa:reconnect:needs_manual"
REDIS_RECONNECT_ATTEMPTS_KEY = "guinevere:wa:reconnect:attempts"
REDIS_RECONNECT_LAST_ERROR_KEY = "guinevere:wa:reconnect:last_error"
REDIS_RECONNECT_LAST_ATTEMPT_KEY = "guinevere:wa:reconnect:last_attempt"


class ConnectionState(StrEnum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class DisconnectReason(StrEnum):
    NETWORK_TIMEOUT = "network_timeout"
    NEONIZE_INTERNAL = "neonize_internal"
    SESSION_EXPIRED = "session_expired"
    PROTOCOL_VERSION_MISMATCH = "protocol_version_mismatch"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ReconnectStateSnapshot:
    state: ConnectionState
    reason: DisconnectReason | None
    attempts: int
    needs_manual_reconnect: bool
    last_error: str | None
    last_attempt_ts: float | None


class ReconnectionHandler:
    def __init__(
        self,
        *,
        redis_client: aioredis.Redis | None = None,
        reconnect_callback: Callable[[], Awaitable[bool]] | None = None,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
        max_attempts: int = 3,
        backoff_schedule: tuple[int, ...] = (30, 60, 120),
    ) -> None:
        self._redis = redis_client
        self._reconnect_callback = reconnect_callback
        self._sleeper = sleeper
        self._max_attempts = max_attempts
        self._backoff_schedule = backoff_schedule
        self._state = ConnectionState.DISCONNECTED
        self._reason: DisconnectReason | None = None
        self._attempts = 0
        self._needs_manual_reconnect = False
        self._last_error: str | None = None
        self._last_attempt_ts: float | None = None
        WHATSAPP_CONNECTED.labels(device=DEFAULT_DEVICE).set(0)

    @property
    def state(self) -> ConnectionState:
        return self._state

    def get_state_snapshot(self) -> ReconnectStateSnapshot:
        return ReconnectStateSnapshot(
            state=self._state,
            reason=self._reason,
            attempts=self._attempts,
            needs_manual_reconnect=self._needs_manual_reconnect,
            last_error=self._last_error,
            last_attempt_ts=self._last_attempt_ts,
        )

    async def on_connected(self) -> None:
        self._state = ConnectionState.CONNECTED
        self._reason = None
        self._attempts = 0
        self._needs_manual_reconnect = False
        self._last_error = None
        self._last_attempt_ts = time.time()
        WHATSAPP_CONNECTED.labels(device=DEFAULT_DEVICE).set(1)
        await self._persist_state()
        logger.info("whatsapp_transport_connected")

    async def on_disconnected(self, reason_text: str | None = None) -> None:
        self._state = ConnectionState.DISCONNECTED
        self._last_error = reason_text
        self._reason = self.categorize_disconnect(reason_text)
        WHATSAPP_CONNECTED.labels(device=DEFAULT_DEVICE).set(0)
        await self._persist_state()
        logger.warning(
            "whatsapp_transport_disconnected",
            reason=self._reason.value,
            detail=reason_text,
        )
        await self._recover_or_fail()

    async def mark_session_age(self, paired_at_ts: float | None) -> None:
        if paired_at_ts is None:
            WHATSAPP_SESSION_AGE_SECONDS.labels(device=DEFAULT_DEVICE).set(0)
            return
        WHATSAPP_SESSION_AGE_SECONDS.labels(device=DEFAULT_DEVICE).set(max(time.time() - paired_at_ts, 0.0))

    def record_received(self, direction: str = "inbound") -> None:
        WHATSAPP_MESSAGES_RECEIVED_TOTAL.labels(device=DEFAULT_DEVICE).inc()

    def record_sent(self, direction: str = "outbound") -> None:
        WHATSAPP_MESSAGES_SENT_TOTAL.labels(device=DEFAULT_DEVICE).inc()

    def observe_response_latency(self, seconds: float) -> None:
        WHATSAPP_RESPONSE_LATENCY_SECONDS.labels(device=DEFAULT_DEVICE).observe(seconds)

    def observe_rate_limit_hit(self) -> None:
        WHATSAPP_RATE_LIMIT_HITS_TOTAL.labels(device=DEFAULT_DEVICE, window="transport").inc()

    def categorize_disconnect(self, reason_text: str | None) -> DisconnectReason:
        detail = (reason_text or "").lower()
        if any(token in detail for token in ["timed out", "timeout", "connection reset", "refused", "keepalive"]):
            return DisconnectReason.NETWORK_TIMEOUT
        if any(token in detail for token in ["logged out", "session expired", "pair required", "401"]):
            return DisconnectReason.SESSION_EXPIRED
        if any(token in detail for token in ["outdated", "deprecated version", "protocol mismatch", "client outdated"]):
            return DisconnectReason.PROTOCOL_VERSION_MISMATCH
        if any(token in detail for token in ["internal", "decrypt", "stream error", "panic"]):
            return DisconnectReason.NEONIZE_INTERNAL
        return DisconnectReason.UNKNOWN

    async def _recover_or_fail(self) -> None:
        if self._reason in {
            DisconnectReason.SESSION_EXPIRED,
            DisconnectReason.PROTOCOL_VERSION_MISMATCH,
        }:
            await self._mark_failed()
            return

        if self._reconnect_callback is None:
            await self._mark_failed()
            return

        for delay in self._backoff_schedule[: self._max_attempts]:
            self._attempts += 1
            self._state = ConnectionState.RECONNECTING
            self._last_attempt_ts = time.time()
            WHATSAPP_RECONNECT_ATTEMPTS_TOTAL.labels(
                device=DEFAULT_DEVICE,
                reason=self._reason.value if self._reason else DisconnectReason.UNKNOWN.value,
            ).inc()
            await self._persist_state()
            logger.info(
                "whatsapp_reconnect_attempt",
                attempt=self._attempts,
                delay_seconds=delay,
                reason=self._reason.value if self._reason else None,
            )
            await self._sleeper(delay)
            try:
                if await self._reconnect_callback():
                    await self.on_connected()
                    return
            except Exception as exc:  # noqa: BLE001
                self._last_error = str(exc)
                logger.warning(
                    "whatsapp_reconnect_attempt_failed",
                    attempt=self._attempts,
                    error=str(exc),
                )

        await self._mark_failed()

    async def _mark_failed(self) -> None:
        self._state = ConnectionState.FAILED
        self._needs_manual_reconnect = True
        WHATSAPP_CONNECTED.set(0)
        await self._persist_state()
        logger.error(
            "whatsapp_reconnect_exhausted",
            reason=self._reason.value if self._reason else None,
            attempts=self._attempts,
            last_error=self._last_error,
        )

    async def _persist_state(self) -> None:
        if self._redis is None:
            return
        mapping = {
            REDIS_CONNECTION_STATE_KEY: self._state.value,
            REDIS_RECONNECT_MANUAL_KEY: "true" if self._needs_manual_reconnect else "false",
            REDIS_RECONNECT_ATTEMPTS_KEY: str(self._attempts),
            REDIS_RECONNECT_LAST_ERROR_KEY: self._last_error or "",
            REDIS_RECONNECT_LAST_ATTEMPT_KEY: "" if self._last_attempt_ts is None else str(self._last_attempt_ts),
        }
        await self._redis.mset(mapping)
