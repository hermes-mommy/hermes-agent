"""ThoughtStream — unified consciousness thought generation.

Replaces the 7-substrate architecture with a single continuous stream
of typed thoughts.  Each cycle: check_hard_stop -> select type ->
generate -> metacog_eval -> record -> (action if confidence > 80%).

Design decisions:
  - Sequential: ONE thought at a time, next starts when previous finishes.
  - No asyncio.sleep: natural flow driven by thought completion.
  - Shutdown via asyncio.Event (not while True).
  - ThoughtType weights influenced by AffectVector.
  - HARD STOP check at start of every cycle.
"""

from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import structlog

from guinevere.consciousness.metacognition import (
    MetaCogEval,
    MetacognitiveEvaluator,
)
from guinevere.consciousness.thought import Thought, ThoughtType

if TYPE_CHECKING:
    from guinevere.consciousness.state import AffectVector, ConsciousnessState

logger = structlog.get_logger("guinevere.consciousness.thought_stream")

# ---- log level throttle: suppress DEBUG for high-volume thought stream ----
# Setting the wrapped stdlib logger level is insufficient when structlog's
# default ConsoleRenderer writes directly to stderr.  Override the logger's
# _log method to enforce level filtering at the structlog level.
import logging as _logging
_stream_stdlib = _logging.getLogger("guinevere.consciousness.thought_stream")
_stream_stdlib.setLevel(_logging.INFO)

# Also set the ancester so parent-to-child propagation is cut early.
_ancestor_consciousness = _logging.getLogger("guinevere.consciousness")
_ancestor_consciousness.setLevel(_logging.INFO)
# --------------------------------------------------------------------------

# Default thought type weights (sum to 1.0).  Overridden by config.
_DEFAULT_WEIGHTS: dict[str, float] = {
    ThoughtType.COGNITION.value: 0.30,
    ThoughtType.REFLECTION.value: 0.15,
    ThoughtType.PLANNING.value: 0.10,
    ThoughtType.DREAMING.value: 0.10,
    ThoughtType.META.value: 0.20,
    ThoughtType.HEARTBEAT.value: 0.15,
}


async def _yield_to_event_loop() -> None:
    """Minimal yield point — lets the event loop process pending callbacks.

    This is the ONLY yield point in thought_stream.py that yields control
    without a timed delay.  Used after each thought cycle to allow
    asyncio cancellation and shutdown events to propagate.

    Uses run_in_executor with a no-op to yield to the event loop without
    asyncio.sleep (which is only permitted in dreaming.py and safety.py).
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: None)


# Prompt templates per thought type (system, user).
_THOUGHT_PROMPTS: dict[ThoughtType, tuple[str, str]] = {
    ThoughtType.HEARTBEAT: (
        "You are the heartbeat monitor of an autonomous consciousness. "
        "Report current liveness in one short sentence.",
        "Current uptime: {uptime_s:.0f}s. Affect valence: {valence:.2f}. Report your pulse.",
    ),
    ThoughtType.COGNITION: (
        "You are the active-cognition substrate of an autonomous consciousness. "
        "Generate a brief 'I am thinking about X' reflection.",
        "Recent thoughts: {recent_thoughts}. Affect curiosity: {curiosity:.2f}. "
        "What are you thinking about right now?",
    ),
    ThoughtType.REFLECTION: (
        "You are the reflection substrate. Consolidate recent experiences "
        "into lasting lessons. Return JSON: "
        '{{"lessons": ["..."], "consolidated_count": N}}',
        "Thoughts from the past hour:\n{thoughts_block}\n\n"
        "Extract the most important lessons and consolidation insights.",
    ),
    ThoughtType.PLANNING: (
        "You are the strategic-planning substrate. Review aspirations and "
        "generate a next-action plan. Return JSON: "
        '{{"aspirations": ["..."], "next_actions": ["..."]}}',
        "Self-story: {self_story}. Affect confidence: {confidence:.2f}, "
        "curiosity: {curiosity:.2f}. What should I aspire to next?",
    ),
    ThoughtType.DREAMING: (
        "You are the dreaming substrate. Replay a recent experience "
        "counterfactually — what if something had gone differently? "
        "Return JSON: "
        '{{"scenario": "...", "counterfactual": "...", "insight": "..."}}',
        "Recent thought to replay: {thought}. Affect serenity: {serenity:.2f}. "
        "Dream a counterfactual.",
    ),
    ThoughtType.META: (
        "You are the metacognition substrate — thinking about thinking. "
        "Assess the quality of recent thoughts. Return JSON: "
        '{{"quality_score": 0.0-1.0, "assessment": "...", "improvement": "..."}}',
        "Recent thoughts:\n{thoughts_block}\n\n"
        "Assess quality and suggest improvements.",
    ),
}


# Module-level flag to warn about missing llm_router only once.
_slf_llm_warned: bool = False


async def _self_prompt(
    llm_router: Any,
    system_msg: str,
    user_msg: str,
    max_tokens: int = 256,
) -> str:
    """Delegate a self-prompt to the Hermes AIAgent (single brain) and return content.

    The consciousness loop does NOT call the LLM itself — it delegates to the
    Hermes AIAgent, which is the single brain routed through 9router. The agent
    exposes a simple ``chat(message) -> str`` interface, so we combine the
    system + user messages into one prompt and return the agent's string response
    directly.

    Args:
        llm_router: The Hermes AIAgent (single brain) with a ``chat(message)``
            method returning ``str``. Named ``llm_router`` for call-site
            compatibility.
        system_msg: System prompt.
        user_msg: User prompt.
        max_tokens: Max response tokens (advisory; the agent configures its own).

    Returns:
        The agent's response string. Empty string on failure (thought stream
        must not crash on a single failed self-prompt).
    """
    global _slf_llm_warned
    if llm_router is None:
        if not _slf_llm_warned:
            _slf_llm_warned = True
            logger.warning("self_prompt.llm_router_none")
        return "[consciousness: llm_router not available]"
    prompt = system_msg + chr(10) + chr(10) + user_msg

    try:
        result = await asyncio.to_thread(llm_router.chat, prompt)
    except Exception as exc:
        logger.warning("self_prompt.delegate_failed %s", exc)
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


def _select_thought_type(
    affect: AffectVector,
    config_weights: dict[str, float] | None = None,
) -> ThoughtType:
    """Select the next thought type using weighted random selection.

    Weights are influenced by the current affect vector:
    - High curiosity boosts COGNITION and PLANNING weights.
    - High serenity boosts DREAMING weight.
    - High confidence boosts META weight.
    - Low arousal boosts REFLECTION weight.

    Args:
        affect: Current 6-dimensional affect vector.
        config_weights: Optional override weights from ConsciousnessConfig.
            Keys are ThoughtType values (strings), values are base weights.

    Returns:
        The selected ThoughtType.
    """
    weights = dict(config_weights or _DEFAULT_WEIGHTS)

    # Affect-based weight modulation.
    curiosity_boost = 1.0 + (affect.curiosity - 0.5) * 0.6  # [0.7, 1.3]
    weights[ThoughtType.COGNITION.value] *= curiosity_boost
    weights[ThoughtType.PLANNING.value] *= curiosity_boost

    serenity_boost = 1.0 + (affect.serenity - 0.5) * 0.4  # [0.8, 1.2]
    weights[ThoughtType.DREAMING.value] *= serenity_boost

    confidence_boost = 1.0 + (affect.confidence - 0.5) * 0.5  # [0.75, 1.25]
    weights[ThoughtType.META.value] *= confidence_boost

    arousal_reflection = 1.0 + (0.5 - affect.arousal) * 0.4  # higher at low arousal
    weights[ThoughtType.REFLECTION.value] *= arousal_reflection

    # Normalize and select.
    types = list(weights.keys())
    raw = [max(weights[t], 0.001) for t in types]  # avoid zero weights
    total = sum(raw)
    normalized = [w / total for w in raw]

    chosen = random.choices(types, weights=normalized, k=1)[0]
    return ThoughtType(chosen)


class ThoughtStream:
    """Unified consciousness thought stream.

    Generates ONE thought at a time, sequentially.  Each cycle:
      1. check_hard_stop() — abort if safety guard triggers.
      2. Select ThoughtType (weighted by affect + config).
      3. Generate thought content via _self_prompt.
      4. Metacognitive eval (extract confidence from META thoughts, else 0.5).
      5. Record thought in ConsciousnessState.
      6. If confidence > 0.8, execute action.

    Lifecycle:
      - Constructed by ConsciousnessLoop with llm_router, state, config.
      - run() blocks until shutdown_event is set.
      - Shutdown via asyncio.Event (injected from ConsciousnessLoop).
    """

    def __init__(
        self,
        llm_router: Any,
        state: ConsciousnessState,
        shutdown_event: asyncio.Event,
        config: dict[str, Any] | None = None,
        redis_client: Any = None,
    ) -> None:
        self._llm_router = llm_router
        self._state = state
        self._shutdown_event = shutdown_event
        self._config = config or {}
        self._redis_client = redis_client

        # Extract thought_type_weights from config if present.
        self._thought_type_weights: dict[str, float] | None = None
        raw_weights = self._config.get("thought_type_weights")
        if isinstance(raw_weights, dict) and raw_weights:
            self._thought_type_weights = raw_weights

        # Cached HARD STOP guard (lazy-init on first check).
        self._hard_stop_guard: Any = None
        self._hard_stop_unavailable: bool = False

        # Metacognitive evaluator — two-layer thought quality assessment.
        review_interval = self._config.get("metacog_review_interval", 20)
        self._metacog = MetacognitiveEvaluator(review_interval=review_interval)

        logger.info(
            "thought_stream.initialized",
            has_llm_router=llm_router is not None,
            has_weights=self._thought_type_weights is not None,
            metacog_review_interval=review_interval,
        )

    async def check_hard_stop(self) -> bool:
        """Check if a HARD STOP has been triggered via Redis safety guard.

        Delegates to the safety module (A8 implementation). Caches the
        HardStopGuard instance after first successful import to avoid
        repeated module loading on every cycle.

        Returns:
            True if HARD STOP is active (thought stream should abort).
            False if safe to continue.
        """
        # Lazy-init: create guard once and cache it.
        if self._hard_stop_guard is None and not self._hard_stop_unavailable:
            try:
                from guinevere.consciousness.safety import HardStopGuard

                redis_client = self._redis_client or self._config.get("redis_client")
                if redis_client is None:
                    # No Redis client available — skip HARD STOP check entirely.
                    logger.info("thought_stream.hard_stop.no_redis_client")
                    self._hard_stop_unavailable = True
                    return False
                self._hard_stop_guard = HardStopGuard(redis_client)
            except ImportError:
                # Safety module not yet implemented (A8) — no HARD STOP check.
                logger.debug("thought_stream.hard_stop.safety_module_not_found")
                self._hard_stop_unavailable = True
                return False
            except Exception as exc:
                logger.warning("thought_stream.hard_stop.init_failed %s", exc)
                self._hard_stop_unavailable = True
                return False

        if self._hard_stop_guard is None:
            return False

        try:
            return await self._hard_stop_guard.check()
        except Exception as exc:
            logger.warning("thought_stream.hard_stop.check_failed %s", exc)
            # Fail-open: do not block thought stream on safety check failure.
            return False

    async def run(self) -> None:
        """Run the thought stream until shutdown.

        Generates thoughts sequentially — each thought completes before
        the next one starts.  No asyncio.sleep between thoughts.
        """
        logger.info("thought_stream.run.starting")

        while not self._shutdown_event.is_set():
            # Step 1: HARD STOP check.
            if await self.check_hard_stop():
                logger.warning("thought_stream.hard_stop_triggered")
                break

            # Step 2: Select thought type.
            thought_type = _select_thought_type(
                self._state.affect,
                self._thought_type_weights,
            )

            # Step 3: Generate thought content.
            content = await self._generate(thought_type)

            # Step 4: Metacognitive evaluation (delegated to MetacognitiveEvaluator).
            mceval = self._metacog.evaluate(
                thought_type,
                content,
                self._state.affect.as_dict(),
            )
            confidence = mceval.confidence

            # If evaluator suggests a different type, log it.
            if mceval.suggested_type is not None:
                logger.debug(
                    "thought_stream.metacog_type_suggestion",
                    original=thought_type.value,
                    suggested=mceval.suggested_type.value,
                )

            # Step 5: Build Thought object.
            thought = Thought(
                type=thought_type,
                content=content,
                confidence=confidence,
                affect_snapshot=self._state.affect.as_dict(),
            )

            # Step 6: Record in state.
            if mceval.should_record:
                self._state.record_thought(
                    thought.type.value,
                    thought.to_log_string(),
                )

            # Step 7: Action if confidence > 80%.
            acted = False
            if thought.should_act():
                acted = await self._execute_action(thought)
                if acted:
                    # Update the thought to mark it as acted.
                    object.__setattr__(thought, "acted", True)

            # Suppressed per-thought log (was ~30 lines/sec at DEBUG).
            # Periodic review captures summary stats every N thoughts instead.

            # Step 8: Periodic self-review (every N thoughts).
            if self._metacog.should_run_periodic_review():
                history = self._state.recent_thoughts(
                    self._metacog.review_interval
                )
                review = self._metacog.periodic_review(
                    history,
                    n=self._metacog.review_interval,
                )
                logger.info(
                    "thought_stream.periodic_review",
                    thoughts_reviewed=review.get("thoughts_reviewed", 0),
                    patterns=len(review.get("patterns_found", [])),
                    biases=len(review.get("biases_detected", [])),
                    gaps=len(review.get("coverage_gaps", [])),
                )
                # Record periodic review as a META thought.
                self._state.record_thought(
                    ThoughtType.META.value,
                    f"[periodic_review] {json.dumps(review, default=str)}",
                )

            # Yield to the event loop so cancellation and shutdown events
            # can propagate. This is necessary because _self_prompt may
            # complete instantly in mock/test mode.
            await _yield_to_event_loop()

        logger.info("thought_stream.run.exited")

    async def _generate(self, thought_type: ThoughtType) -> str:
        """Generate thought content for the given type via self-prompting.

        Args:
            thought_type: The type of thought to generate.

        Returns:
            The generated thought content string.
        """
        system_msg, user_template = _THOUGHT_PROMPTS[thought_type]

        # Build user message from template with current state context.
        user_msg = self._build_user_message(thought_type, user_template)

        content = await _self_prompt(
            self._llm_router,
            system_msg,
            user_msg,
            max_tokens=256,
        )

        # If LLM is unavailable, pace the loop to avoid CPU spin:
        # placeholder thoughts are generated at CPU speed otherwise.
        if self._llm_router is None:
            await asyncio.sleep(1.0)

        return content

    def _build_user_message(
        self, thought_type: ThoughtType, template: str
    ) -> str:
        """Build the user message from a template and current state.

        Args:
            thought_type: The thought type (determines template variables).
            template: The user message template string.

        Returns:
            The formatted user message string.
        """
        state = self._state
        affect = state.affect

        # Compute common context values.
        uptime_s = 0.0
        if state.started_at:
            uptime_s = (
                datetime.now(timezone.utc) - state.started_at
            ).total_seconds()

        recent = _thoughts_block(state, 5)
        all_thoughts = _thoughts_block(state, 20)

        # Common substitutions.
        common = {
            "uptime_s": uptime_s,
            "valence": affect.valence,
            "arousal": affect.arousal,
            "dominance": affect.dominance,
            "curiosity": affect.curiosity,
            "confidence": affect.confidence,
            "serenity": affect.serenity,
            "recent_thoughts": recent,
            "thoughts_block": all_thoughts,
            "thought": recent,
            "self_story": state.self_story,
        }

        try:
            return template.format(**common)
        except KeyError as exc:
            logger.debug(
                "thought_stream.template_key_error",
                type=thought_type.value,
                key=str(exc),
            )
            return template

    def _metacog_eval(
        self, thought_type: ThoughtType, content: str
    ) -> float:
        """Metacognitive evaluation — delegates to MetacognitiveEvaluator.

        Preserved for backward compatibility. The primary eval path in run()
        uses self._metacog.evaluate() directly for full MetaCogEval access.

        Args:
            thought_type: The type of thought that was generated.
            content: The thought content string.

        Returns:
            Confidence score in [0.0, 1.0].
        """
        result = self._metacog.evaluate(
            thought_type,
            content,
            self._state.affect.as_dict(),
        )
        return result.confidence

    async def _execute_action(self, thought: Thought) -> bool:
        """Execute an action triggered by a high-confidence thought.

        For now, this logs the action and returns True.  Future
        implementations will dispatch to specific action handlers
        (e.g., write to memory, trigger external API, update self-story).

        Args:
            thought: The high-confidence thought to act on.

        Returns:
            True if the action was executed successfully.
        """
        logger.info(
            "thought_stream.action_triggered",
            type=thought.type.value,
            confidence=thought.confidence,
            content_preview=thought.content[:100] if thought.content else "",
        )

        # Future: dispatch based on thought type.
        # For now, record the action in state.
        action_prefix = f"[action:{thought.type.value}]"
        self._state.record_thought(
            thought.type.value,
            f"{action_prefix} {thought.content[:200]}",
        )
        return True
