"""Discord /surveillance-pause command handler (P7-020).

Pauses surveillance data collection while preserving consent state.
Creates an audit trail entry and notifies the operator via an
ephemeral Discord embed.

Security:
- Faiz-only: ``is_faiz_interaction`` checks ``guild.owner_id == user.id``.
- Ephemeral: all responses are ephemeral.
- Consent-preserving: consent state is NOT modified during pause.
- No raw surveillance payload exposed.
"""

from __future__ import annotations

from typing import Any

import structlog

from .colors import SURVEILLANCE

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Module-level pause state
# ---------------------------------------------------------------------------

_paused: bool = False
"""Global pause flag. Set to ``True`` when surveillance data collection
is paused via ``/surveillance-pause``. Ingestion pipelines should check
``is_paused()`` before collecting new surveillance events."""


def is_paused() -> bool:
    """Return the current pause state for external consumers.

    Returns:
        ``True`` if surveillance collection is paused, ``False`` otherwise.
    """
    return _paused


def _set_paused_for_testing(val: bool) -> None:
    """Inject a pause state value for testing purposes.

    Args:
        val: The boolean value to set ``_paused`` to.
    """
    global _paused
    _paused = val


# ---------------------------------------------------------------------------
# Faiz-only check
# ---------------------------------------------------------------------------


def is_faiz_interaction(interaction: Any) -> bool:
    """Return True only if the interaction user is the guild owner.

    Args:
        interaction: A ``discord.Interaction`` object.

    Returns:
        ``True`` if ``interaction.guild.owner_id == interaction.user.id``.
    """
    guild = getattr(interaction, "guild", None)
    user = getattr(interaction, "user", None)
    if guild is None or user is None:
        return False
    owner_id = getattr(guild, "owner_id", None)
    user_id = getattr(user, "id", None)
    return isinstance(owner_id, int) and isinstance(user_id, int) and owner_id == user_id


# ---------------------------------------------------------------------------
# Callback
# ---------------------------------------------------------------------------


async def surveillance_pause_callback(interaction: Any) -> None:
    """Handle a ``/surveillance-pause`` interaction.

    Ensures Faiz-only access, defers ephemerally, sets the global
    pause flag, logs an audit entry, and sends a confirmation embed.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    # ── Faiz-only guard ──
    if not is_faiz_interaction(interaction):
        try:
            await interaction.response.send_message(
                "Not authorized.",
                ephemeral=True,
            )
        except Exception:
            logger.exception("surveillance_pause_denied_send_failed")
        return

    # ── Defer ──
    try:
        await interaction.response.defer(ephemeral=True)
    except Exception:
        logger.exception("surveillance_pause_defer_failed")
        return

    # ── Set paused state ──
    global _paused
    _paused = True

    # ── Invalidate consent cache (best-effort, non-blocking) ──
    try:
        import asyncio

        from src.surveillance.consent_gate import (
            VALID_SURVEILLANCE_SCOPES,
            invalidate_cache,
        )

        await asyncio.gather(
            *(invalidate_cache(scope) for scope in VALID_SURVEILLANCE_SCOPES),
            return_exceptions=True,
        )
    except Exception:
        logger.exception("surveillance_pause_cache_invalidation_failed")

    # ── Audit log ──
    logger.info(
        "surveillance_pause_executed",
        action="surveillance_pause",
        user=str(interaction.user),
    )

    # ── Build and send embed ──
    try:
        import importlib

        discord_mod = importlib.import_module("discord")

        embed = discord_mod.Embed(
            title="Surveillance Paused",
            description="Data collection paused. Consent state preserved.",
            colour=discord_mod.Colour(SURVEILLANCE),
        )
        embed.add_field(
            name="Consent",
            value="Unchanged \u2014 still enforced",
            inline=False,
        )
        embed.add_field(
            name="Ingestion Pipeline",
            value="Paused",
            inline=True,
        )
        embed.add_field(
            name="Safe Mode",
            value="Confrontation blocking active",
            inline=True,
        )
        embed.set_footer(text="Guinevere Surveillance Monitor")

        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception:
        logger.exception("surveillance_pause_embed_send_failed")
        try:
            await interaction.followup.send(
                content="\u26a0\ufe0f Surveillance has been paused, but the status embed could not be displayed.",
                ephemeral=True,
            )
        except Exception:
            logger.exception("surveillance_pause_fallback_send_failed")


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "is_faiz_interaction",
    "is_paused",
    "surveillance_pause_callback",
    "_set_paused_for_testing",
]