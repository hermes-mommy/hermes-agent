"""Discord /evidence command implementation for Guinevere (RG-014).

Lists evidence artifacts for a loop.

SAFETY: Must NOT expose raw surveillance data.  Only metadata and
artifact identifiers are shown.

Usage:
    /evidence loop_id:str
"""

from __future__ import annotations

from typing import Any

import structlog

from .colors import PRIMARY
from ._embed_helpers import (
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

TITLE: str = "\U0001f4c1 Evidence Artifacts"
TITLE_FAIL: str = "\u274c Loop Not Found"
DESC_EMPTY: str = "Tidak ada evidence artifacts untuk loop ini."
FOOTER_ICON: str = "\U0001f4c1 Evidence"


async def _get_evidence(loop_id: str) -> list[dict[str, Any]] | None:
    """Get evidence artifacts for a loop.

    Returns list of artifact metadata dicts, or None if loop not found.
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

        # Get recorded artifacts from state machine
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
        logger.exception("evidence_fetch_failed", loop_id=loop_id)
        return None


def _build_embed_data(
    loop_id: str, artifacts: list[dict[str, Any]] | None
) -> EmbedData:
    """Build embed from evidence data."""
    ts = now_wib_str()

    if artifacts is None:
        return EmbedData(
            title=TITLE_FAIL,
            description=f"Loop ``{loop_id}`` tidak ditemukan.",
            color=PRIMARY,
            fields=(
                EmbedField(name="Loop ID", value=f"`{loop_id}`", inline=True),
            ),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    if not artifacts:
        return EmbedData(
            title=TITLE,
            description=DESC_EMPTY,
            color=PRIMARY,
            fields=(
                EmbedField(name="Loop ID", value=f"`{loop_id}`", inline=True),
            ),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    fields: list[EmbedField] = [
        EmbedField(name="Loop ID", value=f"`{loop_id}`", inline=True),
    ]
    for artifact in artifacts[:15]:  # Limit to avoid embed overflow
        phase = artifact.get("phase", "?")
        name = artifact.get("name", "unknown")
        fields.append(
            EmbedField(
                name=f"Phase: {phase}",
                value=f"`{name}`",
                inline=True,
            )
        )

    return EmbedData(
        title=TITLE,
        description=f"{len(artifacts)} artifact(s) recorded.",
        color=PRIMARY,
        fields=tuple(fields),
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


async def evidence_callback(interaction: Any) -> None:
    """Handle a ``/evidence`` interaction."""
    from .commands import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        # Support both "loop_id" and "step" option names for compatibility
        loop_id = get_option_value(interaction, "loop_id")
        if not loop_id:
            loop_id = get_option_value(interaction, "step")
        if not loop_id:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Parameter ``loop_id`` diperlukan, Darling.",
            )
            return

        artifacts = await _get_evidence(loop_id)
        data = _build_embed_data(loop_id, artifacts)
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("evidence_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Evidence is temporarily unavailable.",
        )


__all__ = ["evidence_callback"]
