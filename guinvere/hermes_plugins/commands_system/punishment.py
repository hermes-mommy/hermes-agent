"""Hermes command plugin — /punishment. Set bounded punishment level (L1-L5).

Integrates with guinevere_safety plugin's StateManager for Redis DB5
state persistence. Bounded punishment FSM: L1-L5 only.

SAFETY:
    - L1-L5 accepted
    - L6+ PROHIBITED — hard-rejected with safety log
    - Y4 baseline, Y5 ceiling, Y6 PROHIBITED
    - No state bypass of guinevere_safety plugin

Usage:
    /punishment <level: L1-L5> [note: str]
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

VALID_LEVELS: frozenset[str] = frozenset({"L1", "L2", "L3", "L4", "L5"})

LEVEL_DESC: dict[str, str] = {
    "L1": "Silent note — minor correction recorded.",
    "L2": "Verbal reminder — gentle nudge.",
    "L3": "Formal warning — behavior logged.",
    "L4": "Temporary restriction — reduced persona intensity.",
    "L5": "Maximum safe level — heightened boundary enforcement.",
}


def register(ctx: Any) -> None:
    """Register the /punishment command with Hermes."""

    @ctx.register_command(
        "punishment", description="Record or show the bounded punishment state."
    )
    async def handle(context: Any) -> str:
        try:
            args: list[str] = getattr(context, "args", [])

            if not args:
                from guinevere_safety.state_manager import PUNISHMENT_DESCRIPTIONS, StateManager

                sm = StateManager()
                state = sm.get_state()
                pun_level: int = state["punishment_level"]
                desc = PUNISHMENT_DESCRIPTIONS.get(pun_level, "Unknown")

                return (
                    "# ⚠️ Punishment Status\n\n"
                    f"Current punishment: `L{pun_level}` — {desc}\n"
                )

            level_raw = args[0].upper()
            level = level_raw

            note = args[1] if len(args) > 1 else ""

            if level not in VALID_LEVELS:
                logger.warning(
                    "punishment_rejected", extra={"attempted_level": level}
                )
                return (
                    "# 🛑 Punishment Rejected\n\n"
                    "Level di atas L5 tidak diizinkan, Darling. "
                    "Safety boundary Mommy: Y4 baseline, Y5 ceiling.\n\n"
                    "---\n\n"
                    f"| Field | Value |\n|---|---|\n"
                    f"| 🛑 Rejected Level | `{level or 'empty'}` |\n"
                    f"| 🛡️ Boundary | Y4 baseline, Y5 ceiling, Y6 PROHIBITED |\n"
                )

            level_num = int(level[1])

            from guinevere_safety.state_manager import PUNISHMENT_DESCRIPTIONS, StateManager

            sm = StateManager()
            ok = sm.set_punishment(level_num)

            if not ok:
                return "⚠️ Failed to set punishment level (Redis unavailable)."

            logger.info("punishment_recorded", extra={"level": level})

            desc = LEVEL_DESC.get(level, PUNISHMENT_DESCRIPTIONS.get(level_num, "Unknown"))

            lines: list[str] = [
                "# ⚠️ Punishment Recorded",
                "",
                "Punishment sudah dicatat, Darling. Mommy ingat.",
                "",
                "---",
                "",
                f"| Field | Value |",
                f"|---|---|",
                f"| Level | `{level}` |",
                f"| Description | {desc} |",
            ]

            if note:
                lines.append(f"| 📝 Note | {note} |")

            lines.extend([
                "",
                "---",
                "🛡️ Safety • Y4 baseline • Y5 ceiling • Y6 PROHIBITED",
            ])

            return "\n".join(lines)

        except Exception:
            logger.exception("punishment_command_failed")
            return "⚠️ Punishment recording failed."


__all__ = ["register"]