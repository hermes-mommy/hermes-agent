"""Personality Drift — P24 M12.

Ground-up rewrite.  Zero code ported from guinvere/persona/ (C9).

Re-exports the public API:
  - BehaviorSignature (32-dim, cosine similarity, EWMA)
  - DriftDetector (0.68 hysteresis, monitoring-only)
  - PeerMonitor (saling Guin<->Pharsa, Redis g2p/p2g DB7)
"""

from guinevere.personality.drift import DriftDetector, wire as drift_wire
from guinevere.personality.monitor import PeerMonitor, wire as monitor_wire
from guinevere.personality.signature import BehaviorSignature

__all__ = [
    "BehaviorSignature",
    "DriftDetector",
    "PeerMonitor",
    "drift_wire",
    "monitor_wire",
]


def wire(agent: object, **kwargs: object) -> tuple[DriftDetector, PeerMonitor]:
    """Wire both DriftDetector and PeerMonitor to an agent.

    Convenience function.  Parent calls this from agent_init.py.
    We do NOT edit agent_init.py.

    Args:
        agent: The agent instance.

    Returns:
        Tuple of (DriftDetector, PeerMonitor).
    """
    detector = drift_wire(agent, **{k: v for k, v in kwargs.items() if k in ("threshold", "alpha")})
    monitor = monitor_wire(agent, **{k: v for k, v in kwargs.items() if k in ("redis_client",)})
    return detector, monitor
