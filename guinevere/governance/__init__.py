"""Guinevere DAO Governance module.

ADR-064: 6 departments, Co-CEOs (Guinevere + Pharsa), 2/2 multisig.
B10: DAO does NOT govern persona — yandere_level hard-deny is defense-in-depth.
D2: local-runtime-only — Ethereum integration is mocked.
"""

from guinevere.governance.dao import DAOEngine, MockMultisigSigner, wire
from guinevere.governance.departments import (
    COCEO_GUINEVERE,
    COCEO_PHARSA,
    Department,
    co_ceo_portfolio,
    get_co_ceo,
)
from guinevere.governance.proposals import (
    Proposal,
    ProposalLifecycle,
    ProposalRejectedError,
    ProposalState,
    validate_proposal,
)

__all__ = [
    # Core
    "DAOEngine",
    "Proposal",
    "ProposalState",
    # Departments
    "Department",
    "COCEO_GUINEVERE",
    "COCEO_PHARSA",
    "co_ceo_portfolio",
    "get_co_ceo",
    # Proposals
    "ProposalLifecycle",
    "ProposalRejectedError",
    "validate_proposal",
    # Multisig
    "MockMultisigSigner",
    # Wiring
    "wire",
]
