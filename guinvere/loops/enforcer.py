"""Todo Enforcer — idle agent detection and enforcement.

Tracks sub-agent activity and enforces idle thresholds:
agents idle beyond ``IDLE_THRESHOLD`` get yanked back;
agents idle beyond ``KILL_THRESHOLD`` get killed and respawned.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()


class TodoEnforcer:
    """Enforces idle timeouts on tracked sub-agents.

    Sub-agents that remain idle for too long are first yanked
    (re-prompted), then killed and respawned if they remain idle.
    """

    IDLE_THRESHOLD: int = 30  # seconds idle → yank back
    KILL_THRESHOLD: int = 60  # seconds idle → kill + respawn

    def __init__(self) -> None:
        self.tracked_agents: dict[str, dict[str, Any]] = {}
        logger.info("todo_enforcer_initialized",
                     idle_threshold=self.IDLE_THRESHOLD,
                     kill_threshold=self.KILL_THRESHOLD)

    def track_agent(self, agent_id: str, loop_id: str) -> None:
        """Start tracking an agent for idle enforcement.

        Args:
            agent_id: Unique agent identifier.
            loop_id: Parent loop that owns this agent.
        """
        self.tracked_agents[agent_id] = {
            "loop_id": loop_id,
            "tracked_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "status": "active",
            "yanked": False,
        }
        logger.info("agent_tracked", agent_id=agent_id, loop_id=loop_id)

    def untrack_agent(self, agent_id: str) -> None:
        """Stop tracking an agent.

        Args:
            agent_id: The agent to stop tracking.
        """
        removed = self.tracked_agents.pop(agent_id, None)
        if removed is not None:
            logger.info("agent_untracked", agent_id=agent_id)
        else:
            logger.warning("agent_untrack_not_found", agent_id=agent_id)

    def record_activity(self, agent_id: str) -> None:
        """Record that an agent has performed work, resetting its idle timer.

        Args:
            agent_id: The agent that performed work.
        """
        agent_data = self.tracked_agents.get(agent_id)
        if agent_data is None:
            logger.warning("activity_unknown_agent", agent_id=agent_id)
            return
        agent_data["last_activity"] = datetime.now(timezone.utc)
        agent_data["status"] = "active"
        agent_data["yanked"] = False
        logger.debug("agent_activity", agent_id=agent_id)

    def check_idle(self) -> list[str]:
        """Return a list of agent IDs that exceed the idle threshold.

        Returns:
            List of agent IDs currently idle beyond ``IDLE_THRESHOLD``.
        """
        now = datetime.now(timezone.utc)
        idle_agents: list[str] = []
        for agent_id, data in self.tracked_agents.items():
            if data["status"] != "active":
                continue
            idle_seconds = (now - data["last_activity"]).total_seconds()
            if idle_seconds > self.IDLE_THRESHOLD:
                idle_agents.append(agent_id)
                logger.warning("agent_idle",
                               agent_id=agent_id,
                               idle_seconds=f"{idle_seconds:.0f}")
        return idle_agents

    def enforce(self) -> dict[str, str]:
        """Enforce idle thresholds and return actions taken per agent.

        Returns:
            Dict mapping agent_id → action taken ("yank", "kill_respawn",
            or "none").
        """
        now = datetime.now(timezone.utc)
        actions: dict[str, str] = {}

        for agent_id, data in list(self.tracked_agents.items()):
            if data["status"] != "active":
                actions[agent_id] = "none"
                continue

            idle_seconds = (now - data["last_activity"]).total_seconds()

            if idle_seconds > self.KILL_THRESHOLD:
                # Kill and respawn
                logger.error("agent_kill_respawn",
                             agent_id=agent_id,
                             idle_seconds=f"{idle_seconds:.0f}")
                data["status"] = "killed"
                actions[agent_id] = "kill_respawn"

            elif idle_seconds > self.IDLE_THRESHOLD and not data["yanked"]:
                # Yank back
                logger.warning("agent_yanked",
                               agent_id=agent_id,
                               idle_seconds=f"{idle_seconds:.0f}")
                data["yanked"] = True
                actions[agent_id] = "yank"

            else:
                actions[agent_id] = "none"

        return actions
