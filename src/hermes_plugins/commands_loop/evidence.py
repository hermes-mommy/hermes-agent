"""Hermes command plugin — /evidence.

Migrated from src/discord/cmd_evidence.py for Phase 2 Discord migration.
Lists evidence artifacts for a loop from LoopManager. Preserves the safety
requirement: metadata and artifact identifiers only — NO raw surveillance data.

Original: 160 lines | Migrated: preserves evidence fetch + safety boundary.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

WIB: timezone = timezone(timedelta(hours=7))


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


async def _get_evidence(loop_id: str) -> list[dict[str, Any]] | None:
    """Get evidence artifacts for a loop.

    Returns list of artifact metadata dicts, or None if loop not found.
    NOTE: Metadata only — NO raw surveillance data exposed.
    """
    try:
        from src.loops.manager import LoopManager

        manager = LoopManager()
        state = manager.active_loops.get(loop_id)
        if state is None:
            return None

        pipeline = manager.evidence_pipelines.get(loop_id)
        if pipeline is None:
            return []

        artifacts = getattr(state, "artifacts", {})
        if isinstance(artifacts, dict):
            return [
                {
                    "phase": str(k),
                    "name": str(v) if v else "unknown",
                }
                for k, v in artifacts.items()
            ]
        return []
    except Exception:
        logger.exception(
            "evidence_fetch_failed", extra={"loop_id": loop_id}
        )
        return None


def _render_evidence(
    loop_id: str,
    artifacts: list[dict[str, Any]] | None,
    now: datetime,
) -> str:
    """Render evidence artifacts as markdown."""
    ts_str = _format_wib_timestamp(now)

    if artifacts is None:
        return (
            f"## \u274c Loop Not Found\n\n"
            f"Loop `{loop_id}` tidak ditemukan.\n\n"
            f"*{ts_str} WIB*\n\n"
            f"**Loop ID:** `{loop_id}`"
        )

    if not artifacts:
        return (
            "## \U0001f4c1 Evidence Artifacts\n\n"
            "Tidak ada evidence artifacts untuk loop ini.\n\n"
            f"*{ts_str} WIB*\n\n"
            f"**Loop ID:** `{loop_id}`"
        )

    lines: list[str] = [
        "## \U0001f4c1 Evidence Artifacts",
        "",
        f"{len(artifacts)} artifact(s) recorded.",
        "",
        f"*{ts_str} WIB*",
        "",
        f"**Loop ID:** `{loop_id}`",
        "",
        "| Phase | Artifact |",
        "|---|---|",
    ]

    for artifact in artifacts[:15]:
        phase = artifact.get("phase", "?")
        name = artifact.get("name", "unknown")
        lines.append(f"| {phase} | `{name}` |")

    lines.append("")
    return "\n".join(lines)


def register(ctx: Any) -> None:
    """Register /evidence with Hermes."""

    @ctx.register_command(
        "evidence",
        description="Fetch evidence for a step or active work loop.",
    )
    async def handle(context: Any) -> str:
        try:
            # Support both "loop_id" and "step" option names
            loop_id = _get_arg(context, "loop_id")
            if not loop_id:
                loop_id = _get_arg(context, "step")
            if not loop_id:
                return (
                    "\u26a0\ufe0f Parameter `loop_id` diperlukan, "
                    "Darling."
                )

            artifacts = await _get_evidence(loop_id)
            now = datetime.now(tz=timezone.utc)
            return _render_evidence(loop_id, artifacts, now)

        except Exception as exc:
            logger.exception(
                "evidence_failed",
                extra={"error": str(exc)},
            )
            return (
                "\u26a0\ufe0f Evidence is temporarily unavailable."
            )