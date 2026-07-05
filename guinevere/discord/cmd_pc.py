"""Discord /pc command handler (P15-010).

Provides ``pc_callback`` for the ``/pc`` slash command. Surfaces current
Windows daemon context as available from implementation seams. At minimum
designs a sensible status payload surface for:

- connection state
- active window / app if available
- project / branch / session type if available
- idle state if available

If live status backing is not fully available yet, implements graceful
status reporting that states what is unavailable rather than faking data.

Security:
- Faiz-only: ``is_faiz_interaction`` checks ``guild.owner_id == user.id``.
- Ephemeral: all responses are ephemeral.
- Metadata only: no raw surveillance payload exposed.

Usage:
    # Registered via self.tree.command() in _entrypoint.py setup_hook.
    # Data gathering is injectable for testability.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Final

import structlog

from ._embed_utils import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    format_wib_timestamp,
    now_wib_str,
    send_denied,
    to_discord_embed,
)
from ._auth_guard import is_faiz_interaction
from .colors import PRIMARY

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Timezone
# ---------------------------------------------------------------------------

WIB: Final[timezone] = timezone(timedelta(hours=7))
"""Asia/Bangkok/WIB timezone offset (+07:00)."""

# ---------------------------------------------------------------------------
# Degraded placeholders (P15-010 — live status not yet deployed)
# ---------------------------------------------------------------------------

_UNAVAILABLE: Final[str] = "\u26a0\ufe0f Unavailable"
_NO_LIVE_CONNECTION: Final[str] = (
    "\u26a0\ufe0f Windows daemon WebSocket not yet deployed (P15-007)"
)
_NO_ACTIVE_WINDOW: Final[str] = (
    "\u26a0\ufe0f Active window tracking not yet deployed"
)
_NO_PROJECT_INFO: Final[str] = (
    "\u26a0\ufe0f Project / branch info not yet deployed"
)
_NO_IDLE_STATE: Final[str] = "\u26a0\ufe0f Idle state tracking not yet deployed"

# ---------------------------------------------------------------------------
# Consistent header constants
# ---------------------------------------------------------------------------

_TITLE: Final[str] = "\U0001f4bb Windows PC Status"
_DESCRIPTION: Final[str] = (
    "Windows daemon status — per consent boundary. "
    "Unsubscribed fields report graceful degradation."
)
_FOOTER_TEXT: Final[str] = "Guinevere de Baroque"
_FOOTER_ICON: Final[str] = "\u2699\ufe0f PC"

# ---------------------------------------------------------------------------
# Injectable data gatherers (module-level for test monkeypatching)
# ---------------------------------------------------------------------------


async def _gather_connection_state(**kwargs: Any) -> str:
    """Return Windows daemon connection state string.

    Reads the in-memory ``ConnectionManager.active_connections`` map from
    ``guinevere.surveillance.windows_ws``. If the device_id is currently
    connected the response is formatted as
    ``"\u2705 Connected (device_id: <id>)"``; otherwise it reports
    ``"\u274c Disconnected"``.

    Args:
        **kwargs: Reserved for future/test injection.

    Returns:
        Connection state string, or degraded placeholder on import error.
    """
    device_id: str = "windows-laptop-01"
    try:
        from guinevere.surveillance.windows_ws import manager as connection_manager
    except Exception:
        logger.exception("pc_connection_state_import_failed")
        return _UNAVAILABLE

    try:
        if device_id in connection_manager.active_connections:
            return f"\u2705 Connected (device_id: {device_id})"
        return "\u274c Disconnected"
    except Exception:
        logger.exception("pc_connection_state_lookup_failed")
        return _UNAVAILABLE


async def _gather_active_window(**kwargs: Any) -> str:
    """Return the active window / app name if available.

    Pulls the most recent Windows event via
    :func:`guinevere.surveillance.windows_status.get_latest_windows_status` and
    returns the ``title`` field. Falls back to a degraded placeholder
    when no event is available or the DB lookup fails.

    Args:
        **kwargs: Reserved for future/test injection.

    Returns:
        Active window string, or degraded placeholder.
    """
    try:
        from guinevere.surveillance.windows_status import get_latest_windows_status

        status = await get_latest_windows_status()
    except Exception:
        logger.exception("pc_active_window_status_query_failed")
        return _NO_ACTIVE_WINDOW

    if not status:
        return _NO_ACTIVE_WINDOW

    title = status.get("title")
    if not title:
        return _NO_ACTIVE_WINDOW
    return str(title)


async def _gather_project_info(**kwargs: Any) -> str:
    """Return project / branch / session info if available.

    Reads the latest Windows event and formats the ``project`` and
    ``branch`` fields as ``"<project>:<branch>"``. If both are missing
    the response is ``"No git context"``; otherwise only the present
    fields are joined with a colon.

    Args:
        **kwargs: Reserved for future/test injection.

    Returns:
        Project info string, or ``"No git context"`` placeholder.
    """
    try:
        from guinevere.surveillance.windows_status import get_latest_windows_status

        status = await get_latest_windows_status()
    except Exception:
        logger.exception("pc_project_info_status_query_failed")
        return "No git context"

    if not status:
        return "No git context"

    project = status.get("project")
    branch = status.get("branch")

    if not project and not branch:
        return "No git context"
    if project and branch:
        return f"{project}:{branch}"
    if project:
        return str(project)
    return str(branch)


async def _gather_idle_state(**kwargs: Any) -> str:
    """Return idle state if available.

    Reads the latest Windows event and surfaces the ``state`` field
    together with ``idle_seconds`` (when present) in the format
    ``"<state> (<idle_seconds>s)"``. If no state is present the response
    is the standard degraded placeholder.

    Args:
        **kwargs: Reserved for future/test injection.

    Returns:
        Idle state string, or degraded placeholder.
    """
    try:
        from guinevere.surveillance.windows_status import get_latest_windows_status

        status = await get_latest_windows_status()
    except Exception:
        logger.exception("pc_idle_state_status_query_failed")
        return _NO_IDLE_STATE

    if not status:
        return _NO_IDLE_STATE

    state = status.get("state")
    if not state:
        return _NO_IDLE_STATE

    idle_seconds = status.get("idle_seconds")
    if isinstance(idle_seconds, int):
        return f"{state} ({idle_seconds}s)"
    return str(state)


async def _gather_consent_state(**kwargs: Any) -> str:
    """Return consent status for the Windows surveillance scope.

    Queries the consent gate for ``surveillance.app_usage`` which is the
    default scope for Windows daemon events.

    Args:
        **kwargs: Reserved for future/test injection.

    Returns:
        Consent status string, or ``"Unavailable"`` on failure.
    """
    try:
        from guinevere.surveillance.consent_gate import check_consent

        result = await check_consent("surveillance.app_usage")
        status_val = result.status.value if result.status else "UNKNOWN"
        allowed_str = "Yes" if result.allowed else "No"
        return f"`{status_val}` (allowed: {allowed_str})"
    except Exception:
        logger.exception("pc_consent_check_failed")
        return _UNAVAILABLE


async def _gather_dropped_events(**kwargs: Any) -> str:
    """Return the count of dropped Windows consent-gate events.

    Reads the internal fallback counter from windows_consent. This counter
    increments every time the consent gate drops an event (fail-closed).

    Args:
        **kwargs: Reserved for future/test injection.

    Returns:
        Dropped event count as string, or ``"Unavailable"`` on failure.
    """
    try:
        from guinevere.surveillance.windows_consent import get_dropped_event_count

        count = get_dropped_event_count()
        return str(count)
    except Exception:
        logger.exception("pc_dropped_events_query_failed")
        return _UNAVAILABLE


# ---------------------------------------------------------------------------
# Module-level overrides (for tests)
# ---------------------------------------------------------------------------

_inject_connection_state: Callable[..., Awaitable[str]] = _gather_connection_state
_inject_active_window: Callable[..., Awaitable[str]] = _gather_active_window
_inject_project_info: Callable[..., Awaitable[str]] = _gather_project_info
_inject_idle_state: Callable[..., Awaitable[str]] = _gather_idle_state
_inject_consent_state: Callable[..., Awaitable[str]] = _gather_consent_state
_inject_dropped_events: Callable[..., Awaitable[str]] = _gather_dropped_events


# ---------------------------------------------------------------------------
# Embed builder
# ---------------------------------------------------------------------------


def build_pc_embed(
    connection_state: str,
    active_window: str,
    project_info: str,
    idle_state: str,
    consent_state: str,
    dropped_events: str,
    timestamp_str: str | None = None,
) -> EmbedData:
    """Build an ``EmbedData`` for the ``/pc`` status command.

    Args:
        connection_state: Windows daemon connection status.
        active_window: Active window / app name.
        project_info: Project / branch / session info.
        idle_state: Idle state indicator.
        consent_state: Consent gate status for Windows scope.
        dropped_events: Count of consent-gate dropped events.
        timestamp_str: Override timestamp for determinism.

    Returns:
        A fully populated ``EmbedData``.
    """
    ts = timestamp_str if timestamp_str is not None else now_wib_str()

    fields = (
        EmbedField("Connection", connection_state, inline=False),
        EmbedField("Active Window", active_window, inline=True),
        EmbedField("Project / Branch", project_info, inline=True),
        EmbedField("Idle State", idle_state, inline=True),
        EmbedField("Consent (app_usage)", consent_state, inline=False),
        EmbedField("Dropped Events", dropped_events, inline=True),
    )

    return EmbedData(
        title=_TITLE,
        description=_DESCRIPTION,
        color=PRIMARY,
        fields=fields,
        footer_text=_FOOTER_TEXT,
        footer_icon=_FOOTER_ICON,
        timestamp=ts,
    )


# ---------------------------------------------------------------------------
# Callback
# ---------------------------------------------------------------------------


async def pc_callback(
    interaction: Any,
    *,
    _get_connection_state: Callable[..., Awaitable[str]] | None = None,
    _get_active_window: Callable[..., Awaitable[str]] | None = None,
    _get_project_info: Callable[..., Awaitable[str]] | None = None,
    _get_idle_state: Callable[..., Awaitable[str]] | None = None,
    _get_consent_state: Callable[..., Awaitable[str]] | None = None,
    _get_dropped_events: Callable[..., Awaitable[str]] | None = None,
) -> None:
    """Handle a ``/pc`` interaction.

    Enforces Faiz-only access via ``is_faiz_interaction``, defers
    ephemerally, gathers Windows daemon status, and sends an Embed as a
    followup. If any gathering step fails, a graceful degraded placeholder
    is used rather than crashing.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
        _get_connection_state: Optional connection-state gather override.
        _get_active_window: Optional active-window gather override.
        _get_project_info: Optional project-info gather override.
        _get_idle_state: Optional idle-state gather override.
        _get_consent_state: Optional consent-state gather override.
        _get_dropped_events: Optional dropped-events gather override.
    """
    # ── Faiz-only guard ──
    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    # ── Defer ephemeral ──
    await defer_ephemeral(interaction)

    # ── Gather data with graceful degradation ──
    connection_getter = _get_connection_state or _inject_connection_state
    window_getter = _get_active_window or _inject_active_window
    project_getter = _get_project_info or _inject_project_info
    idle_getter = _get_idle_state or _inject_idle_state
    consent_getter = _get_consent_state or _inject_consent_state
    dropped_getter = _get_dropped_events or _inject_dropped_events

    data: dict[str, str] = {}

    try:
        data["connection_state"] = await connection_getter()
    except Exception:
        logger.exception("pc_connection_state_gather_failed")
        data["connection_state"] = _UNAVAILABLE

    try:
        data["active_window"] = await window_getter()
    except Exception:
        logger.exception("pc_active_window_gather_failed")
        data["active_window"] = _UNAVAILABLE

    try:
        data["project_info"] = await project_getter()
    except Exception:
        logger.exception("pc_project_info_gather_failed")
        data["project_info"] = _UNAVAILABLE

    try:
        data["idle_state"] = await idle_getter()
    except Exception:
        logger.exception("pc_idle_state_gather_failed")
        data["idle_state"] = _UNAVAILABLE

    try:
        data["consent_state"] = await consent_getter()
    except Exception:
        logger.exception("pc_consent_state_gather_failed")
        data["consent_state"] = _UNAVAILABLE

    try:
        data["dropped_events"] = await dropped_getter()
    except Exception:
        logger.exception("pc_dropped_events_gather_failed")
        data["dropped_events"] = _UNAVAILABLE

    # ── Build and send embed ──
    try:
        embed_data = build_pc_embed(
            connection_state=data["connection_state"],
            active_window=data["active_window"],
            project_info=data["project_info"],
            idle_state=data["idle_state"],
            consent_state=data["consent_state"],
            dropped_events=data["dropped_events"],
        )
        embed = to_discord_embed(embed_data)
        await followup_send(interaction, embed=embed)
    except Exception:
        logger.exception("pc_embed_send_failed")
        try:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Windows PC status is temporarily unavailable.",
            )
        except Exception:
            logger.exception("pc_fallback_send_failed")


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "pc_callback",
    "build_pc_embed",
]
