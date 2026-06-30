"""Redis client for Living Autonomy Kernel world model caching (LK-003).

Redis DB7 for world model caching (DB6 for checkpoints, DB2 for surveillance, DB4 for Hermes sessions, DB5 for Hermes bridge).
"""
from __future__ import annotations

import json
import re
from typing import Any

import redis
import structlog

from guinvere.memory.models import Base

logger = structlog.get_logger(__name__)


def _redact_url(url: str) -> str:
    """Redact credentials from a connection URL for safe logging."""
    return re.sub(r"://([^:]+):[^@]+@", r"://\1:***@", url)

# Key prefix for world model state caching
WORLD_STATE_KEY_PREFIX = "life_kernel:world:"
_FEATURE_FLAG_KEY = "feature:projects:enabled"


def _is_projects_flag_on(redis_client: Any) -> bool:
    """Read the feature:projects:enabled flag from Redis (fail-safe OFF)."""
    try:
        raw = redis_client.get(_FEATURE_FLAG_KEY)
    except Exception:
        logger.debug("feature_flag_read_failed_defaulting_off", exc_info=True)
        return False
    if raw is None:
        return False
    decoded = raw.decode() if isinstance(raw, bytes) else str(raw)
    return decoded.strip().lower() in ("true", "1", "yes")


def world_state_key(key: str, project_id: str | None = None, *, redis_client: Any = None) -> str:
    """Return the world-state Redis key, optionally project-scoped.

    When ``project_id`` is provided AND the ``feature:projects:enabled`` flag
    is ON, returns ``life_kernel:{project_id}:world:{key}``.  Otherwise
    returns ``life_kernel:world:{key}`` (legacy).  A ``redis_client`` is
    required only when ``project_id`` is set and the flag must be checked.
    """
    if project_id and redis_client is not None and _is_projects_flag_on(redis_client):
        return f"life_kernel:{project_id}:world:{key}"
    return f"{WORLD_STATE_KEY_PREFIX}{key}"


def create_world_redis_client(redis_url: str, db: int = 7) -> redis.Redis:
    """Create Redis client for world model caching.

    Args:
        redis_url: Redis connection URL (e.g., redis://localhost:6380)
        db: Redis database number (default: 7 for world model)

    Returns:
        Configured redis.Redis client with decode_responses=True
    """
    try:
        client = redis.Redis.from_url(redis_url, db=db, decode_responses=True)
        # Test connection
        client.ping()
        logger.info("world_redis_client_created", db=db, redis_url=_redact_url(redis_url))
        return client
    except Exception as exc:  # noqa: BLE001
        logger.exception("world_redis_client_creation_failed", error=str(exc), db=db, redis_url=_redact_url(redis_url))
        raise


def cache_world_state(
    redis_client: redis.Redis,
    key: str,
    state_json: dict[str, Any],
    ttl: int = 60,
    project_id: str | None = None,
) -> bool:
    """Cache world model state in Redis with TTL.

    Args:
        redis_client: Redis client instance
        key: Cache key (without prefix, e.g., "current_state")
        state_json: State dictionary to cache
        ttl: Time-to-live in seconds (default: 60)
        project_id: Optional project namespace. When set (and the
            ``feature:projects:enabled`` flag is ON), the key is scoped to
            ``life_kernel:{project_id}:world:{key}``.

    Returns:
        True if successful, False if Redis error occurred
    """
    full_key = world_state_key(key, project_id=project_id, redis_client=redis_client)
    try:
        redis_client.setex(full_key, ttl, json.dumps(state_json, default=str))
        logger.debug("world_state_cached", key=key, ttl=ttl)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("world_state_cache_failed", error=str(exc), key=key)
        return False


def get_cached_world_state(
    redis_client: redis.Redis,
    key: str,
    project_id: str | None = None,
) -> dict[str, Any] | None:
    """Retrieve cached world model state from Redis.

    Args:
        redis_client: Redis client instance
        key: Cache key (without prefix, e.g., "current_state")
        project_id: Optional project namespace for scoped lookup.

    Returns:
        Cached state dictionary or None if not found/error
    """
    full_key = world_state_key(key, project_id=project_id, redis_client=redis_client)
    try:
        raw_value = redis_client.get(full_key)
        if raw_value is None:
            logger.debug("world_state_not_found", key=key)
            return None
        return json.loads(raw_value)
    except Exception as exc:  # noqa: BLE001
        logger.exception("world_state_retrieval_failed", error=str(exc), key=key)
        return None


def delete_cached_world_state(
    redis_client: redis.Redis,
    key: str,
    project_id: str | None = None,
) -> bool:
    """Delete cached world model state from Redis.

    Args:
        redis_client: Redis client instance
        key: Cache key (without prefix, e.g., "current_state")
        project_id: Optional project namespace for scoped deletion.

    Returns:
        True if successful, False if Redis error occurred
    """
    full_key = world_state_key(key, project_id=project_id, redis_client=redis_client)
    try:
        deleted = redis_client.delete(full_key)
        logger.debug("world_state_deleted", key=key, deleted=deleted > 0)
        return deleted > 0
    except Exception as exc:  # noqa: BLE001
        logger.exception("world_state_deletion_failed", error=str(exc), key=key)
        return False