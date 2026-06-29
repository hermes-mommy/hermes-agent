"""Guinevere production infrastructure.

Provides:
  - CircuitBreakerSet: 6 circuit breakers with CLOSED/OPEN/HALF_OPEN states
  - BreakerState: 3-state circuit breaker enum
  - TailscaleHardener: VPS hardening script generator (D2 local-only)
  - AutoRecovery: restart-on-crash design (D2 local-only)
  - wire: agent initialization hook

D2 COMPLIANCE: Tailscale and recovery are design-only — no live VPS deploy.
"""

from guinevere.production.circuit_breakers import (
    BreakerState,
    CircuitBreakerOpenError,
    CircuitBreakerSet,
    CircuitBreaker,
    CostExplosionBreaker,
    InfiniteLoopBreaker,
    HallucinationSpiralBreaker,
    EmotionalFixationBreaker,
    DreamFloodingBreaker,
    SubAgentExplosionBreaker,
)
from guinevere.production.tailscale import TailscaleHardener
from guinevere.production.recovery import AutoRecovery, wire

__all__ = [
    "BreakerState",
    "CircuitBreakerOpenError",
    "CircuitBreakerSet",
    "CircuitBreaker",
    "CostExplosionBreaker",
    "InfiniteLoopBreaker",
    "HallucinationSpiralBreaker",
    "EmotionalFixationBreaker",
    "DreamFloodingBreaker",
    "SubAgentExplosionBreaker",
    "TailscaleHardener",
    "AutoRecovery",
    "wire",
]
