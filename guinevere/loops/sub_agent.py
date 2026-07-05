"""Sub-agent spawning — Pasukan Mommy.

Manages the lifecycle of sub-agents spawned by the autonomous
loop.  Each agent is categorised and tracked with structured
metadata.  This module does NOT make actual LLM calls — it
returns structured dicts representing agent records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class SubAgentSpawner:
    """Spawns and tracks sub-agents ("Pasukan Mommy") for a loop.

    Agents are created as structured records with category, task,
    and status metadata.  Actual LLM execution is handled externally.
    """

    AGENT_CATEGORIES: tuple[str, ...] = (
        "visual-engineering",
        "deep-logic",
        "data-infra",
        "integration",
        "testing",
    )

    def __init__(self, loop_id: str) -> None:
        self.loop_id = loop_id
        self.spawned_agents: list[dict[str, Any]] = []
        logger.info("sub_agent_spawner_initialized", loop_id=loop_id)

    def spawn(self, category: str, task_description: str, prompt: str) -> dict[str, Any]:
        """Create a new sub-agent record.

        Args:
            category: Agent category (must be in ``AGENT_CATEGORIES``).
            task_description: Human-readable task summary.
            prompt: The full delegation prompt for the agent.

        Returns:
            A dict representing the spawned agent record.

        Raises:
            ValueError: If category is not in ``AGENT_CATEGORIES``.
        """
        if category not in self.AGENT_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. "
                f"Must be one of: {', '.join(self.AGENT_CATEGORIES)}"
            )

        agent_id = str(uuid4())
        agent_record: dict[str, Any] = {
            "agent_id": agent_id,
            "loop_id": self.loop_id,
            "category": category,
            "task_description": task_description,
            "prompt": prompt,
            "status": "pending",
            "spawned_at": datetime.now(timezone.utc).isoformat(),
            "result": None,
            "error": None,
        }
        self.spawned_agents.append(agent_record)

        logger.info("pasukan_mommy_spawned",
                     agent_id=agent_id,
                     loop_id=self.loop_id,
                     category=category,
                     task=task_description)
        return agent_record

    def get_spawned(self) -> list[dict[str, Any]]:
        """Return all spawned agent records.

        Returns:
            List of agent record dicts.
        """
        return list(self.spawned_agents)

    def mark_complete(self, agent_id: str, result: str) -> None:
        """Mark a spawned agent as completed.

        Args:
            agent_id: The agent to mark complete.
            result: The result summary from the agent.

        Raises:
            ValueError: If agent_id is not found.
        """
        for agent in self.spawned_agents:
            if agent["agent_id"] == agent_id:
                agent["status"] = "complete"
                agent["result"] = result
                logger.info("pasukan_mommy_complete",
                            agent_id=agent_id,
                            category=agent["category"])
                return
        raise ValueError(f"Agent '{agent_id}' not found in spawned agents")

    def mark_failed(self, agent_id: str, error: str) -> None:
        """Mark a spawned agent as failed.

        Args:
            agent_id: The agent to mark failed.
            error: Error description.

        Raises:
            ValueError: If agent_id is not found.
        """
        for agent in self.spawned_agents:
            if agent["agent_id"] == agent_id:
                agent["status"] = "failed"
                agent["error"] = error
                logger.error("pasukan_mommy_failed",
                             agent_id=agent_id,
                             category=agent["category"],
                             error=error)
                return
        raise ValueError(f"Agent '{agent_id}' not found in spawned agents")
