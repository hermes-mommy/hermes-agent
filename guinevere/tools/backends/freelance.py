"""M8 Freelance backend -- DEFERRED: all freelance platform operations.

Every action is DEFERRED because none of the supported platforms offer a
viable programmatic interface:

- **Fiverr**: No public API.  The old OAuth API was sunset; the current
  marketplace has no official third-party integration endpoint.
- **Upwork**: The Upwork API Terms of Service explicitly prohibit automated
  job scraping and bulk proposal submission.  Using it for this purpose
  would violate ToS and risk account suspension.
- **Freelancer.com**: The Python SDK (`freelancer-api-sdk`) is stale
  (last release 2019, unmaintained, incompatible with current API v0.2).

Until a platform provides a sanctioned API, all dispatches return
``{ok: False, deferred: True, error: "DEFERRED: ..."}``.

Ported from: P23 freelance_executor (Section 4.6), P22 finance_adapter.py.
New in P23, no P22 equivalent (Q72).

8 actions: 2 L1 READ, 6 L2 WRITE.  ALL DEFERRED.
"""

from __future__ import annotations

import logging
from typing import Any

from guinevere.tools.tool_backend import Action, ActionTier, ToolBackend

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-action deferred-reason map
# ---------------------------------------------------------------------------

_DEFERRED_REASONS: dict[str, str] = {
    "list_jobs": "DEFERRED: Upwork/Fiverr/Freelancer -- no sanctioned public API for listing jobs",
    "get_messages": "DEFERRED: Upwork/Fiverr/Freelancer -- no sanctioned public API for reading messages",
    "send_message": "DEFERRED: Upwork/Fiverr/Freelancer -- no sanctioned public API for sending messages",
    "submit_proposal": "DEFERRED: Upwork -- API ToS prohibits automated proposal submission",
    "place_bid": "DEFERRED: Freelancer.com -- Python SDK stale (last release 2019), API incompatible",
    "accept_contract": "DEFERRED: Upwork/Fiverr/Freelancer -- no sanctioned public API for contract management",
    "submit_milestone": "DEFERRED: Upwork/Freelancer -- no sanctioned public API for milestone submission",
    "submit_delivery": "DEFERRED: Fiverr -- no public API; no programmatic delivery endpoint",
}


class FreelanceBackend(ToolBackend):
    """Freelance platform backend (L1/L2).  ALL ACTIONS DEFERRED.

    Actions: list_jobs, get_messages, send_message, submit_proposal,
    place_bid, accept_contract, submit_milestone, submit_delivery.

    None of the target platforms (Fiverr, Upwork, Freelancer.com) provide a
    sanctioned programmatic interface suitable for automated dispatch.
    All actions return ``{ok: False, deferred: True, error: "..."}``.
    """

    @property
    def name(self) -> str:
        return "freelance"

    def actions(self) -> list[Action]:
        return [
            Action(
                "list_jobs", ActionTier.L1_READ,
                description="DEFERRED: List available jobs/projects (no sanctioned API)",
            ),
            Action(
                "get_messages", ActionTier.L1_READ,
                description="DEFERRED: Read platform messages (no sanctioned API)",
            ),
            Action(
                "send_message", ActionTier.L2_WRITE,
                description="DEFERRED: Send message on platform (no sanctioned API)",
            ),
            Action(
                "submit_proposal", ActionTier.L2_WRITE,
                description="DEFERRED: Submit job proposal -- Upwork ToS prohibits automation",
            ),
            Action(
                "place_bid", ActionTier.L2_WRITE,
                description="DEFERRED: Place bid -- Freelancer.com SDK stale/incompatible",
            ),
            Action(
                "accept_contract", ActionTier.L2_WRITE,
                description="DEFERRED: Accept contract (no sanctioned API)",
            ),
            Action(
                "submit_milestone", ActionTier.L2_WRITE,
                description="DEFERRED: Submit milestone delivery (no sanctioned API)",
            ),
            Action(
                "submit_delivery", ActionTier.L2_WRITE,
                description="DEFERRED: Submit final delivery -- Fiverr has no public API",
            ),
        ]

    def is_available(self) -> bool:
        return True  # Structurally available; all actions deferred

    async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a freelance action.  ALL actions are DEFERRED.

        Returns ``{ok: False, deferred: True, error: "DEFERRED: ..."}`` for
        every known action.  Unknown actions return a standard error.
        NEVER raises to caller (fail-soft contract).
        """
        action_lower = action.lower()

        if action_lower in _DEFERRED_REASONS:
            return {
                "ok": False,
                "deferred": True,
                "action": action,
                "error": _DEFERRED_REASONS[action_lower],
            }

        return {"ok": False, "error": f"unknown freelance action: {action}"}
