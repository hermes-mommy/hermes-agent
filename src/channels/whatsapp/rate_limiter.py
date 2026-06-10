from __future__ import annotations

"""P11-014 — WhatsApp dedup, rate limiting, and anti-ban posture."""

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import random
import time

import redis.asyncio as aioredis
import structlog

from .auth import build_whatsapp_redis_client
from .envelope import WhatsAppMessageEnvelope, normalize_jid
from .metrics import DEFAULT_DEVICE, WHATSAPP_RATE_LIMIT_HITS_TOTAL

logger = structlog.get_logger()

DEDUP_TTL_SECONDS = 120
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "minute": (8, 60),
    "hour": (30, 3600),
    "day": (200, 86400),
}


@dataclass(frozen=True, slots=True)
class DedupDecision:
    allowed: bool
    reason: str
    key: str


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    reason: str
    retry_after_seconds: float | None = None


class WhatsAppRateLimiter:
    def __init__(self, redis_client: aioredis.Redis | None = None) -> None:
        self._redis: aioredis.Redis = redis_client or build_whatsapp_redis_client()

    def build_dedup_key(self, envelope: WhatsAppMessageEnvelope) -> str:
        payload = "|".join(
            [
                envelope.normalized_sender_phone(),
                envelope.body.strip().lower(),
                (envelope.media_type or "").lower(),
            ]
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"guinevere:whatsapp:dedup:{digest}"

    async def check_inbound_dedup(self, envelope: WhatsAppMessageEnvelope) -> DedupDecision:
        key = self.build_dedup_key(envelope)
        try:
            created = await self._redis.set(key, envelope.message_id, ex=DEDUP_TTL_SECONDS, nx=True)
        except Exception as exc:  # noqa: BLE001
            logger.error("whatsapp_dedup_failed_closed", error=str(exc))
            return DedupDecision(False, "redis_failure", key)
        if not created:
            return DedupDecision(False, "duplicate", key)
        return DedupDecision(True, "fresh", key)

    async def reserve_outbound_slot(self, target_jid: str) -> RateLimitDecision:
        subject = normalize_jid(target_jid)
        now = time.time()
        for window, (limit, ttl) in RATE_LIMITS.items():
            key = f"guinevere:whatsapp:ratelimit:{subject}:{window}"
            cutoff = now - ttl
            try:
                _ = await self._redis.zremrangebyscore(key, "-inf", cutoff)
                count = int(await self._redis.zcard(key))
            except Exception as exc:  # noqa: BLE001
                logger.error("whatsapp_rate_limit_failed_closed", window=window, error=str(exc))
                WHATSAPP_RATE_LIMIT_HITS_TOTAL.labels(device=DEFAULT_DEVICE, window=window).inc()
                return RateLimitDecision(False, "redis_failure")

            if count >= limit:
                retry_after = await self._retry_after_seconds(key, cutoff, ttl)
                WHATSAPP_RATE_LIMIT_HITS_TOTAL.labels(device=DEFAULT_DEVICE, window=window).inc()
                return RateLimitDecision(False, f"rate_limited_{window}", retry_after)

        member = f"{int(now * 1000)}:{random.random():.9f}"
        for window, (_limit, ttl) in RATE_LIMITS.items():
            key = f"guinevere:whatsapp:ratelimit:{subject}:{window}"
            try:
                _ = await self._redis.zadd(key, {member: now})
                _ = await self._redis.expire(key, ttl)
            except Exception as exc:  # noqa: BLE001
                logger.error("whatsapp_rate_limit_reserve_failed", window=window, error=str(exc))
                WHATSAPP_RATE_LIMIT_HITS_TOTAL.labels(device=DEFAULT_DEVICE, window=window).inc()
                return RateLimitDecision(False, "redis_failure")
        return RateLimitDecision(True, "allowed")

    def anti_ban_jitter_seconds(self) -> float:
        return max(0.5, min(2.0, random.gauss(0.0, 0.5)))

    async def _retry_after_seconds(self, key: str, cutoff: float, ttl: int) -> float:
        oldest = await self._redis.zrangebyscore(key, cutoff, "+inf", start=0, num=1, withscores=True)
        if not oldest:
            return float(ttl)
        _member, score = oldest[0]
        return max(0.0, ttl - (time.time() - float(score)))

    def snapshot_timestamp(self) -> str:
        return datetime.now(UTC).isoformat()
