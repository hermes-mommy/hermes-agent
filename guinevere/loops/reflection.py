"""Post-loop reflection hooks — extract lessons learned from completed loops."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class ReflectionEntry:
    """Reflection entry for a completed loop.

    Captures what went well, what could improve, and reusable patterns.
    """

    loop_id: str
    task: str
    outcome: str  # "success", "partial", "failed"
    lessons: list[str]
    timestamp: datetime


class ReflectionExtractor:
    """Extract lessons learned from completed loop artifacts.

    Uses LLM to analyze phase artifacts and extract:
    - What went well
    - What could improve
    - Reusable patterns or skills

    Constructor injection:
    - llm_router: LLMRouter instance (None = return empty reflection)
    """

    def __init__(self, llm_router: Any | None = None) -> None:
        self._llm_router = llm_router

    async def extract(
        self,
        loop_id: str,
        task: str,
        artifacts: list[str],
    ) -> ReflectionEntry:
        """Extract reflection from loop artifacts.

        Args:
            loop_id: The loop identifier
            task: The original task description
            artifacts: List of markdown artifact strings from each phase

        Returns:
            ReflectionEntry with extracted lessons
        """
        if not self._llm_router:
            # No LLM — return minimal reflection
            return ReflectionEntry(
                loop_id=loop_id,
                task=task,
                outcome="unknown",
                lessons=["No LLM router available for reflection extraction"],
                timestamp=datetime.now(timezone.utc),
            )

        # Build prompt with artifacts
        artifact_text = "\n\n---\n\n".join(artifacts[:5])  # Limit to first 5 artifacts
        messages = [
            {
                "role": "system",
                "content": "You are a reflection extractor. Analyze the loop artifacts and extract lessons learned.",
            },
            {
                "role": "user",
                "content": f"Task: {task}\n\nArtifacts:\n{artifact_text}\n\nExtract:\n1. What went well\n2. What could improve\n3. Reusable patterns\n\nReturn as JSON: {{\"outcome\": \"success|partial|failed\", \"lessons\": [\"lesson1\", \"lesson2\"]}}",
            },
        ]

        result = await self._llm_router.chat(
            messages=messages,
            task_type="CORE_REASONING",
            max_tokens=1024,
        )

        content = result.get("content", "")

        # Parse JSON response
        try:
            # Strip markdown fences if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            parsed = json.loads(content)
            outcome = parsed.get("outcome", "unknown")
            lessons = parsed.get("lessons", [])
        except (json.JSONDecodeError, IndexError):
            # Bad JSON — extract as plain text
            outcome = "unknown"
            lessons = [content[:200]]

        return ReflectionEntry(
            loop_id=loop_id,
            task=task,
            outcome=outcome,
            lessons=lessons,
            timestamp=datetime.now(timezone.utc),
        )


def extract_reflection(
    loop_id: str,
    task: str,
    artifacts: list[str],
    llm_router: Any | None = None,
) -> ReflectionEntry:
    """Convenience function to extract reflection.

    Args:
        loop_id: The loop identifier
        task: The original task description
        artifacts: List of markdown artifact strings from each phase
        llm_router: Optional LLM router for reflection extraction

    Returns:
        ReflectionEntry with extracted lessons
    """
    extractor = ReflectionExtractor(llm_router=llm_router)
    return extractor.extract(loop_id, task, artifacts)