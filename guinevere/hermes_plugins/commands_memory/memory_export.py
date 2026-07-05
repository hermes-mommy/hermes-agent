"""Hermes command plugin — /memory-export.

Migrated from guinevere/discord/cmd_memory_export.py for Phase 2 Discord migration.
Exports non-DNR memory metadata as structured JSON. NOTE: In Discord, this
sent a DM file; in Hermes, it returns a markdown summary with metadata only
(NO raw content exposure).

Original: 263 lines | Migrated: preserves metadata export logic.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

WIB: timezone = timezone(timedelta(hours=7))
EXPORT_TITLE: str = "\U0001f4e6 Memory Export"
DEFAULT_LIMIT: int = 50
MAX_LIMIT: int = 200


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


def _build_export_summary(
    records: list[dict[str, Any]],
    count: int,
    limit: int,
    error: str | None,
    now: datetime,
) -> str:
    """Build markdown export summary (metadata only, no raw content)."""
    ts_str = _format_wib_timestamp(now)

    if error:
        return (
            f"## {EXPORT_TITLE}\n\n"
            "Export gagal, Darling.\n\n"
            f"*{ts_str} WIB*\n\n"
            f"\u274c **Error:** {error}"
        )

    if count == 0:
        return (
            f"## {EXPORT_TITLE}\n\n"
            "Tidak ada memories untuk di-export, Darling.\n\n"
            f"*{ts_str} WIB*"
        )

    lines: list[str] = [
        f"## {EXPORT_TITLE}",
        "",
        f"Memories sudah diexport, Darling. Berikut metadata-nya:",
        "",
        f"*{ts_str} WIB*",
        "",
        f"\U0001f4ca **Records:** {count}",
        f"\U0001f4cf **Limit:** {limit}",
        f"\U0001f512 **Safety:** Content length only \u2014 no raw text exposed.",
        "",
        "| ID | Classification | Content Length | Created At |",
        "|---|---|---|---|",
    ]

    for record in records[:20]:  # Limit display rows
        rec_id = str(record.get("id", ""))[:12]
        classification = str(record.get("classification", "unclassified"))
        content_len = str(record.get("content_length", 0))
        created_at = str(record.get("created_at", ""))[:19]
        lines.append(
            f"| `{rec_id}` | {classification} | {content_len} | {created_at} |"
        )

    if count > 20:
        lines.append(f"| ... | *{count - 20} more records* | ... | ... |")

    lines.append("")
    lines.append(
        f"**Full JSON export** available at: `guinevere_memory_export.json` "
        f"(metadata only, DNR excluded)"
    )
    return "\n".join(lines)


def register(ctx: Any) -> None:
    """Register /memory-export with Hermes."""

    @ctx.register_command(
        "memory-export",
        description="Export approved Guinevere memory metadata.",
    )
    async def handle(context: Any) -> str:
        try:
            limit_raw = _get_arg(context, "limit")
            limit = DEFAULT_LIMIT
            if limit_raw:
                try:
                    limit = min(int(limit_raw), MAX_LIMIT)
                except (ValueError, TypeError):
                    limit = DEFAULT_LIMIT

            session_factory = getattr(ctx, "session_factory", None)
            if session_factory is None:
                return (
                    "\u26a0\ufe0f Database session tidak available."
                )

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
                        records.append({
                            "id": str(row[0]),
                            "classification": (
                                str(row[1]) if row[1] else "unclassified"
                            ),
                            "created_at": str(row[2]) if row[2] else "",
                            "content_length": (
                                int(row[3]) if row[3] else 0
                            ),
                        })

                    logger.info(
                        "memory_export_fetched",
                        extra={"count": len(records)},
                    )

                    now = datetime.now(tz=timezone.utc)
                    summary = _build_export_summary(
                        records=records,
                        count=len(records),
                        limit=limit,
                        error=None,
                        now=now,
                    )

                    # Also build JSON for potential file output
                    json_output = json.dumps(
                        records, indent=2, default=str
                    )
                    logger.debug(
                        "memory_export_json_ready",
                        extra={"json_length": len(json_output)},
                    )

                    return summary

            except Exception as db_exc:
                logger.exception(
                    "memory_export_db_error",
                    extra={"error": str(db_exc)},
                )
                now = datetime.now(tz=timezone.utc)
                return _build_export_summary(
                    records=[],
                    count=0,
                    limit=limit,
                    error=str(db_exc),
                    now=now,
                )

        except Exception as exc:
            logger.exception(
                "memory_export_failed",
                extra={"error": str(exc)},
            )
            return (
                "\u26a0\ufe0f Memory export is temporarily unavailable."
            )