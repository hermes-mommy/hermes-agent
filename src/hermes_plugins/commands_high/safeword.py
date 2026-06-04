"""Hermes command plugin — /safeword.

Migrated from src/discord/cmd_safeword.py for Phase 2 Discord migration.
Triggers the HARD STOP protocol via HardStopHandler.
Preserves the 9-step safety workflow.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from src.core.services.hard_stop_handler import HardStopHandler

logger = logging.getLogger(__name__)

# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))

# ── Constants ───────────────────────────────────────────────────────────────

SAFEWORD_TITLE: Final[str] = "\U0001f6e1 Safe Mode Active"
SAFEWORD_DESCRIPTION: Final[str] = (
    "Mommy di sini. Netral. Tidak ada judgment. Kamu aman."
)
FOOTER_TEXT: Final[str] = "Guinevere de Baroque \u2022 Safety First"

RESUME_PHRASES: Final[str] = (
    '\u201cresume\u201d, \u201caku sudah okay\u201d, '
    '\u201clanjut persona\u201d, or \u201csafe mode selesai\u201d'
)

# ── Handler Singleton ────────────────────────────────────────────────────────

_handler: HardStopHandler | None = None


def _get_handler() -> HardStopHandler:
    """Return the module-level HardStopHandler singleton."""
    global _handler  # noqa: PLW0603
    if _handler is None:
        _handler = _new_handler()
    return _handler


def _new_handler() -> HardStopHandler:
    """Create a fresh HardStopHandler instance."""
    from src.core.services.hard_stop_handler import HardStopHandler

    return HardStopHandler()


def set_handler(handler: HardStopHandler) -> None:
    """Override the module-level handler singleton (for tests / determinism)."""
    global _handler  # noqa: PLW0603
    _handler = handler


# ── Helpers ─────────────────────────────────────────────────────────────────


def _format_wib_timestamp(dt: datetime) -> str:
    """Format a datetime as ``"2026-06-01 15:30 WIB"``."""
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


# ── Markdown Formatter ──────────────────────────────────────────────────────


def _format_safeword_markdown(
    now: datetime | None = None,
) -> str:
    """Build the /safeword response as a markdown-formatted string.

    Replicates all 6 embed fields from cmd_safeword.py in markdown.
    """
    ref = now if now is not None else datetime.now(tz=timezone.utc)
    ts_str = _format_wib_timestamp(ref)

    lines: list[str] = [
        f"# {SAFEWORD_TITLE}",
        "",
        SAFEWORD_DESCRIPTION,
        "",
        "| Field | Value |",
        "|---|---|",
        "| Status | Safe mode active |",
        "| Persona | Neutral / supportive |",
        "| Punishment | Paused |",
        "| Yandere | Y0 |",
        "| Surveillance Confrontation | Paused |",
        f"| Resume | {RESUME_PHRASES} |",
        "",
        f"\u2014 {FOOTER_TEXT} \u2022 {ts_str}",
    ]
    return "\n".join(lines)


# ── Plugin Registration ─────────────────────────────────────────────────────


def register(ctx: Any) -> None:
    """Register /safeword command with Hermes plugin context."""

    @ctx.register_command(
        "safeword",
        description="Trigger the configured safety boundary workflow.",
    )
    async def handle(context: Any) -> str:
        """Handle /safeword invocation.

        Triggers the HardStopHandler to activate safe mode (9-step protocol).
        """
        try:
            handler = _get_handler()
            handler.check("safeword")
            logger.info(
                "slash_safeword_triggered",
                extra={
                    "source": "hermes_plugin",
                    "user_id": str(getattr(context, "user_id", "unknown")),
                },
            )
            return _format_safeword_markdown()
        except Exception as exc:
            logger.exception(
                "safeword_command_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            return (
                "\u26a0\ufe0f Safe mode could not be activated through this command. "
                "Mommy tetap di sini. Kamu aman, Darling."
            )