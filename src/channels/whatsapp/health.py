from __future__ import annotations

"""P11-021 — Health probe for the WhatsApp service."""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import redis.asyncio as aioredis
import structlog

from .metrics import DEFAULT_DEVICE, set_connected, set_session_age
from .reconnection import (
    REDIS_CONNECTION_STATE_KEY,
    REDIS_RECONNECT_MANUAL_KEY,
)
from .structured_logging import log_health_check

logger = structlog.get_logger()

REDIS_SESSION_CREATED_AT_KEY = "guinevere:wa:session:created_at"
HEALTH_CHECK_INTERVAL_SECONDS = 60
HEARTBEAT_STALE_SECONDS = 120
SESSION_AGE_WARNING_SECONDS = 1_036_800


class HealthStatus(StrEnum):
    READY = "ready"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class HealthSnapshot:
    status: HealthStatus
    connection_state: str
    needs_manual: bool
    session_age_seconds: float
    last_check: datetime | None
    degraded_reason: str | None


class WhatsAppHealthProbe:
    def __init__(self, redis_client: aioredis.Redis, *, device: str = DEFAULT_DEVICE) -> None:
        self._redis = redis_client
        self._device = device
        self.status = HealthStatus.UNKNOWN
        self.connection_state = "unknown"
        self.needs_manual = False
        self.session_age_seconds = 0.0
        self.last_check: datetime | None = None
        self.degraded_reason: str | None = None
        self._last_heartbeat: datetime | None = None

    def mark_heartbeat(self) -> None:
        self._last_heartbeat = datetime.now(UTC)

    async def run(self) -> None:
        while True:
            try:
                await self.check_once()
            except Exception as exc:  # noqa: BLE001
                logger.exception("health_check_cycle_failed", error=str(exc))
                self.status = HealthStatus.DEGRADED
                self.connection_state = "unknown"
                self.needs_manual = True
                self.degraded_reason = "health_check_exception"
                set_connected(False, device=self._device)
                set_session_age(0.0, device=self._device)
            await asyncio.sleep(HEALTH_CHECK_INTERVAL_SECONDS)

    async def check_once(self) -> HealthSnapshot:
        self.last_check = datetime.now(UTC)
        self.mark_heartbeat()
        state_raw = await self._redis.get(REDIS_CONNECTION_STATE_KEY)
        needs_manual_raw = await self._redis.get(REDIS_RECONNECT_MANUAL_KEY)
        created_raw = await self._redis.get(REDIS_SESSION_CREATED_AT_KEY)

        self.connection_state = self._coerce_string(state_raw, default="unknown")
        self.needs_manual = self._coerce_string(needs_manual_raw, default="false").lower() == "true"
        self.session_age_seconds = self._compute_session_age(created_raw)

        connected = self.connection_state == "connected" and not self.needs_manual
        set_connected(connected, device=self._device)
        set_session_age(self.session_age_seconds, device=self._device)

        if connected:
            self.status = HealthStatus.READY
            self.degraded_reason = None
        elif self.needs_manual:
            self.status = HealthStatus.DEGRADED
            self.degraded_reason = "reconnect_exhausted"
        else:
            self.status = HealthStatus.DEGRADED
            self.degraded_reason = f"connection_state={self.connection_state}"

        log_health_check(
            connection_state=self.connection_state,
            session_age_s=self.session_age_seconds,
            needs_manual=self.needs_manual,
            status=self.status.value,
        )
        return self.snapshot()

    def snapshot(self) -> HealthSnapshot:
        return HealthSnapshot(
            status=self.status,
            connection_state=self.connection_state,
            needs_manual=self.needs_manual,
            session_age_seconds=self.session_age_seconds,
            last_check=self.last_check,
            degraded_reason=self.degraded_reason,
        )

    def get_probe_response(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "connection_state": self.connection_state,
            "needs_manual": self.needs_manual,
            "session_age_seconds": self.session_age_seconds,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "degraded_reason": self.degraded_reason,
            "heartbeat_stale": self.is_heartbeat_stale(),
        }

    def is_heartbeat_stale(self) -> bool:
        if self._last_heartbeat is None:
            return True
        return (datetime.now(UTC) - self._last_heartbeat).total_seconds() > HEARTBEAT_STALE_SECONDS

    def _compute_session_age(self, created_raw: Any) -> float:
        created_text = self._coerce_string(created_raw)
        if not created_text:
            return 0.0
        try:
            created_at = datetime.fromisoformat(created_text)
        except ValueError:
            logger.warning("whatsapp_health_invalid_created_at", value=created_text)
            return 0.0
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return max((self.last_check - created_at).total_seconds(), 0.0) if self.last_check else 0.0

    @staticmethod
    def _coerce_string(value: Any, *, default: str = "") -> str:
        if value is None:
            return default
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)
