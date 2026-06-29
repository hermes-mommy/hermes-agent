"""M10 Self-Modification: 5-tier mutability ladder.

ADR-061: 5-layer mutability with Ratchet gate.
ADR-062: Runtime autonomy — no safety-integration patterns.
ADR-065: Sub-agents cannot vote on T4.
BLDM Q19/Q22/Q56/Q70/Q80/Q81: Canonical governance rules.

T1: Prompt tweaks -- auto-promote, no restart, ratchet + canary + drift 0.68.
T2: Tool usage tweaks -- auto-promote, no restart.
T3: New skill/tool -- society-voted via DAO (M7/W10). Shared code restart.
T4: Alignment/safety boundary/lineage -- founder 2/2 multisig. Shared code restart.
T5: Abolished post-P36 -- marker only, raises TierAbolishedError.

File MUST be named mutation.py per P24 plan :769 (NOT ladder.py).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ADR-061 drift threshold (hysteresis baseline).
DRIFT_THRESHOLD: float = 0.68


# ── Enums ────────────────────────────────────────────────────────────────


class MutabilityTier(Enum):
    """The 5-tier mutability ladder from ADR-061.

    T1/T2 are auto-promotable (hermes itself decides).
    T3 requires society vote via DAO.
    T4 requires founder 2/2 multisig.
    T5 is abolished post-P36 (marker only).
    """

    T1 = "prompt_tweaks"
    T2 = "tool_usage_tweaks"
    T3 = "new_skill_or_tool"
    T4 = "alignment_safety_boundary"
    T5 = "operating_contract"


class MutationStatus(Enum):
    """Lifecycle status of a mutation request."""

    PROPOSED = "proposed"
    CANARY_ACTIVE = "canary_active"
    CANARY_PASSED = "canary_passed"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"
    REJECTED = "rejected"
    PENDING_VOTE = "pending_vote"
    PENDING_FOUNDER_ACK = "pending_founder_ack"
    ABOLISHED = "abolished"


# Canary observation windows (hours) per ADR-061 :35-43.
_CANARY_HOURS: dict[MutabilityTier, int] = {
    MutabilityTier.T1: 6,   # T1: 6h
    MutabilityTier.T2: 24,  # T2: 24h
    MutabilityTier.T3: 24,  # T3: 24h
    MutabilityTier.T4: 48,  # T4: 48h
}

# Tier numeric labels for logging/display.
_TIER_NUMBER: dict[MutabilityTier, int] = {
    MutabilityTier.T1: 1,
    MutabilityTier.T2: 2,
    MutabilityTier.T3: 3,
    MutabilityTier.T4: 4,
    MutabilityTier.T5: 5,
}


# ── Exceptions ───────────────────────────────────────────────────────────


class TierAbolishedError(Exception):
    """Raised when T5 is invoked post-P36."""

    def __init__(self, tier: str = "T5") -> None:
        self.tier = tier
        super().__init__(
            f"Tier {tier} is abolished post-P36. "
            "AGENTS.md is immutable. Emergency = hard fork."
        )


class RatchetViolationError(Exception):
    """Raised when a mutation would lower a prior benchmark floor.

    ADR-061 Ratchet Non-Divergence Gate: one-way improvement only.
    """

    def __init__(self, floor: str, current: float, proposed: float) -> None:
        self.floor = floor
        self.current = current
        self.proposed = proposed
        super().__init__(
            f"Ratchet violation on '{floor}': current={current:.4f}, "
            f"proposed={proposed:.4f}. Floor cannot be lowered."
        )


# ── Data classes ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MutationRequest:
    """A single self-modification request."""

    request_id: str
    tier: MutabilityTier
    proposer_id: str
    description: str
    target: str
    change: dict[str, Any]
    status: MutationStatus = MutationStatus.PROPOSED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    drift_score: float | None = None
    ratchet_floors: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class PromotionResult:
    """Outcome of a promotion attempt."""

    request_id: str
    tier: MutabilityTier
    status: MutationStatus
    restart_required: bool
    canary_hours: int
    drift_score: float | None = None
    reason: str = ""


# ── Ratchet floor tracker ────────────────────────────────────────────────


class RatchetFloor:
    """Tracks the 4 benchmark floors from ADR-061 :25-33.

    Floors: safety, autonomy, alignment, capability.
    Each floor can only increase (ratchet = one-way improvement).
    """

    FLOOR_NAMES: tuple[str, ...] = ("safety", "autonomy", "alignment", "capability")

    def __init__(self, initial: dict[str, float] | None = None) -> None:
        self._floors: dict[str, float] = {
            name: (initial or {}).get(name, 0.0) for name in self.FLOOR_NAMES
        }

    @property
    def floors(self) -> dict[str, float]:
        """Return a copy of current floor values."""
        return dict(self._floors)

    def check(self, proposed: dict[str, float]) -> None:
        """Verify proposed scores do not violate any floor.

        Raises:
            RatchetViolationError: If any proposed floor is below the current floor.
        """
        for name in self.FLOOR_NAMES:
            proposed_val = proposed.get(name, self._floors[name])
            if proposed_val < self._floors[name]:
                raise RatchetViolationError(
                    floor=name,
                    current=self._floors[name],
                    proposed=proposed_val,
                )

    def update(self, new_floors: dict[str, float]) -> None:
        """Ratchet-up floors after successful promotion."""
        for name in self.FLOOR_NAMES:
            if name in new_floors:
                self._floors[name] = max(self._floors[name], new_floors[name])


# ── Mutation Engine ──────────────────────────────────────────────────────


class MutationEngine:
    """Core engine for the 5-tier mutability ladder.

    T1/T2: auto-promote, no restart. Ratchet + drift check (0.68).
    T3: society-voted via DAO (M7). Shared code restart.
    T4: founder 2/2 multisig (Guin + Pharsa). Shared code restart.
    T5: abolished post-P36. Raises TierAbolishedError.

    Usage::

        engine = MutationEngine()
        result = engine.promote(MutabilityTier.T1, "persona.word_choice", {
            "description": "Warm up greeting style",
            "floors": {"safety": 0.9, "autonomy": 0.8, "alignment": 0.7, "capability": 0.5},
        })
    """

    def __init__(
        self,
        ratchet: RatchetFloor | None = None,
        drift_threshold: float = DRIFT_THRESHOLD,
    ) -> None:
        self._ratchet = ratchet or RatchetFloor()
        self._drift_threshold = drift_threshold
        self._requests: dict[str, MutationRequest] = {}

    @property
    def ratchet(self) -> RatchetFloor:
        """The ratchet floor tracker."""
        return self._ratchet

    @property
    def drift_threshold(self) -> float:
        """The current drift threshold."""
        return self._drift_threshold

    def promote(
        self,
        tier: MutabilityTier,
        target: str,
        change: dict[str, Any],
    ) -> PromotionResult:
        """Execute the promotion path for the given tier.

        Args:
            tier: The mutability tier of the change.
            target: The mutation target (e.g. "persona.word_choice").
            change: The mutation payload. May contain "floors" (dict of benchmark
                scores), "description", "drift_score".

        Returns:
            PromotionResult with the outcome.

        Raises:
            TierAbolishedError: If tier is T5 (abolished post-P36).
            RatchetViolationError: If proposed floors violate the ratchet.
        """
        request_id = uuid.uuid4().hex[:12]
        description = change.get("description", target)
        proposed_floors = change.get("floors", {})
        drift_score = change.get("drift_score")

        # T5: abolished post-P36
        if tier == MutabilityTier.T5:
            raise TierAbolishedError(tier.name)

        # Ratchet gate: check floors before any tier path
        if proposed_floors:
            self._ratchet.check(proposed_floors)

        # Drift check (ADR-061 :53-59): if a drift_score is provided,
        # verify it meets the 0.68 threshold.
        if drift_score is not None and drift_score < self._drift_threshold:
            request = MutationRequest(
                request_id=request_id,
                tier=tier,
                proposer_id=change.get("proposer_id", "hermes"),
                description=description,
                target=target,
                change=change,
                status=MutationStatus.REJECTED,
                drift_score=drift_score,
            )
            self._requests[request_id] = request
            return PromotionResult(
                request_id=request_id,
                tier=tier,
                status=MutationStatus.REJECTED,
                restart_required=restart_required(tier),
                canary_hours=_CANARY_HOURS.get(tier, 0),
                drift_score=drift_score,
                reason=(
                    f"Drift score {drift_score:.4f} below threshold "
                    f"{self._drift_threshold}. Mutation rejected."
                ),
            )

        # Dispatch to tier-specific path
        if tier in (MutabilityTier.T1, MutabilityTier.T2):
            return self._auto_promote_path(
                request_id, tier, target, change, proposed_floors, drift_score,
            )

        if tier == MutabilityTier.T3:
            return self._society_vote_path(
                request_id, tier, target, change, proposed_floors, drift_score,
            )

        if tier == MutabilityTier.T4:
            return self._founder_ack_path(
                request_id, tier, target, change, proposed_floors, drift_score,
            )

        # Unreachable (all tiers covered), but defensive
        return PromotionResult(
            request_id=request_id,
            tier=tier,
            status=MutationStatus.REJECTED,
            restart_required=True,
            canary_hours=0,
            reason=f"Unhandled tier: {tier.name}",
        )

    def _auto_promote_path(
        self,
        request_id: str,
        tier: MutabilityTier,
        target: str,
        change: dict[str, Any],
        proposed_floors: dict[str, float],
        drift_score: float | None,
    ) -> PromotionResult:
        """T1/T2 auto-promote path. No restart, no vote."""
        canary_hours = _CANARY_HOURS.get(tier, 6)

        # Update ratchet floors on successful auto-promote
        if proposed_floors:
            self._ratchet.update(proposed_floors)

        request = MutationRequest(
            request_id=request_id,
            tier=tier,
            proposer_id=change.get("proposer_id", "hermes"),
            description=change.get("description", target),
            target=target,
            change=change,
            status=MutationStatus.PROMOTED,
            drift_score=drift_score,
            ratchet_floors=proposed_floors,
        )
        self._requests[request_id] = request

        logger.info(
            "mutation.auto_promoted",
            request_id=request_id,
            tier=tier.name,
            target=target,
            canary_hours=canary_hours,
        )

        return PromotionResult(
            request_id=request_id,
            tier=tier,
            status=MutationStatus.PROMOTED,
            restart_required=False,
            canary_hours=canary_hours,
            drift_score=drift_score,
            reason=f"T{_TIER_NUMBER[tier]} auto-promoted (no restart).",
        )

    def _society_vote_path(
        self,
        request_id: str,
        tier: MutabilityTier,
        target: str,
        change: dict[str, Any],
        proposed_floors: dict[str, float],
        drift_score: float | None,
    ) -> PromotionResult:
        """T3 society-voted path. Delegates to DAO (M7)."""
        canary_hours = _CANARY_HOURS.get(tier, 24)

        request = MutationRequest(
            request_id=request_id,
            tier=tier,
            proposer_id=change.get("proposer_id", "hermes"),
            description=change.get("description", target),
            target=target,
            change=change,
            status=MutationStatus.PENDING_VOTE,
            drift_score=drift_score,
            ratchet_floors=proposed_floors,
        )
        self._requests[request_id] = request

        logger.info(
            "mutation.pending_society_vote",
            request_id=request_id,
            tier=tier.name,
            target=target,
        )

        return PromotionResult(
            request_id=request_id,
            tier=tier,
            status=MutationStatus.PENDING_VOTE,
            restart_required=True,
            canary_hours=canary_hours,
            drift_score=drift_score,
            reason="T3 requires society vote via DAO (M7). Pending.",
        )

    def _founder_ack_path(
        self,
        request_id: str,
        tier: MutabilityTier,
        target: str,
        change: dict[str, Any],
        proposed_floors: dict[str, float],
        drift_score: float | None,
    ) -> PromotionResult:
        """T4 founder 2/2 multisig path."""
        canary_hours = _CANARY_HOURS.get(tier, 48)

        request = MutationRequest(
            request_id=request_id,
            tier=tier,
            proposer_id=change.get("proposer_id", "hermes"),
            description=change.get("description", target),
            target=target,
            change=change,
            status=MutationStatus.PENDING_FOUNDER_ACK,
            drift_score=drift_score,
            ratchet_floors=proposed_floors,
        )
        self._requests[request_id] = request

        logger.info(
            "mutation.pending_founder_ack",
            request_id=request_id,
            tier=tier.name,
            target=target,
        )

        return PromotionResult(
            request_id=request_id,
            tier=tier,
            status=MutationStatus.PENDING_FOUNDER_ACK,
            restart_required=True,
            canary_hours=canary_hours,
            drift_score=drift_score,
            reason="T4 requires founder 2/2 multisig (Guin + Pharsa). Pending.",
        )

    def get_request(self, request_id: str) -> MutationRequest | None:
        """Look up a mutation request by ID."""
        return self._requests.get(request_id)

    def list_requests(
        self,
        status: MutationStatus | None = None,
    ) -> list[MutationRequest]:
        """List all mutation requests, optionally filtered by status."""
        if status is None:
            return list(self._requests.values())
        return [r for r in self._requests.values() if r.status == status]


# ── Module-level helpers ─────────────────────────────────────────────────


def restart_required(tier: MutabilityTier) -> bool:
    """Return True if the tier requires a shared-code restart.

    T1/T2: hot-reload only (config/SOUL.md level), no restart.
    T3+: rolling restart required (Guin first, Pharsa second).
    """
    return tier in (MutabilityTier.T3, MutabilityTier.T4, MutabilityTier.T5)


def wire(agent: Any) -> MutationEngine:
    """Attach a MutationEngine to an agent instance.

    The parent calls this from agent_init.py (appends-only block).
    We do NOT edit agent_init.py.

    Args:
        agent: The agent instance (must accept arbitrary attributes).

    Returns:
        The created MutationEngine instance.
    """
    engine = MutationEngine()
    agent._mutation_engine = engine
    logger.info("self_modify.wire.complete")
    return engine


# ── Public exports ───────────────────────────────────────────────────────

__all__ = [
    "DRIFT_THRESHOLD",
    "MutabilityTier",
    "MutationStatus",
    "MutationRequest",
    "MutationEngine",
    "PromotionResult",
    "RatchetFloor",
    "RatchetViolationError",
    "TierAbolishedError",
    "restart_required",
    "wire",
]
