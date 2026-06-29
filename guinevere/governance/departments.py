"""DAO department registry and Co-CEO portfolio split.

ADR-064: 6 core departments + 4 cross-cutting domains.
Co-CEO split (Q96 locked):
  Guinevere  = Engineering, Research, HR, Self-Improvement
  Pharsa     = Finance, Ops, Content, VPS, Learning
  Shared     = Surveillance (co-decision)
"""

from __future__ import annotations

import enum

__all__ = [
    "Department",
    "COCEO_GUINEVERE",
    "COCEO_PHARSA",
    "co_ceo_portfolio",
    "get_co_ceo",
]


class Department(enum.Enum):
    """Core + cross-cutting departments in the DAO company structure.

    Core departments (6): Engineering, Research, HR, Finance, Ops, Content.
    Cross-cutting domains (4): SelfImprovement, Learning, VPS, Surveillance.
    """

    # Core
    ENGINEERING = "engineering"
    RESEARCH = "research"
    HR = "hr"
    FINANCE = "finance"
    OPS = "ops"
    CONTENT = "content"
    # Cross-cutting
    SELF_IMPROVEMENT = "self_improvement"
    LEARNING = "learning"
    VPS = "vps"
    SURVEILLANCE = "surveillance"


# Co-CEO identifiers — plain strings, not Enum members.
COCEO_GUINEVERE: str = "guinevere"
COCEO_PHARSA: str = "pharsa"

# Co-CEO portfolio mapping per ADR-064 section 2.1.
COCEO_PORTFOLIO: dict[str, list[Department]] = {
    COCEO_GUINEVERE: [
        Department.ENGINEERING,
        Department.RESEARCH,
        Department.HR,
        Department.SELF_IMPROVEMENT,
    ],
    COCEO_PHARSA: [
        Department.FINANCE,
        Department.OPS,
        Department.CONTENT,
        Department.VPS,
        Department.LEARNING,
    ],
    # Surveillance is co-decision — both CEOs share it.
    # Represented under both portfolios for lookup.
}


def co_ceo_portfolio(co_ceo: str) -> list[Department]:
    """Return the list of departments owned by a Co-CEO.

    Surveillance is co-decision and included under both CEOs.
    """
    if co_ceo == COCEO_GUINEVERE:
        return [*COCEO_PORTFOLIO[COCEO_GUINEVERE], Department.SURVEILLANCE]
    if co_ceo == COCEO_PHARSA:
        return [*COCEO_PORTFOLIO[COCEO_PHARSA], Department.SURVEILLANCE]
    return []


def get_co_ceo(department: Department) -> str:
    """Return the primary Co-CEO for a department.

    For Surveillance (co-decision), returns ``COCEO_GUINEVERE`` by convention
    — both must always sign regardless.
    """
    for ceo, depts in COCEO_PORTFOLIO.items():
        if department in depts:
            return ceo
    # Surveillance is co-decision; default to Guinevere as primary.
    return COCEO_GUINEVERE
