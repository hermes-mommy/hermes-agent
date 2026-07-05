"""Hermes Bridge — Redis DB5 pub/sub bridge for Hermes ↔ LoopManager coordination.

Receives cron job results from Hermes Agent and triggers loops via LoopScheduler.
Uses HMAC-SHA256 verification to ensure message authenticity and prevents replay attacks.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any

import structlog

from guinevere.loops.manager import LoopManager

logger = structlog.get_logger("guinevere.loops.hermes")

_HERMES_CHANNEL: str = "hermes:cron:results"
_SIGNATURE_TTL_SECONDS: int = 60
_NONCE_MAX_SIZE: int = 1000


class HermesBridge:
    """Redis DB5 pub/sub bridge for Hermes ↔ LoopManager coordination.

    Listens to hermes:cron:results channel for cron job results. Verifies HMAC-SHA256
    signatures before triggering loops. Prevents replay attacks via nonce tracking.
    """

    def __init__(self, loop_manager: LoopManager) -> None:
        self.loop_manager = loop_manager
        self._redis = None
        self._subscribed = False
        self._listener_task: asyncio.Task[Any] | None = None
        self._lock = asyncio.Lock()
        self._seen_nonces: deque[tuple[str, datetime]] = deque()

        # Load shared secret for HMAC verification (optional — dev mode)
        self._shared_secret = os.environ.get("HERMES_BRIDGE_SECRET", "")
        if self._shared_secret:
            logger.info("hermes_bridge.hmac_enabled", secret_configured=True)
        else:
            logger.warning(
                "hermes_bridge.hmac_disabled",
                reason="HERMES_BRIDGE_SECRET not set — operating in receive-only mode (dev only)",
            )

    async def start(self) -> None:
        """Connect to Redis DB5 and start listening for messages."""
        try:
            import redis.asyncio as aioredis

            _redis_password = os.environ.get("REDIS_PASSWORD", "")
            self._redis = aioredis.Redis(
                host="localhost",
                port=6380,
                db=5,
                username="default",
                password=_redis_password,
                decode_responses=True,
            )

            # Test connection
            await self._redis.ping()
            logger.info("hermes_bridge.redis_connected", channel=_HERMES_CHANNEL)

            # Subscribe to hermes:cron:results
            self._subscribed = True
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(_HERMES_CHANNEL)
            logger.info("hermes_bridge.subscribed", channel=_HERMES_CHANNEL)

            # Start listener task
            self._listener_task = asyncio.create_task(
                self._listen(pubsub), name="hermes-bridge-listener",
            )
            logger.info("hermes_bridge.listener_started")

        except Exception as bridge_err:
            logger.error(
                "hermes_bridge.start_failed",
                error=str(bridge_err),
            )
            raise

    async def stop(self) -> None:
        """Stop listener and close Redis connection."""
        if self._listener_task is not None and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self._subscribed and self._redis is not None:
            async with self._lock:
                self._subscribed = False
            try:
                pubsub = self._redis.pubsub()
                await pubsub.unsubscribe(_HERMES_CHANNEL)
                await pubsub.close()
            except Exception as close_err:
                logger.warning("hermes_bridge.pubsub_close_failed", error=str(close_err))

        if self._redis is not None:
            try:
                await self._redis.aclose()
                logger.info("hermes_bridge.redis_closed")
            except Exception as close_err:
                logger.warning("hermes_bridge.redis_close_failed", error=str(close_err))

    async def _listen(self, pubsub: Any) -> None:
        """Infinite loop reading pub/sub messages from Hermes channel."""
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
                except Exception as parse_err:
                    logger.warning(
                        "hermes_bridge.message_parse_failed",
                        error=str(parse_err),
                    )
                    continue

                try:
                    payload = await self._verify_message(envelope)
                    await self._process_payload(payload)
                except Exception as process_err:
                    logger.error(
                        "hermes_bridge.message_processing_failed",
                        error=str(process_err),
                    )
        except asyncio.CancelledError:
            logger.info("hermes_bridge.listener_cancelled")
            raise
        except Exception as listen_err:
            logger.error(
                "hermes_bridge.listener_error",
                error=str(listen_err),
            )
        finally:
            async with self._lock:
                self._subscribed = False

    async def _verify_message(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """Verify a received Hermes envelope.

        Validates:
        * Signature (HMAC-SHA256 over payload) — if HERMES_BRIDGE_SECRET configured
        * Timestamp (reject if older than 60s)
        * Nonce (reject replays)

        Returns the payload if valid. Raises ValueError with audit log on failure.
        """
        if self._shared_secret:
            # Production mode: strict HMAC verification
            return await self._verify_signed_message(envelope)
        else:
            # Dev mode: no signature verification
            payload = envelope.get("payload")
            if not isinstance(payload, dict):
                raise ValueError("Missing or invalid payload in dev mode")
            return payload

    async def _verify_signed_message(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """Verify a signed Hermes envelope with HMAC-SHA256.

        Returns payload if valid. Raises ValueError with audit log on failure.
        """
        if not self._shared_secret:
            raise ValueError("HERMES_BRIDGE_SECRET not configured")

        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("Missing or invalid payload")

        signature = envelope.get("signature", "")
        if not signature or not isinstance(signature, str):
            logger.error(
                "hermes_bridge.message_unsigned",
                reason="Missing signature",
            )
            raise ValueError("Missing signature")

        # Verify signature
        payload_bytes = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
        expected = hmac.new(
            self._shared_secret.encode("utf-8"), payload_bytes, hashlib.sha256
        ).hexdigest()

        import hashlib
        import hmac

        if not hmac.compare_digest(expected, signature):
            logger.error(
                "hermes_bridge.message_invalid_signature",
                reason="HMAC verification failed",
            )
            raise ValueError("Invalid HMAC signature")

        # Verify timestamp
        timestamp_str = payload.get("timestamp") or envelope.get("timestamp")
        if not isinstance(timestamp_str, str):
            logger.error(
                "hermes_bridge.message_missing_timestamp",
            )
            raise ValueError("Missing timestamp")

        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except Exception as exc:
            logger.error(
                "hermes_bridge.message_invalid_timestamp",
                error=str(exc),
            )
            raise ValueError(f"Invalid timestamp: {timestamp_str}") from exc

        age = (datetime.now(timezone.utc) - timestamp).total_seconds()
        if age > _SIGNATURE_TTL_SECONDS:
            logger.error(
                "hermes_bridge.message_expired",
                age_seconds=age,
            )
            raise ValueError(f"Message timestamp expired ({age:.1f}s old)")

        # Verify nonce (replay prevention)
        nonce = envelope.get("nonce")
        if not isinstance(nonce, str) or not nonce:
            logger.error(
                "hermes_bridge.message_missing_nonce",
            )
            raise ValueError("Missing nonce")

        async with self._lock:
            self._prune_seen_nonces()
            if any(n == nonce for n, _ in self._seen_nonces):
                logger.error(
                    "hermes_bridge.message_replayed",
                    nonce=nonce,
                )
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

    async def _process_payload(self, payload: dict[str, Any]) -> None:
        """Process a verified payload and trigger a loop.

        Args:
            payload: Parsed payload dict with at least 'task' key.
        """
        task = payload.get("task")
        if not task or not isinstance(task, str):
            logger.error(
                "hermes_bridge.missing_task",
                payload=payload,
            )
            raise ValueError("Missing or invalid 'task' field in payload")

        goal = payload.get("goal", "")

        try:
            loop_id = await self.loop_manager.start_loop(task=task, goal=goal)
            logger.info(
                "hermes_bridge.loop_triggered",
                loop_id=loop_id,
                task=task,
                goal=goal,
            )
        except Exception as trigger_err:
            logger.error(
                "hermes_bridge.loop_trigger_failed",
                task=task,
                error=str(trigger_err),
            )
            raise


def create_hermes_bridge(loop_manager: LoopManager) -> HermesBridge:
    """Factory function to create HermesBridge instance.

    Args:
        loop_manager: The LoopManager instance to bridge to.

    Returns:
        Configured HermesBridge instance.
    """
    return HermesBridge(loop_manager=loop_manager)