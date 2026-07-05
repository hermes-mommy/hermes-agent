"""GHI -> mood_engine modifier integration.

Translates Global Health Index scores into persona mood modifiers.
SAFETY BOUNDARY: Does NOT touch yandere_fsm.py. Only modifies mood_engine.py.

Safety gates (structured consent + HARD STOP aware):
- Structured consent: `check_wearable_consent("wearable-health.ghi")` MUST
  grant before any mood modifier is computed, stored, or applied.
- HARD STOP awareness: Redis key `persona:state:safe_mode` == "true" halts
  the integrator immediately and logs `mood_halted_safe_mode`.
- Default-deny: missing `persona:state:active` Redis key is treated as
  unsafe (deny) and logs `mood_persona_state_missing_default_deny`.

Features:
- Caring tone when recovery low (GHI <55)
- Energetic when healthy (GHI >=85)
- Neutral when insufficient data
- Redis persistence: wearable:ghi:current
- Health data invisible during argument/distress state
- Quiet hours: no mood changes between 22:00-08:00 unless SEV0
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import structlog
from redis.asyncio import Redis, from_url

from guinevere.persona.mood_engine import Mood
from guinevere.wearable.health_consent import check_wearable_consent
from guinevere.wearable.models import GHIResult, GHITier

logger = structlog.get_logger(__name__)

QUIET_HOURS_START = 22
QUIET_HOURS_END = 8
REDIS_CURRENT_KEY = "wearable:ghi:current"
REDIS_HISTORY_KEY = "wearable:ghi:history"
REDIS_PERSONA_STATE_KEY = "persona:state:active"
REDIS_PERSONA_SAFE_MODE_KEY = "persona:state:safe_mode"
WearableConsentScope = "wearable-health.ghi"
HISTORY_LIMIT = 30


class _RedisLike(Protocol):
    async def get(self, name: str) -> Any: ...

    async def set(self, name: str, value: Any, ex: int | None = None) -> Any: ...

    async def delete(self, *names: str) -> Any: ...

    async def lpush(self, name: str, *values: Any) -> Any: ...

    async def ltrim(self, name: str, start: int, end: int) -> Any: ...


@dataclass(slots=True)
class WearableMoodModifier:
    target_mood: Mood
    reason: str
    intensity: float
    expires_at: datetime
    source: str = "wearable_ghi"

    def to_json(self) -> str:
        payload = asdict(self)
        payload["target_mood"] = self.target_mood.value
        payload["expires_at"] = self.expires_at.isoformat()
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> WearableMoodModifier:
        data = json.loads(raw)
        return cls(
            target_mood=Mood(data["target_mood"]),
            reason=str(data["reason"]),
            intensity=float(data["intensity"]),
            expires_at=datetime.fromisoformat(str(data["expires_at"])),
            source=str(data.get("source", "wearable_ghi")),
        )


class HealthMoodIntegrator:
    def __init__(self, redis_url: str, database_url: str) -> None:
        self._redis_url = redis_url
        self._database_url = database_url
        self._redis: Redis = from_url(redis_url, decode_responses=True)

    @staticmethod
    def _is_quiet_hours(now: datetime) -> bool:
        hour = now.hour
        return hour >= QUIET_HOURS_START or hour < QUIET_HOURS_END

    async def is_safe_to_apply(self) -> bool:
        safe_mode = await self._redis.get(REDIS_PERSONA_SAFE_MODE_KEY)
        if safe_mode is not None and str(safe_mode).strip().lower() == "true":
            logger.warning("mood_halted_safe_mode")
            return False

        consent = await check_wearable_consent(WearableConsentScope)
        if not consent.allowed:
            return False

        state = await self._redis.get(REDIS_PERSONA_STATE_KEY)
        if not state:
            logger.warning("mood_persona_state_missing_default_deny")
            return False
        state_normalized = str(state).strip().lower()
        return state_normalized not in {"argument", "distress"}

    async def compute_modifier(self, ghi: GHIResult) -> WearableMoodModifier | None:
        if ghi.suppressed:
            return None
        if not await self.is_safe_to_apply():
            return None

        now = datetime.now(UTC)
        if self._is_quiet_hours(now) and ghi.tier is not GHITier.CRITICAL:
            return None

        target_mood, intensity, reason = self._map_tier_to_mood(ghi)
        if target_mood is None:
            return None

        return WearableMoodModifier(
            target_mood=target_mood,
            reason=reason,
            intensity=intensity,
            expires_at=now + timedelta(hours=24),
        )

    async def apply_modifier(self, modifier: WearableMoodModifier) -> None:
        consent = await check_wearable_consent(WearableConsentScope)
        if not consent.allowed:
            logger.info("mood_consent_blocked", scope=WearableConsentScope)
            return None

        await self._redis.set(REDIS_CURRENT_KEY, modifier.to_json(), ex=24 * 60 * 60)
        await self._redis.lpush(REDIS_HISTORY_KEY, modifier.to_json())
        await self._redis.ltrim(REDIS_HISTORY_KEY, 0, HISTORY_LIMIT - 1)
        logger.info(
            "wearable_mood_modifier_applied",
            target_mood=modifier.target_mood.value,
            intensity=modifier.intensity,
            expires_at=modifier.expires_at.isoformat(),
            source=modifier.source,
        )

    async def get_active_modifier(self) -> WearableMoodModifier | None:
        raw = await self._redis.get(REDIS_CURRENT_KEY)
        if not raw:
            return None
        modifier = WearableMoodModifier.from_json(str(raw))
        if modifier.expires_at <= datetime.now(UTC):
            await self.clear_modifier()
            return None
        return modifier

    async def clear_modifier(self) -> None:
        await self._redis.delete(REDIS_CURRENT_KEY)

    def _map_tier_to_mood(self, ghi: GHIResult) -> tuple[Mood | None, float, str]:
        if ghi.tier is GHITier.EXCELLENT or ghi.ghi_score >= 85:
            return Mood.PLEASED, 0.7, "Healthy recovery trend; energetic caring tone"
        if ghi.tier is GHITier.GOOD or ghi.ghi_score >= 70:
            return Mood.CONTENT, 0.5, "Good recovery trend; steady supportive tone"
        if ghi.tier is GHITier.FAIR or ghi.ghi_score >= 55:
            return Mood.CONTENT, 0.3, "Fair recovery trend; gentle supportive tone"
        if ghi.tier is GHITier.POOR or ghi.ghi_score >= 40:
            return Mood.DISAPPOINTED, 0.4, "Low recovery trend; caring concern tone"
        if ghi.tier is GHITier.CRITICAL or ghi.ghi_score < 40:
            return Mood.DISAPPOINTED, 0.6, "Critical recovery trend; concerned tone"
        return None, 0.0, "Insufficient data"


__all__ = ["WearableMoodModifier", "HealthMoodIntegrator", "QUIET_HOURS_START", "QUIET_HOURS_END"]
