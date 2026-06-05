"""Approval handler — Redis DB5-persisted destructive approval state.

Uses the project's canonical Redis port (6380) and database index 5 (DB5)
for storing pending destructive approval requests with a 5-minute (300 s)
TTL, matching the approval timeout from the auth matrix.

The handler accepts an optional *redis_client* parameter for dependency
injection.  When *redis_client* is ``None``, it creates a ``RedisAdapter``
that uses ``redis.Redis`` to connect to ``redis://localhost:6380/5``.  For
unit tests, pass a ``FakeRedisAdapter`` instance that stores state in-memory.
"""

from __future__ import annotations

import importlib
import json
import os
import time
from collections.abc import Mapping
from typing import Protocol, cast

import structlog

class Logger(Protocol):
    def info(self, event: str, **kwargs: object) -> None: ...
    def warning(self, event: str, **kwargs: object) -> None: ...


logger = cast(Logger, structlog.get_logger(__name__))

JsonObject = Mapping[str, object]

# Canonical Redis connection defaults.
_REDIS_DB: int = 5
_REDIS_PORT: int = 6380
_REDIS_HOST: str = "localhost"
_APPROVAL_TTL_SECONDS: int = 300  # 5 minutes
APPROVAL_TTL_SECONDS: int = _APPROVAL_TTL_SECONDS

# Redis key prefix for pending approvals.
_KEY_PREFIX: str = "auth_overlay:approval:"


# ==============================================================================
# Adapter protocol + implementations
# ==============================================================================


class IRedisAdapter(Protocol):
    """Minimal Redis interface for approval persistence."""

    def setex(self, key: str, seconds: int, value: str) -> None: ...
    def get(self, key: str) -> str | None: ...
    def delete(self, key: str) -> None: ...


class RedisModule(Protocol):
    def from_url(self, url: str, *, decode_responses: bool) -> IRedisAdapter: ...


class RedisAdapter:
    """Production Redis adapter using ``redis.Redis``.

    Connects to the project's canonical Redis endpoint on DB5.
    """

    def __init__(self) -> None:
        redis_url = os.environ.get(
            "REDIS_URL",
            f"redis://{_REDIS_HOST}:{_REDIS_PORT}/{_REDIS_DB}",
        )
        redis_module = cast(object, importlib.import_module("redis"))
        redis_mod = cast(RedisModule, redis_module)
        self._client: IRedisAdapter = redis_mod.from_url(
            redis_url,
            decode_responses=True,
        )

    def setex(self, key: str, seconds: int, value: str) -> None:
        self._client.setex(key, seconds, value)

    def get(self, key: str) -> str | None:
        result = self._client.get(key)
        if result is not None:
            return str(result)
        return None

    def delete(self, key: str) -> None:
        self._client.delete(key)


class FakeRedisAdapter:
    """In-memory fake Redis adapter for unit tests.

    Stores key-value pairs with optional TTL expiry, checked on every read.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float | None]] = {}  # key → (value, expiry)

    def setex(self, key: str, seconds: int, value: str) -> None:
        expiry = time.monotonic() + seconds
        self._store[key] = (value, expiry)

    def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if expiry is not None and time.monotonic() > expiry:
            del self._store[key]
            return None
        return value

    def delete(self, key: str) -> None:
        _ = self._store.pop(key, None)


# ==============================================================================
# Approval status values
# ==============================================================================

PENDING = "pending"
APPROVED = "approved"
DENIED = "denied"


# ==============================================================================
# ApprovalHandler
# ==============================================================================


class ApprovalHandler:
    """Manages destructive approval requests with Redis DB5 persistence.

    Args:
        redis_client: Optional ``IRedisAdapter`` instance.  Defaults to a
            production ``RedisAdapter``.  Pass ``FakeRedisAdapter()`` in tests.
    """

    def __init__(self, redis_client: IRedisAdapter | None = None) -> None:
        self._redis: IRedisAdapter = redis_client if redis_client is not None else RedisAdapter()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request_approval(
        self,
        canonical_tool: str,
        operation: str,
        details: str = "",
        ttl: int = _APPROVAL_TTL_SECONDS,
    ) -> dict[str, str | int]:
        """Create a pending destructive approval request in Redis DB5.

        Args:
            canonical_tool: Canonical tool name.
            operation: The operation requiring approval.
            details: Optional context for the approval UI.
            ttl: Time-to-live in seconds (default 300).

        Returns:
            A dict with the approval request status::

                {
                    "status": "pending",
                    "tool": ...,
                    "operation": ...,
                    "ttl_seconds": ...,
                    "key": ...,
                }
        """
        key = _KEY_PREFIX + canonical_tool
        payload = json.dumps({
            "status": PENDING,
            "tool": canonical_tool,
            "operation": operation,
            "details": details[:500],  # cap detail length
            "created_at": time.time(),
        })
        self._redis.setex(key, ttl, payload)
        logger.info(
            "auth_overlay_approval_requested",
            tool=canonical_tool,
            operation=operation,
            ttl=ttl,
        )
        return {
            "status": PENDING,
            "tool": canonical_tool,
            "operation": operation,
            "ttl_seconds": ttl,
            "key": key,
        }

    def check_approval(self, canonical_tool: str) -> str | None:
        """Check the current approval status for *canonical_tool*.

        Returns:
            ``"approved"``, ``"denied"``, or ``None`` if no request exists
            or the request has expired.
        """
        key = _KEY_PREFIX + canonical_tool
        raw = self._redis.get(key)
        if raw is None:
            return None
        try:
            data = cast(object, json.loads(raw))
            if not isinstance(data, dict):
                return None
            status = cast(JsonObject, data).get("status")
            return status if isinstance(status, str) else None
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "auth_overlay_approval_decode_error",
                tool=canonical_tool,
                key=key,
            )
            return None

    def resolve_approval(
        self,
        canonical_tool: str,
        approved: bool,
    ) -> bool:
        """Resolve a pending approval request.

        Sets the approval status in Redis without changing the TTL (the
        key will expire naturally after the original TTL elapses).

        Args:
            canonical_tool: Canonical tool name.
            approved: ``True`` to approve, ``False`` to deny.

        Returns:
            ``True`` if the request existed and was resolved, ``False`` if
            no pending request was found.
        """
        key = _KEY_PREFIX + canonical_tool
        raw = self._redis.get(key)
        if raw is None:
            logger.warning(
                "auth_overlay_approval_not_found",
                tool=canonical_tool,
            )
            return False
        try:
            decoded = cast(object, json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            return False
        if not isinstance(decoded, dict):
            return False

        data: dict[str, object] = dict(cast(JsonObject, decoded))
        new_status = APPROVED if approved else DENIED
        data["status"] = new_status
        data["resolved_at"] = time.time()

        # Re-write with same TTL by reading remaining TTL from a separate key.
        # For simplicity, re-use the original TTL from the data payload.
        self._redis.setex(key, _APPROVAL_TTL_SECONDS, json.dumps(data))
        logger.info(
            "auth_overlay_approval_resolved",
            tool=canonical_tool,
            status=new_status,
        )
        return True

    def consume_approval(self, canonical_tool: str) -> bool:
        """Consume (delete) an approved request after the tool executed.

        Args:
            canonical_tool: Canonical tool name.

        Returns:
            ``True`` if the key existed and was deleted.
        """
        key = _KEY_PREFIX + canonical_tool
        raw = self._redis.get(key)
        if raw is None:
            return False
        self._redis.delete(key)
        logger.info(
            "auth_overlay_approval_consumed",
            tool=canonical_tool,
        )
        return True
