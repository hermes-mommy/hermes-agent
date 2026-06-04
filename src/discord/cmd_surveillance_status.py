"""Discord /surveillance-status command handler (P7-019).

Provides ``surveillance_status_callback`` for the ``/surveillance-status``
slash command. Gathers consent-bound surveillance metadata (consent status
per scope, active device count, last event timestamp, buffer size, consumer
health) and renders it as a teal Discord Embed. All data queries are
injectable via optional keyword arguments for testability.

Security:
- Faiz-only: ``is_faiz_interaction`` checks ``guild.owner_id == user.id``.
- Ephemeral: all responses are ephemeral.
- Metadata only: no raw surveillance payload exposed.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

import structlog

from .colors import SURVEILLANCE

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Surveillance scopes (must match consent_gate.VALID_SURVEILLANCE_SCOPES)
# ---------------------------------------------------------------------------

_SURVEILLANCE_SCOPES: tuple[str, ...] = (
    "surveillance.app_usage",
    "surveillance.location",
    "surveillance.notifications",
    "surveillance.clipboard",
)

_SCOPE_DISPLAY_NAMES: dict[str, str] = {
    "surveillance.app_usage": "App Usage",
    "surveillance.location": "Location",
    "surveillance.notifications": "Notifications",
    "surveillance.clipboard": "Clipboard",
}

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
# Embed builder
# ---------------------------------------------------------------------------


def _build_status_embed(data: dict[str, Any]) -> Any:
    """Build a ``discord.Embed`` from gathered status data.

    Args:
        data: A dict with keys matching surveillance status fields:
              ``consent_status``, ``active_devices``, ``last_event``,
              ``buffer_size``, ``consumer_status``.

    Returns:
        A ``discord.Embed`` instance.
    """
    import importlib

    discord_mod = importlib.import_module("discord")

    embed = discord_mod.Embed(
        title="Surveillance Status",
        description="Consent-bound surveillance metadata — no raw payload exposed.",
        colour=discord_mod.Colour(SURVEILLANCE),
    )

    # ── Consent Status ──
    consent_status = data.get("consent_status", {})
    consent_lines: list[str] = []
    for scope in _SURVEILLANCE_SCOPES:
        display = _SCOPE_DISPLAY_NAMES.get(scope, scope)
        status_str = consent_status.get(scope, "Unavailable")
        icon = "\u2705" if status_str == "ACTIVE" else "\u274c" if status_str != "Unavailable" else "\u26a0\ufe0f"
        consent_lines.append(f"{icon} **{display}:** `{status_str}`")
    embed.add_field(
        name="Consent Status",
        value="\n".join(consent_lines) if consent_lines else "Unavailable",
        inline=False,
    )

    # ── Active Devices ──
    active_devices = data.get("active_devices", "Unavailable")
    embed.add_field(
        name="Active Devices",
        value=str(active_devices),
        inline=True,
    )

    # ── Last Event ──
    last_event = data.get("last_event", "Unavailable")
    embed.add_field(
        name="Last Event",
        value=str(last_event),
        inline=True,
    )

    # ── Buffer Size ──
    buffer_size = data.get("buffer_size", "Unavailable")
    embed.add_field(
        name="Buffer Size",
        value=str(buffer_size),
        inline=True,
    )

    # ── Consumer Status ──
    consumer_status = data.get("consumer_status", "Unavailable")
    embed.add_field(
        name="Consumer Status",
        value=str(consumer_status),
        inline=False,
    )

    embed.set_footer(text="Guinevere Surveillance Monitor")
    return embed


# ---------------------------------------------------------------------------
# Data gatherers (production defaults)
# ---------------------------------------------------------------------------


async def _gather_consent_status(**kwargs: Any) -> dict[str, str]:
    """Query consent gate for all four surveillance scopes.

    Args:
        **kwargs: Reserved for future/test injection.

    Returns:
        A dict mapping scope → status string (e.g. ``"ACTIVE"``).
        On failure, returns ``"Unavailable"``.
    """
    from src.surveillance.consent_gate import check_consent

    results: dict[str, str] = {}
    for scope in _SURVEILLANCE_SCOPES:
        try:
            result = await check_consent(scope)
            results[scope] = result.status.value if result.status else "UNKNOWN"
        except Exception:
            logger.exception("surveillance_status_consent_failed", scope=scope)
            results[scope] = "Unavailable"
    return results


async def _gather_device_count(**kwargs: Any) -> int:
    """Return the count of unique active surveillance devices.

    Args:
        **kwargs: Reserved for future/test injection.

    Returns:
        Number of active devices, or 0 on failure.
    """
    try:
        from src.surveillance.redis_buffer import create_buffer

        buffer = create_buffer()
        # Device count: we count unique device_ids from buffered events.
        # This is a best-effort approximation; a dedicated device registry
        # may replace it in future phases.
        events = await buffer.pop_events(count=0)  # peek without consuming
        # A proper implementation would query a device set from Redis.
        # For now, return 0 until consumer/device registry is implemented.
        _ = events  # unused placeholder
        await buffer.close()
        return 0  # Phase 7: device registry not yet deployed
    except Exception:
        logger.exception("surveillance_status_device_count_failed")
        return 0


async def _gather_last_event_timestamp(**kwargs: Any) -> str:
    """Return the ISO timestamp of the most recent buffered event.

    Args:
        **kwargs: Reserved for future/test injection.

    Returns:
        ISO 8601 string or ``"N/A"`` on failure.
    """
    try:
        from src.surveillance.redis_buffer import create_buffer

        buffer = create_buffer()
        events = await buffer.pop_events(count=0)  # peek
        _ = events  # placeholder — proper impl in later phase
        await buffer.close()
        return "N/A"  # Phase 7: event timestamp query not yet deployed
    except Exception:
        logger.exception("surveillance_status_last_event_failed")
        return "Unavailable"


async def _gather_buffer_size(**kwargs: Any) -> str:
    """Return the current Redis buffer event count.

    Args:
        **kwargs: Reserved for future/test injection.

    Returns:
        Buffer size as string, e.g. ``"42"``. ``"Unavailable"`` on failure.
    """
    try:
        from src.surveillance.redis_buffer import create_buffer

        buffer = create_buffer()
        size = await buffer.buffer_size()
        await buffer.close()
        return str(size)
    except Exception:
        logger.exception("surveillance_status_buffer_size_failed")
        return "Unavailable"


async def _gather_consumer_health(**kwargs: Any) -> str:
    """Return the consumer health status string.

    Args:
        **kwargs: Reserved for future/test injection.

    Returns:
        Health status string, or ``"Unavailable"`` on failure.
    """
    try:
        # Consumer health: check if the consumer has processed events recently.
        # Proper implementation requires a Prometheus metric or health endpoint.
        # For Phase 7, placeholder.
        return "N/A"  # Phase 7: consumer health endpoint not yet deployed
    except Exception:
        logger.exception("surveillance_status_consumer_health_failed")
        return "Unavailable"


# ---------------------------------------------------------------------------
# Injectable callables (module-level for test monkeypatching)
# ---------------------------------------------------------------------------

_inject_consent_status: Callable[..., Awaitable[dict[str, str]]] = _gather_consent_status
_inject_device_count: Callable[..., Awaitable[int]] = _gather_device_count
_inject_last_event_timestamp: Callable[..., Awaitable[str]] = _gather_last_event_timestamp
_inject_buffer_size: Callable[..., Awaitable[str]] = _gather_buffer_size
_inject_consumer_health: Callable[..., Awaitable[str]] = _gather_consumer_health


# ---------------------------------------------------------------------------
# Callback
# ---------------------------------------------------------------------------


async def surveillance_status_callback(
    interaction: Any,
) -> None:
    """Handle a ``/surveillance-status`` interaction.

    Ensures Faiz-only access, defers ephemerally, gathers surveillance
    metadata, and sends an Embed as a followup.

    Data-gathering callables are injectable via module-level
    ``_inject_*`` variables for testability (monkeypatch in tests).

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    # ── Faiz-only guard ──
    if not is_faiz_interaction(interaction):
        try:
            await interaction.response.send_message(
                "This command is restricted.",
                ephemeral=True,
            )
        except Exception:
            logger.exception("surveillance_status_denied_send_failed")
        return

    # ── Defer ──
    try:
        await interaction.response.defer(ephemeral=True, thinking=True)
    except Exception:
        logger.exception("surveillance_status_defer_failed")
        return

    # ── Gather data ──
    data: dict[str, Any] = {}

    try:
        data["consent_status"] = await _inject_consent_status()
    except Exception:
        logger.exception("surveillance_status_consent_gather_failed")
        data["consent_status"] = {}

    try:
        data["active_devices"] = await _inject_device_count()
    except Exception:
        logger.exception("surveillance_status_device_count_gather_failed")
        data["active_devices"] = "Unavailable"

    try:
        data["last_event"] = await _inject_last_event_timestamp()
    except Exception:
        logger.exception("surveillance_status_last_event_gather_failed")
        data["last_event"] = "Unavailable"

    try:
        data["buffer_size"] = await _inject_buffer_size()
    except Exception:
        logger.exception("surveillance_status_buffer_size_gather_failed")
        data["buffer_size"] = "Unavailable"

    try:
        data["consumer_status"] = await _inject_consumer_health()
    except Exception:
        logger.exception("surveillance_status_consumer_health_gather_failed")
        data["consumer_status"] = "Unavailable"

    # ── Build and send embed ──
    try:
        embed = _build_status_embed(data)
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception:
        logger.exception("surveillance_status_embed_send_failed")
        try:
            await interaction.followup.send(
                content="\u26a0\ufe0f Surveillance status is temporarily unavailable.",
                ephemeral=True,
            )
        except Exception:
            logger.exception("surveillance_status_fallback_send_failed")


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "is_faiz_interaction",
    "surveillance_status_callback",
    "_build_status_embed",
]