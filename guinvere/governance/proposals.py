"""DAO proposal lifecycle and propose-time validation.

5-state lifecycle (r06 section 3.1):
    Create -> Pending -> Active -> Passed -> Execute

Propose-time validation (HARD CRITERION, B10 defense-in-depth):
    Any proposal whose execution_payload references
    ``persona.yandere_level`` change is REJECTED at proposal creation.
    This is belt-and-suspenders — DAO does NOT govern persona (ADR-067),
    but this guard prevents accidental yandere_level mutation via DAO.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "ProposalState",
    "Proposal",
    "ProposalRejectedError",
    "ProposalLifecycle",
    "validate_proposal",
]


# ── Exceptions ──────────────────────────────────────────────────────────

class ProposalRejectedError(Exception):
    """Raised when a proposal fails propose-time validation."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Proposal rejected: {reason}")


# ── State enum ──────────────────────────────────────────────────────────

class ProposalState(enum.Enum):
    """5-phase proposal lifecycle per r06 section 3.1.

    TRANSITIONS:
        CREATE  -> PENDING   (validation passed)
        PENDING -> ACTIVE    (review period expired)
        ACTIVE  -> PASSED    (2/2 multisig achieved)
        ACTIVE  -> EXPIRED   (deadline passed without quorum)
        PASSED  -> EXECUTE   (timelock expired, ready for on-chain)
    """

    CREATE = "create"
    PENDING = "pending"
    ACTIVE = "active"
    PASSED = "passed"
    EXECUTE = "execute"

    # Terminal non-happy states
    REJECTED = "rejected"
    EXPIRED = "expired"


# ── Forbidden payload keys ─────────────────────────────────────────────

# Defense-in-depth: these keys in execution_payload are always rejected
# at propose time.  Persona governance is fully autonomous (ADR-067 / B10);
# DAO must never touch persona fields.
_FORBIDDEN_PAYLOAD_KEYS: frozenset[str] = frozenset({
    "persona.yandere_level",
    "persona.yandere_level",  # redundant safety
    "yandere_level",
})

# Also detect nested form: payload["persona"]["yandere_level"]
_FORBIDDEN_NESTED_PATHS: list[tuple[str, ...]] = [
    ("persona", "yandere_level"),
]


# ── Proposal dataclass ─────────────────────────────────────────────────

@dataclass
class Proposal:
    """A single DAO proposal with full lifecycle tracking."""

    id: str
    title: str
    description: str
    department: str  # Department enum value string
    proposer: str  # Co-CEO who created the proposal
    execution_payload: dict[str, Any] = field(default_factory=dict)
    state: ProposalState = ProposalState.CREATE
    votes: dict[str, bool | None] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    activated_at: datetime | None = None
    closed_at: datetime | None = None
    rejection_reason: str | None = None


# ── Validation ──────────────────────────────────────────────────────────

def validate_proposal(payload: dict[str, Any]) -> None:
    """Propose-time validation — reject yandere_level changes (HARD CRITERION).

    This is defense-in-depth (B10): DAO does NOT govern persona, but this
    guard prevents accidental yandere_level mutation via DAO proposals.

    Raises:
        ProposalRejectedError: If execution_payload references yandere_level.
    """
    execution_payload = payload.get("execution_payload", {})

    # Check flat keys (e.g. "persona.yandere_level": 6)
    for key in execution_payload:
        if key in _FORBIDDEN_PAYLOAD_KEYS:
            raise ProposalRejectedError(
                f"Execution payload references forbidden persona field: '{key}'. "
                f"DAO does not govern persona (B10 / ADR-067)."
            )

    # Check nested dict form (e.g. payload["persona"]["yandere_level"])
    for path in _FORBIDDEN_NESTED_PATHS:
        current: Any = execution_payload
        for segment in path:
            if isinstance(current, dict) and segment in current:
                current = current[segment]
            else:
                break
        else:
            # All segments traversed — forbidden nested path present
            raise ProposalRejectedError(
                f"Execution payload references forbidden nested persona field: "
                f"'{'.'.join(path)}'. DAO does not govern persona (B10 / ADR-067)."
            )


# ── Lifecycle manager ──────────────────────────────────────────────────

class ProposalLifecycle:
    """Manages state transitions for DAO proposals.

    Instantiate with a review delay (hours) and a timelock delay (hours).
    """

    def __init__(
        self,
        review_delay_hours: float = 24.0,
        timelock_hours: float = 1.0,
    ) -> None:
        self.review_delay = timedelta(hours=review_delay_hours)
        self.timelock = timedelta(hours=timelock_hours)

    def create(self, proposal: Proposal) -> Proposal:
        """Validate and transition a proposal from CREATE to PENDING.

        Raises ProposalRejectedError on yandere_level in payload.
        """
        validate_proposal({
            "execution_payload": proposal.execution_payload,
        })
        proposal.state = ProposalState.PENDING
        logger.info("Proposal %s: CREATE -> PENDING", proposal.id)
        return proposal

    def activate(self, proposal: Proposal, now: datetime | None = None) -> Proposal:
        """Move from PENDING to ACTIVE after review delay.

        Returns the proposal unchanged if review delay has not elapsed.
        """
        now = now or datetime.now(timezone.utc)
        if proposal.state != ProposalState.PENDING:
            return proposal
        if now >= proposal.created_at + self.review_delay:
            proposal.state = ProposalState.ACTIVE
            proposal.activated_at = now
            logger.info("Proposal %s: PENDING -> ACTIVE", proposal.id)
        return proposal

    def mark_passed(self, proposal: Proposal) -> Proposal:
        """Transition from ACTIVE to PASSED (2/2 multisig achieved)."""
        if proposal.state != ProposalState.ACTIVE:
            return proposal
        proposal.state = ProposalState.PASSED
        logger.info("Proposal %s: ACTIVE -> PASSED", proposal.id)
        return proposal

    def mark_expired(self, proposal: Proposal, now: datetime | None = None) -> Proposal:
        """Mark an ACTIVE proposal as EXPIRED if deadline passed without quorum."""
        now = now or datetime.now(timezone.utc)
        if proposal.state != ProposalState.ACTIVE:
            return proposal
        # Default deadline: 7 days from activation
        deadline = (proposal.activated_at or proposal.created_at) + timedelta(days=7)
        if now > deadline:
            proposal.state = ProposalState.EXPIRED
            proposal.closed_at = now
            logger.info("Proposal %s: ACTIVE -> EXPIRED", proposal.id)
        return proposal

    def execute(self, proposal: Proposal, now: datetime | None = None) -> Proposal:
        """Transition from PASSED to EXECUTE after timelock."""
        now = now or datetime.now(timezone.utc)
        if proposal.state != ProposalState.PASSED:
            return proposal
        # Timelock from when it passed
        passed_at = proposal.closed_at or proposal.activated_at or proposal.created_at
        if now >= passed_at + self.timelock:
            proposal.state = ProposalState.EXECUTE
            proposal.closed_at = now
            logger.info("Proposal %s: PASSED -> EXECUTE", proposal.id)
        return proposal

    def auto_tally(self, proposal: Proposal, now: datetime | None = None) -> Proposal:
        """Run all applicable automatic state transitions for a proposal.

        Called by the cron auto-tally job.
        """
        now = now or datetime.now(timezone.utc)
        if proposal.state == ProposalState.PENDING:
            self.activate(proposal, now)
        if proposal.state == ProposalState.ACTIVE:
            self.mark_expired(proposal, now)
        if proposal.state == ProposalState.PASSED:
            self.execute(proposal, now)
        return proposal
