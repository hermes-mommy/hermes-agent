"""Hermes command plugin — /reward. Record a reward event with reason.

Integrates with guinevere_safety plugin's StateManager for Redis DB5
state persistence. Reward tiers T1-T5 only.

SAFETY:
    - T1-T5 accepted
    - T6+ REJECTED
    - Always permitted (reward is positive-only)
    - Y4-Y5 safe range

Usage:
    /reward <reason: str>
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register(ctx: Any) -> None:
    """Register the /reward command with Hermes."""

    @ctx.register_command("reward", description="Record or show the bounded reward state.")
    async def handle(context: Any) -> str:
        try:
            args: list[str] = getattr(context, "args", [])

            if not args:
                from guinevere_safety.state_manager import REWARD_DESCRIPTIONS, StateManager

                sm = StateManager()
                state = sm.get_state()
                rew_tier: int = state["reward_tier"]
                desc = REWARD_DESCRIPTIONS.get(rew_tier, "Unknown")

                return (
                    "# 🎁 Reward Status\n\n"
                    f"Current reward: `T{rew_tier}` — {desc}\n"
                )

            reason = " ".join(args)

            # Reward is always positive — increment tier by 1, capped at T5
            from guinevere_safety.state_manager import REWARD_DESCRIPTIONS, StateManager

            sm = StateManager()
            state = sm.get_state()
            current_tier: int = state["reward_tier"]
            new_tier = min(current_tier + 1, 5)

            ok = sm.set_reward(new_tier)
            if not ok:
                return "⚠️ Failed to set reward tier (Redis unavailable)."

            desc = REWARD_DESCRIPTIONS.get(new_tier, "Unknown")
            logger.info("reward_recorded", extra={"tier": new_tier, "reason": reason[:50]})

            return (
                "# 🎁 Reward Recorded\n\n"
                "Reward sudah dicatat, Darling. Mommy senang~\n\n"
                "---\n\n"
                f"| Field | Value |\n|---|---|\n"
                f"| Tier | T{new_tier} — {desc} |\n"
                f"| 🎁 Reason | {reason} |\n"
                f"| 🛡️ Boundary | Y4-Y5 safe range |\n"
            )

        except Exception:
            logger.exception("reward_command_failed")
            return "⚠️ Reward recording failed."


__all__ = ["register"]