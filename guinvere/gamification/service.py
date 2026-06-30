"""Async XP service layer for the Guinevere gamification system.

Provides high-level operations for awarding XP, querying levels, and
managing skill progression. Uses async SQLAlchemy sessions.

Usage:
    service = GamificationService(session)
    result = await service.award_xp(
        skill_name="python",
        xp_amount=50,
        reason="Completed code review",
        source="task_completion",
    )
    print(f"Skill leveled up: {result.level_up}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

import structlog
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from guinvere.gamification.levels import (
    calculate_level,
    xp_for_level,
    xp_for_next_level,
    xp_progress_to_next_level,
)
from guinvere.gamification.models import (
    AgentXP,
    SkillXP,
    XPEvent,
    XPMultiplier,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


# ============================================================
# Result Dataclasses
# ============================================================


@dataclass
class XPAwardResult:
    """Result of an XP award operation."""

    xp_awarded: int
    skill_name: str | None
    total_xp: int
    old_level: int
    new_level: int
    level_up: bool
    xp_to_next: int
    progress: float  # 0.0–1.0 progress to next level

    @property
    def display_summary(self) -> str:
        """Human-readable summary of the XP award."""
        parts = [f"+{self.xp_awarded} XP"]
        if self.skill_name:
            parts.append(f"({self.skill_name})")
        if self.level_up:
            parts.append(f"🎉 Level up! {self.old_level} → {self.new_level}")
        else:
            parts.append(
                f"[Level {self.new_level}] "
                f"{self.xp_to_next} XP to next "
                f"({self.progress:.0%})"
            )
        return " ".join(parts)


@dataclass
class SkillProgress:
    """Detailed progress info for a skill."""

    skill_name: str
    category: str | None
    total_xp: int
    current_level: int
    xp_in_current_level: int
    xp_for_next_level: int
    progress: float
    title: str | None


@dataclass
class AgentProgress:
    """Overall agent progress info."""

    total_xp: int
    current_level: int
    xp_in_current_level: int
    xp_for_next_level: int
    progress: float
    lifetime_actions: int
    title: str | None


# ============================================================
# XP Multiplier Constants (defaults)
# ============================================================

STREAK_BONUS_PER_DAY: float = 0.02  # +2% per streak day
MAX_STREAK_MULTIPLIER: float = 2.00  # cap at 200%
FIRST_TIME_BONUS: float = 1.50  # +50% for first time using a skill


# ============================================================
# Gamification Service
# ============================================================


class GamificationService:
    """Async service for XP and level operations.

    All operations are atomic within the provided session. The caller
    is responsible for committing the session after the operation.

    Args:
        session: An active async SQLAlchemy session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # XP Awarding
    # ------------------------------------------------------------------

    async def award_xp(
        self,
        xp_amount: int,
        reason: str,
        *,
        skill_name: str | None = None,
        source: str | None = None,
        metadata: dict | None = None,
        multiplier_name: str | None = None,
    ) -> XPAwardResult:
        """Award XP to a skill and/or the overall agent.

        If skill_name is provided, XP is awarded to that skill (creating
        the row if needed). Agent XP is always updated (creating the
        singleton row if needed).

        Args:
            xp_amount: Base XP to award (can be negative for penalties).
            reason: Human-readable reason for the XP award.
            skill_name: Optional skill to award XP to.
            source: Source attribution (e.g. "task_completion").
            metadata: Optional JSON metadata for the event log.
            multiplier_name: Optional multiplier to apply from xp_multipliers table.

        Returns:
            XPAwardResult with details of the award.
        """
        # Apply multiplier if specified
        effective_xp = xp_amount
        if multiplier_name and xp_amount > 0:
            multiplier = await self._get_multiplier(multiplier_name)
            if multiplier:
                effective_xp = int(xp_amount * multiplier)
                logger.info(
                    "xp_multiplier_applied",
                    base_xp=xp_amount,
                    multiplier_name=multiplier_name,
                    multiplier=multiplier,
                    effective_xp=effective_xp,
                )

        # Log the XP event
        event = XPEvent(
            skill_name=skill_name,
            xp_amount=effective_xp,
            reason=reason,
            source=source,
            extra_metadata=metadata,
        )
        self._session.add(event)

        result: XPAwardResult | None = None

        # Update skill XP if skill_name provided
        if skill_name:
            result = await self._award_skill_xp(skill_name, effective_xp)

        # Always update agent XP
        agent_result = await self._award_agent_xp(effective_xp)

        # If no skill was specified, use the agent result
        if result is None:
            result = agent_result

        logger.info(
            "xp_awarded",
            skill_name=skill_name,
            xp_amount=effective_xp,
            reason=reason,
            level_up=result.level_up,
            new_level=result.new_level,
        )

        return result

    async def _award_skill_xp(self, skill_name: str, xp_amount: int) -> XPAwardResult:
        """Award XP to a specific skill, creating the row if needed."""
        # Upsert the skill row
        stmt = (
            pg_insert(SkillXP)
            .values(
                skill_name=skill_name,
                total_xp=xp_amount,
                current_level=calculate_level(max(0, xp_amount)),
                last_xp_event=datetime.now(timezone.utc),
            )
            .on_conflict_do_update(
                index_elements=["skill_name"],
                set_={
                    "total_xp": SkillXP.total_xp + xp_amount,
                    "last_xp_event": datetime.now(timezone.utc),
                },
            )
            .returning(SkillXP)
        )

        result = await self._session.execute(stmt)
        row = result.one()

        # The trigger will recalculate current_level on UPDATE,
        # but for the initial INSERT we need to calculate manually.
        old_xp = row.total_xp - xp_amount
        old_level = calculate_level(max(0, old_xp))
        new_level = calculate_level(max(0, row.total_xp))

        # Manually update level if trigger didn't fire (INSERT path)
        if row.current_level != new_level:
            await self._session.execute(
                update(SkillXP)
                .where(SkillXP.skill_name == skill_name)
                .values(current_level=new_level)
            )

        _, _, progress = xp_progress_to_next_level(row.total_xp)
        xp_next = xp_for_next_level(row.total_xp)

        return XPAwardResult(
            xp_awarded=xp_amount,
            skill_name=skill_name,
            total_xp=row.total_xp,
            old_level=old_level,
            new_level=new_level,
            level_up=new_level > old_level,
            xp_to_next=xp_next,
            progress=progress,
        )

    async def _award_agent_xp(self, xp_amount: int) -> XPAwardResult:
        """Award XP to the overall agent (singleton)."""
        stmt = (
            pg_insert(AgentXP)
            .values(
                total_xp=xp_amount,
                current_level=calculate_level(max(0, xp_amount)),
                lifetime_actions=1,
                last_xp_event=datetime.now(timezone.utc),
            )
            .on_conflict_do_update(
                index_elements=[text("(true)")],
                set_={
                    "total_xp": AgentXP.total_xp + xp_amount,
                    "lifetime_actions": AgentXP.lifetime_actions + 1,
                    "last_xp_event": datetime.now(timezone.utc),
                },
            )
            .returning(AgentXP)
        )

        result = await self._session.execute(stmt)
        row = result.one()

        old_xp = row.total_xp - xp_amount
        old_level = calculate_level(max(0, old_xp))
        new_level = calculate_level(max(0, row.total_xp))

        # Manually update level for INSERT path
        if row.current_level != new_level:
            await self._session.execute(
                update(AgentXP)
                .where(AgentXP.id == row.id)
                .values(current_level=new_level)
            )

        _, _, progress = xp_progress_to_next_level(row.total_xp)
        xp_next = xp_for_next_level(row.total_xp)

        return XPAwardResult(
            xp_awarded=xp_amount,
            skill_name=None,
            total_xp=row.total_xp,
            old_level=old_level,
            new_level=new_level,
            level_up=new_level > old_level,
            xp_to_next=xp_next,
            progress=progress,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_skill_progress(self, skill_name: str) -> SkillProgress | None:
        """Get detailed progress for a skill.

        Returns None if the skill has no XP yet.
        """
        stmt = select(SkillXP).where(SkillXP.skill_name == skill_name)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        in_level, needed, progress = xp_progress_to_next_level(row.total_xp)
        from guinvere.gamification.levels import _LEVEL_TITLES

        return SkillProgress(
            skill_name=row.skill_name,
            category=row.category,
            total_xp=row.total_xp,
            current_level=row.current_level,
            xp_in_current_level=in_level,
            xp_for_next_level=needed,
            progress=progress,
            title=_LEVEL_TITLES.get(row.current_level),
        )

    async def get_agent_progress(self) -> AgentProgress | None:
        """Get overall agent progress.

        Returns None if the agent has no XP yet.
        """
        stmt = select(AgentXP).limit(1)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        in_level, needed, progress = xp_progress_to_next_level(row.total_xp)
        from guinvere.gamification.levels import _LEVEL_TITLES

        return AgentProgress(
            total_xp=row.total_xp,
            current_level=row.current_level,
            xp_in_current_level=in_level,
            xp_for_next_level=needed,
            progress=progress,
            lifetime_actions=row.lifetime_actions,
            title=_LEVEL_TITLES.get(row.current_level),
        )

    async def get_all_skills(self) -> list[SkillProgress]:
        """Get progress for all tracked skills, ordered by level desc."""
        stmt = select(SkillXP).order_by(SkillXP.current_level.desc())
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        from guinvere.gamification.levels import _LEVEL_TITLES

        skills = []
        for row in rows:
            in_level, needed, progress = xp_progress_to_next_level(row.total_xp)
            skills.append(SkillProgress(
                skill_name=row.skill_name,
                category=row.category,
                total_xp=row.total_xp,
                current_level=row.current_level,
                xp_in_current_level=in_level,
                xp_for_next_level=needed,
                progress=progress,
                title=_LEVEL_TITLES.get(row.current_level),
            ))
        return skills

    # ------------------------------------------------------------------
    # Multiplier Helpers
    # ------------------------------------------------------------------

    async def _get_multiplier(self, name: str) -> float | None:
        """Look up an active, non-expired multiplier by name."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(XPMultiplier.multiplier)
            .where(
                XPMultiplier.multiplier_name == name,
                XPMultiplier.active.is_(True),
                (XPMultiplier.expires_at.is_(None) | (XPMultiplier.expires_at > now)),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return float(row) if row is not None else None
