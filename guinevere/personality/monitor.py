"""PeerMonitor — saling drift monitor (Guin <-> Pharsa, equal status).

B35: Guin monitors Pharsa, Pharsa monitors Guin.  No hierarchy.
Redis DB7 pub/sub channels: g2p (Guin->Pharsa), p2g (Pharsa->Guin).
B40: conflict resolution — negotiate directly, if fail -> DAO vote.

Fail-soft if no Redis (D2): monitoring degrades gracefully.
Anomaly -> escalate to DAO (M7) as Tier-4 proposal (not governance).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import structlog

from guinevere.personality.signature import (
    BehaviorSignature,
    _cosine_similarity,
)

logger = structlog.get_logger("guinevere.personality")

# Redis DB7 for M2M communication.
_REDIS_DB: int = 7

# Peer anomaly threshold (cross-instance cosine similarity).
_PEER_ANOMALY_THRESHOLD: float = 0.65

# Signature TTL in Redis (seconds) — staleness guard.
_SIGNATURE_TTL: int = 600


class PeerMonitor:
    """Saling drift monitor — Guin <-> Pharsa equal status.

    Each instance publishes its behavior signature delta to the peer's
    channel and subscribes to its own channel to receive peer updates.

    Channel mapping (DB7):
        Guinevere: publish g2p, subscribe p2g
        Pharsa:    publish p2g, subscribe g2p

    Attributes:
        instance_name: "guinevere" or "pharsa".
        publish_channel: Redis channel to publish to.
        subscribe_channel: Redis channel to subscribe to.
    """

    def __init__(
        self,
        instance_name: str = "guinevere",
        redis_client: Any | None = None,
        peer_anomaly_threshold: float = _PEER_ANOMALY_THRESHOLD,
    ) -> None:
        self.instance_name = instance_name
        self.peer_anomaly_threshold = peer_anomaly_threshold

        # Channel assignment: equal status.
        if instance_name == "guinevere":
            self.publish_channel = "g2p"
            self.subscribe_channel = "p2g"
        else:
            self.publish_channel = "p2g"
            self.subscribe_channel = "g2p"

        # Redis client (None = fail-soft mode per D2).
        self._redis = redis_client

        # Peer state tracking.
        self._peer_signature: BehaviorSignature | None = None
        self._baseline_for_peer: BehaviorSignature | None = None
        self._peer_name: str = "pharsa" if instance_name == "guinevere" else "guinevere"
        self._peer_anomaly_count: int = 0
        self._last_peer_cosine: float = 1.0
        self._publish_count: int = 0

        logger.info(
            "peer_monitor.initialized",
            instance=instance_name,
            publish=self.publish_channel,
            subscribe=self.subscribe_channel,
            redis_available=redis_client is not None,
        )

    # ── publish ──────────────────────────────────────────────

    def publish_signature(
        self,
        signature: BehaviorSignature,
        cosine_vs_baseline: float,
        anomaly_detected: bool,
    ) -> bool:
        """Publish the current behavior signature to the peer channel.

        Args:
            signature: Current BehaviorSignature.
            cosine_vs_baseline: Cosine similarity vs own baseline.
            anomaly_detected: Whether local anomaly was detected.

        Returns:
            True if published successfully, False if Redis unavailable.
        """
        if self._redis is None:
            logger.debug("peer_monitor.publish.skip", reason="no_redis")
            return False

        message = {
            "sender": self.instance_name,
            "type": "drift_signature_update",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signature_vector": signature.vector,
            "cos_sim_vs_baseline": round(cosine_vs_baseline, 4),
            "anomaly_detected": anomaly_detected,
        }

        try:
            pubsub = self._redis.pubsub()
            # Use the publish channel.
            self._redis.publish(self.publish_channel, json.dumps(message))
            self._publish_count += 1
            logger.debug(
                "peer_monitor.published",
                channel=self.publish_channel,
                publish_count=self._publish_count,
            )
            return True
        except (ConnectionError, TimeoutError, OSError) as exc:
            logger.warning(
                "peer_monitor.publish.failed",
                error=str(exc),
            )
            return False

    # ── receive ──────────────────────────────────────────────

    def receive_peer_signature(self, raw_message: str) -> float | None:
        """Process a received peer signature message.

        Computes cross-instance cosine similarity against own baseline
        to detect if the peer has drifted relative to our expectation.

        Args:
            raw_message: JSON string from Redis pub/sub.

        Returns:
            Cross-instance cosine similarity, or None if message invalid.
        """
        try:
            data = json.loads(raw_message)
        except (json.JSONDecodeError, TypeError):
            logger.warning("peer_monitor.receive.invalid_json")
            return None

        if data.get("type") != "drift_signature_update":
            logger.debug("peer_monitor.receive.unknown_type", type=data.get("type"))
            return None

        vector = data.get("signature_vector")
        if not isinstance(vector, list) or len(vector) != 32:
            logger.warning(
                "peer_monitor.receive.bad_vector",
                length=len(vector) if isinstance(vector, list) else "non-list",
            )
            return None

        self._peer_signature = BehaviorSignature(vector=vector)

        # For cross-instance comparison, we use the peer's raw signature.
        # Anomaly means the peer's behavior has diverged significantly
        # from what we last saw.
        if self._peer_signature is not None and self._baseline_for_peer is not None:
            self._last_peer_cosine = _cosine_similarity(
                self._peer_signature.vector,
                self._baseline_for_peer.vector,
            )
        elif self._peer_signature is not None:
            # First time seeing peer — establish baseline.
            self._last_peer_cosine = 1.0

        # Update peer baseline (EWMA-style).
        if self._peer_signature is not None:
            if self._baseline_for_peer is None:
                self._baseline_for_peer = BehaviorSignature(
                    vector=list(self._peer_signature.vector),
                )
            else:
                alpha = 0.15
                self._baseline_for_peer = BehaviorSignature(
                    vector=[
                        alpha * p + (1.0 - alpha) * b
                        for p, b in zip(
                            self._peer_signature.vector,
                            self._baseline_for_peer.vector,
                        )
                    ]
                )

        # Check anomaly.
        if self._last_peer_cosine < self.peer_anomaly_threshold:
            self._peer_anomaly_count += 1
            logger.warning(
                "peer_monitor.peer_anomaly",
                peer=self._peer_name,
                cosine=self._last_peer_cosine,
                threshold=self.peer_anomaly_threshold,
                peer_anomaly_count=self._peer_anomaly_count,
            )

        return self._last_peer_cosine

    # ── state ────────────────────────────────────────────────

    @property
    def peer_signature(self) -> BehaviorSignature | None:
        """The last received peer behavior signature."""
        return self._peer_signature

    @property
    def last_peer_cosine(self) -> float:
        """Cross-instance cosine similarity from last peer update."""
        return self._last_peer_cosine

    @property
    def peer_anomaly_count(self) -> int:
        """Total anomalies detected in peer behavior."""
        return self._peer_anomaly_count

    # Lazy-init peer baseline (set on first receive, initialized in __init__).

    # ── escalation ───────────────────────────────────────────

    def escalate_to_dao(self, proposal_context: dict[str, Any]) -> dict[str, Any]:
        """Create a Tier-4 DAO proposal for drift anomaly escalation.

        B10: DAO does NOT govern persona.  This is anomaly escalation
        to founders via DAO proposal, not persona governance.

        B40: If peer negotiation fails, escalate to DAO for society vote.

        Args:
            proposal_context: Context about the anomaly for the proposal.

        Returns:
            Proposal dict ready for M7 DAO propose().
        """
        proposal = {
            "type": "drift_anomaly_escalation",
            "tier": 4,
            "source": self.instance_name,
            "peer": self._peer_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "peer_anomaly_count": self._peer_anomaly_count,
            "last_peer_cosine": round(self._last_peer_cosine, 4),
            "context": proposal_context,
            "resolution_mode": "founder_2_of_2",
        }
        logger.info(
            "peer_monitor.dao_escalation",
            proposal_type=proposal["type"],
            peer=self._peer_name,
        )
        return proposal


# ── wire function ────────────────────────────────────────────


def wire(
    agent: Any,
    redis_client: Any | None = None,
) -> PeerMonitor:
    """Attach a PeerMonitor to an agent instance.

    The parent calls this from agent_init.py (appends-only block).
    We do NOT edit agent_init.py.

    Args:
        agent: The agent instance (must accept arbitrary attributes).
        redis_client: Optional Redis client (None = fail-soft per D2).

    Returns:
        The created PeerMonitor instance.
    """
    instance_name = getattr(agent, "_instance_name", "guinevere")
    monitor = PeerMonitor(
        instance_name=instance_name,
        redis_client=redis_client,
    )
    agent._peer_monitor = monitor
    logger.info("peer_monitor.wire.complete", instance=instance_name)
    return monitor
