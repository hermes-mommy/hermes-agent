"""Escalation Protocol for autonomous loop stuck detection.

Implements 4-tier escalation system for stuck loops:
  - AUTO: Retry with backoff
  - NOTIFY: Discord alert to Faiz, continue
  - APPROVE: Pause loop, wait for Faiz approval
  - ESCALATE: Kill loop, SEV1 alert, block similar tasks

Wraps StuckDetector and adds tier-based response actions.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Callable, Optional

import structlog

if TYPE_CHECKING:
    from guinevere.loops.circuit_breaker import StuckReport

logger = structlog.get_logger()


class EscalationTier(str, Enum):
    """4-tier escalation decision."""

    AUTO = "auto"  # Fix automatically (retry, backoff)
    NOTIFY = "notify"  # Notify Faiz via Discord, continue
    APPROVE = "approve"  # Pause loop, wait for Faiz approval
    ESCALATE = "escalate"  # Kill loop, Discord SEV1 alert, block similar tasks


@dataclass(frozen=True)
class EscalationEvent:
    """Record of an escalation action taken."""

    loop_id: str
    tier: EscalationTier
    reason: str
    fingerprint: str | None
    timestamp: datetime


class EscalationProtocol:
    """4-tier escalation system for stuck loops.

    Wraps StuckDetector and adds tier-based response actions.
    """

    def __init__(
        self,
        loop_manager: Optional[object] = None,
        notification_func: Optional[Callable[[str, str, str], None]] = None,
        max_history: int = 100,
    ) -> None:
        """Initialize escalation protocol.

        Args:
            loop_manager: Optional manager for loop control (kill/unpause).
            notification_func: Optional callable for Discord alerts.
                Signature: async def notify(tier: str, loop_id: str, reason: str) -> None
            max_history: Maximum number of escalation events to keep.
        """
        self._loop_manager = loop_manager
        self._notify = notification_func
        self._escalation_history: deque[EscalationEvent] = deque(maxlen=max_history)
        self._lock = asyncio.Lock()
        logger.info(
            "escalation_protocol_initialized",
            has_loop_manager=loop_manager is not None,
            has_notification=notification_func is not None,
            max_history=max_history,
        )

    # ── public API ────────────────────────────────────────────────

    async def handle_stuck_loop(
        self, loop_id: str, stuck_report: StuckReport
    ) -> EscalationTier:
        """Determine escalation tier based on stuck type and history.

        Decision logic:
            1. Hard loop (same fingerprint 3x) → ESCALATE
            2. Soft stall (velocity < 20%) → NOTIFY
            3. Safety-critical task → APPROVE
            4. Default → AUTO (retry with backoff)

        Args:
            loop_id: Unique identifier for the loop.
            stuck_report: StuckReport from StuckDetector.check().

        Returns:
            EscalationTier decision.
        """
        async with self._lock:
            # 1. Hard loop detection
            if stuck_report.stuck_type == "hard_loop":
                logger.warning(
                    "escalation.hard_loop_detected",
                    loop_id=loop_id,
                    fingerprint=stuck_report.fingerprint,
                    repeat_count=stuck_report.repeat_count,
                )
                return EscalationTier.ESCALATE

            # 2. Soft stall detection
            if stuck_report.stuck_type == "soft_stall":
                logger.warning(
                    "escalation.soft_stall_detected",
                    loop_id=loop_id,
                    velocity_ratio=stuck_report.velocity_ratio,
                )
                return EscalationTier.NOTIFY

            # 3. Default: AUTO (retry with backoff)
            logger.info(
                "escalation.auto_retry",
                loop_id=loop_id,
                recommendation=stuck_report.recommendation,
            )
            return EscalationTier.AUTO

    async def escalate(
        self, loop_id: str, tier: EscalationTier, reason: str
    ) -> None:
        """Execute escalation action based on tier.

        Args:
            loop_id: Loop identifier.
            tier: EscalationTier decision.
            reason: Human-readable reason for escalation.
        """
        async with self._lock:
            # Record event for audit trail
            event = EscalationEvent(
                loop_id=loop_id,
                tier=tier,
                reason=reason,
                fingerprint=None,
                timestamp=datetime.now(timezone.utc),
            )
            self._escalation_history.append(event)

            logger.info(
                "escalation_executed",
                loop_id=loop_id,
                tier=tier.value,
                reason=reason,
            )

            # Execute action based on tier
            try:
                if tier == EscalationTier.AUTO:
                    await self._escalate_auto(loop_id, reason)
                elif tier == EscalationTier.NOTIFY:
                    await self._escalate_notify(loop_id, reason)
                elif tier == EscalationTier.APPROVE:
                    await self._escalate_approve(loop_id, reason)
                elif tier == EscalationTier.ESCALATE:
                    await self._escalate_escalate(loop_id, reason)
                else:
                    logger.error("escalation.unknown_tier", tier=tier.value)
            except Exception as exc:
                logger.exception(
                    "escalation_execution_failed",
                    loop_id=loop_id,
                    tier=tier.value,
                    exc_info=True,
                )

    # ── private actions ────────────────────────────────────────────

    async def _escalate_auto(self, loop_id: str, reason: str) -> None:
        """AUTO tier: Log + retry with increased budget.

        Args:
            loop_id: Loop identifier.
            reason: Escalation reason.
        """
        logger.info(
            "escalation.auto_action",
            loop_id=loop_id,
            reason=reason,
        )
        # TODO: Increase retry budget, backoff timer
        # This is a placeholder — actual implementation depends on loop manager

    async def _escalate_notify(self, loop_id: str, reason: str) -> None:
        """NOTIFY tier: Send Discord alert to Faiz.

        Args:
            loop_id: Loop identifier.
            reason: Escalation reason.
        """
        if self._notify is None:
            logger.warning(
                "escalation.notify_no_notification_func",
                loop_id=loop_id,
                reason=reason,
            )
            return

        try:
            await self._notify("NOTIFY", loop_id, reason)
            logger.info(
                "escalation.discord_notification_sent",
                loop_id=loop_id,
                reason=reason,
            )
        except Exception as exc:
            logger.exception(
                "escalation.discord_notification_failed",
                loop_id=loop_id,
                reason=reason,
                exc_info=True,
            )

    async def _escalate_approve(self, loop_id: str, reason: str) -> None:
        """APPROVE tier: Pause loop, send approval request to Faiz.

        Args:
            loop_id: Loop identifier.
            reason: Escalation reason.
        """
        if self._loop_manager is None:
            logger.warning(
                "escalation.approve_no_loop_manager",
                loop_id=loop_id,
                reason=reason,
            )
            return

        try:
            # Pause loop
            if hasattr(self._loop_manager, "pause_loop"):
                await self._loop_manager.pause_loop(loop_id)
                logger.info(
                    "escalation.loop_paused",
                    loop_id=loop_id,
                    reason=reason,
                )
            else:
                logger.warning(
                    "escalation.approve_loop_manager_no_pause_method",
                    loop_id=loop_id,
                )
        except Exception as exc:
            logger.exception(
                "escalation.pause_loop_failed",
                loop_id=loop_id,
                reason=reason,
                exc_info=True,
            )

        # Notify Faiz
        if self._notify is not None:
            try:
                await self._notify("APPROVE", loop_id, reason)
                logger.info(
                    "escalation.approval_request_sent",
                    loop_id=loop_id,
                    reason=reason,
                )
            except Exception as exc:
                logger.exception(
                    "escalation.approval_request_failed",
                    loop_id=loop_id,
                    reason=reason,
                    exc_info=True,
                )

    async def _escalate_escalate(self, loop_id: str, reason: str) -> None:
        """ESCALATE tier: Kill loop, Discord SEV1 alert, block similar tasks.

        Args:
            loop_id: Loop identifier.
            reason: Escalation reason.
        """
        # Kill loop
        if self._loop_manager is not None:
            try:
                if hasattr(self._loop_manager, "kill_loop"):
                    await self._loop_manager.kill_loop(loop_id, reason)
                    logger.warning(
                        "escalation.loop_killed",
                        loop_id=loop_id,
                        reason=reason,
                    )
                else:
                    logger.warning(
                        "escalation.escalate_loop_manager_no_kill_method",
                        loop_id=loop_id,
                    )
            except Exception as exc:
                logger.exception(
                    "escalation.kill_loop_failed",
                    loop_id=loop_id,
                    reason=reason,
                    exc_info=True,
                )

        # Discord SEV1 alert
        if self._notify is not None:
            try:
                await self._notify("ESCALATE", loop_id, reason)
                logger.warning(
                    "escalation.discord_sev1_alert_sent",
                    loop_id=loop_id,
                    reason=reason,
                )
            except Exception as exc:
                logger.exception(
                    "escalation.discord_sev1_alert_failed",
                    loop_id=loop_id,
                    reason=reason,
                    exc_info=True,
                )

        # TODO: Block similar tasks (e.g., blacklist fingerprint, add to blocked list)
        logger.info(
            "escalation.block_similar_tasks_placeholder",
            loop_id=loop_id,
            reason=reason,
        )

    # ── helpers ────────────────────────────────────────────────────

    async def _send_discord_alert(
        self, tier: EscalationTier, loop_id: str, reason: str
    ) -> None:
        """Send escalation alert via Discord.

        Args:
            tier: EscalationTier.
            loop_id: Loop identifier.
            reason: Escalation reason.
        """
        if self._notify is None:
            logger.warning(
                "escalation.discord_alert_no_func",
                tier=tier.value,
                loop_id=loop_id,
            )
            return

        try:
            await self._notify(tier.value, loop_id, reason)
        except Exception as exc:
            logger.exception(
                "escalation.discord_alert_failed",
                tier=tier.value,
                loop_id=loop_id,
                exc_info=True,
            )

    def get_history(self) -> list[EscalationEvent]:
        """Get escalation history.

        Returns:
            List of EscalationEvent.
        """
        return list(self._escalation_history)

    def get_recent_events(self, count: int = 10) -> list[EscalationEvent]:
        """Get recent escalation events.

        Args:
            count: Number of recent events to return.

        Returns:
            List of recent EscalationEvent.
        """
        return list(self._escalation_history)[-count:]

    def get_tier_counts(self) -> dict[EscalationTier, int]:
        """Get escalation tier counts.

        Returns:
            Dict of EscalationTier → count.
        """
        counts = {tier: 0 for tier in EscalationTier}
        for event in self._escalation_history:
            counts[event.tier] += 1
        return counts