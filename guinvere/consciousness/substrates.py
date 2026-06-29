"""7 Consciousness Substrates — ADR-063 composite architecture.

Each substrate is an async coroutine with its own cadence.  They are
instantiated as methods on ConsciousnessLoop and registered via
substrate_registry.build_registry().

All substrates use MockLLMRouter (D3) for self-prompting.  No real
LLM calls — deterministic responses only.

Cadences (from ADR-063 §5.2):
  heartbeat        : 1s / 10s / 30s / 60s (multi-tier liveness)
  active_cognition : 5m (LLM-light thought pulse)
  reflection       : 1h (memory consolidation)
  strategic_planning : self-triggered (aspiration EWMA pull)
  dreaming         : ~5% of runtime (counterfactual replay)
  metacognition    : C2 continuous (quality assessment)
  emotion_driven   : continuous (EWMA lambda ~0.3)

Failure isolation:
  Exceptions propagate to ConsciousnessLoop._run_substrate() which
  logs and sets FAILED status.  The ``finally`` block only resets to
  IDLE when the substrate completed without error (status still RUNNING).
  CancelledError is always re-raised for TaskGroup / asyncio cancellation.
"""

from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from guinevere.consciousness.loop import ConsciousnessLoop
    from guinevere.consciousness.state import ConsciousnessState

logger = structlog.get_logger("guinevere.consciousness.substrates")


# ── helpers ─────────────────────────────────────────────────


async def _self_prompt(
    llm_router: Any,
    system_msg: str,
    user_msg: str,
    max_tokens: int = 256,
) -> str:
    """Send a self-prompt to the (mock) LLM router and return content.

    Args:
        llm_router: Injected LLM router (MockLLMRouter in tests, D3).
        system_msg: System prompt.
        user_msg: User prompt.
        max_tokens: Max response tokens.

    Returns:
        The LLM response content string.
    """
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]
    result = await llm_router.chat(
        messages=messages,
        task_type="CORE_REASONING",
        max_tokens=max_tokens,
    )
    return result.get("content", "")


def _thoughts_block(state: ConsciousnessState, n: int = 5) -> str:
    """Format recent thoughts as a newline-separated block."""
    thoughts = state.recent_thoughts(n)
    if not thoughts:
        return "(no recent thoughts)"
    return "\n".join(f"- {t}" for t in thoughts)


def _safe_finish(name: str, state: Any, status_enum: Any) -> None:
    """Reset substrate to IDLE only if it was still RUNNING.

    If _run_substrate already set FAILED, do not override.
    """
    current = state.substrate_statuses.get(name)
    if current == status_enum.RUNNING:
        state.set_substrate_status(name, status_enum.IDLE)


# ── heartbeat (1s / 10s / 30s / 60s) ───────────────────────


async def substrate_heartbeat(self: ConsciousnessLoop) -> None:
    """Heartbeat substrate — multi-tier liveness check.

    Tiers: 1s (basic tick), 10s (state snapshot), 30s (affect check),
    60s (full status report).  Each tier logs at its cadence.
    """
    name = "heartbeat"
    self._state.set_substrate_status(name, self._SubstrateStatus.RUNNING)
    tick = 0
    try:
        while not self._shutdown_event.is_set():
            tick += 1
            uptime = 0.0
            if self._state.started_at:
                uptime = (datetime.now(timezone.utc) - self._state.started_at).total_seconds()

            # 1s tier — basic liveness
            content = await _self_prompt(
                self._llm_router,
                self._prompts.HEARTBEAT_SYSTEM,
                self._prompts.HEARTBEAT_USER.format(
                    uptime_s=uptime,
                    valence=self._state.affect.valence,
                ),
                max_tokens=64,
            )
            self._state.record_thought(name, content)

            # 10s tier — state snapshot
            if tick % 10 == 0:
                snap = self._state.snapshot()
                logger.debug("heartbeat.10s_snapshot tick=%d %s", tick, snap)

            # 30s tier — affect check
            if tick % 30 == 0:
                logger.debug(
                    "heartbeat.30s_affect valence=%.2f arousal=%.2f",
                    self._state.affect.valence,
                    self._state.affect.arousal,
                )

            # 60s tier — full status report
            if tick % 60 == 0:
                logger.info("heartbeat.60s_report %s", self._state.snapshot())

            await asyncio.sleep(1)
    except asyncio.CancelledError:
        raise
    finally:
        _safe_finish(name, self._state, self._SubstrateStatus)


# ── active cognition (5m) ───────────────────────────────────


async def substrate_active_cognition(self: ConsciousnessLoop) -> None:
    """Active cognition — 5-minute 'I am thinking X' pulse.

    Generates a brief reflective thought via the LLM, using recent
    thoughts and affect curiosity as context.
    """
    name = "active_cognition"
    self._state.set_substrate_status(name, self._SubstrateStatus.RUNNING)
    try:
        while not self._shutdown_event.is_set():
            content = await _self_prompt(
                self._llm_router,
                self._prompts.ACTIVE_COGNITION_SYSTEM,
                self._prompts.ACTIVE_COGNITION_USER.format(
                    recent_thoughts=_thoughts_block(self._state, 5),
                    curiosity=self._state.affect.curiosity,
                ),
                max_tokens=128,
            )
            self._state.record_thought(name, content)
            await asyncio.sleep(300)  # 5 minutes
    except asyncio.CancelledError:
        raise
    finally:
        _safe_finish(name, self._state, self._SubstrateStatus)


# ── reflection (1h) ─────────────────────────────────────────


async def substrate_reflection(self: ConsciousnessLoop) -> None:
    """Reflection substrate — 1-hour memory consolidation.

    Consolidates recent thoughts into lessons via the LLM.
    """
    name = "reflection"
    self._state.set_substrate_status(name, self._SubstrateStatus.RUNNING)
    try:
        while not self._shutdown_event.is_set():
            content = await _self_prompt(
                self._llm_router,
                self._prompts.REFLECTION_SYSTEM,
                self._prompts.REFLECTION_USER.format(
                    thoughts_block=_thoughts_block(self._state, 20),
                ),
                max_tokens=256,
            )
            self._state.record_thought(name, f"[reflection] {content}")
            await asyncio.sleep(3600)  # 1 hour
    except asyncio.CancelledError:
        raise
    finally:
        _safe_finish(name, self._state, self._SubstrateStatus)


# ── strategic planning (self-triggered, ~24h cadence) ───────


async def substrate_strategic_planning(self: ConsciousnessLoop) -> None:
    """Strategic planning — aspiration-weighted self-triggered planning.

    Runs at ~24h cadence (86400s).  In mock mode this is shortened
    to demonstrate the loop works.  Uses aspiration EWMA pull.
    """
    name = "strategic_planning"
    self._state.set_substrate_status(name, self._SubstrateStatus.RUNNING)
    try:
        while not self._shutdown_event.is_set():
            content = await _self_prompt(
                self._llm_router,
                self._prompts.PLANNING_SYSTEM,
                self._prompts.PLANNING_USER.format(
                    self_story=self._state.self_story,
                    confidence=self._state.affect.confidence,
                    curiosity=self._state.affect.curiosity,
                ),
                max_tokens=256,
            )
            self._state.record_thought(name, f"[plan] {content}")
            # 24h in production; shorter cadence is acceptable for mock/test.
            await asyncio.sleep(86400)
    except asyncio.CancelledError:
        raise
    finally:
        _safe_finish(name, self._state, self._SubstrateStatus)


# ── dreaming (~5% of runtime) ───────────────────────────────


async def substrate_dreaming(self: ConsciousnessLoop) -> None:
    """Dreaming substrate — counterfactual replay (~5% of runtime).

    Sleeps for a randomised interval (simulating ~5% active time),
    then generates a counterfactual scenario from a recent thought.
    """
    name = "dreaming"
    self._state.set_substrate_status(name, self._SubstrateStatus.RUNNING)
    try:
        while not self._shutdown_event.is_set():
            # Sleep to approximate ~5% active ratio (sleep ~19x active).
            # 4-6h staggered per ADR-063; for mock mode use shorter intervals.
            sleep_seconds = random.randint(14400, 21600)  # 4-6h
            await asyncio.sleep(sleep_seconds)

            thought = _thoughts_block(self._state, 1)
            content = await _self_prompt(
                self._llm_router,
                self._prompts.DREAMING_SYSTEM,
                self._prompts.DREAMING_USER.format(
                    thought=thought,
                    serenity=self._state.affect.serenity,
                ),
                max_tokens=256,
            )

            # Parse dream content (best effort).
            try:
                parsed = json.loads(content)
                scenario = parsed.get("scenario", "unknown")
                counterfactual = parsed.get("counterfactual", content)
                insight = parsed.get("insight", "")
            except (json.JSONDecodeError, TypeError):
                scenario = "unstructured dream"
                counterfactual = content
                insight = ""

            from guinevere.consciousness.state import DreamJournalEntry

            self._state.add_dream_entry(
                DreamJournalEntry(
                    timestamp=datetime.now(timezone.utc),
                    scenario=scenario,
                    counterfactual=counterfactual,
                    insight=insight,
                )
            )
            self._state.record_thought(name, f"[dream] {insight or counterfactual[:100]}")
    except asyncio.CancelledError:
        raise
    finally:
        _safe_finish(name, self._state, self._SubstrateStatus)


# ── metacognition (C2 continuous) ───────────────────────────


async def substrate_metacognition(self: ConsciousnessLoop) -> None:
    """Metacognition substrate (C2) — continuous quality assessment.

    Periodically assesses the quality of recent thoughts and suggests
    improvements.  Runs every 30s in continuous mode.
    """
    name = "metacognition"
    self._state.set_substrate_status(name, self._SubstrateStatus.RUNNING)
    try:
        while not self._shutdown_event.is_set():
            content = await _self_prompt(
                self._llm_router,
                self._prompts.METACOGNITION_SYSTEM,
                self._prompts.METACOGNITION_USER.format(
                    thoughts_block=_thoughts_block(self._state, 10),
                ),
                max_tokens=128,
            )
            self._state.record_thought(name, f"[meta] {content}")
            await asyncio.sleep(30)  # C2 continuous — every 30s
    except asyncio.CancelledError:
        raise
    finally:
        _safe_finish(name, self._state, self._SubstrateStatus)


# ── emotion-driven (continuous, EWMA lambda ~0.3) ───────────


async def substrate_emotion_driven(self: ConsciousnessLoop) -> None:
    """Emotion-driven substrate — continuous affect vector maintenance.

    Reads current affect, applies EWMA updates.  When M4 emotion
    provider lands (W7), this substrate will read from it.  For now
    it runs a self-prompt cycle at 60s intervals.
    """
    name = "emotion_driven"
    self._state.set_substrate_status(name, self._SubstrateStatus.RUNNING)
    try:
        while not self._shutdown_event.is_set():
            content = await _self_prompt(
                self._llm_router,
                self._prompts.EMOTION_SYSTEM,
                self._prompts.EMOTION_USER.format(
                    valence=self._state.affect.valence,
                    arousal=self._state.affect.arousal,
                    curiosity=self._state.affect.curiosity,
                    recent_thoughts=_thoughts_block(self._state, 3),
                ),
                max_tokens=128,
            )

            # Attempt to parse affect updates from the LLM response.
            try:
                parsed = json.loads(content)
                self._state.affect.ewma_update(
                    {
                        k: float(parsed[k])
                        for k in ("valence", "arousal", "curiosity")
                        if k in parsed
                    },
                    lam=0.3,
                )
            except (json.JSONDecodeError, TypeError, KeyError, ValueError):
                # Stub mode — no real affect update; just log.
                logger.debug("emotion_driven.stub_mode — no affect update parsed")

            self._state.record_thought(name, f"[emotion] {content[:100]}")
            await asyncio.sleep(60)  # 1-minute continuous cycle
    except asyncio.CancelledError:
        raise
    finally:
        _safe_finish(name, self._state, self._SubstrateStatus)
