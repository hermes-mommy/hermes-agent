"""Discord /memory-export command implementation for Guinevere (RG-010).

Exports memories as JSON, sent via DM (NOT public channel — safety
requirement).  Uses the async session factory from bot.

Usage:
    /memory-export limit:int=50
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import structlog

from .colors import PRIMARY
from ._embed_utils import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    get_option_value,
    now_wib_str,
    send_denied,
    to_discord_embed,
)

logger = structlog.get_logger()

EXPORT_TITLE: str = "\U0001f4e6 Memory Export"
EXPORT_OK_DESC: str = "Memories sudah dikirim via DM, Darling."
EXPORT_EMPTY_DESC: str = "Tidak ada memories untuk di-export, Darling."
FOOTER_ICON: str = "\U0001f9e0 Memory"

DEFAULT_LIMIT: int = 50
MAX_LIMIT: int = 200


@dataclass(frozen=True)
class ExportResult:
    """Result of a memory-export operation."""

    count: int
    records: list[dict[str, Any]]
    error: str | None = None


# ── Database Operation ──────────────────────────────────────────────────────


async def _fetch_memories(session_factory: Any, limit: int) -> ExportResult:
    """Fetch memory records for export.

    Only exports non-DNR memories with safe fields (id, content hash,
    classification, created_at).  Never exports raw content in plaintext
    to logs.

    Args:
        session_factory: Async SQLAlchemy session factory.
        limit: Maximum number of records.

    Returns:
        ExportResult with records or error.
    """
    try:
        from sqlalchemy import text

        async with session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT id, classification, created_at, "
                    "LENGTH(content) AS content_length "
                    "FROM memories "
                    "WHERE dnr = false "
                    "ORDER BY created_at DESC "
                    "LIMIT :lim"
                ),
                {"lim": limit},
            )
            rows = result.fetchall()

            records: list[dict[str, Any]] = []
            for row in rows:
                records.append(
                    {
                        "id": str(row[0]),
                        "classification": str(row[1]) if row[1] else "unclassified",
                        "created_at": str(row[2]) if row[2] else "",
                        "content_length": int(row[3]) if row[3] else 0,
                    }
                )

            logger.info("memory_export_fetched", count=len(records))
            return ExportResult(count=len(records), records=records)
    except Exception as exc:
        logger.exception("memory_export_db_error")
        return ExportResult(count=0, records=[], error=str(exc))


# ── Embed Builder ───────────────────────────────────────────────────────────


def _build_embed_data(result: ExportResult, limit: int) -> EmbedData:
    """Build embed data from an export result."""
    ts = now_wib_str()

    if result.error:
        fields = (
            EmbedField(name="\u274c Error", value=result.error, inline=False),
        )
        return EmbedData(
            title=EXPORT_TITLE,
            description="Export gagal, Darling.",
            color=PRIMARY,
            fields=fields,
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    if result.count == 0:
        return EmbedData(
            title=EXPORT_TITLE,
            description=EXPORT_EMPTY_DESC,
            color=PRIMARY,
            fields=(),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    fields = (
        EmbedField(name="\U0001f4ca Records", value=str(result.count), inline=True),
        EmbedField(name="\U0001f4cf Limit", value=str(limit), inline=True),
        EmbedField(name="\U0001f4e4 Delivery", value="DM (private)", inline=True),
        EmbedField(
            name="\U0001f512 Safety",
            value="Content length only — no raw text exposed.",
            inline=False,
        ),
    )
    return EmbedData(
        title=EXPORT_TITLE,
        description=EXPORT_OK_DESC,
        color=PRIMARY,
        fields=fields,
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


# ── DM Helper ───────────────────────────────────────────────────────────────


async def _send_dm_with_json(interaction: Any, records: list[dict[str, Any]]) -> bool:
    """Send memory export JSON to the user via DM.

    Args:
        interaction: The Discord interaction.
        records: Memory records to export.

    Returns:
        True if DM was sent successfully.
    """
    try:
        import importlib

        discord_mod = importlib.import_module("discord")
        user = getattr(interaction, "user", None)
        if user is None:
            return False

        dm_channel = await user.create_dm()
        json_str = json.dumps(records, indent=2, default=str)

        # Truncate if too long for a single message
        if len(json_str) > 1900:
            json_str = json_str[:1900] + "\n... (truncated)"

        file_obj = discord_mod.File(
            fp=__import__("io").BytesIO(json_str.encode("utf-8")),
            filename="guinevere_memory_export.json",
        )
        await dm_channel.send(
            content="\U0001f4e6 Guinevere Memory Export (metadata only)",
            file=file_obj,
        )
        return True
    except Exception:
        logger.exception("memory_export_dm_failed")
        return False


# ── Callback ────────────────────────────────────────────────────────────────


async def memory_export_callback(interaction: Any) -> None:
    """Handle a ``/memory-export`` interaction.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        limit_raw = get_option_value(interaction, "limit")
        limit = DEFAULT_LIMIT
        if limit_raw:
            try:
                limit = min(int(limit_raw), MAX_LIMIT)
            except (ValueError, TypeError):
                limit = DEFAULT_LIMIT

        bot = getattr(interaction, "client", None)
        if bot is None or not hasattr(bot, "get_session_factory"):
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Database session tidak available.",
            )
            return

        session_factory = bot.get_session_factory()
        if session_factory is None:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Database URL not configured.",
            )
            return

        result = await _fetch_memories(session_factory, limit)

        # Send DM if we have records
        if result.count > 0 and result.error is None:
            dm_ok = await _send_dm_with_json(interaction, result.records)
            if not dm_ok:
                await followup_send(
                    interaction,
                    content=(
                        "\u26a0\ufe0f DM gagal dikirim. Pastikan DM dari server "
                        "ini diaktifkan, Darling."
                    ),
                )
                return

        data = _build_embed_data(result, limit)
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("memory_export_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Memory export is temporarily unavailable.",
        )


__all__ = ["memory_export_callback"]
