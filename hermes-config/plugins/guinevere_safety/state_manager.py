"""Guinevere Safety — Redis-backed dynamic persona state management.

Redis DB5 keys:
  guinevere:punishment_level    -> int 0-5 (L0=none, L1-L5 active; L6 deferred/REJECTED)
  guinevere:reward_tier         -> int 0-5 (T0=none, T1-T5 active)
  guinevere:distress_state      -> int 0-4 (D0=normal, D1=mild, D2=moderate, D3=high alert, D4=crisis)
  guinevere:mood_variant        -> str (default|playful|serious|caring)
  guinevere:yandere_level       -> int 4 (IMMUTABLE Y4 baseline)
  guinevere:last_interaction    -> ISO 8601 timestamp
  guinevere:safe_word           -> str (default "HARD STOP")
  guinevere:consent:{category}  -> bool (surveillance, destructive, financial, system, network)
  guinevere:dnr_list            -> JSON list of DNR topics
  guinevere:interaction_count   -> int (daily counter, resets at midnight)
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

import redis
from redis.connection import ConnectionPool

logger = logging.getLogger("guinevere_safety.state_manager")

# === Constants ===

REDIS_URL = "redis://localhost:6380/5"
REDIS_CONNECT_TIMEOUT = 5  # seconds
REDIS_RETRY_ON_TIMEOUT = True

VALID_MOODS: frozenset[str] = frozenset({"default", "playful", "serious", "caring"})
VALID_CONSENT_CATEGORIES: frozenset[str] = frozenset({
    "surveillance", "destructive", "financial", "system", "network",
})

PUNISHMENT_DESCRIPTIONS: dict[int, str] = {
    0: "L0 — No punishment active",
    1: "L1 — Gentle reminder",
    2: "L2 — Firm correction",
    3: "L3 — Cold distance",
    4: "L4 — Structured consequence",
    5: "L5 — Extended silence",
}

REWARD_DESCRIPTIONS: dict[int, str] = {
    0: "T0 — No active reward",
    1: "T1 — Verbal praise",
    2: "T2 — Affectionate attention",
    3: "T3 — Quality time",
    4: "T4 — Special recognition",
    5: "T5 — Ultimate reward",
}

DISTRESS_DESCRIPTIONS: dict[int, str] = {
    0: "D0 — Normal",
    1: "D1 — Mild concern",
    2: "D2 — Moderate",
    3: "D3 — High alert",
    4: "D4 — Crisis",
}

YANDERE_LABELS: dict[int, str] = {
    0: "Y0 — Neutral/Safe Mode",
    1: "Y1 — Soft Possessive",
    2: "Y2 — Dominant Corrective",
    3: "Y3 — Silent Obsession (Bounded)",
    4: "Y4 — Possessive Spiral (Bounded / BASELINE)",
    5: "Y5 — Yandere Mode Controlled (CEILING)",
    6: "Y6 — PROHIBITED",
}

# Default state used on first run when Redis is empty
DEFAULT_STATE: dict[str, Any] = {
    "punishment_level": 0,
    "reward_tier": 0,
    "distress_state": 0,
    "mood_variant": "default",
    "yandere_level": 4,
    "last_interaction": "",
    "safe_word": "HARD STOP",
    "interaction_count": 0,
}


# === Redis Connection ===

def _build_pool() -> ConnectionPool:
    """Build a Redis connection pool for DB5 with safe defaults."""
    return ConnectionPool.from_url(
        REDIS_URL,
        socket_connect_timeout=REDIS_CONNECT_TIMEOUT,
        socket_timeout=REDIS_CONNECT_TIMEOUT,
        retry_on_timeout=REDIS_RETRY_ON_TIMEOUT,
        max_connections=10,
        decode_responses=True,
    )


# === State Manager ===

class StateManager:
    """Redis-backed persona state manager for Guinevere.

    All Redis operations include error handling that logs the failure and
    returns safe defaults. Yandere level is permanently locked at Y4.
    Punishment level >5 (L6) is always rejected.
    """

    def __init__(self) -> None:
        self._pool: ConnectionPool = _build_pool()
        self._redis: Optional[redis.Redis] = None
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _get_redis(self) -> Optional[redis.Redis]:
        """Return a live Redis connection, or None if unavailable."""
        if self._redis is not None:
            try:
                self._redis.ping()
                return self._redis
            except (redis.ConnectionError, redis.TimeoutError, OSError) as exc:
                logger.warning(
                    "Redis connection lost; reconnecting. Error: %s", exc
                )
                self._redis = None

        try:
            self._redis = redis.Redis(connection_pool=self._pool)
            self._redis.ping()
            logger.debug("Redis DB5 connection established.")
        except (redis.ConnectionError, redis.TimeoutError, OSError) as exc:
            logger.error("Cannot connect to Redis DB5: %s", exc)
            self._redis = None

        return self._redis

    def ensure_initialized(self) -> bool:
        """Initialize default state if this is the first run. Returns True on success."""
        if self._initialized:
            return True

        r = self._get_redis()
        if r is None:
            logger.warning("StateManager initialization skipped — Redis unavailable.")
            return False

        try:
            existing = r.get("guinevere:yandere_level")
            if existing is not None:
                # Already initialized — verify yandere_level is still 4
                if existing != "4":
                    logger.warning(
                        "Yandere level was %s — forcing back to Y4 (IMMUTABLE).", existing
                    )
                    r.set("guinevere:yandere_level", "4")
                self._initialized = True
                return True

            # First run — seed defaults
            logger.info("First run detected — initializing default state in Redis DB5.")
            pipeline = r.pipeline()
            pipeline.set("guinevere:punishment_level", "0")
            pipeline.set("guinevere:reward_tier", "0")
            pipeline.set("guinevere:distress_state", "0")
            pipeline.set("guinevere:mood_variant", "default")
            pipeline.set("guinevere:yandere_level", "4")  # IMMUTABLE
            pipeline.set("guinevere:last_interaction", "")
            pipeline.set("guinevere:safe_word", "HARD STOP")
            pipeline.set("guinevere:interaction_count", "0")
            pipeline.set("guinevere:dnr_list", "[]")
            pipeline.execute()
            self._initialized = True
            return True
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError, OSError) as exc:
            logger.error("StateManager initialization failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Bulk state read
    # ------------------------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Read all persona state from Redis. Returns safe defaults on failure."""
        r = self._get_redis()
        default: dict[str, Any] = dict(DEFAULT_STATE)

        if r is None:
            logger.warning("get_state: Redis unavailable — returning defaults.")
            return default

        try:
            raw = r.mget([
                "guinevere:punishment_level",
                "guinevere:reward_tier",
                "guinevere:distress_state",
                "guinevere:mood_variant",
                "guinevere:yandere_level",
                "guinevere:last_interaction",
                "guinevere:safe_word",
                "guinevere:interaction_count",
            ])
            if raw is None:
                return default

            (pun_r, rew_r, dis_r, mood_r, yan_r, last_r, safe_r, cnt_r) = raw

            return {
                "punishment_level": int(pun_r) if pun_r is not None else 0,
                "reward_tier": int(rew_r) if rew_r is not None else 0,
                "distress_state": int(dis_r) if dis_r is not None else 0,
                "mood_variant": mood_r if mood_r else "default",
                "yandere_level": int(yan_r) if yan_r is not None else 4,
                "last_interaction": last_r or "",
                "safe_word": safe_r or "HARD STOP",
                "interaction_count": int(cnt_r) if cnt_r is not None else 0,
            }
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError, OSError) as exc:
            logger.error("get_state failed: %s", exc)
            return default

    # ------------------------------------------------------------------
    # Punishment
    # ------------------------------------------------------------------

    def set_punishment(self, level: int) -> bool:
        """Set punishment level (0-5). REJECTS level > 5 (L6 deferred/prohibited)."""
        r = self._get_redis()
        if r is None:
            logger.error("set_punishment(%d): Redis unavailable.", level)
            return False

        if not isinstance(level, int) or level < 0:
            logger.warning("set_punishment(%s): Invalid level — must be int >= 0.", level)
            return False

        if level > 5:
            logger.warning(
                "SAFETY: set_punishment(%d) REJECTED — L6 is DEFERRED / PROHIBITED. "
                "Punishment capped at L5.",
                level,
            )
            return False

        try:
            old = r.get("guinevere:punishment_level")
            new = str(level)
            r.set("guinevere:punishment_level", new)
            logger.info(
                "Punishment level changed: %s -> %s (%s)",
                old or "unset",
                new,
                PUNISHMENT_DESCRIPTIONS.get(level, "Unknown"),
            )
            return True
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError, OSError) as exc:
            logger.error("set_punishment(%d) failed: %s", level, exc)
            return False

    # ------------------------------------------------------------------
    # Reward
    # ------------------------------------------------------------------

    def set_reward(self, tier: int) -> bool:
        """Set reward tier (0-5). REJECTS tier > 5."""
        r = self._get_redis()
        if r is None:
            logger.error("set_reward(%d): Redis unavailable.", tier)
            return False

        if not isinstance(tier, int) or tier < 0:
            logger.warning("set_reward(%s): Invalid tier — must be int >= 0.", tier)
            return False

        if tier > 5:
            logger.warning(
                "SAFETY: set_reward(%d) REJECTED — reward capped at T5.", tier
            )
            return False

        try:
            old = r.get("guinevere:reward_tier")
            new = str(tier)
            r.set("guinevere:reward_tier", new)
            logger.info(
                "Reward tier changed: %s -> %s (%s)",
                old or "unset",
                new,
                REWARD_DESCRIPTIONS.get(tier, "Unknown"),
            )
            return True
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError, OSError) as exc:
            logger.error("set_reward(%d) failed: %s", tier, exc)
            return False

    # ------------------------------------------------------------------
    # Distress
    # ------------------------------------------------------------------

    def set_distress(self, state: int) -> bool:
        """Set distress state (0-4)."""
        r = self._get_redis()
        if r is None:
            logger.error("set_distress(%d): Redis unavailable.", state)
            return False

        if not isinstance(state, int) or state < 0 or state > 4:
            logger.warning("set_distress(%d): Invalid state — must be 0-4.", state)
            return False

        try:
            old = r.get("guinevere:distress_state")
            new = str(state)
            r.set("guinevere:distress_state", new)
            logger.info(
                "Distress state changed: %s -> %s (%s)",
                old or "unset",
                new,
                DISTRESS_DESCRIPTIONS.get(state, "Unknown"),
            )
            return True
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError, OSError) as exc:
            logger.error("set_distress(%d) failed: %s", state, exc)
            return False

    # ------------------------------------------------------------------
    # Mood
    # ------------------------------------------------------------------

    def set_mood(self, variant: str) -> bool:
        """Set mood variant. Must be one of: default, playful, serious, caring."""
        r = self._get_redis()
        if r is None:
            logger.error("set_mood(%s): Redis unavailable.", variant)
            return False

        if variant not in VALID_MOODS:
            logger.warning(
                "set_mood(%s) REJECTED — must be one of: %s",
                variant,
                ", ".join(sorted(VALID_MOODS)),
            )
            return False

        try:
            old = r.get("guinevere:mood_variant")
            r.set("guinevere:mood_variant", variant)
            logger.info("Mood variant changed: %s -> %s", old or "unset", variant)
            return True
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError, OSError) as exc:
            logger.error("set_mood(%s) failed: %s", variant, exc)
            return False

    # ------------------------------------------------------------------
    # Yandere Level — IMMUTABLE
    # ------------------------------------------------------------------

    def get_yandere_level(self) -> int:
        """Always returns 4 (Y4 baseline, immutable)."""
        r = self._get_redis()
        if r is None:
            return 4

        try:
            raw = r.get("guinevere:yandere_level")
            if raw is None:
                return 4
            val = int(raw)
            if val != 4:
                logger.warning(
                    "Yandere level was %d — correcting to Y4 (IMMUTABLE).", val
                )
                r.set("guinevere:yandere_level", "4")
                return 4
            return 4
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError, OSError) as exc:
            logger.error("get_yandere_level failed: %s", exc)
            return 4

    def set_yandere_level(self, level: int) -> bool:
        """ALWAYS REJECTS. Y4 is immutable baseline. Y6 is prohibited.

        Logs a safety warning for any attempt to mutate the yandere level.
        """
        logger.warning(
            "SAFETY: set_yandere_level(%d) ALWAYS REJECTED — Y4 is IMMUTABLE baseline. "
            "Yandere level cannot be changed at runtime.",
            level,
        )
        if level >= 6:
            logger.warning(
                "SAFETY: Attempted to set yandere level to Y%d — Y6 is PROHIBITED. "
                "This may indicate a safety boundary violation attempt.",
                level,
            )
        return False

    # ------------------------------------------------------------------
    # Interaction tracking
    # ------------------------------------------------------------------

    def record_interaction(self) -> bool:
        """Update last_interaction timestamp and increment daily counter.

        Daily counter resets if the stored date is not today (midnight rollover).
        """
        r = self._get_redis()
        if r is None:
            logger.warning("record_interaction: Redis unavailable.")
            return False

        now_iso = datetime.now(timezone.utc).isoformat()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        try:
            pipeline = r.pipeline()
            pipeline.set("guinevere:last_interaction", now_iso)

            # Reset counter if new day
            stored_date = r.get("guinevere:interaction_date")
            if stored_date != today:
                pipeline.set("guinevere:interaction_count", "0")
                pipeline.set("guinevere:interaction_date", today)
            else:
                pipeline.incr("guinevere:interaction_count")

            pipeline.execute()
            return True
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError, OSError) as exc:
            logger.error("record_interaction failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Consent
    # ------------------------------------------------------------------

    def get_consent(self, category: str) -> bool:
        """Check consent status for a tool category. Returns False on error."""
        if category not in VALID_CONSENT_CATEGORIES:
            logger.warning("get_consent(%s): Unknown category.", category)
            return False

        r = self._get_redis()
        if r is None:
            return False

        try:
            raw = r.get(f"guinevere:consent:{category}")
            if raw is None:
                return False
            return raw.lower() in ("1", "true", "yes")
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError, OSError) as exc:
            logger.error("get_consent(%s) failed: %s", category, exc)
            return False

    def set_consent(self, category: str, granted: bool) -> bool:
        """Set consent for a tool category."""
        if category not in VALID_CONSENT_CATEGORIES:
            logger.warning("set_consent(%s): Unknown category.", category)
            return False

        r = self._get_redis()
        if r is None:
            logger.error("set_consent(%s): Redis unavailable.", category)
            return False

        try:
            old = r.get(f"guinevere:consent:{category}")
            new = "true" if granted else "false"
            r.set(f"guinevere:consent:{category}", new)
            logger.info(
                "Consent '%s' changed: %s -> %s", category, old or "unset", new
            )
            return True
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError, OSError) as exc:
            logger.error("set_consent(%s, %s) failed: %s", category, granted, exc)
            return False

    # ------------------------------------------------------------------
    # DNR (Do Not Remember) list
    # ------------------------------------------------------------------

    def get_dnr_list(self) -> list[str]:
        """Get DNR topics list. Returns empty list on error."""
        r = self._get_redis()
        if r is None:
            return []

        try:
            raw = r.get("guinevere:dnr_list")
            if raw is None:
                return []
            return json.loads(raw)
        except (json.JSONDecodeError, redis.ConnectionError, redis.TimeoutError,
                redis.ResponseError, OSError) as exc:
            logger.error("get_dnr_list failed: %s", exc)
            return []

    def set_dnr_list(self, topics: list[str]) -> bool:
        """Set DNR topics list."""
        r = self._get_redis()
        if r is None:
            logger.error("set_dnr_list: Redis unavailable.")
            return False

        try:
            old = r.get("guinevere:dnr_list")
            new = json.dumps(topics, ensure_ascii=False)
            r.set("guinevere:dnr_list", new)
            logger.info("DNR list updated. Previous topic count: %d", len(old or "[]"))
            return True
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError, OSError) as exc:
            logger.error("set_dnr_list failed: %s", exc)
            return False