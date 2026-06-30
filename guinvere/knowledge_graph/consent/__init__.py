"""Knowledge Graph consent framework (P16-008).

Public surface of the consent package. All callers (agent loop, ingestion
pipelines, admin tools) interact with the KG through these three classes:

* :class:`ConsentManager`  -- token generation, revocation, tombstoning,
  HARD STOP / DNR gates, and scope lookups.
* :class:`RLSPolicyManager` -- RLS policy apply / upgrade / verify.
* :class:`ConsentAuditor`   -- write-ahead audit trail for every consent
  mutation (write-ahead audit is MANDATORY; never share a transaction
  with the business mutation).

Invariants enforced by this package:

1. Every KG mutation writes a ``kg_consent_audit`` row in its OWN
   transaction BEFORE the business mutation lands (write-ahead audit).
2. Consent revocation is soft-delete only (``is_tombstoned = TRUE``);
   hard-delete is forbidden by FK constraints (``ON DELETE RESTRICT``).
3. ``KGConsentError`` is never swallowed by internal helpers; it
   propagates to the caller so consent failures are never silent.
4. All read/write goes through the ``session_factory`` (RLS principal
   is the database role; never bypass via superuser).
5. No module-level imports from ``src.memory`` -- safe-word indicators
   and DNR are resolved via lazy imports inside functions.
"""
from __future__ import annotations

from guinvere.knowledge_graph.consent.audit import (
    CONSENT_EVENT_TYPES,
    ConsentAuditor,
)
from guinvere.knowledge_graph.consent.manager import (
    ConsentManager,
    ConsentRevocationResult,
    ConsentScope,
)
from guinvere.knowledge_graph.consent.rls import RLSPolicyManager

__all__ = [
    "ConsentAuditor",
    "ConsentManager",
    "ConsentRevocationResult",
    "ConsentScope",
    "CONSENT_EVENT_TYPES",
    "RLSPolicyManager",
]
