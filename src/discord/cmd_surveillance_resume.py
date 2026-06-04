"""Discord /surveillance-resume command handler (P7-020).

Resumes surveillance data collection that was previously paused via
``/surveillance-pause``. Consent state is unchanged — only the pause
flag is cleared. Creates an audit trail entry and notifies the operator.

Security:
- Faiz-only: ``is_faiz_interaction`` checks ``guild.owner_id == user.id``.
- Ephemeral: all responses are ephemeral.
- Consent-preserving: consent state is NOT modified during resume.
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
"""Global pause flag. Set to ``True`` by ``cmd_surveillance_pause``
and cleared to ``False`` by ``/surveillance-resume``. Ingestion pipelines
should check ``is_paused()`` before collecting new surveillance events."""


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


async def surveillance_resume_callback(interaction: Any) -> None:
    """Handle a ``/surveillance-resume`` interaction.

    Ensures Faiz-only access, defers ephemerally, clears the global
    pause flag (if currently paused), logs an audit entry, and sends
    a confirmation embed. If surveillance is already active, notifies
    the operator accordingly.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    global _paused

    # ── Faiz-only guard ──
    if not is_faiz_interaction(interaction):
        try:
            await interaction.response.send_message(
                "Not authorized.",
                ephemeral=True,
            )
        except Exception:
            logger.exception("surveillance_resume_denied_send_failed")
        return

    # ── Defer ──
    try:
        await interaction.response.defer(ephemeral=True)
    except Exception:
        logger.exception("surveillance_resume_defer_failed")
        return

    # ── Already-active check ──
    if not _paused:
        try:
            await interaction.followup.send(
                content="Surveillance is already active.",
                ephemeral=True,
            )
        except Exception:
            logger.exception("surveillance_resume_already_active_send_failed")
        return

    # ── Clear paused state ──
    _paused = False

    # ── Audit log ──
    logger.info(
        "surveillance_resume_executed",
        action="surveillance_resume",
        user=str(interaction.user),
    )

    # ── Build and send embed ──
    try:
        import importlib

        discord_mod = importlib.import_module("discord")

        embed = discord_mod.Embed(
            title="Surveillance Resumed",
            description="Data collection resumed.",
            colour=discord_mod.Colour(SURVEILLANCE),
        )
        embed.add_field(
            name="Consent",
            value="Unchanged \u2014 still enforced",
            inline=False,
        )
        embed.add_field(
            name="Ingestion Pipeline",
            value="Active",
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
        logger.exception("surveillance_resume_embed_send_failed")
        try:
            await interaction.followup.send(
                content="\u26a0\ufe0f Surveillance has been resumed, but the status embed could not be displayed.",
                ephemeral=True,
            )
        except Exception:
            logger.exception("surveillance_resume_fallback_send_failed")


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "is_faiz_interaction",
    "is_paused",
    "surveillance_resume_callback",
    "_set_paused_for_testing",
]