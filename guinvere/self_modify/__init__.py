"""M10 Self-Modification module.

Re-exports the public API:
  - MutationEngine (5-tier mutability ladder)
  - MutabilityTier (T1-T5 enum)
  - wire (agent attachment)
"""

from guinevere.self_modify.mutation import (
    DRIFT_THRESHOLD,
    MutabilityTier,
    MutationEngine,
    MutationRequest,
    MutationStatus,
    PromotionResult,
    RatchetFloor,
    RatchetViolationError,
    TierAbolishedError,
    restart_required,
    wire,
)

__all__ = [
    "DRIFT_THRESHOLD",
    "MutabilityTier",
    "MutationEngine",
    "MutationRequest",
    "MutationStatus",
    "PromotionResult",
    "RatchetFloor",
    "RatchetViolationError",
    "TierAbolishedError",
    "restart_required",
    "wire",
]
