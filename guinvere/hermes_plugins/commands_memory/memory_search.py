"""Hermes command plugin — /memory-search.

Migrated from guinvere/discord/cmd_memory_search.py for Phase 2 Discord migration.
Uses HermesMemoryBridge.recall_for_context() for memory recall with
DNR exclusion, classification ceiling, and safe-mode support.

Original: 493 lines | Migrated: preserves all backend recall logic.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

WIB: timezone = timezone(timedelta(hours=7))
DEFAULT_LIMIT: int = 10


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


def _render_results(
    results: list[dict[str, object]],
    query: str,
    now: datetime,
) -> str:
    """Render memory recall results as markdown."""
    ts_str = _format_wib_timestamp(now)
    lines: list[str] = [
        "## \U0001f50d Memory Search",
        "",
        f"*{ts_str} WIB*",
        "",
    ]

    if not results:
        lines.append(
            "Mommy tidak menemukan apa-apa untuk query itu, Darling."
        )
        lines.append(f"\n**Query:** `{query}`")
        return "\n".join(lines)

    lines.append(
        "Ini hasilnya, Darling. Mommy cari yang terbaik untukmu."
    )
    lines.append("")

    for i, result in enumerate(results):
        content = str(result.get("safe_content", ""))
        score = result.get("combined_score", 0.0)
        truncated = content[:100] + "..." if len(content) > 100 else content
        lines.append(f"**#{i + 1}** (score: `{score:.2f}`)")
        lines.append(f"> {truncated}")
        lines.append("")

    lines.append(f"**Query:** `{query}`")
    lines.append(f"**Results:** {len(results)}")
    return "\n".join(lines)


def register(ctx: Any) -> None:
    """Register /memory-search with Hermes."""

    @ctx.register_command(
        "memory-search",
        description="Search Guinevere's approved memory index.",
    )
    async def handle(context: Any) -> str:
        try:
            query = _get_arg(context, "query")
            if not query:
                return "\u26a0\ufe0f Query tidak boleh kosong, Darling."

            # Use HermesMemoryBridge for recall with DNR exclusion
            bridge = getattr(ctx, "memory_bridge", None)
            if bridge is None:
                # Fallback: try direct recall pipeline via session factory
                session_factory = getattr(ctx, "session_factory", None)
                if session_factory is None:
                    return (
                        "\u26a0\ufe0f Memory search is temporarily "
                        "unavailable. Database not configured."
                    )

                from guinvere.memory.embeddings import EmbeddingService
                from guinvere.memory.read_pipeline import recall_memories

                embedding_service = EmbeddingService()

                async with session_factory() as session:
                    results = await recall_memories(
                        session,
                        query,
                        limit=DEFAULT_LIMIT,
                        exclude_dnr=True,
                        safe_mode=False,
                        principal="guinevere_core",
                        embedding_service=embedding_service,
                    )
            else:
                results = await bridge.recall_for_context(
                    query,
                    safe_mode=False,
                    principal="guinevere_core",
                    limit=DEFAULT_LIMIT,
                )

            now = datetime.now(tz=timezone.utc)
            return _render_results(results, query, now)

        except Exception as exc:
            logger.exception(
                "memory_search_failed",
                extra={"error": str(exc)},
            )
            return (
                "\u26a0\ufe0f Memory search is temporarily unavailable. "
                "Mommy sudah log errornya untuk investigasi."
            )