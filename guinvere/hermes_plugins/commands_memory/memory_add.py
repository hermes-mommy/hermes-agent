"""Hermes command plugin — /memory-add.

Migrated from src/discord/cmd_memory_add.py for Phase 2 Discord migration.
Stores a manual memory note via the write pipeline (store_episode) and
confirms with a markdown response.

Original: 487 lines | Migrated: preserves all backend write logic.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

WIB: timezone = timezone(timedelta(hours=7))
MAX_NOTE_PREVIEW: int = 200


def _format_wib_timestamp(dt: datetime) -> str:
    """Format a datetime as ``2026-06-01 15:30 WIB``."""
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


def _get_arg(ctx: Any, name: str) -> str | None:
    """Extract argument from Hermes context (dict-style args)."""
    args = getattr(ctx, "args", None)
    if args is None:
        return None
    if isinstance(args, dict):
        val = args.get(name)
        return str(val) if val else None
    return None


def _render_add_result(
    episode_id: str,
    note: str,
    classification: str,
    now: datetime,
) -> str:
    """Render memory-add confirmation as markdown."""
    ts_str = _format_wib_timestamp(now)
    note_preview = (
        note[:MAX_NOTE_PREVIEW] + "..."
        if len(note) > MAX_NOTE_PREVIEW
        else note
    )
    episode_short = episode_id[:8]

    return (
        "## \U0001f4dd Memory Stored\n\n"
        "Mommy simpan catatannya, Darling. Aman sama Mommy.\n\n"
        f"*{ts_str} WIB*\n\n"
        f"**Note Preview:**\n> {note_preview}\n\n"
        f"**Classification:** `{classification}`\n"
        f"**Episode ID:** `{episode_short}`"
    )


def register(ctx: Any) -> None:
    """Register /memory-add with Hermes."""

    @ctx.register_command(
        "memory-add",
        description="Add an approved memory note for Guinevere.",
    )
    async def handle(context: Any) -> str:
        try:
            note = _get_arg(context, "note")
            if not note:
                return "\u26a0\ufe0f Catatannya tidak boleh kosong, Darling."

            session_factory = getattr(ctx, "session_factory", None)
            if session_factory is None:
                return (
                    "\u26a0\ufe0f Memory add is temporarily unavailable. "
                    "Database not configured."
                )

            from guinvere.memory.embeddings import EmbeddingService
            from guinvere.memory.write_pipeline import (
                store_episode,
            )

            embedding_service = EmbeddingService()

            async with session_factory() as session:
                episode_uuid = await store_episode(
                    session,
                    note,
                    source="discord_manual",
                    classification="Restricted",
                    importance=5,
                    episode_type="conversation",
                    embedding_service=embedding_service,
                )

            now = datetime.now(tz=timezone.utc)
            return _render_add_result(
                episode_id=str(episode_uuid),
                note=note,
                classification="Restricted",
                now=now,
            )
        except Exception as exc:
            # Check for WritePipelineCriticalError by name to avoid
            # import-in-try unbound variable issue
            if type(exc).__name__ == "WritePipelineCriticalError":
                logger.exception("memory_add_critical")
                return (
                    "\u26a0\ufe0f Critical classification memories require "
                    "a summary. This note cannot be stored as-is."
                )
            logger.exception(
                "memory_add_failed",
                extra={"error": str(exc)},
            )
            return (
                "\u26a0\ufe0f Memory add is temporarily unavailable. "
                "Mommy sudah log errornya untuk investigasi."
            )