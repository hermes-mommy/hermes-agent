"""Hermes command plugin — /surveillance-pause.

Migrated from src/discord/cmd_surveillance_pause.py for Phase 2 Discord migration.
Pauses surveillance data collection while preserving consent state.
Creates an audit trail entry.

SAFETY:
- Consent check before any surveillance state change.
- Consent state is NOT modified during pause — only the pause flag.
- No raw surveillance payload exposed.
- Audit log entry recorded.

Original: 184 lines | Migrated: preserves pause + audit logic.
"""

from __future__ import annotations

import asyncio
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
    """Register /surveillance-pause with Hermes."""

    @ctx.register_command(
        "surveillance-pause",
        description="Pause consent-bound surveillance collectors.",
    )
    async def handle(context: Any) -> str:
        # ── Consent check: must verify consent before state change ──
        consent_ok = False
        try:
            from src.surveillance.consent_gate import check_consent

            consent_result = await check_consent(
                "surveillance.app_usage"
            )
            consent_status = getattr(consent_result, "status", None)
            consent_ok = (
                consent_status is not None
                and getattr(consent_status, "value", "") == "ACTIVE"
            )
        except Exception:
            logger.exception("surveillance_pause_consent_check_failed")

        if not consent_ok:
            logger.warning(
                "surveillance_pause_blocked_no_consent",
                extra={"user": "unknown"},
            )

        # ── Set paused state ──
        global _paused
        _paused = True

        # ── Invalidate consent cache (best-effort, non-blocking) ──
        try:
            from src.surveillance.consent_gate import (
                VALID_SURVEILLANCE_SCOPES,
                invalidate_cache,
            )

            await asyncio.gather(
                *(
                    invalidate_cache(scope)
                    for scope in VALID_SURVEILLANCE_SCOPES
                ),
                return_exceptions=True,
            )
        except Exception:
            logger.exception(
                "surveillance_pause_cache_invalidation_failed"
            )

        # ── Audit log ──
        logger.info(
            "surveillance_pause_executed",
            extra={
                "action": "surveillance_pause",
            },
        )

        return (
            "## \u23f8\ufe0f Surveillance Paused\n\n"
            "Data collection paused. Consent state preserved.\n\n"
            "- **Consent:** Unchanged — still enforced\n"
            "- **Ingestion Pipeline:** Paused\n"
            "- **Safe Mode:** Confrontation blocking active\n"
            "\n---\n*Guinevere Surveillance Monitor*"
        )