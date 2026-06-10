from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.channels.whatsapp.health import (
    REDIS_SESSION_CREATED_AT_KEY,
    HealthStatus,
    WhatsAppHealthProbe,
)
from src.channels.whatsapp.reconnection import (
    REDIS_CONNECTION_STATE_KEY,
    REDIS_RECONNECT_MANUAL_KEY,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str):
        return self.values.get(key)


@pytest.mark.asyncio
async def test_health_probe_ready_and_degraded() -> None:
    redis = FakeRedis()
    probe = WhatsAppHealthProbe(redis)

    redis.values[REDIS_CONNECTION_STATE_KEY] = "connected"
    redis.values[REDIS_RECONNECT_MANUAL_KEY] = "false"
    redis.values[REDIS_SESSION_CREATED_AT_KEY] = (datetime.now(UTC) - timedelta(seconds=30)).isoformat()

    snapshot = await probe.check_once()
    assert snapshot.status == HealthStatus.READY
    assert snapshot.session_age_seconds >= 0

    redis.values[REDIS_RECONNECT_MANUAL_KEY] = "true"
    snapshot = await probe.check_once()
    assert snapshot.status == HealthStatus.DEGRADED
    assert snapshot.degraded_reason == "reconnect_exhausted"
