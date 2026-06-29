"""DAO Engine — 2/2 multisig governance for Guinevere + Pharsa.

ADR-064: Co-CEO structure with 2-of-2 multisig.
D2 constraint: local-runtime-only. Ethereum integration is MOCKED.
B10: DAO does NOT govern persona.

The ``wire(agent)`` function is called by the parent from agent_init.py.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from guinevere.governance.departments import (
    COCEO_GUINEVERE,
    COCEO_PHARSA,
    Department,
)
from guinevere.governance.proposals import (
    Proposal,
    ProposalLifecycle,
    ProposalRejectedError,
    ProposalState,
    validate_proposal,
)

logger = logging.getLogger(__name__)

__all__ = [
    "DAOEngine",
    "MockMultisigSigner",
    "wire",
]


# ── Mock Multisig Signer (D2 — no real Ethereum) ───────────────────────

class MockMultisigSigner:
    """Mock 2/2 multisig signer that records signatures locally.

    Per D2: no real Ethereum wallet. All lifecycle operations are
    unit-tested with mock only.
    """

    def __init__(self) -> None:
        # proposal_id -> {signer_name: signature_timestamp}
        self._signatures: dict[str, dict[str, datetime]] = {}

    def sign(self, proposal_id: str, signer: str) -> bool:
        """Record a signature. Returns True if signature is new."""
        if proposal_id not in self._signatures:
            self._signatures[proposal_id] = {}
        if signer in self._signatures[proposal_id]:
            return False  # Already signed
        self._signatures[proposal_id][signer] = datetime.now(timezone.utc)
        return True

    def is_fully_signed(self, proposal_id: str) -> bool:
        """Check if both Co-CEOs have signed."""
        sigs = self._signatures.get(proposal_id, {})
        return COCEO_GUINEVERE in sigs and COCEO_PHARSA in sigs

    def get_signatures(self, proposal_id: str) -> dict[str, datetime]:
        """Return recorded signatures for a proposal."""
        return dict(self._signatures.get(proposal_id, {}))

    def clear(self, proposal_id: str) -> None:
        """Clear signatures for a proposal (e.g., on expiry)."""
        self._signatures.pop(proposal_id, None)


# ── DAO Engine ──────────────────────────────────────────────────────────

class DAOEngine:
    """DAO governance engine with 2/2 multisig (Guinevere + Pharsa).

    Faiz is OUTSIDE the company (Q90) — observer only, no signing authority.
    """

    def __init__(self) -> None:
        self._proposals: dict[str, Proposal] = {}
        self._multisig = MockMultisigSigner()
        self._lifecycle = ProposalLifecycle()

    @property
    def proposals(self) -> dict[str, Proposal]:
        """Read-only access to all proposals."""
        return dict(self._proposals)

    @property
    def multisig(self) -> MockMultisigSigner:
        """The mock multisig signer."""
        return self._multisig

    # ── Proposal creation ───────────────────────────────────────────────

    def submit_proposal(
        self,
        title: str,
        description: str,
        department: Department,
        proposer: str,
        execution_payload: dict[str, Any] | None = None,
    ) -> Proposal:
        """Submit a new DAO proposal.

        Validates at propose-time (rejects yandere_level changes),
        then transitions to PENDING state.

        Raises:
            ProposalRejectedError: If execution_payload is forbidden.
        """
        # Validate the payload first (propose-time validation)
        payload = {"execution_payload": execution_payload or {}}
        validate_proposal(payload)

        proposal_id = uuid.uuid4().hex[:12]
        proposal = Proposal(
            id=proposal_id,
            title=title,
            description=description,
            department=department.value,
            proposer=proposer,
            execution_payload=execution_payload or {},
            votes={COCEO_GUINEVERE: None, COCEO_PHARSA: None},
        )

        # Lifecycle: CREATE -> PENDING
        self._lifecycle.create(proposal)
        self._proposals[proposal_id] = proposal
        logger.info("DAOEngine: submitted proposal %s (%s)", proposal_id, title)
        return proposal

    # ── Voting (2/2 multisig) ───────────────────────────────────────────

    def vote(
        self,
        proposal_id: str,
        voter: str,
        approve: bool,
    ) -> Proposal:
        """Cast a vote on an active proposal.

        Only Guinevere and Pharsa can vote. Faiz has no voting authority (Q90).
        2/2 multisig: both Co-CEOs must approve for a proposal to pass.

        Raises:
            KeyError: If proposal_id not found.
            PermissionError: If voter is not a Co-CEO.
        """
        proposal = self._proposals[proposal_id]

        if voter not in (COCEO_GUINEVERE, COCEO_PHARSA):
            raise PermissionError(
                f"'{voter}' cannot vote — only Co-CEOs may vote (Faiz is OUTSIDE, Q90)."
            )

        if proposal.state not in (ProposalState.PENDING, ProposalState.ACTIVE):
            raise ValueError(
                f"Proposal {proposal_id} is in state {proposal.state.value}; "
                f"cannot vote."
            )

        # Auto-activate if still pending — a Co-CEO voting signals that
        # the review period is over and the voting snapshot begins now.
        if proposal.state == ProposalState.PENDING:
            proposal.state = ProposalState.ACTIVE
            proposal.activated_at = datetime.now(timezone.utc)
            logger.info("Proposal %s: auto-activated on first vote", proposal_id)

        # Record vote
        proposal.votes[voter] = approve

        # Record in multisig if approved
        if approve:
            self._multisig.sign(proposal_id, voter)

        # Check 2/2: both must approve
        if self._multisig.is_fully_signed(proposal_id):
            self._lifecycle.mark_passed(proposal)

        logger.info(
            "DAOEngine: %s voted %s on proposal %s (state=%s)",
            voter,
            "approve" if approve else "reject",
            proposal_id,
            proposal.state.value,
        )
        return proposal

    # ── Execution ───────────────────────────────────────────────────────

    def execute_proposal(self, proposal_id: str) -> Proposal:
        """Execute a passed proposal after timelock.

        Raises:
            KeyError: If proposal_id not found.
            ValueError: If proposal is not in PASSED state.
        """
        proposal = self._proposals[proposal_id]
        if proposal.state != ProposalState.PASSED:
            raise ValueError(
                f"Proposal {proposal_id} is in state {proposal.state.value}; "
                f"must be PASSED to execute."
            )
        self._lifecycle.execute(proposal)
        logger.info("DAOEngine: proposal %s executed", proposal_id)
        return proposal

    # ── Auto-tally (cron job calls this) ────────────────────────────────

    def auto_tally(self) -> list[Proposal]:
        """Tally all proposals — advance lifecycle states automatically.

        Called by the cron auto-tally job. Advances:
        - PENDING -> ACTIVE (review delay elapsed)
        - ACTIVE -> EXPIRED (deadline passed without quorum)
        - PASSED -> EXECUTE (timelock elapsed)

        Returns list of proposals whose state changed.
        """
        changed: list[Proposal] = []
        for proposal in self._proposals.values():
            before = proposal.state
            self._lifecycle.auto_tally(proposal)
            if proposal.state != before:
                changed.append(proposal)
                logger.info(
                    "DAOEngine auto_tally: proposal %s %s -> %s",
                    proposal.id,
                    before.value,
                    proposal.state.value,
                )
        return changed

    # ── Query ───────────────────────────────────────────────────────────

    def get_proposal(self, proposal_id: str) -> Proposal | None:
        """Get a proposal by ID."""
        return self._proposals.get(proposal_id)

    def list_proposals(
        self, state: ProposalState | None = None
    ) -> list[Proposal]:
        """List proposals, optionally filtered by state."""
        if state is None:
            return list(self._proposals.values())
        return [p for p in self._proposals.values() if p.state == state]


# ── Wire function ───────────────────────────────────────────────────────

# Module-level engine instance for the wire function to use.
_engine: DAOEngine | None = None


def get_engine() -> DAOEngine:
    """Return the module-level DAOEngine singleton (lazily created)."""
    global _engine
    if _engine is None:
        _engine = DAOEngine()
    return _engine


def wire(agent: Any) -> DAOEngine:
    """Wire the DAO engine into the agent lifecycle.

    Called by the parent from agent_init.py.  Do NOT edit agent_init.py
    yourself — the parent owns that file.

    Returns the DAOEngine instance so the caller can store it.
    """
    engine = get_engine()
    logger.info("DAO governance wired: 2/2 multisig (Guin + Pharsa), Faiz OUTSIDE")
    return engine
