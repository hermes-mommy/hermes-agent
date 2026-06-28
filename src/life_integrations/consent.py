"""P22 consent enforcement.

Integrates with Guinevere's existing consent ledger and HARD STOP handler.
Every L2+ action must pass consent check + HARD STOP check before execution.

Consent revocation is absolute — no autonomy bypass (AGENTS.md §0.1).
"""

from __future__ import annotations

import uuid
from typing import Any, Protocol

import structlog

from src.life_integrations.types import PermissionTier

logger = structlog.get_logger(__name__)


class ConsentCheckerProtocol(Protocol):
    """Protocol for consent checking (mirrors existing consent_ledger API)."""

    async def check_consent(
        self,
        scope: str,
        project_id: uuid.UUID | None = None,
    ) -> bool:
        """Check if consent is granted for a scope.

        Args:
            scope: Consent scope (e.g., "consent.comms.discord.write").
            project_id: Optional project UUID for scoping.

        Returns:
            True if consent is granted, False if revoked or not granted.
        """
        ...


class HardStopCheckerProtocol(Protocol):
    """Protocol for HARD STOP checking (mirrors existing HardStopHandler)."""

    def is_hard_stop_active(self) -> bool:
        """Check if HARD STOP is currently active.

        Returns:
            True if HARD STOP is active (all L2+ actions blocked).
        """
        ...


class ConsentGate:
    """Consent enforcement gate for P22 integration actions.

    Wraps consent checking and HARD STOP checking into a single gate that
    all L2+ actions must pass before execution.

    Usage:
        gate = ConsentGate(consent_checker, hard_stop_checker)
        allowed, reason = await gate.check(
            tier=PermissionTier.L2_WRITE,
            consent_scope="consent.comms.discord.write",
            project_id=project_id,
        )
        if not allowed:
            raise PermissionError(reason)
    """

    def __init__(
        self,
        consent_checker: ConsentCheckerProtocol | None = None,
        hard_stop_checker: HardStopCheckerProtocol | None = None,
    ) -> None:
        """Initialize the consent gate.

        Args:
            consent_checker: Consent ledger checker (optional, fail-closed if None).
            hard_stop_checker: HARD STOP handler (optional, fail-closed for L2+
                if None — a missing HARD STOP checker cannot be safely treated
                as "clear"; we close the fail-open asymmetry that previously
                let a missing checker silently skip HARD STOP for L2/L3).
        """
        self._consent_checker = consent_checker
        self._hard_stop_checker = hard_stop_checker

    async def check(
        self,
        tier: PermissionTier,
        consent_scope: str,
        project_id: uuid.UUID | None = None,
    ) -> tuple[bool, str]:
        """Check if an action is allowed by consent + HARD STOP gates.

        Args:
            tier: Required permission tier.
            consent_scope: Consent scope to check.
            project_id: Optional project UUID for scoping.

        Returns:
            Tuple of (allowed, reason).
        """
        # L1 (read) passes without consent/HARD STOP check
        if tier == PermissionTier.L1_READ:
            return True, "L1 read — no consent required"

        # L4 is always forbidden — unconditionally, regardless of whether a
        # HARD STOP checker is configured. Checked BEFORE the fail-closed
        # branch so L4 reports its dedicated "never autonomous" reason rather
        # than the generic "no hard_stop_checker" reason (both deny; L4's
        # reason is more specific and informative).
        if tier == PermissionTier.L4_FORBIDDEN:
            logger.warning(
                "consent_gate.forbidden",
                tier=tier.name,
                scope=consent_scope,
            )
            return False, "L4_FORBIDDEN — never autonomous"

        # Fail-closed: if no HARD STOP checker is configured, L2/L3 actions are
        # denied. L1 passed above; L4 was handled above (always forbidden).
        # This closes the fail-open asymmetry where a missing checker silently
        # skipped HARD STOP checks for L2/L3 (audit finding F03 — CRITICAL).
        if self._hard_stop_checker is None and tier >= PermissionTier.L2_WRITE:
            logger.warning(
                "consent_gate.no_hard_stop_checker_fail_closed",
                tier=tier.name,
                scope=consent_scope,
            )
            return False, "hard_stop_checker not configured — fail-closed"

        # HARD STOP check (blocks all L2+ when checker is present)
        if self._hard_stop_checker is not None:
            if self._hard_stop_checker.is_hard_stop_active():
                logger.warning(
                    "consent_gate.hard_stop_blocked",
                    tier=tier.name,
                    scope=consent_scope,
                )
                return False, "HARD STOP active — action blocked"

        # L2+ requires consent check (fail-closed if no checker)
        if tier >= PermissionTier.L2_WRITE:
            if self._consent_checker is None:
                logger.warning(
                    "consent_gate.no_checker_fail_closed",
                    tier=tier.name,
                    scope=consent_scope,
                )
                return False, "no consent checker configured — fail-closed"

            consented = await self._consent_checker.check_consent(
                scope=consent_scope,
                project_id=project_id,
            )
            if not consented:
                logger.warning(
                    "consent_gate.consent_revoked",
                    tier=tier.name,
                    scope=consent_scope,
                )
                return False, f"consent not granted for scope: {consent_scope}"

        return True, "allowed"

    async def check_bulk(
        self,
        actions: list[tuple[PermissionTier, str]],
        project_id: uuid.UUID | None = None,
    ) -> list[tuple[bool, str]]:
        """Check multiple actions at once.

        Args:
            actions: List of (tier, consent_scope) tuples.
            project_id: Optional project UUID for scoping.

        Returns:
            List of (allowed, reason) tuples, one per action.
        """
        results: list[tuple[bool, str]] = []
        for tier, scope in actions:
            allowed, reason = await self.check(
                tier=tier,
                consent_scope=scope,
                project_id=project_id,
            )
            results.append((allowed, reason))
        return results
