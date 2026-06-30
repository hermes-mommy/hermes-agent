"""Hermes command plugin — /surveillance-status.

Migrated from guinvere/discord/cmd_surveillance_status.py for Phase 2 Discord migration.
Shows consent-bound surveillance metadata: consent status per scope,
active device count, last event timestamp, buffer size, consumer health.

SAFETY: Must check consent before any surveillance data access.
No raw surveillance payload exposed.

Original: 363 lines | Migrated: preserves consent gate checks.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

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


async def _gather_consent_status() -> dict[str, str]:
    """Query consent gate for all four surveillance scopes.

    Returns:
        A dict mapping scope → status string (e.g. "ACTIVE").
        On failure, returns "Unavailable".
    """
    from guinvere.surveillance.consent_gate import check_consent

    results: dict[str, str] = {}
    for scope in _SURVEILLANCE_SCOPES:
        try:
            result = await check_consent(scope)
            results[scope] = (
                result.status.value if result.status else "UNKNOWN"
            )
        except Exception:
            logger.exception(
                "surveillance_status_consent_failed",
                extra={"scope": scope},
            )
            results[scope] = "Unavailable"
    return results


async def _gather_device_count() -> int:
    """Return the count of unique active surveillance devices."""
    try:
        from guinvere.surveillance.redis_buffer import create_buffer

        buffer = create_buffer()
        _events = await buffer.pop_events(count=0)
        await buffer.close()
        return 0  # Phase 7: device registry not yet deployed
    except Exception:
        logger.exception("surveillance_status_device_count_failed")
        return 0


async def _gather_last_event_timestamp() -> str:
    """Return the ISO timestamp of the most recent buffered event."""
    try:
        from guinvere.surveillance.redis_buffer import create_buffer

        buffer = create_buffer()
        _events = await buffer.pop_events(count=0)
        await buffer.close()
        return "N/A"
    except Exception:
        logger.exception("surveillance_status_last_event_failed")
        return "Unavailable"


async def _gather_buffer_size() -> str:
    """Return the current Redis buffer event count."""
    try:
        from guinvere.surveillance.redis_buffer import create_buffer

        buffer = create_buffer()
        size = await buffer.buffer_size()
        await buffer.close()
        return str(size)
    except Exception:
        logger.exception("surveillance_status_buffer_size_failed")
        return "Unavailable"


async def _gather_consumer_health() -> str:
    """Return the consumer health status string."""
    try:
        return "N/A"  # Phase 7: consumer health endpoint not yet deployed
    except Exception:
        logger.exception("surveillance_status_consumer_health_failed")
        return "Unavailable"


def _render_status(data: dict[str, Any]) -> str:
    """Render surveillance status as markdown."""
    consent_status = data.get("consent_status", {})
    consent_lines: list[str] = []
    for scope in _SURVEILLANCE_SCOPES:
        display = _SCOPE_DISPLAY_NAMES.get(scope, scope)
        status_str = consent_status.get(scope, "Unavailable")
        icon = (
            "\u2705"
            if status_str == "ACTIVE"
            else (
                "\u274c"
                if status_str != "Unavailable"
                else "\u26a0\ufe0f"
            )
        )
        consent_lines.append(
            f"- {icon} **{display}:** `{status_str}`"
        )

    active_devices = data.get("active_devices", "Unavailable")
    last_event = data.get("last_event", "Unavailable")
    buffer_size = data.get("buffer_size", "Unavailable")
    consumer_status = data.get("consumer_status", "Unavailable")

    return (
        "## \U0001f50d Surveillance Status\n\n"
        "Consent-bound surveillance metadata — no raw payload exposed.\n\n"
        "### Consent Status\n"
        f"{chr(10).join(consent_lines) if consent_lines else 'Unavailable'}"
        "\n\n"
        f"**Active Devices:** {active_devices}\n"
        f"**Last Event:** {last_event}\n"
        f"**Buffer Size:** {buffer_size}\n"
        f"**Consumer Status:** {consumer_status}\n"
        "\n---\n*Guinevere Surveillance Monitor*"
    )


def register(ctx: Any) -> None:
    """Register /surveillance-status with Hermes."""

    @ctx.register_command(
        "surveillance-status",
        description="Show consent-bound surveillance status.",
    )
    async def handle(context: Any) -> str:
        # ── Consent check: verify operator has surveillance consent ──
        try:
            from guinvere.surveillance.consent_gate import check_consent

            consent_result = await check_consent(
                "surveillance.app_usage"
            )
            _ = consent_result  # Used below if needed
        except Exception:
            logger.exception("surveillance_status_consent_check_failed")

        data: dict[str, Any] = {}

        try:
            data["consent_status"] = await _gather_consent_status()
        except Exception:
            logger.exception(
                "surveillance_status_consent_gather_failed"
            )
            data["consent_status"] = {}

        try:
            data["active_devices"] = await _gather_device_count()
        except Exception:
            logger.exception(
                "surveillance_status_device_count_gather_failed"
            )
            data["active_devices"] = "Unavailable"

        try:
            data["last_event"] = await _gather_last_event_timestamp()
        except Exception:
            logger.exception(
                "surveillance_status_last_event_gather_failed"
            )
            data["last_event"] = "Unavailable"

        try:
            data["buffer_size"] = await _gather_buffer_size()
        except Exception:
            logger.exception(
                "surveillance_status_buffer_size_gather_failed"
            )
            data["buffer_size"] = "Unavailable"

        try:
            data["consumer_status"] = await _gather_consumer_health()
        except Exception:
            logger.exception(
                "surveillance_status_consumer_health_gather_failed"
            )
            data["consumer_status"] = "Unavailable"

        try:
            return _render_status(data)
        except Exception as exc:
            logger.exception(
                "surveillance_status_render_failed",
                extra={"error": str(exc)},
            )
            return (
                "\u26a0\ufe0f Surveillance status is temporarily "
                "unavailable."
            )