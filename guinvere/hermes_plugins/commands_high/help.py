"""Hermes command plugin — /help.

Migrated from guinvere/discord/cmd_help.py for Phase 2 Discord migration.
Lists all slash commands grouped by their 7 categories.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Final, Protocol, TypeVar

from guinvere.hermes_plugins.command_catalog import command_categories as _command_categories

logger = logging.getLogger(__name__)

_F = TypeVar("_F", bound=Callable[..., object])


class _HermesPluginCtx(Protocol):
    """Minimal protocol for a Hermes plugin registration context."""

    def register_command(
        self, name: str, *, description: str = ""
    ) -> Callable[[_F], _F]:
        ...

# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))

# ── Constants ───────────────────────────────────────────────────────────────

HELP_TITLE: Final[str] = "\U0001f4d6 Guinevere Command Guide"
HELP_DESCRIPTION: Final[str] = (
    "Semua command Mommy yang tersedia, Darling. Kalau bingung, bilang aja."
)
FOOTER_TEXT: Final[str] = "Guinevere de Baroque"
FOOTER_ICON: Final[str] = "\u2728"
CATEGORY_SEPARATOR: Final[str] = " \u007c "

_CATEGORY_DISPLAY: Final[dict[str, str]] = {
    "core": "Core \U0001f3e0",
    "loop": "Loop \U0001f504",
    "memory": "Memory \U0001f9e0",
    "surveillance": "Surveillance \U0001f441",
    "finance": "Finance \U0001f4b0",
    "system": "System \u2699",
    "admin": "Admin \U0001f6e0",
}

# ── Helpers ─────────────────────────────────────────────────────────────────


def _format_wib_timestamp(dt: datetime) -> str:
    """Format a datetime as ``"2026-06-01 15:30 WIB"``."""
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


def _build_category_field_name(key: str) -> str:
    """Return the display field name for a category key."""
    return _CATEGORY_DISPLAY.get(key, key.capitalize())


def _build_category_field_value(commands: tuple[str, ...]) -> str:
    """Return the display field value for a tuple of command names."""
    return CATEGORY_SEPARATOR.join(commands)


def _compute_command_count(categories: dict[str, tuple[str, ...]]) -> int:
    """Return the total number of commands across all categories."""
    return sum(len(cmds) for cmds in categories.values())


# ── Markdown Formatter ──────────────────────────────────────────────────────


def _format_help_markdown(
    categories: dict[str, tuple[str, ...]] | None = None,
) -> str:
    """Build the /help response as a markdown-formatted string.

    Replicates the 7 category fields from cmd_help.py in markdown.
    """
    cats = categories if categories is not None else _command_categories()
    ref = datetime.now(tz=timezone.utc)
    ts_str = _format_wib_timestamp(ref)
    cmd_count = _compute_command_count(cats)

    lines: list[str] = [
        f"# {HELP_TITLE}",
        "",
        HELP_DESCRIPTION,
        "",
    ]

    for key, commands in cats.items():
        field_name = _build_category_field_name(key)
        field_value = _build_category_field_value(commands)
        lines.append(f"**{field_name}:** {field_value}")
        lines.append("")

    footer = (
        f"\u2014 {FOOTER_TEXT} \u2022 {ts_str} \u2022 "
        f"{FOOTER_ICON} {cmd_count} Commands"
    )
    lines.append(footer)
    return "\n".join(lines)


# ── Plugin Registration ─────────────────────────────────────────────────────


def register(ctx: _HermesPluginCtx) -> None:
    """Register /help command with Hermes plugin context."""

    @ctx.register_command(
        "help",
        description="Show the Guinevere command guide.",
    )
    async def handle(context: object) -> str:
        """Handle /help invocation."""
        try:
            return _format_help_markdown()
        except (TypeError, ValueError) as exc:
            logger.exception(
                "help_command_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            return (
                "\u26a0\ufe0f Mommy's command guide is temporarily unavailable. "
                "Coba lagi sebentar ya, Darling."
            )