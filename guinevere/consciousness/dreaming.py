"""ContinuousDreamer — background speculative thought generator.

Runs as an asyncio.Task alongside ThoughtStream. During natural pauses
or low-activity periods, generates DREAMING-type thoughts (counterfactuals,
"what if" scenarios, creative combinations).

Design decisions:
  - Uses asyncio.sleep(30-120) with explicit shutdown_event check.
  - Sleep interval is EXEMPTED from the no-asyncio.sleep rule (see plan).
  - Dreamer yields to the main ThoughtStream — only generates when idle.
  - Dream thoughts are recorded as ThoughtType.DREAMING in state.
  - DreamJournalEntry is created from parsed JSON dream content.
  - Pause/resume at runtime via asyncio-safe flag.
"""

from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import structlog

from guinevere.consciousness.state import DreamJournalEntry
from guinevere.consciousness.thought import Thought, ThoughtType

if TYPE_CHECKING:
    from guinevere.consciousness.state import ConsciousnessState

logger = structlog.get_logger("guinevere.consciousness.dreaming")

# Dream cadence bounds (seconds).
_MIN_DREAM_INTERVAL: float = 30.0
_MAX_DREAM_INTERVAL: float = 120.0

# Idle threshold: if main stream generated a thought within this window,
# the dreamer yields (does not generate).
_IDLE_THRESHOLD_S: float = 5.0


async def _self_prompt(
    llm_router: Any,
    system_msg: str,
    user_msg: str,
    max_tokens: int = 256,
) -> str:
    """Delegate a self-prompt to the Hermes AIAgent and return content.

    Compatible with thought_stream._self_prompt — same interface, same
    defensive handling of dict returns and exceptions.

    Args:
        llm_router: The Hermes AIAgent with a ``chat(message)`` method.
        system_msg: System prompt.
        user_msg: User prompt.
        max_tokens: Max response tokens (advisory).

    Returns:
        The agent's response string. Empty string on failure.
    """
    prompt = system_msg + chr(10) + chr(10) + user_msg
    try:
        result = llm_router.chat(prompt)
    except Exception as exc:
        logger.warning("dreaming.self_prompt.delegate_failed %s", exc)
        return ""
    if not isinstance(result, str):
        if isinstance(result, dict):
            return str(result.get("content", ""))
        return str(result) if result else ""
    return result


def _thoughts_block(state: ConsciousnessState, n: int = 5) -> str:
    """Format recent thoughts as a newline-separated block."""
    thoughts = state.recent_thoughts(n)
    if not thoughts:
        return "(no recent thoughts)"
    return "\n".join(f"- {t}" for t in thoughts)


class ContinuousDreamer:
    """Background speculative thought generator.

    Runs as an asyncio.Task alongside ThoughtStream. During natural
    pauses or low-activity periods, generates DREAMING-type thoughts
    (counterfactuals, "what if" scenarios, creative combinations).

    Dream thoughts are fed into the main state.record_thought() but
    at lower priority — the dreamer yields to the main stream if
    a cognition/planning thought is in progress.

    Lifecycle:
      - Constructed by ConsciousnessLoop (or test harness) with
        llm_router, state, shutdown_event.
      - run() is the asyncio.Task target — loops until shutdown.
      - pause() / resume() control dream generation at runtime.
    """

    def __init__(
        self,
        llm_router: Any,
        state: ConsciousnessState,
        shutdown_event: asyncio.Event,
    ) -> None:
        self._llm_router = llm_router
        self._state = state
        self._shutdown_event = shutdown_event
        self._paused: bool = False
        self._dream_count: int = 0

        logger.info(
            "dreaming.initialized",
            has_llm_router=llm_router is not None,
        )

    # ── public properties ───────────────────────────────────

    @property
    def is_paused(self) -> bool:
        """Return True if dream generation is paused."""
        return self._paused

    @property
    def dream_count(self) -> int:
        """Return the total number of dreams generated this session."""
        return self._dream_count

    # ── runtime control ─────────────────────────────────────

    def pause(self) -> None:
        """Pause dream generation. run() will sleep without generating."""
        self._paused = True
        logger.info("dreaming.paused")

    def resume(self) -> None:
        """Resume dream generation after a pause."""
        self._paused = False
        logger.info("dreaming.resumed")

    # ── main loop ───────────────────────────────────────────

    async def run(self) -> None:
        """Run the dream generator until shutdown.

        Each cycle:
          1. Check shutdown_event — exit if set.
          2. Sleep for a random interval (30-120s).
          3. Check shutdown_event again after sleep.
          4. If paused, skip generation and loop.
          5. Check if main stream is idle — if not, skip.
          6. Generate a dream thought via _self_prompt.
          7. Parse JSON, create DreamJournalEntry, record in state.

        This method is the target for asyncio.create_task().
        """
        logger.info("dreaming.run.starting")

        while not self._shutdown_event.is_set():
            # Sleep with randomized interval for natural cadence.
            interval = random.uniform(_MIN_DREAM_INTERVAL, _MAX_DREAM_INTERVAL)
            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                logger.info("dreaming.run.cancelled_during_sleep")
                break

            # Check shutdown after sleep.
            if self._shutdown_event.is_set():
                break

            # If paused, skip generation but continue loop.
            if self._paused:
                logger.debug("dreaming.run.paused_skip")
                continue

            # Yield to main stream: check if it's active.
            if self._is_main_stream_active():
                logger.debug("dreaming.run.yielding_to_main_stream")
                continue

            # Generate a dream thought.
            try:
                await self._generate_dream()
            except asyncio.CancelledError:
                logger.info("dreaming.run.cancelled_during_generation")
                break
            except Exception as exc:
                logger.warning("dreaming.run.generation_failed %s", exc)
                # Continue loop — a single failure doesn't stop the dreamer.

        logger.info(
            "dreaming.run.exited",
            total_dreams=self._dream_count,
        )

    # ── internal helpers ────────────────────────────────────

    def _is_main_stream_active(self) -> bool:
        """Check if the main ThoughtStream generated a thought recently.

        Returns True if the last recorded thought timestamp is within
        the idle threshold, indicating the main stream is active.
        """
        last_thought_at = self._state.last_thought_at
        if not last_thought_at:
            # No thoughts yet — stream hasn't started, safe to dream.
            return False

        # Find the most recent timestamp across all substrates.
        most_recent = max(last_thought_at.values())
        elapsed = (datetime.now(timezone.utc) - most_recent).total_seconds()
        return elapsed < _IDLE_THRESHOLD_S

    async def _generate_dream(self) -> None:
        """Generate a single dream thought and record it in state.

        Uses DREAMING_SYSTEM and DREAMING_USER prompts from prompts.py.
        Parses the JSON response to extract scenario, counterfactual, insight.
        Records the thought and creates a DreamJournalEntry.
        """
        from guinevere.consciousness.prompts import DREAMING_SYSTEM, DREAMING_USER

        # Build user message with current state context.
        affect = self._state.affect
        recent = _thoughts_block(self._state, 5)
        user_msg = DREAMING_USER.format(
            thought=recent,
            serenity=affect.serenity,
        )

        # Self-prompt the LLM.
        content = await _self_prompt(
            self._llm_router,
            DREAMING_SYSTEM,
            user_msg,
            max_tokens=256,
        )

        if not content:
            logger.debug("dreaming.generate.empty_response")
            return

        # Parse JSON response for dream journal entry.
        scenario = ""
        counterfactual = ""
        insight = ""
        try:
            parsed = json.loads(content)
            scenario = str(parsed.get("scenario", ""))
            counterfactual = str(parsed.get("counterfactual", ""))
            insight = str(parsed.get("insight", ""))
        except (json.JSONDecodeError, TypeError, KeyError):
            # Non-JSON response — use raw content as scenario.
            scenario = content[:200]
            counterfactual = ""
            insight = ""

        # Build and record the Thought.
        thought = Thought(
            type=ThoughtType.DREAMING,
            content=content,
            confidence=0.3,  # Low confidence — dreams are speculative.
            affect_snapshot=self._state.affect.as_dict(),
        )

        self._state.record_thought(
            thought.type.value,
            thought.to_log_string(),
        )

        # Create DreamJournalEntry if we have meaningful content.
        if scenario or counterfactual or insight:
            entry = DreamJournalEntry(
                timestamp=datetime.now(timezone.utc),
                scenario=scenario,
                counterfactual=counterfactual,
                insight=insight,
            )
            self._state.add_dream_entry(entry)

        self._dream_count += 1

        logger.debug(
            "dreaming.generate.success",
            dream_count=self._dream_count,
            scenario_preview=scenario[:80] if scenario else "",
        )
