from __future__ import annotations

"""P11-016 — WhatsApp consent + channel access policy.

This gate runs after whitelist and HARD STOP. It owns only WhatsApp consent
state and channel-access decisions. It does not own identity binding, HARD
STOP, persona behavior, or routing.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog

from .auth import build_whatsapp_redis_client
from .envelope import WhatsAppMessageEnvelope

logger = structlog.get_logger()

REDIS_CONSENT_KEY = "guinevere:whatsapp:consent"
CONSENT_CHANNEL = "whatsapp"
CONSENT_GRANTED_BY = "Faiz"


@dataclass(frozen=True, slots=True)
class ConsentState:
    granted: bool
    timestamp: str | None
    channel: str
    granted_by: str | None
    revoked_at: str | None

    @classmethod
    def default(cls) -> "ConsentState":
        return cls(
            granted=False,
            timestamp=None,
            channel=CONSENT_CHANNEL,
            granted_by=None,
            revoked_at=None,
        )


@dataclass(frozen=True, slots=True)
class ConsentDecision:
    allowed: bool
    envelope: WhatsAppMessageEnvelope | None
    response: str | None
    reason: str
    state: ConsentState


class WhatsAppConsentManager:
    def __init__(self, redis_client: aioredis.Redis | None = None, *, redis_key: str = REDIS_CONSENT_KEY) -> None:
        self._redis: aioredis.Redis = redis_client or build_whatsapp_redis_client()
        self._redis_key: str = redis_key

    async def load_state(self) -> ConsentState:
        mapping = await self._redis.hgetall(self._redis_key)
        if not mapping:
            return ConsentState.default()
        normalized = {str(key): str(value) for key, value in mapping.items()}
        return ConsentState(
            granted=normalized.get("granted", "false").lower() == "true",
            timestamp=normalized.get("timestamp") or None,
            channel=normalized.get("channel") or CONSENT_CHANNEL,
            granted_by=normalized.get("granted_by") or None,
            revoked_at=normalized.get("revoked_at") or None,
        )

    async def grant(self, *, granted_by: str = CONSENT_GRANTED_BY) -> ConsentState:
        now = datetime.now(UTC).isoformat()
        mapping = {
            "granted": "true",
            "timestamp": now,
            "channel": CONSENT_CHANNEL,
            "granted_by": granted_by,
            "revoked_at": "",
        }
        _ = await self._redis.delete(self._redis_key)
        for field_name, field_value in mapping.items():
            _ = await self._redis.hset(self._redis_key, field_name, field_value)
        state = ConsentState(True, now, CONSENT_CHANNEL, granted_by, None)
        logger.info("whatsapp_consent_granted", granted_by=granted_by)
        return state

    async def revoke(self) -> ConsentState:
        now = datetime.now(UTC).isoformat()
        previous = await self.load_state()
        mapping = {
            "granted": "false",
            "timestamp": previous.timestamp or "",
            "channel": CONSENT_CHANNEL,
            "granted_by": previous.granted_by or "",
            "revoked_at": now,
        }
        _ = await self._redis.delete(self._redis_key)
        for field_name, field_value in mapping.items():
            _ = await self._redis.hset(self._redis_key, field_name, field_value)
        state = ConsentState(False, previous.timestamp, CONSENT_CHANNEL, previous.granted_by, now)
        logger.info("whatsapp_consent_revoked")
        return state

    async def evaluate(self, envelope: WhatsAppMessageEnvelope) -> ConsentDecision:
        try:
            state = await self.load_state()
        except Exception as exc:  # noqa: BLE001
            logger.error("whatsapp_consent_failed_closed", error=str(exc))
            fallback = ConsentState.default()
            return ConsentDecision(
                allowed=False,
                envelope=None,
                response=self._consent_required_response(),
                reason="redis_failure",
                state=fallback,
            )

        if state.granted:
            return ConsentDecision(
                allowed=True,
                envelope=envelope,
                response=None,
                reason="granted",
                state=state,
            )

        return ConsentDecision(
            allowed=False,
            envelope=None,
            response=self._consent_required_response(),
            reason="not_granted",
            state=state,
        )

    def _consent_required_response(self) -> str:
        return (
            "WhatsApp access is not enabled yet. Consent is required before I can continue on this channel. "
            "Please ask Faiz to grant WhatsApp consent first."
        )
