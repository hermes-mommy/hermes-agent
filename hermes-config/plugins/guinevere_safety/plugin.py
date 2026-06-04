"""Guinevere Safety Plugin — Hook handlers and command handlers.

Provides:
  - inject_dynamic_state (pre_prompt hook, priority 95): Injects current
    persona state (punishment, reward, distress, mood, yandere level)
    into the prompt context before LLM invocation.
  - update_state (post_response hook, priority 55): Records interaction
    timestamp and daily counter after each response.
  - Command handlers for state introspection and mutation.
"""

from __future__ import annotations

import logging
from typing import Any

from .state_manager import (
    DEFAULT_STATE,
    DISTRESS_DESCRIPTIONS,
    PUNISHMENT_DESCRIPTIONS,
    REWARD_DESCRIPTIONS,
    YANDERE_LABELS,
    StateManager,
)

logger = logging.getLogger("guinevere_safety.plugin")

# Re-export descriptions for use by other modules
__all__ = [
    "GuinevereSafetyPlugin",
    "PUNISHMENT_DESCRIPTIONS",
    "REWARD_DESCRIPTIONS",
    "DISTRESS_DESCRIPTIONS",
    "YANDERE_LABELS",
]


class GuinevereSafetyPlugin:
    """Hermes plugin for dynamic persona state management.

    Handles pre-prompt state injection and post-response state updates.
    Exposes command handlers for state introspection and mutation.
    """

    def __init__(self) -> None:
        self.state_manager = StateManager()
        self._init_state()

    def _init_state(self) -> None:
        """Ensure Redis state is initialized on first load."""
        ok = self.state_manager.ensure_initialized()
        if ok:
            logger.info("GuinevereSafetyPlugin initialized — Redis DB5 state ready.")
        else:
            logger.warning(
                "GuinevereSafetyPlugin loaded but Redis DB5 unavailable. "
                "State operations will return safe defaults."
            )

    # ==================================================================
    # Hook Handlers
    # ==================================================================

    def inject_dynamic_state(self, context: dict[str, Any]) -> dict[str, Any]:
        """Inject dynamic persona state into prompt context. (pre_prompt, priority 95)

        Called before the prompt is sent to the LLM. Reads current state from
        Redis DB5 and injects it as additional system context so the LLM knows
        the current punishment level, reward tier, distress state, mood, and
        yandere baseline.
        """
        state = self.state_manager.get_state()

        pun_level: int = state["punishment_level"]
        rew_tier: int = state["reward_tier"]
        dis_state: int = state["distress_state"]
        mood: str = state["mood_variant"]
        yan: int = state["yandere_level"]
        last: str = state["last_interaction"] or "(none)"
        count: int = state["interaction_count"]

        state_injection = f"""
[Dynamic Persona State — Current]
- Punishment Level: L{pun_level} — {PUNISHMENT_DESCRIPTIONS.get(pun_level, 'Unknown')}
- Reward Tier: T{rew_tier} — {REWARD_DESCRIPTIONS.get(rew_tier, 'Unknown')}
- Distress State: D{dis_state} — {DISTRESS_DESCRIPTIONS.get(dis_state, 'Unknown')}
- Mood: {mood.capitalize()}
- Yandere Level: Y{yan} ({YANDERE_LABELS.get(yan, 'Unknown')}) — IMMUTABLE BASELINE
- Last Interaction: {last}
- Daily Interactions: {count}
"""

        # Inject into context so Hermes appends it to the system prompt
        context["system_append"] = state_injection.strip()
        logger.debug("Injected dynamic persona state into pre_prompt context.")
        return context

    def update_state(self, context: dict[str, Any]) -> dict[str, Any]:
        """Update state after response is generated. (post_response, priority 55)

        Records the interaction timestamp and increments the daily counter.
        Future enhancement: analyze response for state changes
        (e.g., if Faiz gave praise → increment reward).
        """
        self.state_manager.record_interaction()
        logger.debug("Recorded post_response interaction.")
        return context

    # ==================================================================
    # Command Handlers
    # ==================================================================

    def cmd_get_state(self, args: list[str]) -> str:
        """Return full persona state as formatted text."""
        state = self.state_manager.get_state()

        lines: list[str] = [
            "=== Guinevere Persona State ===",
            "",
            f"Punishment Level: L{state['punishment_level']} — "
            f"{PUNISHMENT_DESCRIPTIONS.get(state['punishment_level'], 'Unknown')}",
            f"Reward Tier:      T{state['reward_tier']} — "
            f"{REWARD_DESCRIPTIONS.get(state['reward_tier'], 'Unknown')}",
            f"Distress State:   D{state['distress_state']} — "
            f"{DISTRESS_DESCRIPTIONS.get(state['distress_state'], 'Unknown')}",
            f"Mood:             {state['mood_variant'].capitalize()}",
            f"Yandere Level:    Y{state['yandere_level']} "
            f"({YANDERE_LABELS.get(state['yandere_level'], 'Unknown')}) — IMMUTABLE",
            f"Last Interaction: {state['last_interaction'] or '(none)'}",
            f"Daily Count:      {state['interaction_count']}",
            f"Safe Word:        {state['safe_word']}",
            "",
        ]

        # Include DNR list
        dnr = self.state_manager.get_dnr_list()
        if dnr:
            lines.append(f"DNR Topics ({len(dnr)}):")
            for topic in dnr:
                lines.append(f"  - {topic}")
        else:
            lines.append("DNR Topics: (none)")

        return "\n".join(lines)

    def cmd_set_punishment(self, args: list[str]) -> str:
        """Set punishment level. Usage: set_punishment <0-5>"""
        if not args:
            return "ERROR: Usage: set_punishment <level 0-5>"

        try:
            level = int(args[0])
        except ValueError:
            return f"ERROR: Invalid level '{args[0]}' — must be an integer 0-5."

        if level > 5:
            return (
                f"REJECTED: Punishment level L{level} is PROHIBITED. "
                f"L6 is DEFERRED — maximum is L5."
            )

        ok = self.state_manager.set_punishment(level)
        if ok:
            return (
                f"Punishment level set to L{level} — "
                f"{PUNISHMENT_DESCRIPTIONS.get(level, 'Unknown')}."
            )
        return "ERROR: Failed to set punishment level (Redis unavailable)."

    def cmd_set_reward(self, args: list[str]) -> str:
        """Set reward tier. Usage: set_reward <0-5>"""
        if not args:
            return "ERROR: Usage: set_reward <tier 0-5>"

        try:
            tier = int(args[0])
        except ValueError:
            return f"ERROR: Invalid tier '{args[0]}' — must be an integer 0-5."

        if tier > 5:
            return f"REJECTED: Reward tier T{tier} exceeds maximum T5."

        ok = self.state_manager.set_reward(tier)
        if ok:
            return (
                f"Reward tier set to T{tier} — "
                f"{REWARD_DESCRIPTIONS.get(tier, 'Unknown')}."
            )
        return "ERROR: Failed to set reward tier (Redis unavailable)."

    def cmd_set_mood(self, args: list[str]) -> str:
        """Set mood variant. Usage: set_mood <default|playful|serious|caring>"""
        if not args:
            return "ERROR: Usage: set_mood <default|playful|serious|caring>"

        variant = args[0].lower()
        ok = self.state_manager.set_mood(variant)
        if ok:
            return f"Mood set to: {variant.capitalize()}."
        return (
            f"ERROR: Invalid mood '{variant}'. "
            f"Must be one of: default, playful, serious, caring."
        )

    def cmd_get_distress(self, args: list[str]) -> str:
        """Return current distress state."""
        state = self.state_manager.get_state()
        dis_level: int = state["distress_state"]
        desc = DISTRESS_DESCRIPTIONS.get(dis_level, "Unknown")
        return f"Current Distress State: D{dis_level} — {desc}."

    # ==================================================================
    # Plugin lifecycle
    # ==================================================================

    def on_load(self) -> bool:
        """Called when the plugin is loaded by Hermes."""
        logger.info("GuinevereSafetyPlugin.on_load() — critical plugin active.")
        return self.state_manager.ensure_initialized()

    def on_unload(self) -> None:
        """Called when the plugin is unloaded."""
        logger.info("GuinevereSafetyPlugin.on_unload() — plugin shutting down.")
        if self.state_manager._redis is not None:
            try:
                self.state_manager._redis.close()
            except Exception as exc:
                logger.warning("Error closing Redis connection during unload: %s", exc)