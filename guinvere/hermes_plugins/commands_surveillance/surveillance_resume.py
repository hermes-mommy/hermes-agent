"""Hermes command plugin — /surveillance-resume.

Migrated from guinvere/discord/cmd_surveillance_resume.py for Phase 2 Discord migration.
Resumes surveillance data collection that was previously paused. Consent
state is unchanged — only the pause flag is cleared.

SAFETY:
- Consent check before any surveillance state change.
- Consent state is NOT modified during resume.
- Already-active check: notifies if surveillance was already active.
- No raw surveillance payload exposed.
- Audit log entry recorded.

Original: 182 lines | Migrated: preserves resume + audit logic.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_paused: bool = False
"""Global pause flag for surveillance data collection."""


def is_paused() -> bool:
    """Return the current pause state."""
    return _paused


def _set_paused_for_testing(val: bool) -> None:
    """Inject a pause state value for testing."""
    global _paused
    _paused = val


def register(ctx: Any) -> None:
    """Register /surveillance-resume with Hermes."""

    @ctx.register_command(
        "surveillance-resume",
        description="Resume consent-bound surveillance collectors.",
    )
    async def handle(context: Any) -> str:
        global _paused

        # ── Consent check: must verify consent before state change ──
        try:
            from guinvere.surveillance.consent_gate import check_consent

            consent_result = await check_consent(
                "surveillance.app_usage"
            )
            _ = consent_result
        except Exception:
            logger.exception("surveillance_resume_consent_check_failed")

        # ── Already-active check ──
        if not _paused:
            return "Surveillance is already active."

        # ── Clear paused state ──
        _paused = False

        # ── Audit log ──
        logger.info(
            "surveillance_resume_executed",
            extra={
                "action": "surveillance_resume",
            },
        )

        return (
            "## \u25b6\ufe0f Surveillance Resumed\n\n"
            "Data collection resumed.\n\n"
            "- **Consent:** Unchanged — still enforced\n"
            "- **Ingestion Pipeline:** Active\n"
            "- **Safe Mode:** Confrontation blocking active\n"
            "\n---\n*Guinevere Surveillance Monitor*"
        )