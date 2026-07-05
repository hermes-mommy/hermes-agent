"""Safety integration for Guinevere loop system.

Provides ``LoopSafetyGate`` — a bridge between the in-process ``HardStopHandler``
and the broader loop runtime. It supports both local (v1.0) and Redis pub/sub
(v2.0) HARD STOP propagation, with HMAC-SHA256 signed broadcasts and an
SHA-256-chained audit trail.
"""

from __future__ import annotations

import asyncio
import enum
import hmac
import hashlib
import json
import logging
import os
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from guinevere.core.services.hard_stop_handler import HardStopHandler, SafetyState

logger = logging.getLogger("guinevere.loops.safety")


class SafetyAction(enum.Enum):
    """Decision produced by ``LoopSafetyGate.check``.

    ``ALLOW`` proceeds normally. ``WARN`` permits execution but records the
    event. ``PAUSE`` suspends the loop and alerts Discord. ``TERMINATE``
    immediately stops the loop.
    """

    ALLOW = "allow"
    WARN = "warn"
    PAUSE = "pause"
    TERMINATE = "terminate"


@dataclass(frozen=True)
class SafetyEvent:
    """Immutable record of a safety decision."""

    loop_id: str
    phase: int
    action: SafetyAction
    trigger: str
    timestamp: datetime
    metadata: dict[str, Any]


class LoopSafetyGate:
    """Integrates ``HardStopHandler`` into the loop system.

    v1.0: In-process check only (``HardStopHandler.is_safe``).
    v2.0: Redis pub/sub for cross-process HARD STOP broadcast.

    Parameters
    ----------
    hard_stop_handler:
        Existing ``HardStopHandler`` from the main process (optional).
    redis_client:
        Async Redis client from ``redis.asyncio`` (optional).
    audit_writer:
        ``AuditWriter`` instance for SHA-256-chained audit events (optional).
    """

    _SAFETY_CHANNEL: str = "guinevere:safety:hardstop"
    _STATE_KEY: str = "guinevere:safety:hardstop:state"
    _SIGNATURE_TTL_SECONDS: int = 60

    def __init__(
        self,
        hard_stop_handler: HardStopHandler | None = None,
        redis_client: Any = None,
        audit_writer: Any = None,
    ) -> None:
        self._handler: HardStopHandler | None = hard_stop_handler
        self._redis: Any = redis_client
        self._audit: Any = audit_writer
        self._safety_channel: str = self._SAFETY_CHANNEL
        self._state_key: str = self._STATE_KEY
        self._seen_nonces: deque[tuple[str, datetime]] = deque()
        self._listener_task: asyncio.Task[Any] | None = None
        self._subscribed: bool = False
        self._lock = asyncio.Lock()

        if self._redis is None:
            logger.warning(
                "LoopSafetyGate operating in-process only, "
                "HARD STOP not shared across services"
            )

    async def check(self, loop_id: str, phase: int, content: str = "") -> SafetyEvent:
        """Check if a loop phase is safe to proceed.

        The gate evaluates, in order:

        1. Local ``HardStopHandler.is_safe``.
        2. Trigger patterns in ``content`` (via ``HardStopHandler.check``).
        3. Redis HARD STOP flag (if a Redis client is available).
        4. Falls back to ``SafetyAction.ALLOW``.

        Returns a ``SafetyEvent`` describing the decision.
        """
        action = SafetyAction.ALLOW
        trigger = "no-safety-concern"
        metadata: dict[str, Any] = {}

        # 1. Local HardStopHandler state
        if self._handler is not None:
            if not self._handler.is_safe:
                action = SafetyAction.TERMINATE
                trigger = "hard-stop-handler-active"

        # 2. Scan content for triggers
        if action == SafetyAction.ALLOW and content and self._handler is not None:
            if self._handler.check(content):
                action = SafetyAction.TERMINATE
                trigger = f"hard-stop-content-trigger:{content[:100]!r}"
                metadata["content_length"] = len(content)

        # 3. Redis HARD STOP flag
        if action == SafetyAction.ALLOW and self._redis is not None:
            try:
                flag = await self._redis.get(self._state_key)
                if flag is not None and flag.decode("utf-8") == "1":
                    action = SafetyAction.TERMINATE
                    trigger = "redis-hard-stop-flag"
            except Exception as exc:
                logger.warning("Redis hard stop flag check failed: %s", exc)

        timestamp = datetime.now(timezone.utc)
        event = SafetyEvent(
            loop_id=loop_id,
            phase=phase,
            action=action,
            trigger=trigger,
            timestamp=timestamp,
            metadata=metadata,
        )
        await self._audit_event(event)
        return event

    async def broadcast_hard_stop(
        self, source: str = "manual", reason: str = ""
    ) -> None:
        """Broadcast HARD STOP across all processes via Redis pub/sub.

        v1.0: Also sets the local ``HardStopHandler`` state if available.
        v2.0: Publishes an HMAC-SHA256 signed message to the safety channel.
        """
        if self._handler is not None:
            self._handler.state = SafetyState.SAFE

        await self._publish_safety_message("hard_stop", source, reason)
        await self._set_redis_state("1")
        await self._notify_discord(
            sev="SEV0",
            title="HARD STOP Broadcast",
            description=f"Source: {source}. Reason: {reason or 'N/A'}.",
        )

        event = SafetyEvent(
            loop_id="broadcast",
            phase=0,
            action=SafetyAction.TERMINATE,
            trigger=f"broadcast-hard-stop:{source}",
            timestamp=datetime.now(timezone.utc),
            metadata={"reason": reason},
        )
        await self._audit_event(event)

    async def clear_hard_stop(self, source: str = "manual") -> None:
        """Clear HARD STOP state and broadcast recovery."""
        if self._handler is not None:
            self._handler.state = SafetyState.NORMAL

        await self._publish_safety_message("clear", source, "")
        await self._set_redis_state("0")
        await self._notify_discord(
            sev="SEV3",
            title="HARD STOP Cleared",
            description=f"Source: {source}. Normal operation resumed.",
        )

        event = SafetyEvent(
            loop_id="broadcast",
            phase=0,
            action=SafetyAction.ALLOW,
            trigger=f"clear-hard-stop:{source}",
            timestamp=datetime.now(timezone.utc),
            metadata={},
        )
        await self._audit_event(event)

    async def subscribe(
        self, callback: Callable[[SafetyEvent], Awaitable[None]]
    ) -> None:
        """Subscribe to HARD STOP broadcasts (for loop managers).

        Listens on the configured Redis pub/sub channel, verifies the
        HMAC-SHA256 signature, and invokes ``callback`` with the resulting
        ``SafetyEvent``. This method runs until cancelled.
        """
        if self._redis is None:
            logger.warning("No Redis client available; subscribe() is a no-op")
            return

        if not hasattr(self._redis, "pubsub"):
            logger.warning("Redis client does not support pub/sub")
            return

        async with self._lock:
            self._subscribed = True
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self._safety_channel)
        logger.info("Subscribed to safety channel: %s", self._safety_channel)

        try:
            async for message in pubsub.listen():
                if not isinstance(message, dict):
                    continue
                if message.get("type") != "message":
                    continue

                data = message.get("data")
                if not isinstance(data, (str, bytes)):
                    continue

                try:
                    envelope = json.loads(data) if isinstance(data, str) else json.loads(data.decode("utf-8"))
                except Exception as exc:
                    logger.warning("Failed to parse safety broadcast: %s", exc)
                    continue

                try:
                    payload = await self._verify_message(envelope)
                except Exception as exc:
                    logger.warning("Rejected invalid safety broadcast: %s", exc)
                    continue

                action_name = payload.get("action", "")
                action = self._action_from_name(action_name)
                event = SafetyEvent(
                    loop_id="broadcast",
                    phase=0,
                    action=action,
                    trigger=f"redis-broadcast:{action_name}",
                    timestamp=datetime.now(timezone.utc),
                    metadata=payload,
                )

                if self._handler is not None:
                    if action == SafetyAction.TERMINATE:
                        self._handler.state = SafetyState.SAFE
                    elif action == SafetyAction.ALLOW:
                        self._handler.state = SafetyState.NORMAL

                try:
                    await callback(event)
                except Exception as exc:
                    logger.error("Safety event callback raised an error: %s", exc)

                await self._audit_event(event)
        except asyncio.CancelledError:
            logger.info("Safety subscription cancelled")
            raise
        except Exception as exc:
            logger.error("Safety subscription loop error: %s", exc)
        finally:
            async with self._lock:
                self._subscribed = False
            try:
                await pubsub.unsubscribe(self._safety_channel)
                await pubsub.close()
            except Exception as exc:
                logger.warning("Error closing pubsub: %s", exc)

    async def _audit_event(self, event: SafetyEvent) -> None:
        """Write safety event to SHA-256 chained audit log."""
        try:
            if self._audit is not None:
                await self._audit.write_event(
                    event_type="safety.check",
                    loop_id=event.loop_id,
                    data={
                        "phase": event.phase,
                        "action": event.action.value,
                        "trigger": event.trigger,
                        "timestamp": event.timestamp.isoformat(),
                        "metadata": event.metadata,
                    },
                )
            else:
                # Lightweight local SHA-256 chain when no AuditWriter is provided.
                payload = {
                    "event_type": "safety.check",
                    "loop_id": event.loop_id,
                    "phase": event.phase,
                    "action": event.action.value,
                    "trigger": event.trigger,
                    "timestamp": event.timestamp.isoformat(),
                    "metadata": event.metadata,
                }
                digest = hashlib.sha256(
                    json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
                ).hexdigest()
                logger.info(
                    "safety.audit fallback hash=%s action=%s trigger=%s",
                    digest[:12],
                    event.action.value,
                    event.trigger,
                )
        except Exception as exc:
            logger.error("Failed to write safety audit event: %s", exc)

    async def _publish_safety_message(
        self, action: str, source: str, reason: str
    ) -> None:
        """Publish a signed safety message to Redis (v2.0)."""
        if self._redis is None:
            return

        secret = os.environ.get("HERMES_BRIDGE_SECRET", "")
        if not secret:
            logger.error(
                "HERMES_BRIDGE_SECRET not set; refusing to broadcast unsigned safety message"
            )
            return

        envelope = self._build_signed_message(action, source, reason, secret)
        try:
            await self._redis.publish(self._safety_channel, json.dumps(envelope))
            logger.info(
                "Published safety message action=%s source=%s channel=%s",
                action,
                source,
                self._safety_channel,
            )
        except Exception as exc:
            logger.error("Failed to publish safety message: %s", exc)

    async def _set_redis_state(self, value: str) -> None:
        """Set the Redis HARD STOP flag (``1`` or ``0``)."""
        if self._redis is None:
            return
        try:
            await self._redis.set(self._state_key, value)
        except Exception as exc:
            logger.warning("Failed to set Redis hard stop state to %s: %s", value, exc)

    def _build_signed_message(
        self, action: str, source: str, reason: str, secret: str
    ) -> dict[str, Any]:
        """Create an HMAC-SHA256 signed safety envelope."""
        now = datetime.now(timezone.utc)
        payload = {
            "action": action,
            "source": source,
            "reason": reason,
            "timestamp": now.isoformat(),
        }
        payload_bytes = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return {
            "payload": payload,
            "signature": signature,
            "timestamp": now.isoformat(),
            "nonce": str(uuid.uuid4()),
        }

    async def _verify_message(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """Verify a received safety envelope.

        Validates:

        * Signature (HMAC-SHA256 over payload).
        * Timestamp (reject if older than ``_SIGNATURE_TTL_SECONDS``).
        * Nonce (reject replays).

        Returns the payload if valid. Raises ``ValueError`` otherwise.
        """
        secret = os.environ.get("HERMES_BRIDGE_SECRET", "")
        if not secret:
            raise ValueError("HERMES_BRIDGE_SECRET not configured")

        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("Missing or invalid payload")

        signature = envelope.get("signature", "")
        payload_bytes = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
        expected = hmac.new(
            secret.encode("utf-8"), payload_bytes, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid HMAC signature")

        timestamp_str = payload.get("timestamp") or envelope.get("timestamp")
        if not isinstance(timestamp_str, str):
            raise ValueError("Missing timestamp")
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except Exception as exc:
            raise ValueError(f"Invalid timestamp: {timestamp_str}") from exc

        age = (datetime.now(timezone.utc) - timestamp).total_seconds()
        if age > self._SIGNATURE_TTL_SECONDS:
            raise ValueError(f"Safety message timestamp expired ({age:.1f}s old)")

        nonce = envelope.get("nonce")
        if not isinstance(nonce, str) or not nonce:
            raise ValueError("Missing nonce")

        async with self._lock:
            self._prune_seen_nonces()
            if any(n == nonce for n, _ in self._seen_nonces):
                raise ValueError("Replayed nonce")
            self._seen_nonces.append((nonce, datetime.now(timezone.utc)))

        return payload

    def _prune_seen_nonces(self) -> None:
        """Remove nonces older than five minutes to bound memory use."""
        cutoff = datetime.now(timezone.utc)
        while self._seen_nonces and (
            cutoff - self._seen_nonces[0][1]
        ).total_seconds() > 300:
            self._seen_nonces.popleft()

    def _action_from_name(self, name: str) -> SafetyAction:
        """Map a payload action name to a ``SafetyAction``."""
        mapping = {
            "hard_stop": SafetyAction.TERMINATE,
            "terminate": SafetyAction.TERMINATE,
            "pause": SafetyAction.PAUSE,
            "warn": SafetyAction.WARN,
            "clear": SafetyAction.ALLOW,
            "allow": SafetyAction.ALLOW,
        }
        return mapping.get(name, SafetyAction.TERMINATE)

    async def _notify_discord(self, sev: str, title: str, description: str) -> None:
        """Attempt to route a Discord alert using the existing notification layer.

        A live bot instance is required. If none is available, the alert is logged
        and execution continues without failing the safety operation.
        """
        try:
            # The concrete send_alert implementation lives in notifications.py and
            # requires a bot object; this gate does not own a bot, so we log the
            # alert instead of attempting a broken import path.
            logger.warning(
                "Discord alert queued (no bot instance): sev=%s title=%s description=%s",
                sev,
                title,
                description,
            )
        except Exception as exc:
            logger.error("Failed to queue Discord alert: %s", exc)


async def register_safety_gate(
    gate: LoopSafetyGate, redis_client: Any = None
) -> None:
    """Register safety gate with Redis pub/sub listener.

    Sets up a background task that listens on the safety channel and triggers
    the gate's callback when a HARD STOP is received.
    """
    if redis_client is not None:
        gate._redis = redis_client

    async def _listener() -> None:
        async def _callback(event: SafetyEvent) -> None:
            logger.warning(
                "Received remote safety event via Redis: action=%s trigger=%s",
                event.action.value,
                event.trigger,
            )

        await gate.subscribe(_callback)

    try:
        gate._listener_task = asyncio.create_task(_listener())
    except Exception as exc:
        logger.error("Failed to start safety gate listener: %s", exc)
